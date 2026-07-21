/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DispositionRequest } from '../models/DispositionRequest';
import type { GeminiResponse } from '../models/GeminiResponse';
import type { SuggestionRequest } from '../models/SuggestionRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WritingApi {
    /**
     * Get Suggestions
     * @param requestBody
     * @returns GeminiResponse Successful Response
     * @throws ApiError
     */
    public static getSuggestions(
        requestBody: SuggestionRequest,
    ): CancelablePromise<GeminiResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/writing-assistance/suggestions',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Record Disposition
     * @param incidentId
     * @param suggestionId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static recordDisposition(
        incidentId: string,
        suggestionId: string,
        requestBody: DispositionRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/writing-assistance/suggestions/{incident_id}/disposition/{suggestion_id}',
            path: {
                'incident_id': incidentId,
                'suggestion_id': suggestionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
