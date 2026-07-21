/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CloseUnreachableRequest } from '../models/CloseUnreachableRequest';
import type { ContactAttemptRequest } from '../models/ContactAttemptRequest';
import type { InPersonAckRequest } from '../models/InPersonAckRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GuardianApi {
    /**
     * Record In Person Acknowledgement
     * @param packetId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static recordInPersonAcknowledgement(
        packetId: string,
        requestBody: InPersonAckRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/guardian-packets/{packet_id}/in-person-acknowledgements',
            path: {
                'packet_id': packetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Send Email Link
     * @param packetId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static sendEmailLink(
        packetId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/guardian-packets/{packet_id}/email-links',
            path: {
                'packet_id': packetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Record Contact Attempt
     * @param incidentId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static recordContactAttempt(
        incidentId: string,
        requestBody: ContactAttemptRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/contact-attempts',
            path: {
                'incident_id': incidentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Close Unreachable
     * @param incidentId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static closeUnreachable(
        incidentId: string,
        requestBody: CloseUnreachableRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/incidents/{incident_id}/acknowledgement/close-unreachable',
            path: {
                'incident_id': incidentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
