"""
Sumatic Modern IoT - WebSocket Endpoint
Real-time updates via WebSocket.
"""
from typing import Optional
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.database import get_db
from app.models.user import User
from app.services.websocket_manager import get_websocket_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time updates.
    
    Connect to: ws://host/api/v1/ws?token=YOUR_JWT_TOKEN
    
    Messages sent to client:
    - {"type": "reading", "device_id": 1, "data": {...}, "timestamp": "..."}
    - {"type": "status_change", "device_id": 1, "status": "ONLINE", ...}
    - {"type": "alert", "alert_type": "...", "title": "...", "message": "...", ...}
    
    Messages accepted from client:
    - {"action": "subscribe", "topic": "readings"} - Subscribe to topic
    - {"action": "subscribe", "device_id": 1} - Subscribe to device
    - {"action": "unsubscribe", "topic": "readings"} - Unsubscribe from topic
    - {"action": "unsubscribe", "device_id": 1} - Unsubscribe from device
    - {"action": "ping"} - Ping/pong
    
    Args:
        websocket: WebSocket connection
        token: Optional JWT token for authentication
        db: Database session
    """
    ws_manager = get_websocket_manager()
    
    # Get user from token if provided
    user = None
    if token:
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = payload.get("sub")
                if user_id:
                    from sqlalchemy import select
                    from app.models.user import User
                    result = await db.execute(
                        select(User).where(User.id == int(user_id))
                    )
                    user = result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
    
    # Generate client ID
    client_id = f"ws_{id(websocket)}"
    
    # Accept connection
    await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        user_id=user.id if user else None,
    )
    
    # Send welcome message
    await ws_manager.send_personal_message(
        websocket,
        {
            "type": "connected",
            "client_id": client_id,
            "authenticated": user is not None,
            "timestamp": ws_manager._active_connections[websocket]["connected_at"],
        },
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    # Handle subscription
                    topic = message.get("topic")
                    device_id = message.get("device_id")
                    
                    if topic:
                        ws_manager.subscribe_to_topic(websocket, topic)
                        await ws_manager.send_personal_message(
                            websocket,
                            {
                                "type": "subscribed",
                                "topic": topic,
                            },
                        )
                    
                    if device_id:
                        ws_manager.subscribe_to_device(websocket, device_id)
                        await ws_manager.send_personal_message(
                            websocket,
                            {
                                "type": "subscribed",
                                "device_id": device_id,
                            },
                        )
                
                elif action == "unsubscribe":
                    # Handle unsubscription
                    topic = message.get("topic")
                    device_id = message.get("device_id")
                    
                    if topic:
                        ws_manager.unsubscribe_from_topic(websocket, topic)
                        await ws_manager.send_personal_message(
                            websocket,
                            {
                                "type": "unsubscribed",
                                "topic": topic,
                            },
                        )
                    
                    if device_id:
                        ws_manager.unsubscribe_from_device(websocket, device_id)
                        await ws_manager.send_personal_message(
                            websocket,
                            {
                                "type": "unsubscribed",
                                "device_id": device_id,
                            },
                        )
                
                elif action == "ping":
                    # Respond to ping
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "pong"},
                    )
                
                else:
                    await ws_manager.send_personal_message(
                        websocket,
                        {
                            "type": "error",
                            "message": f"Unknown action: {action}",
                        },
                    )
            
            except json.JSONDecodeError:
                await ws_manager.send_personal_message(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                    },
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await ws_manager.send_personal_message(
                    websocket,
                    {
                        "type": "error",
                        "message": str(e),
                    },
                )
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.get("/status")
async def websocket_status():
    """
    Get WebSocket connection status.
    
    Returns:
        WebSocket status information
    """
    ws_manager = get_websocket_manager()
    
    return {
        "active_connections": ws_manager.get_connection_count(),
        "connections": ws_manager.get_all_connections_info(),
    }
