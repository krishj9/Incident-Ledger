/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EvidenceFinalizeRequest } from '../models/EvidenceFinalizeRequest';
import type { EvidenceFinalizeResponse } from '../models/EvidenceFinalizeResponse';
import type { EvidenceIntentRequest } from '../models/EvidenceIntentRequest';
import type { EvidenceIntentResponse } from '../models/EvidenceIntentResponse';
import type { IncidentCreate } from '../models/IncidentCreate';
import type { IncidentDraftUpdate } from '../models/IncidentDraftUpdate';
import type { IncidentListResponse } from '../models/IncidentListResponse';
import type { IncidentResponse } from '../models/IncidentResponse';
import type { IncidentSubmit } from '../models/IncidentSubmit';
import type { SubmitResponse } from '../models/SubmitResponse';
import type { SyncOperationsRequest } from '../models/SyncOperationsRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class IncidentsApi {
    /**
     * List Incidents
     * List incidents. Scoped to user's center_id.
     * Staff see own; director+ see all.
     * @param status
     * @param page
     * @param perPage
     * @returns IncidentListResponse Successful Response
     * @throws ApiError
     */
    public static listIncidents(
        status?: (string | null),
        page: number = 1,
        perPage: number = 50,
    ): CancelablePromise<IncidentListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/incidents',
            query: {
                'status': status,
                'page': page,
                'per_page': perPage,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Draft
     * Create a new draft incident.
     * Requires staff role.
     * @param requestBody
     * @param idempotencyKey
     * @returns IncidentResponse Successful Response
     * @throws ApiError
     */
    public static createDraft(
        requestBody: IncidentCreate,
        idempotencyKey?: (string | null),
    ): CancelablePromise<IncidentResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents',
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Incident Detail
     * Get incident detail with version history.
     * Policy-scoped (staff see own; director+ see center; restricted needs compliance).
     * Returns 404 (non-disclosing) if not accessible.
     * @param incidentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getIncidentDetail(
        incidentId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/incidents/{incident_id}',
            path: {
                'incident_id': incidentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Draft Endpoint
     * Update draft fields.
     * @param incidentId
     * @param requestBody
     * @param ifMatch
     * @param idempotencyKey
     * @returns IncidentResponse Successful Response
     * @throws ApiError
     */
    public static updateDraftEndpoint(
        incidentId: string,
        requestBody: IncidentDraftUpdate,
        ifMatch?: (string | null),
        idempotencyKey?: (string | null),
    ): CancelablePromise<IncidentResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/v1/incidents/{incident_id}/draft',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'If-Match': ifMatch,
                'Idempotency-Key': idempotencyKey,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Incident Endpoint
     * Submit incident.
     * @param incidentId
     * @param requestBody
     * @param idempotencyKey
     * @returns SubmitResponse Successful Response
     * @throws ApiError
     */
    public static submitIncidentEndpoint(
        incidentId: string,
        requestBody: IncidentSubmit,
        idempotencyKey?: (string | null),
    ): CancelablePromise<SubmitResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/submit',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Sync Operations Endpoint
     * Idempotent offline operation batch sync.
     * Requires staff role and device_id.
     * @param incidentId
     * @param xDeviceId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static syncOperationsEndpoint(
        incidentId: string,
        xDeviceId: string,
        requestBody: SyncOperationsRequest,
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/sync-operations',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'X-Device-Id': xDeviceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Evidence Intent Endpoint
     * Validate conditions and create an upload intent for evidence.
     * @param incidentId
     * @param xDeviceId
     * @param requestBody
     * @returns EvidenceIntentResponse Successful Response
     * @throws ApiError
     */
    public static createEvidenceIntentEndpoint(
        incidentId: string,
        xDeviceId: string,
        requestBody: EvidenceIntentRequest,
    ): CancelablePromise<EvidenceIntentResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/evidence/intents',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'X-Device-Id': xDeviceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Finalize Evidence Endpoint
     * Finalize an evidence upload, verifying hash and moving it to retention storage.
     * @param incidentId
     * @param evidenceId
     * @param xDeviceId
     * @param requestBody
     * @returns EvidenceFinalizeResponse Successful Response
     * @throws ApiError
     */
    public static finalizeEvidenceEndpoint(
        incidentId: string,
        evidenceId: string,
        xDeviceId: string,
        requestBody: EvidenceFinalizeRequest,
    ): CancelablePromise<EvidenceFinalizeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/evidence/{evidence_id}/finalize',
            path: {
                'incident_id': incidentId,
                'evidence_id': evidenceId,
            },
            headers: {
                'X-Device-Id': xDeviceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
