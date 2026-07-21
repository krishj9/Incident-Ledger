/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AckRequest } from '../models/AckRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GuardianPublicApi {
    /**
     * Get Packet For Token
     * @param token
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPacketForToken(
        token: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/guardian/acknowledgements/{token}',
            path: {
                'token': token,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Acknowledgement
     * @param token
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static submitAcknowledgement(
        token: string,
        requestBody: AckRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/guardian/acknowledgements/{token}',
            path: {
                'token': token,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
