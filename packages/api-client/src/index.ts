export * from './generated';
export { IncidentsApi as IncidentApi } from './generated';

import { OpenAPI } from './generated';

/**
 * Configure the API client globally.
 * @param baseUrl - The base URL of the FastAPI backend.
 * @param token - The Bearer token for authentication. Can be a string or a function returning a string/promise.
 */
export function configureApiClient(baseUrl: string, token?: string | (() => Promise<string>)) {
    OpenAPI.BASE = baseUrl;
    if (token) {
        OpenAPI.TOKEN = token;
    }
}
