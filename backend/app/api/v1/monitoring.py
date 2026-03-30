"""
Sumatic Modern IoT - Memory Monitoring API
Provides real-time memory usage statistics for the backend process.
"""
import os
from typing import Dict, Any

from fastapi import APIRouter

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Monitoring"])


def _get_process_memory() -> Dict[str, Any]:
    """Get process memory info using /proc/self/status (Linux) or psutil fallback."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
            "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2),
            "available": True,
        }
    except ImportError:
        # psutil yoksa /proc/self/status'dan oku (Linux only)
        try:
            with open("/proc/self/status", "r") as f:
                status = {}
                for line in f:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        status[parts[0].strip()] = parts[1].strip()
                
                vmrss = status.get("VmRSS", "0 kB").replace(" kB", "").strip()
                vmsize = status.get("VmSize", "0 kB").replace(" kB", "").strip()
                
                return {
                    "rss_mb": round(int(vmrss) / 1024, 2),
                    "vms_mb": round(int(vmsize) / 1024, 2),
                    "percent": None,
                    "available": True,
                }
        except Exception:
            return {
                "rss_mb": None,
                "vms_mb": None,
                "percent": None,
                "available": False,
            }


@router.get("/monitoring/memory")
async def get_memory_usage() -> Dict[str, Any]:
    """
    Get detailed memory usage statistics.
    
    Returns process memory, MQTT consumer cache, WebSocket connections,
    and other memory-related metrics.
    """
    # Process memory
    process_mem = _get_process_memory()
    
    # MQTT consumer stats
    mqtt_stats = {}
    try:
        from app.services.mqtt_consumer import get_mqtt_consumer
        consumer = get_mqtt_consumer()
        mqtt_stats = consumer.get_memory_stats()
    except Exception as e:
        mqtt_stats = {"error": str(e)}
    
    # WebSocket stats
    ws_stats = {}
    try:
        from app.services.websocket_manager import get_websocket_manager
        ws_manager = get_websocket_manager()
        ws_stats = {
            "active_connections": ws_manager.get_connection_count(),
        }
    except Exception as e:
        ws_stats = {"error": str(e)}
    
    # Spike filter stats
    spike_stats = {}
    try:
        from app.services.spike_filter import get_spike_filter
        spike_filter = get_spike_filter()
        spike_stats = spike_filter.get_stats()
    except Exception as e:
        spike_stats = {"error": str(e)}
    
    # MQTT logs stats
    try:
        from app.api.v1.mqtt_logs import _mqtt_logs
        logs_count = len(_mqtt_logs)
    except Exception:
        logs_count = 0
    
    return {
        "process": process_mem,
        "mqtt_consumer": mqtt_stats,
        "websocket": ws_stats,
        "spike_filter": spike_stats,
        "mqtt_logs_count": logs_count,
    }


@router.post("/monitoring/cleanup")
async def trigger_cleanup() -> Dict[str, Any]:
    """
    Manually trigger RAM cleanup operations.
    
    Cleans up stale WebSocket connections and triggers MQTT consumer cleanup.
    """
    results = {}
    
    # WebSocket stale connection cleanup
    try:
        from app.services.websocket_manager import get_websocket_manager
        ws_manager = get_websocket_manager()
        cleaned = await ws_manager.cleanup_stale_connections()
        results["websocket_cleaned"] = cleaned
    except Exception as e:
        results["websocket_error"] = str(e)
    
    # MQTT consumer cleanup
    try:
        from app.services.mqtt_consumer import get_mqtt_consumer
        consumer = get_mqtt_consumer()
        await consumer._cleanup_old_data()
        results["mqtt_cleanup"] = "ok"
    except Exception as e:
        results["mqtt_cleanup_error"] = str(e)
    
    # Spike filter stats
    try:
        from app.services.spike_filter import get_spike_filter
        spike_filter = get_spike_filter()
        results["spike_filter_stats"] = spike_filter.get_stats()
    except Exception as e:
        results["spike_filter_error"] = str(e)
    
    # Memory after cleanup
    results["memory_after"] = _get_process_memory()
    
    return results
