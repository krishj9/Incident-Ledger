import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Ensure we have the client initialized
# In a real app, API_KEY would be loaded from env, for this demo we mock or expect it in env
try:
    client = genai.Client()
except Exception:
    # If no credentials, we'll instantiate it without, but calls might fail if not mocked
    client = genai.Client(api_key="mock_key")

MODEL_ID = "gemini-2.5-flash"
PROMPT_VERSION = "v1"

SYSTEM_INSTRUCTION = """
You are a factual writing assistant for an incident reporting system.
Your job is to review the staff-provided incident details and provide writing suggestions.
You must adhere STRICTLY to the following guardrails:
- NEVER invent facts, motives, intent, diagnosis, blame, causation, treatment advice, legal advice, or regulatory advice.
- If information is missing, ask for it; do NOT fill it in.
- Suggested wording may ONLY restate supplied facts in neutral, time-ordered language.
- DO NOT hallucinate names, dates, or locations.

Analyze the incident and return suggestions using the specified JSON schema.
"""

class SuggestionSpan(BaseModel):
    start: int
    end: int

class SuggestionItem(BaseModel):
    id: str
    type: str = Field(description="One of: missing_information_question, subjective_language_flag, chronology_suggestion, clarity_suggestion")
    source_span: SuggestionSpan
    rationale: str
    question: str | None = None
    proposed_text: str | None = None

class GeminiResponse(BaseModel):
    available: bool = True
    reason: str | None = None
    suggestions: list[SuggestionItem] = []
    model_version: str = MODEL_ID
    prompt_version: str = PROMPT_VERSION

async def get_writing_suggestions(incident_data: dict) -> dict:
    """
    Calls Gemini 2.5 Flash with the bounded prompt and returns the structured response.
    """
    prompt = f"""
Please review the following incident report and provide writing suggestions.

Category: {incident_data.get('category')}
Severity: {incident_data.get('severity')}
Time Precision: {incident_data.get('event_time_precision')}
Event Time: {incident_data.get('event_at')}
Location: {incident_data.get('location')}
Witnesses Known: {incident_data.get('witnesses_known')}

Original Factual Notes:
{incident_data.get('original_factual_notes')}

Actions Taken:
{incident_data.get('actions_taken')}

Treatment/Response:
{incident_data.get('treatment_response')}
"""

    response = await client.aio.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=GeminiResponse,
            temperature=0.0,
        ),
    )
    
    # Parse the response
    try:
        if not response.text:
            return {"suggestions": [], "model_version": MODEL_ID, "prompt_version": PROMPT_VERSION}
        parsed = json.loads(response.text)
        return parsed
    except Exception:
        # Fallback empty list on parsing failure
        return {"suggestions": [], "model_version": MODEL_ID, "prompt_version": PROMPT_VERSION}
