/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SuggestionItem } from './SuggestionItem';
export type GeminiResponse = {
    available?: boolean;
    reason?: (string | null);
    suggestions?: Array<SuggestionItem>;
    model_version?: string;
    prompt_version?: string;
};

