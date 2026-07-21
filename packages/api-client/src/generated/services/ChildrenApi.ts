/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChildrenListResponse } from '../models/ChildrenListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChildrenApi {
    /**
     * List Children
     * List children. Scoped to user's center_id.
     * @returns ChildrenListResponse Successful Response
     * @throws ApiError
     */
    public static listChildren(): CancelablePromise<ChildrenListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/children',
        });
    }
}
