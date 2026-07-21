from typing import Any
from pydantic import BaseModel, Field

class EvidenceIntentRequest(BaseModel):
    media_type: str = Field(pattern="^image/(jpeg|heic)$")
    byte_size: int = Field(le=10485760)

class EvidenceIntentResponse(BaseModel):
    evidence_id: str
    upload_url: str
    expires_in: int

class EvidenceFinalizeRequest(BaseModel):
    client_sha256: str = Field(min_length=64, max_length=64)

class EvidenceFinalizeResponse(BaseModel):
    evidence_id: str
    status: str
