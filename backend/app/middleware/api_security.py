"""
Sumatic Modern IoT - API Security Middleware
Additional security headers and response filtering for API endpoints.
"""
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class APISecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for additional API security measures:
    - Remove sensitive information from responses
    - Add security headers to API responses
    - Validate response content types
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Only apply to API endpoints
        if request.url.path.startswith("/api/"):
            # Add security headers specific to API responses
            response.headers["X-API-Version"] = "1.0"
            response.headers["X-Powered-By"] = "Sumatic Modern IoT"
            
            # Prevent MIME type sniffing for JSON responses
            if "application/json" in response.headers.get("content-type", ""):
                response.headers["X-Content-Type-Options"] = "nosniff"
            
            # Prevent caching of sensitive API responses
            if request.url.path.startswith("/api/v1/auth") or \
               request.url.path.startswith("/api/v1/users"):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        return response


class ResponseFilterMiddleware(BaseHTTPMiddleware):
    """
    Filter sensitive information from API responses in development/production.
    """

    SENSITIVE_FIELDS = {
        'password', 'ssh_password', 'jwt_secret_key', 'secret_key',
        'api_key', 'token', 'refresh_token', 'access_token',
        'private_key', 'private_pem', 'secret'
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and filter sensitive data from response."""
        response = await call_next(request)

        # Only filter JSON responses
        if "application/json" not in response.headers.get("content-type", ""):
            return response

        # For error responses and health checks, don't filter
        if response.status_code >= 400 or request.url.path == "/health":
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            # Parse JSON
            data = json.loads(body)
            
            # Filter sensitive fields (only top-level for now)
            filtered_data = self._filter_sensitive_data(data)
            
            # Create new response with filtered data
            filtered_body = json.dumps(filtered_data).encode("utf-8")
            
            # Update content-length header
            response.headers["content-length"] = str(len(filtered_body))
            
            # Return filtered response
            async def iter_filtered_response():
                yield filtered_body

            response.body_iterator = iter_filtered_response()

        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Could not filter response body: {e}")
            # Return original response if filtering fails
            async def iter_original_response():
                yield body

            response.body_iterator = iter_original_response()

        return response

    def _filter_sensitive_data(self, data):
        """Recursively filter sensitive fields from data structure."""
        if isinstance(data, dict):
            return {
                k: self._filter_sensitive_data(v) if not self._is_sensitive_field(k) else "[REDACTED]"
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._filter_sensitive_data(item) for item in data]
        return data

    @staticmethod
    def _is_sensitive_field(field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        field_lower = field_name.lower()
        return any(
            sensitive in field_lower
            for sensitive in ResponseFilterMiddleware.SENSITIVE_FIELDS
        )
