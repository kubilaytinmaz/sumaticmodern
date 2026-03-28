"""
Sumatic Modern IoT - Security Headers Middleware
Adds security-related HTTP headers to all API responses.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff - Prevents MIME type sniffing
    - X-Frame-Options: DENY - Prevents clickjacking attacks
    - X-XSS-Protection: 1; mode=block - Enables XSS filtering
    - Referrer-Policy: strict-origin-when-cross-origin - Controls referrer information
    - Permissions-Policy: Restricts browser features and APIs
    - Strict-Transport-Security (HSTS): Enforces HTTPS in production
    - Content-Security-Policy: Restricts resource sources
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and add security headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler in chain
            
        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking - deny all framing
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Restrict browser features and APIs
        # Disable geolocation, camera, microphone, payment, etc. by default
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Content Security Policy - restrict resource sources
        # Note: For API-only responses, this is less critical but still good practice
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # HSTS - Only add in production when using HTTPS
        # Check if request came via HTTPS (including proxy headers)
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto", "").lower() == "https"
        )
        
        if is_https:
            # Strict-Transport-Security: Enforce HTTPS for 1 year including subdomains
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; "
                "includeSubDomains; "
                "preload"
            )
        
        # Cache control for API responses
        # Prevent caching of sensitive API responses by default
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]
        
        # Add X-Request-ID for tracing if not present
        if "X-Request-ID" not in response.headers:
            import uuid
            response.headers["X-Request-ID"] = str(uuid.uuid4())
        
        return response
