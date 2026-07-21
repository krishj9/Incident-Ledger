"""
Incident Ledger API — FastAPI application factory.

Responsibilities:
  - Structured JSON logging via structlog (correlation_id bound to every log line)
  - CORS middleware scoped to configured origins
  - Request-ID middleware: generates correlation_id, sets X-Correlation-ID header
  - Global exception handler returning RFC 9457-style error JSON
  - Router registration

Component rules (architecture.md):
  - The API owns authorization, business transitions, versioning, and audit writes.
  - Clients never infer authorization.
  - Every response includes X-Correlation-ID.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.api.audit import router as audit_router
from app.api.children import router as children_router
from app.api.incidents import router as incidents_router
from app.api.operations import router as operations_router
from app.api.review import router as review_router
from app.api.guardian import router as guardian_router
from app.api.guardian_public import router as guardian_public_router
from app.api.writing import router as writing_router
from app.config import settings
from app.repositories.exceptions import EntityNotFoundError, StaleVersionError
from app.services.exceptions import InvalidStateError, UnauthorizedError, ValidationFailedError


# ── Structured logging setup ──────────────────────────────────────────────────

def _filter_sensitive_data(logger: logging.Logger, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from structured logs."""
    sensitive_keys = {"token", "bearer", "jwt", "image", "narrative", "original_factual_notes", "actions_taken"}
    # Keys might be substrings or exact matches, let's strip exactly or substring if obvious
    keys_to_remove = []
    for k in event_dict.keys():
        kl = k.lower()
        if any(sec in kl for sec in sensitive_keys):
            keys_to_remove.append(k)
    
    for k in keys_to_remove:
        event_dict[k] = "[REDACTED]"
    
    # Also ensure the event message itself isn't a raw token
    if "event" in event_dict and isinstance(event_dict["event"], str):
        evt = event_dict["event"].lower()
        if "bearer " in evt or "jwt" in evt or "eyjh" in evt:
            event_dict["event"] = "[REDACTED]"
            
    return event_dict


def _configure_logging() -> None:
    """
    Configure structlog for structured JSON output.

    Sensitive fields that must NEVER appear in logs (architecture rule):
    - Raw JWT / bearer tokens
    - Raw guardian email-link tokens
    - Original image bytes
    - Full report narrative content
    Log only: correlation IDs, opaque IDs, status codes, actor IDs, event types.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            _filter_sensitive_data,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger(__name__)


# ── Request-ID middleware ─────────────────────────────────────────────────────

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a UUIDv4 correlation_id for every request and:
      - Binds it to structlog context (all log lines for this request include it)
      - Sets X-Correlation-ID response header
    Accepts X-Correlation-ID from client if provided (for tracing across services).
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        correlation_id = (
            request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        )
        # Bind to structlog context for the lifetime of this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


# ── Demo Guard middleware ─────────────────────────────────────────────────────

async def _set_req_body(request: Request, body: bytes) -> None:
    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body}
    request._receive = receive


class DemoGuardMiddleware(BaseHTTPMiddleware):
    """
    In DEMO_ONLY mode, enforces synthetic data constraints on mutations:
      - Any created/updated entity with center_id must use an allowed center.
      - Any created/updated entity with synthetic_marker must set it to true.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        if settings.DEMO_ONLY and request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body_bytes = await request.body()
                await _set_req_body(request, body_bytes)
                if body_bytes:
                    try:
                        payload = json.loads(body_bytes)
                        if isinstance(payload, dict):
                            # Enforce center_id if present
                            cid = payload.get("center_id")
                            if cid and str(cid) not in settings.ALLOWED_CENTER_CODES:
                                return _error_response(
                                    403, "DEMO_POLICY_VIOLATION", "Demo Policy Violation",
                                    f"Center '{cid}' is not allowed in this demo environment.",
                                    request.headers.get("X-Correlation-ID", "")
                                )

                            # Enforce synthetic_marker for applicable entity creates
                            # (Skip for endpoints that don't create/update domain entities)
                            if request.url.path not in ("/v1/auth/session/switch",):
                                if payload.get("synthetic_marker") is not True:
                                    return _error_response(
                                        403, "DEMO_POLICY_VIOLATION", "Demo Policy Violation",
                                        "synthetic_marker must be true in demo environments",
                                        request.headers.get("X-Correlation-ID", "")
                                    )
                    except json.JSONDecodeError:
                        pass
                        
        response: Response = await call_next(request)
        return response


# ── RFC 9457 error helpers ─────────────────────────────────────────────────────

_ERROR_BASE = "https://incident-ledger.dev/errors"


def _error_response(
    status: int,
    code: str,
    title: str,
    detail: str,
    correlation_id: str = "",
    extra: dict | None = None,  # type: ignore[type-arg]
) -> JSONResponse:
    body: dict = {  # type: ignore[type-arg]
        "type": f"{_ERROR_BASE}/{code.lower()}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "correlation_id": correlation_id,
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body)


# ── App factory ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "api_startup",
        demo_only=settings.DEMO_ONLY,
        mock_auth=settings.MOCK_AUTH,
        log_level=settings.LOG_LEVEL,
    )
    yield
    logger.info("api_shutdown")


def custom_generate_unique_id(route: APIRoute) -> str:
    return route.name


def create_app() -> FastAPI:
    application = FastAPI(
        title="Incident Ledger API",
        version="1.0.0",
        description="Incident reporting workflow for child-care staff, directors, and guardians.",
        lifespan=lifespan,
        generate_unique_id_function=custom_generate_unique_id,
        docs_url="/v1/docs" if not settings.DEMO_ONLY else None,
        redoc_url="/v1/redoc" if not settings.DEMO_ONLY else None,
        openapi_url="/v1/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # ── Correlation ID ────────────────────────────────────────────────────────
    application.add_middleware(CorrelationIDMiddleware)

    # ── Demo Guard ────────────────────────────────────────────────────────────
    application.add_middleware(DemoGuardMiddleware)

    # ── Global exception handlers ─────────────────────────────────────────────

    @application.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=404,
            code="NOT_FOUND",
            title="Resource not found",
            detail=f"The requested path '{request.url.path}' does not exist.",
            correlation_id=correlation_id,
        )

    @application.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=405,
            code="METHOD_NOT_ALLOWED",
            title="Method not allowed",
            detail=f"Method '{request.method}' is not allowed on '{request.url.path}'.",
            correlation_id=correlation_id,
        )

    @application.exception_handler(ValidationFailedError)
    async def validation_failed_handler(request: Request, exc: ValidationFailedError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=422,
            code="VALIDATION_FAILED",
            title="Validation failed",
            detail=str(exc),
            correlation_id=correlation_id,
            extra={"field_errors": [str(e) for e in exc.errors]},
        )

    @application.exception_handler(InvalidStateError)
    async def invalid_state_handler(request: Request, exc: InvalidStateError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=409,
            code="INVALID_STATE",
            title="Invalid state",
            detail=str(exc),
            correlation_id=correlation_id,
        )

    @application.exception_handler(StaleVersionError)
    async def stale_version_handler(request: Request, exc: StaleVersionError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=409,
            code="STALE_VERSION",
            title="Stale version",
            detail=str(exc),
            correlation_id=correlation_id,
        )

    @application.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=403,
            code="UNAUTHORIZED",
            title="Unauthorized",
            detail=str(exc),
            correlation_id=correlation_id,
        )

    @application.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        return _error_response(
            status=404,
            code="NOT_FOUND",
            title="Resource not found",
            detail=str(exc),
            correlation_id=correlation_id,
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = request.headers.get("X-Correlation-ID", "")
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            # Never log exc.args directly — may contain sensitive data
        )
        return _error_response(
            status=500,
            code="INTERNAL_SERVER_ERROR",
            title="An unexpected error occurred",
            detail="Please include the correlation_id when reporting this issue.",
            correlation_id=correlation_id,
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(operations_router)
    application.include_router(auth_router)
    application.include_router(incidents_router)
    application.include_router(audit_router)
    application.include_router(children_router)
    application.include_router(review_router)
    application.include_router(guardian_router)
    application.include_router(guardian_public_router)
    application.include_router(writing_router)

    return application


# Module-level app instance — used by uvicorn and Alembic env.py
app = create_app()
