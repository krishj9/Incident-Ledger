/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AcknowledgeResponse } from '../models/AcknowledgeResponse';
import type { AddendumRequest } from '../models/AddendumRequest';
import type { AddendumResponse } from '../models/AddendumResponse';
import type { ApproveResponse } from '../models/ApproveResponse';
import type { ChangeSeverityRequest } from '../models/ChangeSeverityRequest';
import type { ChangeSeverityResponse } from '../models/ChangeSeverityResponse';
import type { DirectorEditRequest } from '../models/DirectorEditRequest';
import type { DirectorEditResponse } from '../models/DirectorEditResponse';
import type { RequestChangesRequest } from '../models/RequestChangesRequest';
import type { RequestChangesResponse } from '../models/RequestChangesResponse';
import type { ReviewQueueResponse } from '../models/ReviewQueueResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ReviewApi {
    /**
     * Get Review Queue
     * Get the review queue of submitted and under-review incidents.
     * @returns ReviewQueueResponse Successful Response
     * @throws ApiError
     */
    public static getReviewQueue(): CancelablePromise<ReviewQueueResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/review-queue',
        });
    }
    /**
     * Acknowledge Review
     * Acknowledge review ownership; transitions submitted → under_review.
     * @param incidentId
     * @param idempotencyKey
     * @returns AcknowledgeResponse Successful Response
     * @throws ApiError
     */
    public static acknowledgeReview(
        incidentId: string,
        idempotencyKey?: (string | null),
    ): CancelablePromise<AcknowledgeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/review/acknowledge',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Director Edit
     * Create a minor wording edit on an incident under review.
     * Edits MUST be limited to grammar, spelling, formatting, neutrality, or clarity only.
     * Requires edit_reason.
     * @param incidentId
     * @param requestBody
     * @param idempotencyKey
     * @returns DirectorEditResponse Successful Response
     * @throws ApiError
     */
    public static createDirectorEdit(
        incidentId: string,
        requestBody: DirectorEditRequest,
        idempotencyKey?: (string | null),
    ): CancelablePromise<DirectorEditResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/review/edits',
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
     * Request Changes
     * Return incident to staff for factual clarification.
     * @param incidentId
     * @param requestBody
     * @param idempotencyKey
     * @returns RequestChangesResponse Successful Response
     * @throws ApiError
     */
    public static requestChanges(
        incidentId: string,
        requestBody: RequestChangesRequest,
        idempotencyKey?: (string | null),
    ): CancelablePromise<RequestChangesResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/review/request-changes',
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
     * Change Severity
     * Change incident severity. Staff-selected severity is preserved. Reason required.
     * @param incidentId
     * @param requestBody
     * @param idempotencyKey
     * @returns ChangeSeverityResponse Successful Response
     * @throws ApiError
     */
    public static changeSeverity(
        incidentId: string,
        requestBody: ChangeSeverityRequest,
        idempotencyKey?: (string | null),
    ): CancelablePromise<ChangeSeverityResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/review/severity',
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
     * Approve Incident
     * Approve an incident; creates frozen approved version and triggers guardian notification.
     * @param incidentId
     * @param idempotencyKey
     * @returns ApproveResponse Successful Response
     * @throws ApiError
     */
    public static approveIncident(
        incidentId: string,
        idempotencyKey?: (string | null),
    ): CancelablePromise<ApproveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/review/approve',
            path: {
                'incident_id': incidentId,
            },
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Addendum
     * Create a post-approval addendum. Original approved version remains immutable.
     * @param incidentId
     * @param requestBody
     * @param idempotencyKey
     * @returns AddendumResponse Successful Response
     * @throws ApiError
     */
    public static createAddendum(
        incidentId: string,
        requestBody: AddendumRequest,
        idempotencyKey?: (string | null),
    ): CancelablePromise<AddendumResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/addenda',
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
}
