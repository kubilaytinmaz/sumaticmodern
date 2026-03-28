"""
MQTT Logs API Endpoint
Provides real-time MQTT message logs for frontend monitoring.
"""
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import json

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["MQTT Logs"])


class MQTTLogEntry(BaseModel):
    """Single MQTT log entry."""
    timestamp: str
    level: str
    message: str
    device_code: str | None = None
    modem_id: str | None = None
    data: dict | None = None


# In-memory log storage (last 1000 entries)
_mqtt_logs: List[MQTTLogEntry] = []
_max_logs = 1000


def add_mqtt_log(level: str, message: str, device_code: str = None, modem_id: str = None, data: dict = None):
    """Add a log entry to the in-memory storage."""
    entry = MQTTLogEntry(
        timestamp=datetime.utcnow().isoformat(),
        level=level,
        message=message,
        device_code=device_code,
        modem_id=modem_id,
        data=data
    )
    _mqtt_logs.append(entry)
    if len(_mqtt_logs) > _max_logs:
        _mqtt_logs.pop(0)


def get_recent_logs(limit: int = 100) -> List[MQTTLogEntry]:
    """Get recent log entries."""
    return _mqtt_logs[-limit:]


@router.get("/mqtt-logs", response_model=List[MQTTLogEntry])
async def get_mqtt_logs(limit: int = 100):
    """
    Get recent MQTT logs.
    
    Args:
        limit: Maximum number of logs to return (default: 100, max: 1000)
    
    Returns:
        List of MQTT log entries
    """
    limit = min(max(1, limit), 1000)
    return get_recent_logs(limit)


@router.websocket("/ws/mqtt-logs")
async def mqtt_logs_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time MQTT log streaming.
    """
    await websocket.accept()
    logger.info("MQTT logs WebSocket client connected")
    
    try:
        # Send initial logs
        initial_logs = get_recent_logs(50)
        await websocket.send_json({
            "type": "initial",
            "logs": [log.model_dump() for log in initial_logs]
        })
        
        # Keep connection alive and send new logs
        last_index = len(_mqtt_logs)
        
        while True:
            # Wait for new logs
            if len(_mqtt_logs) > last_index:
                new_logs = _mqtt_logs[last_index:]
                await websocket.send_json({
                    "type": "new_logs",
                    "logs": [log.model_dump() for log in new_logs]
                })
                last_index = len(_mqtt_logs)
            
            # Send heartbeat
            await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
            
            # Wait a bit before checking again
            import asyncio
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("MQTT logs WebSocket client disconnected")
    except Exception as e:
        logger.error(f"MQTT logs WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
