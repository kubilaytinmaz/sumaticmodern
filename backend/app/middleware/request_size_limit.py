"""
Request Size Limit Middleware for FastAPI
Limits the size of incoming requests to prevent large payload attacks.
"""
from typing import Optional, Callable
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# Default size limits (in bytes)
DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB for file uploads


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit the size of incoming request bodies.
    Prevents large payload attacks and memory exhaustion.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        max_body_size: Optional[int] = None,
        enabled: bool = True
    ):
        super().__init__(app)
        self.max_body_size = max_body_size or DEFAULT_MAX_BODY_SIZE
        self.enabled = enabled and not settings.DEBUG  # Can be disabled in debug mode
        
        # Larger limit for file upload endpoints
        self.upload_endpoints = [
            "/api/v1/devices/import",
            "/api/v1/devices/bulk-upload",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with size limit check."""
        
        # Skip size limit check if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Determine max size for this endpoint
        max_size = self.max_body_size
        for upload_endpoint in self.upload_endpoints:
            if request.url.path.startswith(upload_endpoint):
                max_size = MAX_UPLOAD_SIZE
                break
        
        # Check content length header if available
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int > max_size:
                    logger.warning(
                        f"Request size limit exceeded: {content_length_int} > {max_size} "
                        f"for {request.client.host if request.client else 'unknown'} "
                        f"on {request.method} {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "Request entity too large",
                            "detail": f"Request body exceeds maximum size of {max_size} bytes",
                            "max_size": max_size
                        }
                    )
            except ValueError:
                # Invalid content-length header, will check actual body size
                pass
        
        # For requests without content-length or with invalid header,
        # we need to wrap the receive to check actual body size
        if request.method in ("POST", "PUT", "PATCH"):
            # Wrap the receive function to check body size
            receive = request.receive
            
            async def limited_receive() -> Message:
                message = await receive()
                
                if message["type"] == "http.request":
                    body_size = len(message.get("body", b""))
                    if body_size > max_size:
                        logger.warning(
                            f"Request body size limit exceeded: {body_size} > {max_size} "
                            f"for {request.client.host if request.client else 'unknown'} "
                            f"on {request.method} {request.url.path}"
                        )
                        # Return an error response
                        raise RequestSizeLimitException(
                            f"Request body exceeds maximum size of {max_size} bytes",
                            max_size
                        )
                
                return message
            
            # Replace the receive function
            request._receive = limited_receive
        
        try:
            return await call_next(request)
        except RequestSizeLimitException as e:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request entity too large",
                    "detail": str(e),
                    "max_size": e.max_size
                }
            )


class RequestSizeLimitException(Exception):
    """Exception raised when request size limit is exceeded."""
    
    def __init__(self, message: str, max_size: int):
        self.message = message
        self.max_size = max_size
        super().__init__(message)


# Size limits for different content types
CONTENT_TYPE_LIMITS = {
    "application/json": 1 * 1024 * 1024,  # 1 MB for JSON
    "application/x-www-form-urlencoded": 1 * 1024 * 1024,  # 1 MB for form data
    "multipart/form-data": MAX_UPLOAD_SIZE,  # 50 MB for file uploads
    "text/plain": 1 * 1024 * 1024,  # 1 MB for text
}


def get_size_limit_for_content_type(content_type: Optional[str]) -> int:
    """
    Get the size limit for a specific content type.
    
    Args:
        content_type: The content type header value
        
    Returns:
        Maximum size in bytes for the content type
    """
    if not content_type:
        return DEFAULT_MAX_BODY_SIZE
    
    # Extract the base content type (ignore charset etc.)
    base_type = content_type.split(";")[0].strip().lower()
    
    return CONTENT_TYPE_LIMITS.get(base_type, DEFAULT_MAX_BODY_SIZE)


# Special limits for specific endpoints
ENDPOINT_LIMITS = {
    "/api/v1/auth/login": 10 * 1024,  # 10 KB for login
    "/api/v1/auth/register": 10 * 1024,  # 10 KB for registration
    "/api/v1/auth/change-password": 10 * 1024,  # 10 KB for password change
    "/api/v1/devices": 100 * 1024,  # 100 KB for device creation/update
    "/api/v1/readings/bulk": 5 * 1024 * 1024,  # 5 MB for bulk readings
}


def get_size_limit_for_endpoint(path: str, method: str) -> Optional[int]:
    """
    Get the size limit for a specific endpoint.
    
    Args:
        path: The request path
        method: The HTTP method
        
    Returns:
        Maximum size in bytes for the endpoint, or None if no specific limit
    """
    # Check for exact match
    key = f"{path}:{method.lower()}"
    if key in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[key]
    
    # Check for path match
    for endpoint_path, limit in ENDPOINT_LIMITS.items():
        if path.startswith(endpoint_path):
            return limit
    
    return None
