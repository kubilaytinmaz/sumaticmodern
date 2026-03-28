"""
Rate Limiting Middleware for FastAPI
IP-based rate limiting to prevent brute force attacks and DDoS.
"""
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, Optional

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings

settings = get_settings()


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    For production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(self):
        # Store request timestamps per IP: {ip: [timestamp1, timestamp2, ...]}
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, ip: str, limit: int, window: int = 60) -> bool:
        """
        Check if request from IP is allowed based on rate limit.
        
        Args:
            ip: Client IP address
            limit: Maximum requests allowed
            window: Time window in seconds (default: 60)
        
        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()
        
        # Get existing requests for this IP
        request_times = self.requests[ip]
        
        # Remove requests outside the time window
        self.requests[ip] = [
            req_time for req_time in request_times
            if current_time - req_time < window
        ]
        
        # Check if limit is exceeded
        if len(self.requests[ip]) >= limit:
            return False
        
        # Add current request
        self.requests[ip].append(current_time)
        return True
    
    def get_remaining_requests(self, ip: str, limit: int, window: int = 60) -> int:
        """Get remaining requests for an IP."""
        current_time = time.time()
        request_times = self.requests[ip]
        
        # Count requests within window
        valid_requests = [
            req_time for req_time in request_times
            if current_time - req_time < window
        ]
        
        return max(0, limit - len(valid_requests))
    
    def reset(self, ip: str):
        """Reset rate limit for an IP."""
        if ip in self.requests:
            del self.requests[ip]


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    Applies rate limiting to all incoming requests based on client IP.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: Optional[int] = None,
        enabled: bool = True
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.enabled = enabled and not settings.DEBUG  # Disable in debug mode
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Get client IP
        ip = self._get_client_ip(request)
        
        # Check rate limit
        if not rate_limiter.is_allowed(ip, self.requests_per_minute, 60):
            remaining = rate_limiter.get_remaining_requests(ip, self.requests_per_minute, 60)
            
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time() + 60)),
                    "Retry-After": "60"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = rate_limiter.get_remaining_requests(ip, self.requests_per_minute, 60)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        Checks X-Forwarded-For header for proxied requests.
        """
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


def rate_limit_check(requests_per_minute: int = 60):
    """
    Decorator for rate limiting specific endpoints.
    Can be used as an alternative to global middleware.
    
    Usage:
        @router.get("/protected-endpoint")
        @rate_limit_check(requests_per_minute=30)
        async def protected_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object from args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, just call the function
                return await func(*args, **kwargs)
            
            # Get client IP
            ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not rate_limiter.is_allowed(ip, requests_per_minute, 60):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {requests_per_minute} requests per minute allowed"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Special rate limits for sensitive endpoints
AUTH_RATE_LIMIT = 10  # 10 requests per minute for auth endpoints
LOGIN_RATE_LIMIT = 5   # 5 login attempts per minute
