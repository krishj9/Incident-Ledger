/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IncidentCategory } from './IncidentCategory';
import type { IncidentChildDraft } from './IncidentChildDraft';
import type { SeverityLevel } from './SeverityLevel';
import type { TimePrecision } from './TimePrecision';
export type IncidentDraftUpdate = {
    category?: (IncidentCategory | null);
    severity?: (SeverityLevel | null);
    event_at?: (string | null);
    event_time_precision?: (TimePrecision | null);
    location?: (string | null);
    original_factual_notes?: (string | null);
    actions_taken?: (string | null);
    treatment_response?: (string | null);
    witnesses_known?: (boolean | null);
    children?: (Array<IncidentChildDraft> | null);
};

