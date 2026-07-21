import * as SQLite from 'expo-sqlite';
import * as Crypto from 'expo-crypto';
import { encryptPayload, decryptPayload } from './encryption';

const DB_NAME = 'incident-ledger.db';

export async function getDb() {
  const db = await SQLite.openDatabaseAsync(DB_NAME);
  return db;
}

export async function initDb() {
  const db = await getDb();
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS local_incidents (
      id TEXT PRIMARY KEY,
      server_id TEXT,
      draft_json_encrypted TEXT,
      local_status TEXT,
      server_etag TEXT,
      updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS local_operations (
      id TEXT PRIMARY KEY,
      entity_id TEXT,
      operation_type TEXT,
      payload_encrypted TEXT,
      payload_sha256 TEXT,
      state TEXT,
      retry_count INTEGER DEFAULT 0,
      created_at TEXT,
      completed_at TEXT,
      error_message TEXT
    );

    CREATE TABLE IF NOT EXISTS local_evidence (
      id TEXT PRIMARY KEY,
      incident_id TEXT,
      local_file_path TEXT,
      sha256 TEXT,
      media_type TEXT,
      byte_size INTEGER,
      upload_status TEXT,
      captured_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cached_roster (
      id TEXT PRIMARY KEY,
      data_encrypted TEXT,
      refreshed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS session (
      id TEXT PRIMARY KEY,
      user_json_encrypted TEXT,
      device_json_encrypted TEXT,
      is_online INTEGER
    );
  `);
}

// Ensure database is initialized before exporting helpers
initDb().catch(console.error);

export type LocalIncident = {
  id: string;
  server_id?: string;
  draft_json: any;
  local_status: 'draft' | 'submitted_pending_sync' | 'synced';
  server_etag?: string;
  updated_at: string;
};

export async function saveLocalDraft(id: string, payload: any, localStatus: 'draft' | 'submitted_pending_sync' | 'synced') {
  const db = await getDb();
  const encrypted = await encryptPayload(payload);
  const now = new Date().toISOString();
  
  await db.runAsync(
    `INSERT INTO local_incidents (id, draft_json_encrypted, local_status, updated_at) 
     VALUES (?, ?, ?, ?) 
     ON CONFLICT(id) DO UPDATE SET 
      draft_json_encrypted = excluded.draft_json_encrypted,
      local_status = excluded.local_status,
      updated_at = excluded.updated_at`,
    [id, encrypted, localStatus, now]
  );
}

export async function getLocalDraft(id: string): Promise<LocalIncident | null> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ id: string, server_id: string, draft_json_encrypted: string, local_status: string, server_etag: string, updated_at: string }>(
    `SELECT * FROM local_incidents WHERE id = ?`, 
    [id]
  );
  if (!row) return null;
  const draft_json = await decryptPayload(row.draft_json_encrypted);
  return {
    id: row.id,
    server_id: row.server_id,
    draft_json,
    local_status: row.local_status as any,
    server_etag: row.server_etag,
    updated_at: row.updated_at,
  };
}

export type LocalEvidence = {
  id: string;
  incident_id: string;
  local_file_path: string;
  sha256: string;
  media_type: string;
  byte_size: number;
  upload_status: string;
  captured_at: string;
};

export async function getLocalEvidence(incidentId: string): Promise<LocalEvidence[]> {
  const db = await getDb();
  return await db.getAllAsync<LocalEvidence>(
    `SELECT * FROM local_evidence WHERE incident_id = ? ORDER BY captured_at ASC`,
    [incidentId]
  );
}
