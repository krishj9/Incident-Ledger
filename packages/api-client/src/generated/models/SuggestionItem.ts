/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SuggestionSpan } from './SuggestionSpan';
export type SuggestionItem = {
    id: string;
    /**
     * One of: missing_information_question, subjective_language_flag, chronology_suggestion, clarity_suggestion
     */
    type: string;
    source_span: SuggestionSpan;
    rationale: string;
    question?: (string | null);
    proposed_text?: (string | null);
};

