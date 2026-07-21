/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeviceRegisterRequest } from '../models/DeviceRegisterRequest';
import type { DeviceRegisterResponse } from '../models/DeviceRegisterResponse';
import type { MeResponse } from '../models/MeResponse';
import type { SessionSwitchResponse } from '../models/SessionSwitchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthApi {
    /**
     * Get current user profile
     * Returns the authenticated user's profile. Returns 401 if unauthenticated. No roster, report, or sensitive data is included — just identity fields.
     * @returns MeResponse Successful Response
     * @throws ApiError
     */
    public static getMe(): CancelablePromise<MeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/me',
        });
    }
    /**
     * Switch active user session
     * Ends any prior active session on this device and begins a new session for the authenticated user. Writes an audit event. Requires Idempotency-Key header.
     * @param idempotencyKey
     * @returns SessionSwitchResponse Successful Response
     * @throws ApiError
     */
    public static sessionSwitch(
        idempotencyKey?: (string | null),
    ): CancelablePromise<SessionSwitchResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/auth/session/switch',
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Register a mobile device
     * Register a device installation for the authenticated user's center. Validates that the center has not exceeded max_active_mobile_installations (default 20). Platform must be 'ios' or 'ipados'. Requires Idempotency-Key header.
     * @param requestBody
     * @param idempotencyKey
     * @returns DeviceRegisterResponse Successful Response
     * @throws ApiError
     */
    public static registerDevice(
        requestBody: DeviceRegisterRequest,
        idempotencyKey?: (string | null),
    ): CancelablePromise<DeviceRegisterResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/devices/register',
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
