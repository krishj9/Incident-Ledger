"""
OIDC JWT validation module.

Production path:
  - Fetch JWKS from OIDC_JWKS_URI (cached in-process for TTL seconds)
  - Validate JWT: issuer, audience, expiry, signature
  - Extract external_subject from token claims

MOCK_AUTH path (local dev only):
  - Accept any Bearer token that is a JSON payload {"sub": "...", "name": "..."}
  - No signature validation — never enable in production
  - Gated by MOCK_AUTH setting so it cannot be accidentally deployed

Security rules (security-privacy.md):
  - Never log raw tokens or JWTs at any level
  - Raise OIDCError with a safe code; never surface internal exception detail to client
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass

import httpx
import structlog
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jose import JWTError, jwk, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from app.config import settings

logger = structlog.get_logger(__name__)


# ── Domain types ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OIDCClaims:
    external_subject: str   # the 'sub' claim — maps to users.external_subject
    display_name: str       # 'name' claim (used only for logging/display; not stored here)


class OIDCError(Exception):
    """Raised when token validation fails — never expose .args to client."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"OIDCError({code}): {detail}")


# ── JWKS cache ─────────────────────────────────────────────────────────────────

_JWKS_CACHE: dict[str, object] | None = None
_JWKS_CACHED_AT: float = 0.0
_JWKS_TTL_SECONDS: int = 3600  # refresh JWKS every hour


async def _fetch_jwks() -> dict[str, object]:
    """Fetch JWKS from configured URI, with in-process TTL cache."""
    global _JWKS_CACHE, _JWKS_CACHED_AT

    now = time.monotonic()
    if _JWKS_CACHE is not None and (now - _JWKS_CACHED_AT) < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.OIDC_JWKS_URI)
            response.raise_for_status()
            data: dict[str, object] = response.json()
            _JWKS_CACHE = data
            _JWKS_CACHED_AT = now
            keys = data.get("keys")
            num_keys = len(keys) if isinstance(keys, list) else 0
            logger.info("jwks_refreshed", num_keys=num_keys)
            return data
    except OIDCError:
        raise
    except Exception as exc:
        logger.error("jwks_fetch_failed", error_type=type(exc).__name__)
        raise OIDCError("JWKS_FETCH_FAILED", "Unable to fetch signing keys") from exc


# ── Production validation ──────────────────────────────────────────────────────

async def validate_oidc_token(token: str) -> OIDCClaims:
    """
    Validate a production OIDC JWT.

    Validates: signature (via JWKS), issuer, audience, expiry.
    Returns OIDCClaims on success; raises OIDCError on any failure.
    """
    try:
        jwks = await _fetch_jwks()

        # jose/python-jose expects the JWKS as a dict with 'keys'
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.OIDC_AUDIENCE,
            issuer=settings.OIDC_ISSUER,
            options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
        )
    except ExpiredSignatureError:
        raise OIDCError("TOKEN_EXPIRED", "The provided token has expired")
    except JWTClaimsError as exc:
        raise OIDCError("TOKEN_CLAIMS_INVALID", "Token claims validation failed")
    except JWTError as exc:
        raise OIDCError("TOKEN_INVALID", "Token signature or format is invalid")

    sub = claims.get("sub")
    if not sub:
        raise OIDCError("TOKEN_MISSING_SUB", "Token is missing required 'sub' claim")

    return OIDCClaims(
        external_subject=str(sub),
        display_name=str(claims.get("name", "")),
    )


# ── Mock validation (MOCK_AUTH=true, local dev only) ───────────────────────────

def _validate_mock_token(token: str) -> OIDCClaims:
    """
    Accept a plain JSON string as Bearer token value for local development.

    Expected format: {"sub": "demo-alex-kim", "name": "DEMO-Alex Kim"}
    The token must be a valid JSON object — no signature required.

    This path is ONLY active when MOCK_AUTH=true in settings.
    Never reachable in production (settings enforces DEMO_ONLY guards).
    """
    try:
        # Try raw JSON
        payload = json.loads(token)
    except (json.JSONDecodeError, ValueError):
        # Try base64-encoded JSON (for curl convenience)
        try:
            padded = token + "=" * (-len(token) % 4)
            payload = json.loads(base64.b64decode(padded).decode())
        except Exception:
            raise OIDCError("MOCK_TOKEN_INVALID", "Mock token must be valid JSON: {\"sub\":\"...\",\"name\":\"...\"}")

    sub = payload.get("sub")
    if not sub:
        raise OIDCError("MOCK_TOKEN_MISSING_SUB", "Mock token JSON must include 'sub' field")

    return OIDCClaims(
        external_subject=str(sub),
        display_name=str(payload.get("name", "")),
    )


# ── Public entrypoint ──────────────────────────────────────────────────────────

async def extract_claims(raw_token: str) -> OIDCClaims:
    """
    Validate bearer token and return claims.

    Routes to mock path when MOCK_AUTH=true, otherwise full OIDC validation.
    """
    if settings.MOCK_AUTH:
        return _validate_mock_token(raw_token)
    return await validate_oidc_token(raw_token)
