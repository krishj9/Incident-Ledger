/**
 * useApi — hook that wraps ReviewApi and IncidentsApi calls
 * with Bearer token from AuthContext.
 */
import { useCallback } from 'react';
import { OpenAPI, ReviewApi, IncidentsApi } from '@incident-ledger/api-client';
import { useAuth } from '../contexts/AuthContext';
import { v4 as uuidv4 } from 'uuid';

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export function useApi() {
  const { token } = useAuth();

  // Ensure token is set before each call
  const ensureToken = useCallback(() => {
    OpenAPI.BASE = API_BASE;
    if (token) OpenAPI.TOKEN = token;
  }, [token]);

  const getReviewQueue = useCallback(async () => {
    ensureToken();
    return ReviewApi.getReviewQueue();
  }, [ensureToken]);

  const acknowledgeReview = useCallback(async (incidentId: string) => {
    ensureToken();
    return ReviewApi.acknowledgeReview(incidentId, uuidv4());
  }, [ensureToken]);

  const createDirectorEdit = useCallback(async (incidentId: string, renderedNarrative: string, editReason: string) => {
    ensureToken();
    return ReviewApi.createDirectorEdit(incidentId, { rendered_narrative: renderedNarrative, edit_reason: editReason }, uuidv4());
  }, [ensureToken]);

  const requestChanges = useCallback(async (incidentId: string, reason: string) => {
    ensureToken();
    return ReviewApi.requestChanges(incidentId, { reason }, uuidv4());
  }, [ensureToken]);

  const changeSeverity = useCallback(async (incidentId: string, newSeverity: string, reason: string) => {
    ensureToken();
    return ReviewApi.changeSeverity(incidentId, { new_severity: newSeverity, reason }, uuidv4());
  }, [ensureToken]);

  const approveIncident = useCallback(async (incidentId: string) => {
    ensureToken();
    return ReviewApi.approveIncident(incidentId, uuidv4());
  }, [ensureToken]);

  const createAddendum = useCallback(async (incidentId: string, content: string) => {
    ensureToken();
    return ReviewApi.createAddendum(incidentId, { content }, uuidv4());
  }, [ensureToken]);

  const getIncident = useCallback(async (incidentId: string) => {
    ensureToken();
    return IncidentsApi.getIncidentDetail(incidentId);
  }, [ensureToken]);

  return {
    getReviewQueue,
    acknowledgeReview,
    createDirectorEdit,
    requestChanges,
    changeSeverity,
    approveIncident,
    createAddendum,
    getIncident,
  };
}
