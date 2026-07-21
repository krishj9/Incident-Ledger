/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssignedReviewer } from './AssignedReviewer';
import type { IncidentStatus } from './IncidentStatus';
export type SubmitResponse = {
    incident_id: string;
    status: IncidentStatus;
    server_received_at: string;
    sync_state: string;
    assigned_reviewer?: (AssignedReviewer | null);
    version_etag?: (string | null);
};

