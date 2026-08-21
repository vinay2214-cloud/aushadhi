"""AUSHADHI — API middleware."""

from api.middleware.auth import APIKeyMiddleware

__all__ = ["APIKeyMiddleware"]
