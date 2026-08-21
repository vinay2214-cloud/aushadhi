"""AUSHADHI — X-API-Key authentication middleware.

Every /api/v1 route requires `X-API-Key: <AUSHADHI_API_KEY>` except:

  * /health              — liveness probe, must work for Cloud Run without auth
  * /api/v1/stream       — EventSource cannot set request headers, so the SSE
                           endpoint takes ?api_key= instead and is checked here
                           against the same secret
  * OPTIONS preflights   — browsers never attach custom headers to them
  * the docs endpoints   — /docs, /redoc, /openapi.json

Keys are compared with secrets.compare_digest to keep the check
constant-time, and a missing/blank server-side key rejects everything rather
than silently allowing all traffic.
"""

import secrets
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from config import settings
from utils.logger import get_logger

log = get_logger(__name__)

API_KEY_HEADER = "X-API-Key"
API_KEY_QUERY_PARAM = "api_key"

#: Paths that never require a key.
PUBLIC_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/"})

#: Paths authenticated by ?api_key= instead of the header (EventSource).
QUERY_PARAM_AUTH_PATHS = frozenset({"/api/v1/stream"})


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths: Iterable[str] = PUBLIC_PATHS) -> None:
        super().__init__(app)
        self.public_paths = frozenset(public_paths)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path.rstrip("/") or "/"

        if request.method == "OPTIONS" or path in self.public_paths:
            return await call_next(request)

        expected = settings.aushadhi_api_key
        if not expected:
            log.error("api_key_not_configured", path=path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "AUSHADHI_API_KEY is not configured on the server",
                },
            )

        if path in QUERY_PARAM_AUTH_PATHS:
            provided = request.query_params.get(API_KEY_QUERY_PARAM, "")
            source = "query"
        else:
            provided = request.headers.get(API_KEY_HEADER, "")
            source = "header"

        if not provided or not secrets.compare_digest(provided, expected):
            log.warning(
                "api_key_rejected",
                path=path,
                method=request.method,
                source=source,
                key_present=bool(provided),
                client=request.client.host if request.client else None,
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        f"Missing or invalid API key. Send {API_KEY_HEADER}: <key>"
                        if source == "header"
                        else f"Missing or invalid API key. Send ?{API_KEY_QUERY_PARAM}=<key>"
                    )
                },
            )

        return await call_next(request)
