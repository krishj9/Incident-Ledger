import { useState, useEffect, useRef } from 'react';
import * as Crypto from 'expo-crypto';
import { saveLocalDraft, getLocalDraft, LocalIncident } from '../db';
import { enqueueOperation } from '../db/operations';
import { IncidentCreate, IncidentDraftUpdate } from '@incident-ledger/api-client';

export type SaveStatus = 'Saving locally' | 'Saved locally' | 'Submitted—pending secure sync' | 'Synced' | '';

export function useDraftPersistence(initialId?: string) {
  const [draftId, setDraftId] = useState<string>(initialId || Crypto.randomUUID());
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('');
  const [isHydrating, setIsHydrating] = useState(true);
  
  const draftStateRef = useRef<any>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Hydrate on mount
  useEffect(() => {
    async function load() {
      if (initialId) {
        const local = await getLocalDraft(initialId);
        if (local) {
          draftStateRef.current = local.draft_json;
          setSaveStatus(local.local_status === 'synced' ? 'Synced' : 'Saved locally');
        }
      }
      setIsHydrating(false);
    }
    load();
  }, [initialId]);

  const updateDraftFields = (fields: any) => {
    draftStateRef.current = { ...draftStateRef.current, ...fields };
    
    setSaveStatus('Saving locally');

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    
    debounceTimerRef.current = setTimeout(async () => {
      try {
        await saveLocalDraft(draftId, draftStateRef.current, 'draft');
        setSaveStatus('Saved locally');
      } catch (e) {
        console.error('Failed to auto-save to local DB:', e);
      }
    }, 500);
  };

  const getDraftState = () => draftStateRef.current || {};

  const saveExplicitly = async () => {
    setSaveStatus('Saving locally');
    await saveLocalDraft(draftId, draftStateRef.current, 'draft');
    
    // Determine if it's a create or patch. We check if there's a server_id
    const local = await getLocalDraft(draftId);
    const operation = local?.server_id ? 'patch' : 'create';
    
    await enqueueOperation(draftId, operation, draftStateRef.current);
    setSaveStatus('Saved locally');
  };

  const submitDraft = async (attestation: any, deviceInfo: any) => {
    setSaveStatus('Saving locally');
    await saveLocalDraft(draftId, draftStateRef.current, 'submitted_pending_sync');
    
    // Enqueue a final patch to ensure server matches local
    const local = await getLocalDraft(draftId);
    if (!local?.server_id) {
       await enqueueOperation(draftId, 'create', draftStateRef.current);
    } else {
       await enqueueOperation(draftId, 'patch', draftStateRef.current);
    }

    // Enqueue submit
    await enqueueOperation(draftId, 'submit', { staff_attestation: attestation, submitted_from: deviceInfo }, 'submitted_pending_sync');
    setSaveStatus('Submitted—pending secure sync');
  };

  return {
    draftId,
    saveStatus,
    isHydrating,
    getDraftState,
    updateDraftFields,
    saveExplicitly,
    submitDraft
  };
}
