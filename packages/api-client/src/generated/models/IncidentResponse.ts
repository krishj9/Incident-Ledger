/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IncidentCategory } from './IncidentCategory';
import type { IncidentStatus } from './IncidentStatus';
import type { SeverityLevel } from './SeverityLevel';
export type IncidentResponse = {
    id: string;
    status: IncidentStatus;
    category: IncidentCategory;
    severity: SeverityLevel;
    event_at?: (string | null);
    location?: (string | null);
    created_at: string;
    submitted_at?: (string | null);
    first_child_name?: (string | null);
    version_etag?: (string | null);
};

