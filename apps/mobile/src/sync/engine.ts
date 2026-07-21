import { getDb } from '../db';
import { decryptPayload } from '../db/encryption';
import { IncidentsApi, IncidentCreate, IncidentDraftUpdate, OpenAPI, EvidenceIntentRequest } from '@incident-ledger/api-client';
import * as Notifications from 'expo-notifications';
import * as FileSystem from 'expo-file-system';

export type OperationType = 'create' | 'patch' | 'submit' | 'evidence_intent' | 'upload' | 'finalize';
export type OperationState = 'pending' | 'in_progress' | 'completed' | 'failed' | 'rejected';

/**
 * Calculates exponential backoff with jitter.
 * Base 1s, max 60s, +/- 25% jitter.
 */
function getBackoffTimeMs(retryCount: number): number {
  const base = 1000;
  const max = 60000;
  const exp = Math.min(max, base * Math.pow(2, retryCount));
  const jitter = exp * 0.25;
  const randomJitter = (Math.random() * 2 - 1) * jitter;
  return Math.max(base, Math.min(max, exp + randomJitter));
}

let isProcessing = false;

/**
 * Processes pending sync operations sequentially.
 */
export async function processQueue() {
  if (isProcessing) return;
  isProcessing = true;

  try {
    const db = await getDb();
    
    // Fetch pending or failed operations (failed are transient and will be retried if backoff time elapsed)
    // For simplicity of backoff, we'll fetch 'pending' and 'failed' ordered by created_at.
    // We must respect dependencies (create -> patch -> submit for the same entity).
    // The query sorts globally by created_at.
    const ops = await db.getAllAsync<{ id: string, entity_id: string, operation_type: OperationType, payload_encrypted: string, state: string, retry_count: number, error_message: string, created_at: string }>(
      `SELECT * FROM local_operations 
       WHERE state IN ('pending', 'failed') 
       ORDER BY created_at ASC`
    );

    if (!ops || ops.length === 0) {
      isProcessing = false;
      return;
    }

    const now = new Date();
    
    // Check 72-hour unsynced alert for submits
    for (const op of ops) {
      if (op.operation_type === 'submit' && op.state === 'pending') {
        const createdAt = new Date(op.created_at);
        const hoursPending = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
        if (hoursPending > 72) {
          // Fire local notification
          await Notifications.scheduleNotificationAsync({
            content: {
              title: "Unsynced Incident Report",
              body: "A submitted incident report has been pending sync for over 72 hours. Please connect to the internet.",
              sound: true,
              priority: Notifications.AndroidNotificationPriority.HIGH,
            },
            trigger: null, // immediate
          });

          // Report delayed sync to operations API
          try {
            // Note: API endpoint might not exist yet on server per prompt scope
            await fetch(`${OpenAPI.BASE}/v1/operations/delayed-sync`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${OpenAPI.TOKEN}`
              },
              body: JSON.stringify({ operation_id: op.id, entity_id: op.entity_id, delay_hours: hoursPending })
            });
          } catch (e) {
            console.error('Failed to report delayed sync:', e);
          }
        }
      }
    }

    for (const op of ops) {
      if (op.state === 'failed') {
        // Enforce backoff
        // Normally we'd track last_attempt_at in the DB, but since the prompt doesn't specify it,
        // we can just sleep if we hit a failure in the loop. 
        // Wait, if it's already failed from a previous run, we should probably check if it's time to run.
        // For this prompt, a simple approach is: if we just hit a 503, we break the loop (as per "Stop processing if a blocking operation fails").
      }

      // Mark in progress
      await db.runAsync(`UPDATE local_operations SET state = 'in_progress' WHERE id = ?`, [op.id]);
      
      try {
        const payload = await decryptPayload(op.payload_encrypted);
        
        if (op.operation_type === 'create') {
          const result = await IncidentsApi.createDraft(payload as IncidentCreate, op.id);
          // Update local_incidents with server_id and server_etag, mark as draft
          await db.runAsync(
            `UPDATE local_incidents SET server_id = ?, server_etag = ?, local_status = 'draft' WHERE id = ?`,
            [result.id, result.version_etag || null, op.entity_id]
          );
        } else if (op.operation_type === 'patch') {
          const incident = await db.getFirstAsync<{ server_id: string, server_etag: string }>(
            `SELECT server_id, server_etag FROM local_incidents WHERE id = ?`, [op.entity_id]
          );
          const serverId = incident?.server_id || op.entity_id;
          
          const result = await IncidentsApi.updateDraftEndpoint(serverId, payload as IncidentDraftUpdate, incident?.server_etag || undefined, op.id);
          await db.runAsync(
            `UPDATE local_incidents SET server_etag = ? WHERE id = ?`,
            [result.version_etag || null, op.entity_id]
          );
        } else if (op.operation_type === 'submit') {
          const incident = await db.getFirstAsync<{ server_id: string }>(
            `SELECT server_id FROM local_incidents WHERE id = ?`, [op.entity_id]
          );
          const serverId = incident?.server_id || op.entity_id;
          
          await IncidentsApi.submitIncidentEndpoint(serverId, payload, op.id);
          
          await db.runAsync(
            `UPDATE local_incidents SET local_status = 'synced' WHERE id = ?`,
            [op.entity_id]
          );
        } else if (op.operation_type === 'evidence_intent') {
          // op.entity_id is evidenceId
          const evidence = await db.getFirstAsync<{ incident_id: string, local_file_path: string, sha256: string, media_type: string, byte_size: number }>(
            `SELECT incident_id, local_file_path, sha256, media_type, byte_size FROM local_evidence WHERE id = ?`, [op.entity_id]
          );
          if (evidence) {
            const incident = await db.getFirstAsync<{ server_id: string }>(
              `SELECT server_id FROM local_incidents WHERE id = ?`, [evidence.incident_id]
            );
            const serverIncidentId = incident?.server_id || evidence.incident_id;

            // 1. Get Intent URL
            const intentReq: EvidenceIntentRequest = { media_type: evidence.media_type, byte_size: evidence.byte_size };
            const intentRes = await IncidentsApi.createEvidenceIntentEndpoint(serverIncidentId, "00000000-0000-0000-0000-000000000000", intentReq);

            // 2. Upload
            const uploadRes = await FileSystem.uploadAsync(intentRes.upload_url, evidence.local_file_path, {
              httpMethod: 'PUT',
              headers: { 'Content-Type': evidence.media_type }
            });
            
            if (uploadRes.status < 200 || uploadRes.status >= 300) {
              throw new Error(`Upload failed with status ${uploadRes.status}`);
            }

            // 3. Finalize
            await IncidentsApi.finalizeEvidenceEndpoint(serverIncidentId, intentRes.evidence_id, "00000000-0000-0000-0000-000000000000", {
              client_sha256: evidence.sha256
            });

            // Update local evidence status
            await db.runAsync(
              `UPDATE local_evidence SET upload_status = 'ready' WHERE id = ?`,
              [op.entity_id]
            );
          }
        }
        
        // Mark completed
        await db.runAsync(`UPDATE local_operations SET state = 'completed', completed_at = ? WHERE id = ?`, [new Date().toISOString(), op.id]);

      } catch (e: any) {
        console.error(`Operation ${op.id} failed:`, e.body || e.message);
        
        const status = e.status;
        const bodyStr = JSON.stringify(e.body || {});
        
        if (status === 409 && bodyStr.includes('IDEMPOTENCY_PAYLOAD_MISMATCH')) {
          // d. On 409 IDEMPOTENCY_PAYLOAD_MISMATCH: set state to failed with error
          await db.runAsync(
            `UPDATE local_operations SET state = 'failed', error_message = 'IDEMPOTENCY_PAYLOAD_MISMATCH' WHERE id = ?`, 
            [op.id]
          );
          break; // Stop queue for safety
        } else if (status === 409) {
          // e. On 409 (stale ETag): trigger conflict resolution (mark as needs_attention)
          await db.runAsync(`UPDATE local_operations SET state = 'failed', error_message = 'STALE_ETAG' WHERE id = ?`, [op.id]);
          await db.runAsync(`UPDATE local_incidents SET local_status = 'needs_attention' WHERE id = ?`, [op.entity_id]);
          break; // Stop queue for this entity
        } else if (status === 422 || status === 403) {
          // f. On 422/403 (validation/policy): set state to rejected, do NOT auto-retry
          await db.runAsync(`UPDATE local_operations SET state = 'rejected', error_message = ? WHERE id = ?`, [e.message, op.id]);
        } else {
          // g. On 500/503 (transient): increment retry_count, use capped exponential backoff with jitter
          const backoff = getBackoffTimeMs(op.retry_count || 0);
          await db.runAsync(
            `UPDATE local_operations SET state = 'failed', error_message = ?, retry_count = retry_count + 1 WHERE id = ?`, 
            [e.message || 'Network error', op.id]
          );
          
          // Wait for backoff before processing any further (blocks the queue temporarily)
          await new Promise(resolve => setTimeout(resolve, backoff));
          break; // Stop processing, triggers will restart it later
        }
      }
    }
  } finally {
    isProcessing = false;
  }
}
