"""
Sumatic Modern IoT - SSH Tunnel Service
Manages SSH tunnel to remote MQTT broker using SSHTunnelForwarder.
Supports both password and key-based authentication (key-based preferred for production).

Features:
- Automatic reconnection with exponential backoff
- Circuit breaker pattern for repeated failures
- Detailed health monitoring and metrics
- Connection quality tracking
"""
import asyncio
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any
from sshtunnel import SSHTunnelForwarder
import paramiko

from app.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Fix for paramiko DSSKey issue
if not hasattr(paramiko, "DSSKey"):
    paramiko.DSSKey = paramiko.RSAKey


class SSHTunnelManager:
    """
    Manages SSH tunnel connection to remote MQTT broker.
    Provides automatic reconnection, health monitoring, and circuit breaker.
    """

    def __init__(self):
        self._tunnel: Optional[SSHTunnelForwarder] = None
        self._running = False
        
        # Reconnection settings with exponential backoff
        self._base_reconnect_interval = 5  # seconds
        self._max_reconnect_interval = 300  # 5 minutes
        self._current_reconnect_interval = self._base_reconnect_interval
        
        # Health monitoring settings
        self._last_check = 0.0
        self._check_interval = 10  # seconds
        
        # Circuit breaker settings
        self._failure_count = 0
        self._failure_threshold = 5  # consecutive failures before opening circuit
        self._circuit_open_until = 0.0
        self._circuit_open_duration = 300  # 5 minutes
        self._circuit_state = "closed"  # closed, open, half-open
        
        # Health metrics
        self._connection_start_time: Optional[float] = None
        self._total_connection_time = 0.0
        self._successful_connections = 0
        self._failed_connections = 0
        self._last_connection_error: Optional[str] = None
        self._reconnect_attempts = 0
        
        self._auth_method = self._determine_auth_method()

    def _determine_auth_method(self) -> str:
        """
        Determine which authentication method to use.
        Key-based authentication is preferred for production.
        
        Returns:
            'key', 'password', or 'none'
        """
        if settings.SSH_KEY_PATH and os.path.exists(settings.SSH_KEY_PATH):
            return 'key'
        elif settings.SSH_PASSWORD:
            return 'password'
        return 'none'

    async def start(self) -> bool:
        """
        Start the SSH tunnel.
        
        Returns:
            True if tunnel started successfully, False otherwise
        """
        if self._running and self._is_tunnel_active():
            logger.info("SSH tunnel already running")
            return True

        if not settings.SSH_ENABLED:
            logger.info("SSH tunnel disabled in settings, skipping")
            return True

        try:
            # Prepare SSH tunnel configuration
            tunnel_config = {
                'ssh_address_or_host': (settings.SSH_HOST, settings.SSH_PORT),
                'ssh_username': settings.SSH_USER,
                'remote_bind_address': (
                    settings.SSH_REMOTE_MQTT_HOST,
                    settings.SSH_REMOTE_MQTT_PORT
                ),
                'local_bind_address': (
                    settings.SSH_LOCAL_MQTT_HOST,
                    settings.SSH_LOCAL_MQTT_PORT
                ),
                'allow_agent': False,
                'set_keepalive': settings.SSH_KEEPALIVE,
            }

            # Add authentication based on available method
            if self._auth_method == 'key':
                tunnel_config['ssh_pkey'] = settings.SSH_KEY_PATH
                logger.info(f"Using SSH key-based authentication from: {settings.SSH_KEY_PATH}")
            elif self._auth_method == 'password':
                tunnel_config['ssh_password'] = settings.SSH_PASSWORD
                logger.warning("[WARN] Using SSH password authentication. Consider migrating to key-based auth for production.")
            else:
                logger.error("[ERROR] No SSH authentication method configured. Set SSH_KEY_PATH or SSH_PASSWORD.")
                return False

            # Create SSH tunnel with determined configuration
            self._tunnel = SSHTunnelForwarder(**tunnel_config)

            # Start tunnel in thread pool to avoid blocking
            await asyncio.to_thread(self._tunnel.start)
            
            self._running = True
            self._connection_start_time = time.time()
            self._successful_connections += 1
            self._last_connection_error = None
            
            logger.info(
                f"[OK] SSH tunnel established: "
                f"{settings.SSH_HOST}:{settings.SSH_PORT} -> "
                f"{settings.SSH_LOCAL_MQTT_HOST}:{settings.SSH_LOCAL_MQTT_PORT}"
            )
            
            # Start health monitoring task
            asyncio.create_task(self._monitor_loop())
            
            return True

        except Exception as e:
            error_msg = str(e)
            self._last_connection_error = error_msg
            self._failed_connections += 1
            self._record_failure()
            logger.error(f"[ERROR] Failed to start SSH tunnel: {error_msg}")
            self._running = False
            return False

    async def stop(self) -> None:
        """Stop the SSH tunnel."""
        self._running = False
        
        if self._tunnel:
            try:
                self._tunnel.stop()
                logger.info("SSH tunnel stopped")
            except Exception as e:
                logger.error(f"Error stopping SSH tunnel: {e}")
            finally:
                self._tunnel = None

    def _is_tunnel_active(self) -> bool:
        """Check if tunnel is currently active."""
        return (
            self._tunnel is not None
            and self._tunnel.is_active
        )
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        return (
            self._circuit_state == "open"
            and time.time() < self._circuit_open_until
        )
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after successful connection."""
        self._circuit_state = "closed"
        self._failure_count = 0
        self._current_reconnect_interval = self._base_reconnect_interval
        logger.info("Circuit breaker reset after successful connection")
    
    def _record_failure(self) -> None:
        """Record a connection failure and update circuit breaker state."""
        self._failure_count += 1
        self._failed_connections += 1
        
        if self._failure_count >= self._failure_threshold:
            self._circuit_state = "open"
            self._circuit_open_until = time.time() + self._circuit_open_duration
            self._current_reconnect_interval = min(
                self._current_reconnect_interval * 2,
                self._max_reconnect_interval
            )
            logger.warning(
                f"Circuit breaker OPEN after {self._failure_count} failures. "
                f"Will retry after {self._circuit_open_duration}s. "
                f"Next reconnect interval: {self._current_reconnect_interval}s"
            )
    
    def _calculate_backoff(self) -> float:
        """Calculate exponential backoff delay for reconnection."""
        return min(
            self._base_reconnect_interval * (2 ** min(self._failure_count, 6)),
            self._max_reconnect_interval
        )

    async def ensure_tunnel(self) -> bool:
        """
        Ensure tunnel is active, reconnect if needed.
        
        Returns:
            True if tunnel is active, False otherwise
        """
        if not settings.SSH_ENABLED:
            return True

        if self._is_tunnel_active():
            return True

        if not self._running:
            return False
        
        # Check if circuit breaker is open
        if self._is_circuit_open():
            remaining_time = int(self._circuit_open_until - time.time())
            logger.debug(
                f"Circuit breaker is open. Skipping reconnect. "
                f"Remaining cooldown: {remaining_time}s"
            )
            return False

        logger.warning("SSH tunnel inactive, attempting reconnection...")
        return await self._reconnect()

    async def _reconnect(self) -> bool:
        """Attempt to reconnect the SSH tunnel with exponential backoff."""
        self._reconnect_attempts += 1
        
        # Calculate backoff delay
        backoff_delay = self._calculate_backoff()
        
        try:
            # Stop existing tunnel
            if self._tunnel:
                try:
                    await asyncio.to_thread(self._tunnel.stop)
                except Exception:
                    pass
                self._tunnel = None
            
            # Wait before reconnecting (exponential backoff)
            if backoff_delay > 0:
                logger.info(f"Waiting {backoff_delay:.1f}s before reconnect attempt #{self._reconnect_attempts}")
                await asyncio.sleep(backoff_delay)

            # Start new tunnel
            success = await self.start()
            
            if success:
                self._reset_circuit_breaker()
                self._reconnect_attempts = 0
            else:
                self._record_failure()
            
            return success

        except Exception as e:
            error_msg = str(e)
            self._last_connection_error = error_msg
            self._record_failure()
            logger.error(f"Reconnection attempt #{self._reconnect_attempts} failed: {error_msg}")
            return False

    async def _monitor_loop(self) -> None:
        """Background health monitoring loop with circuit breaker."""
        logger.info("SSH tunnel monitor loop started")

        while self._running:
            try:
                now = time.time()
                
                # Periodic health check
                if now - self._last_check >= self._check_interval:
                    self._last_check = now
                    
                    # Check if circuit breaker cooldown has expired
                    if self._circuit_state == "open" and now >= self._circuit_open_until:
                        self._circuit_state = "half-open"
                        logger.info("Circuit breaker entering HALF-OPEN state. Attempting reconnection...")
                    
                    # Perform health check
                    if not self._is_tunnel_active():
                        if self._circuit_state == "half-open":
                            logger.info("Half-open: Testing connection...")
                        
                        logger.warning("Tunnel health check failed, reconnecting...")
                        await self._reconnect()
                    else:
                        # Connection is healthy, update metrics
                        if self._connection_start_time:
                            self._total_connection_time = now - self._connection_start_time
                        
                        # Log connection health periodically
                        if self._successful_connections > 0 and self._reconnect_attempts == 0:
                            logger.debug(
                                f"Tunnel healthy. Uptime: {self._total_connection_time:.0f}s, "
                                f"Total connections: {self._successful_connections}, "
                                f"Failures: {self._failed_connections}"
                            )

            except Exception as e:
                logger.error(f"Error in tunnel monitor loop: {e}")

            await asyncio.sleep(1)

        logger.info("SSH tunnel monitor loop stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current tunnel status with detailed health metrics."""
        uptime = 0.0
        if self._connection_start_time and self._is_tunnel_active():
            uptime = time.time() - self._connection_start_time
        
        return {
            # Basic status
            "running": self._running,
            "active": self._is_tunnel_active(),
            "enabled": settings.SSH_ENABLED,
            
            # Connection details
            "auth_method": self._auth_method,
            "remote_host": settings.SSH_HOST,
            "remote_port": settings.SSH_REMOTE_MQTT_PORT,
            "local_host": settings.SSH_LOCAL_MQTT_HOST,
            "local_port": settings.SSH_LOCAL_MQTT_PORT,
            
            # Health metrics
            "uptime_seconds": round(uptime, 2),
            "total_connection_time": round(self._total_connection_time, 2),
            "successful_connections": self._successful_connections,
            "failed_connections": self._failed_connections,
            "reconnect_attempts": self._reconnect_attempts,
            
            # Circuit breaker status
            "circuit_breaker": {
                "state": self._circuit_state,
                "failure_count": self._failure_count,
                "failure_threshold": self._failure_threshold,
                "cooldown_remaining": max(0, int(self._circuit_open_until - time.time())),
                "next_reconnect_interval": self._current_reconnect_interval,
            },
            
            # Last error
            "last_error": self._last_connection_error,
            
            # Connection quality score (0-100)
            "health_score": self._calculate_health_score(),
        }
    
    def _calculate_health_score(self) -> int:
        """
        Calculate a health score (0-100) based on connection stability.
        
        Returns:
            Health score from 0 (poor) to 100 (excellent)
        """
        if not self._is_tunnel_active():
            return 0
        
        total_attempts = self._successful_connections + self._failed_connections
        if total_attempts == 0:
            return 100
        
        # Base score from success rate
        success_rate = self._successful_connections / total_attempts
        score = int(success_rate * 100)
        
        # Penalty for recent failures
        if self._failure_count > 0:
            score -= min(self._failure_count * 10, 50)
        
        # Penalty for high reconnect attempts
        if self._reconnect_attempts > 0:
            score -= min(self._reconnect_attempts * 5, 30)
        
        # Bonus for long uptime
        if self._total_connection_time > 3600:  # 1 hour
            score += 10
        elif self._total_connection_time > 86400:  # 24 hours
            score += 20
        
        return max(0, min(100, score))


# Global singleton instance
_ssh_tunnel_manager: Optional[SSHTunnelManager] = None


def get_ssh_tunnel() -> SSHTunnelManager:
    """Get or create the SSH tunnel manager singleton."""
    global _ssh_tunnel_manager
    if _ssh_tunnel_manager is None:
        _ssh_tunnel_manager = SSHTunnelManager()
    return _ssh_tunnel_manager
