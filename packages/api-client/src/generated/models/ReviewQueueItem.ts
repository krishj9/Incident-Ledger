/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ReviewQueueItem = {
    incident_id: string;
    status: string;
    category: string;
    severity: string;
    location: string;
    submitted_at: (string | null);
    elapsed_seconds: number;
    escalation_state: (string | null);
    assigned_director_id: (string | null);
};

