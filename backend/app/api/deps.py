"""
Sumatic Modern IoT - API Dependencies
FastAPI dependencies for authentication, authorization, and pagination.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.logging import get_logger
from app.database import get_db
from app.models.user import User
from app.redis_client import is_token_blacklisted

logger = get_logger(__name__)

# HTTP Bearer scheme for JWT
security = HTTPBearer()


# ─── Authentication Dependencies ──────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT token and return the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Authenticated User instance
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Debug logging for token validation
    logger.debug(f"Token validation attempt. Token length: {len(token)}, Token prefix: {token[:20] if len(token) > 20 else token}...")
    
    try:
        payload = decode_token(token)
        logger.debug(f"Token decoded successfully. Payload: {payload}")
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        raise credentials_exception
    
    # Check token type
    if payload.get("type") != "access":
        logger.warning(f"Invalid token type: {payload.get('type')}, expected 'access'")
        raise credentials_exception
    
    # Check token blacklist (for logged out tokens)
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        logger.warning(f"Token is blacklisted. JTI: {jti}")
        raise credentials_exception
    
    # Get user from database
    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Token payload missing 'sub' field")
        raise credentials_exception
    
    logger.debug(f"Looking up user with ID: {user_id}")
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User not found with ID: {user_id}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"User account is disabled: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    logger.debug(f"User authenticated successfully: {user.username}")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current user has admin role.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User with admin role
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optionally authenticate a user. Returns None if no token provided.
    Useful for endpoints that work both with and without auth.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        Authenticated User instance or None
    """
    if credentials is None:
        return None
    
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        return None
    
    if payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        return None
    
    return user


# ─── Pagination Helpers ───────────────────────────────────────────────


class PaginationParams:
    """
    Pagination parameters dependency.
    
    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=50, ge=1, le=1000, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size

    def paginate_response(self, items: list, total: int) -> dict:
        """
        Create a paginated response dict.
        
        Args:
            items: List of items for current page
            total: Total number of items
            
        Returns:
            Paginated response dict
        """
        pages = (total + self.page_size - 1) // self.page_size if total > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": pages,
        }
