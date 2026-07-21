# Writing Assistance Specification

## Scope
This is a bounded optional assistance feature, not an autonomous agent. It improves clarity and identifies missing facts without changing report state or content automatically.

## API boundary
`POST /v1/writing-assistance/suggestions` accepts only the current staff-provided text and selected structured fields for one draft. It cannot call database search, evidence, roster, email, workflow, notification, or approval tools.

## Allowed inputs
- Category, severity, time precision, event time, location
- Witness indicator, original factual notes, actions, treatment/response
- Configured factual-writing rubric and prompt version

## Disallowed inputs
- Images, EXIF or photo metadata, guardian contact details, other incidents, child history, web content, external tools, medical/legal/regulatory guidance
- Any narrative field when category is suspected abuse/neglect

## Output contract
```json
{
  "suggestions": [{
    "id": "sug_01",
    "type": "missing_information_question|subjective_language_flag|chronology_suggestion|clarity_suggestion",
    "source_span": {"start": 0, "end": 24},
    "rationale": "The time is not stated.",
    "question": "What time did staff first observe the event?",
    "proposed_text": null
  }],
  "model_version": "configured-model-id",
  "prompt_version": "v1"
}
```

## Guardrails
- Never invent facts, motives, intent, diagnosis, blame, causation, treatment advice, legal advice, or regulatory advice.
- Ask for missing information; do not fill it.
- Suggested wording may only restate supplied facts in neutral, time-ordered language.
- Never automatically apply a suggestion.
- Never mention the assistant in a report, guardian packet, email, or acknowledgement.
- Return `ASSISTANCE_UNAVAILABLE_FOR_RESTRICTED_INCIDENT` for suspected abuse/neglect.
- Failure or timeout must return a non-blocking unavailable response; manual reporting continues.

## Staff disposition
Each suggestion can be accepted, rejected, or edited. Acceptance inserts the staff-selected text into the draft through the ordinary draft update API. Persist the suggestion ID, disposition, actor, timestamp, model/prompt version, and field hashes. Do not persist raw prompts outside the incident retention boundary.

## Evaluation suite
Before release, run curated tests for invented facts, unsupported advice, subjective-language detection, chronology, restricted-case refusal, prompt injection in notes, and availability failure. Release gate: zero fabricated-fact outputs and zero restricted narrative outputs in the adversarial suite.
