"""
Sumatic Modern IoT - WebSocket Manager
Manages WebSocket connections and real-time updates.
"""
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Singleton WebSocket connection manager.
    Handles connection lifecycle and message broadcasting.
    """

    _instance: Optional["WebSocketManager"] = None

    def __new__(cls) -> "WebSocketManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        # Active connections: {websocket: client_info}
        self._active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        # Device subscriptions: {device_id: set of websockets}
        self._device_subscriptions: Dict[int, Set[WebSocket]] = {}
        # Topic subscriptions: {topic: set of websockets}
        self._topic_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        logger.info("WebSocketManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            client_id: Optional client identifier
            user_id: Optional authenticated user ID
        """
        await websocket.accept()
        
        self._active_connections[websocket] = {
            "client_id": client_id or f"client_{id(websocket)}",
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "subscriptions": set(),
        }
        
        logger.info(
            f"WebSocket connected: {client_id}, total connections: {len(self._active_connections)}"
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection and clean up subscriptions.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket not in self._active_connections:
            return
        
        client_info = self._active_connections[websocket]
        client_id = client_info.get("client_id", "unknown")
        
        # Clean up device subscriptions
        for device_id in list(self._device_subscriptions.keys()):
            self._device_subscriptions[device_id].discard(websocket)
            if not self._device_subscriptions[device_id]:
                del self._device_subscriptions[device_id]
        
        # Clean up topic subscriptions
        for topic in list(self._topic_subscriptions.keys()):
            self._topic_subscriptions[topic].discard(websocket)
            if not self._topic_subscriptions[topic]:
                del self._topic_subscriptions[topic]
        
        # Remove connection
        del self._active_connections[websocket]
        
        logger.info(
            f"WebSocket disconnected: {client_id}, remaining connections: {len(self._active_connections)}"
        )

    def subscribe_to_device(self, websocket: WebSocket, device_id: int) -> None:
        """
        Subscribe a connection to device updates.
        
        Args:
            websocket: WebSocket connection
            device_id: Device ID to subscribe to
        """
        if websocket not in self._active_connections:
            return
        
        if device_id not in self._device_subscriptions:
            self._device_subscriptions[device_id] = set()
        
        self._device_subscriptions[device_id].add(websocket)
        self._active_connections[websocket]["subscriptions"].add(f"device:{device_id}")
        
        logger.debug(f"WebSocket subscribed to device {device_id}")

    def unsubscribe_from_device(self, websocket: WebSocket, device_id: int) -> None:
        """
        Unsubscribe a connection from device updates.
        
        Args:
            websocket: WebSocket connection
            device_id: Device ID to unsubscribe from
        """
        if device_id in self._device_subscriptions:
            self._device_subscriptions[device_id].discard(websocket)
            if not self._device_subscriptions[device_id]:
                del self._device_subscriptions[device_id]
        
        if websocket in self._active_connections:
            self._active_connections[websocket]["subscriptions"].discard(f"device:{device_id}")

    def subscribe_to_topic(self, websocket: WebSocket, topic: str) -> None:
        """
        Subscribe a connection to a topic.
        
        Args:
            websocket: WebSocket connection
            topic: Topic to subscribe to (e.g., "readings", "alerts", "status")
        """
        if websocket not in self._active_connections:
            return
        
        if topic not in self._topic_subscriptions:
            self._topic_subscriptions[topic] = set()
        
        self._topic_subscriptions[topic].add(websocket)
        self._active_connections[websocket]["subscriptions"].add(f"topic:{topic}")
        
        logger.debug(f"WebSocket subscribed to topic {topic}")

    def unsubscribe_from_topic(self, websocket: WebSocket, topic: str) -> None:
        """
        Unsubscribe a connection from a topic.
        
        Args:
            websocket: WebSocket connection
            topic: Topic to unsubscribe from
        """
        if topic in self._topic_subscriptions:
            self._topic_subscriptions[topic].discard(websocket)
            if not self._topic_subscriptions[topic]:
                del self._topic_subscriptions[topic]
        
        if websocket in self._active_connections:
            self._active_connections[websocket]["subscriptions"].discard(f"topic:{topic}")

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            websocket: Target WebSocket connection
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if websocket not in self._active_connections:
            return False
        
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
                return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
        
        return False

    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        disconnected = []
        
        for websocket in self._active_connections:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                    sent_count += 1
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
        
        return sent_count

    async def broadcast_to_device(
        self,
        device_id: int,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all clients subscribed to a device.
        
        Args:
            device_id: Device ID
            message: Message to broadcast
            
        Returns:
            Number of clients that received the message
        """
        if device_id not in self._device_subscriptions:
            return 0
        
        sent_count = 0
        disconnected = []
        
        for websocket in self._device_subscriptions[device_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                    sent_count += 1
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to device subscribers: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
        
        return sent_count

    async def broadcast_to_topic(
        self,
        topic: str,
        message: Dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all clients subscribed to a topic.
        
        Args:
            topic: Topic name
            message: Message to broadcast
            
        Returns:
            Number of clients that received the message
        """
        if topic not in self._topic_subscriptions:
            return 0
        
        sent_count = 0
        disconnected = []
        
        for websocket in self._topic_subscriptions[topic]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                    sent_count += 1
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to topic subscribers: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)
        
        return sent_count

    async def broadcast_reading(
        self,
        device_id: int,
        reading_data: Dict[str, Any],
    ) -> None:
        """
        Broadcast a new reading to subscribers.
        
        Args:
            device_id: Device ID
            reading_data: Reading data
        """
        message = {
            "type": "device_reading",
            "device_id": device_id,
            "data": reading_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Send to device subscribers
        await self.broadcast_to_device(device_id, message)
        
        # Also send to "readings" topic subscribers
        await self.broadcast_to_topic("readings", message)

    async def broadcast_status_change(
        self,
        device_id: int,
        status: str,
        previous_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Broadcast a device status change.
        
        Args:
            device_id: Device ID
            status: New status (ONLINE, OFFLINE, PENDING)
            previous_status: Previous status
            metadata: Additional metadata
        """
        message = {
            "type": "status_change",
            "device_id": device_id,
            "status": status,
            "previous_status": previous_status,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Send to device subscribers
        await self.broadcast_to_device(device_id, message)
        
        # Also send to "status" topic subscribers
        await self.broadcast_to_topic("status", message)

    async def broadcast_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        device_id: Optional[int] = None,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Broadcast an alert to all clients.
        
        Args:
            alert_type: Type of alert (e.g., "device_offline", "fault_detected")
            title: Alert title
            message: Alert message
            device_id: Optional related device ID
            severity: Alert severity (info, warning, error, critical)
            metadata: Additional metadata
        """
        alert_data = {
            "type": "alert",
            "alert_type": alert_type,
            "title": title,
            "message": message,
            "severity": severity,
            "device_id": device_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Broadcast to all clients
        await self.broadcast_to_all(alert_data)
        
        # Also send to "alerts" topic subscribers
        await self.broadcast_to_topic("alerts", alert_data)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._active_connections)

    def get_device_subscriber_count(self, device_id: int) -> int:
        """Get the number of subscribers for a device."""
        if device_id not in self._device_subscriptions:
            return 0
        return len(self._device_subscriptions[device_id])

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get the number of subscribers for a topic."""
        if topic not in self._topic_subscriptions:
            return 0
        return len(self._topic_subscriptions[topic])

    def get_connection_info(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection."""
        return self._active_connections.get(websocket)

    def get_all_connections_info(self) -> list:
        """Get information about all connections."""
        return [
            {
                "client_id": info["client_id"],
                "user_id": info["user_id"],
                "connected_at": info["connected_at"],
                "subscriptions": list(info["subscriptions"]),
            }
            for info in self._active_connections.values()
        ]


# Global singleton instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get the WebSocket manager singleton."""
    return websocket_manager
