/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IncidentCategory } from './IncidentCategory';
import type { IncidentChildDraft } from './IncidentChildDraft';
import type { SeverityLevel } from './SeverityLevel';
export type IncidentCreate = {
    category?: (IncidentCategory | null);
    severity?: (SeverityLevel | null);
    children?: Array<IncidentChildDraft>;
};

