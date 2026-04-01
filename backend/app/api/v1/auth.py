"""
Sumatic Modern IoT - Auth Endpoints
Authentication and authorization endpoints.
"""
from datetime import timedelta, datetime
from typing import Annotated
from uuid import uuid4
import time

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, PaginationParams
from app.config import get_settings
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    Token,
    PasswordChange,
)
from app.schemas.user import UserResponse, UserUpdate
from app.redis_client import blacklist_token, get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Brute force protection settings
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 300  # 5 minutes in seconds
LOGIN_COOLDOWN = 900  # 15 minutes in seconds


async def check_login_attempts(identifier: str) -> tuple[bool, int]:
    """
    Check if login attempts exceed threshold.
    
    Args:
        identifier: IP address or username to check
        
    Returns:
        Tuple of (is_blocked, remaining_attempts)
    """
    try:
        redis = await get_redis()
        if redis is None:
            # Redis unavailable - skip rate limiting
            return False, MAX_LOGIN_ATTEMPTS
        
        key = f"login_attempts:{identifier}"
        
        # Get current attempts
        attempts = await redis.get(key)
        if attempts is None:
            return False, MAX_LOGIN_ATTEMPTS
        
        attempts = int(attempts)
        
        if attempts >= MAX_LOGIN_ATTEMPTS:
            # Check if cooldown period has passed
            ttl = await redis.ttl(key)
            if ttl > 0:
                return True, 0  # Still blocked
        
        return False, max(0, MAX_LOGIN_ATTEMPTS - attempts)
    except Exception as e:
        logger.error(f"Error checking login attempts: {e}")
        return False, MAX_LOGIN_ATTEMPTS


async def record_login_attempt(identifier: str, success: bool = False):
    """
    Record a login attempt.
    
    Args:
        identifier: IP address or username
        success: Whether the login was successful
    """
    try:
        redis = await get_redis()
        if redis is None:
            # Redis unavailable - skip recording
            return
        
        key = f"login_attempts:{identifier}"
        
        if success:
            # Clear attempts on successful login
            await redis.delete(key)
        else:
            # Increment failed attempts
            attempts = await redis.incr(key)
            if attempts == 1:
                # Set expiry on first attempt
                await redis.expire(key, LOGIN_ATTEMPT_WINDOW)
            
            logger.warning(f"Failed login attempt {attempts}/{MAX_LOGIN_ATTEMPTS} for {identifier}")
    except Exception as e:
        logger.error(f"Error recording login attempt: {e}")


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate user and return JWT tokens.
    
    Args:
        credentials: Login credentials (username, password)
        request: FastAPI request object
        db: Database session
        
    Returns:
        Login response with access and refresh tokens
        
    Raises:
        HTTPException: If credentials are invalid or rate limited
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    # Check IP-based rate limiting
    is_blocked_ip, remaining_ip = await check_login_attempts(client_ip)
    if is_blocked_ip:
        logger.warning(f"Login blocked for IP: {client_ip} (too many attempts)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={
                "Retry-After": str(LOGIN_COOLDOWN),
                "X-RateLimit-Limit": str(MAX_LOGIN_ATTEMPTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + LOGIN_COOLDOWN),
            },
        )
    
    # Check username-based rate limiting
    is_blocked_user, remaining_user = await check_login_attempts(credentials.username)
    if is_blocked_user:
        logger.warning(f"Login blocked for username: {credentials.username} (too many attempts)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts for this username. Please try again later.",
            headers={
                "Retry-After": str(LOGIN_COOLDOWN),
                "X-RateLimit-Limit": str(MAX_LOGIN_ATTEMPTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + LOGIN_COOLDOWN),
            },
        )
    
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        # Record failed attempts for both IP and username
        await record_login_attempt(client_ip, success=False)
        await record_login_attempt(credentials.username, success=False)
        
        logger.warning(f"Failed login attempt for username: {credentials.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer",
                "X-RateLimit-Limit": str(MAX_LOGIN_ATTEMPTS),
                "X-RateLimit-Remaining": str(min(remaining_ip, remaining_user)),
                "X-RateLimit-Reset": str(int(time.time()) + LOGIN_ATTEMPT_WINDOW),
            },
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Create tokens
    access_token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role,
    )
    
    refresh_token = create_refresh_token(
        subject=str(user.id),
        username=user.username,
        role=user.role,
    )
    
    logger.info(f"User logged in: {user.username}")
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Logout user and blacklist the current token.
    
    Args:
        credentials: HTTP Bearer credentials
        current_user: Authenticated user
        
    Returns:
        Success message
    """
    token = credentials.credentials
    
    # Decode token to extract the actual jti claim
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
    except Exception:
        jti = None
    
    if jti:
        # Blacklist using the real jti from the token payload
        await blacklist_token(
            jti,
            expire_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        logger.info(f"User logged out: {current_user.username}, JTI: {jti}")
    else:
        logger.warning(f"Logout for {current_user.username}: token has no jti, skipping blacklist")
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_request: Refresh token
        db: Database session
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        payload = decode_refresh_token(refresh_request.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Create new access token
    access_token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role,
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        User information
    """
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change current user's password.
    
    Args:
        password_data: Current and new password
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )
    
    # Update password
    from app.core.security import get_password_hash
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Update current user's profile.
    
    Args:
        user_update: User update data
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    # Update allowed fields only (not role or is_active)
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    # Password update if provided
    if user_update.password is not None:
        from app.core.security import get_password_hash
        current_user.password_hash = get_password_hash(user_update.password)
    
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(f"Profile updated for user: {current_user.username}")
    
    return current_user
