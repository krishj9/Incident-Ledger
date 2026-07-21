import * as Crypto from 'expo-crypto';
import { getDb, saveLocalDraft } from './index';
import { encryptPayload, decryptPayload } from './encryption';
import * as Network from 'expo-network';
import { IncidentsApi, IncidentCreate, IncidentDraftUpdate } from '@incident-ledger/api-client';

export type OperationType = 'create' | 'patch' | 'submit';
export type OperationState = 'pending' | 'in_progress' | 'completed' | 'failed' | 'rejected';

/**
 * Enqueues a sync operation into the local operations table.
 * If online, immediately triggers queue processing.
 */
export async function enqueueOperation(
  entityId: string, 
  operationType: OperationType, 
  payload: any,
  localStatusUpdate?: 'draft' | 'submitted_pending_sync'
) {
  const db = await getDb();
  
  // 1. Generate UUIDv7-like ID (using expo-crypto randomBytes for now)
  const id = Crypto.randomUUID();
  
  // 2. Encrypt and Hash payload
  const jsonStr = JSON.stringify(payload || {});
  const payload_sha256 = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, jsonStr);
  const payload_encrypted = await encryptPayload(payload);
  
  const now = new Date().toISOString();

  // We wrap both the operation insert and local incident state update in a single transaction
  await db.withTransactionAsync(async () => {
    await db.runAsync(
      `INSERT INTO local_operations (id, entity_id, operation_type, payload_encrypted, payload_sha256, state, created_at)
       VALUES (?, ?, ?, ?, ?, 'pending', ?)`,
      [id, entityId, operationType, payload_encrypted, payload_sha256, now]
    );

    if (localStatusUpdate) {
      await db.runAsync(
        `UPDATE local_incidents SET local_status = ?, updated_at = ? WHERE id = ?`,
        [localStatusUpdate, now, entityId]
      );
    }
  });

  // Attempt sync immediately if online
  const network = await Network.getNetworkStateAsync();
  if (network.isConnected) {
    processQueue().catch(console.error);
  }
}

/**
 * Processes pending sync operations sequentially.
 */
export async function processQueue() {
  const db = await getDb();
  
  // Fetch pending operations ordered by created_at
  const pendingOps = await db.getAllAsync<{ id: string, entity_id: string, operation_type: OperationType, payload_encrypted: string }>(
    `SELECT * FROM local_operations WHERE state = 'pending' ORDER BY created_at ASC`
  );

  if (!pendingOps || pendingOps.length === 0) return;

  for (const op of pendingOps) {
    // Mark in progress
    await db.runAsync(`UPDATE local_operations SET state = 'in_progress' WHERE id = ?`, [op.id]);
    
    try {
      const payload = await decryptPayload(op.payload_encrypted);
      
      if (op.operation_type === 'create') {
        const result = await IncidentsApi.createDraft(payload as IncidentCreate, op.id);
        // Update local_incidents with server_id and mark as draft
        await db.runAsync(
          `UPDATE local_incidents SET server_id = ?, local_status = 'draft' WHERE id = ?`,
          [result.id, op.entity_id]
        );
      } else if (op.operation_type === 'patch') {
        // Resolve server_id if needed
        const incident = await db.getFirstAsync<{ server_id: string, server_etag: string }>(
          `SELECT server_id, server_etag FROM local_incidents WHERE id = ?`, [op.entity_id]
        );
        const serverId = incident?.server_id || op.entity_id;
        
        await IncidentsApi.updateDraftEndpoint(serverId, payload as IncidentDraftUpdate, incident?.server_etag || undefined, op.id);
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
      }
      
      // Mark completed
      await db.runAsync(`UPDATE local_operations SET state = 'completed', completed_at = ? WHERE id = ?`, [new Date().toISOString(), op.id]);

    } catch (e: any) {
      console.error(`Operation ${op.id} failed:`, e);
      // Determine if fatal or transient
      const isValidation = e.status === 422 || e.status === 409 || e.status === 403;
      const state = isValidation ? 'rejected' : 'failed';
      await db.runAsync(
        `UPDATE local_operations SET state = ?, error_message = ?, retry_count = retry_count + 1 WHERE id = ?`, 
        [state, e.message || 'Unknown error', op.id]
      );
      
      // Stop queue on first transient failure to maintain ordering
      if (state === 'failed') break;
    }
  }
}
