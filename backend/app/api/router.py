"""
Sumatic Modern IoT - API Router
Combines all v1 routers into a single API router.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.devices import router as devices_router
from app.api.v1.readings import router as readings_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.charts import router as charts_router
from app.api.v1.mqtt_logs import router as mqtt_logs_router


def create_api_router() -> APIRouter:
    """
    Create and return the main API router with all v1 sub-routers.
    
    Returns:
        APIRouter with all endpoints registered
    """
    api_router = APIRouter()
    
    # Include all v1 routers
    api_router.include_router(auth_router)
    api_router.include_router(devices_router)
    api_router.include_router(readings_router)
    api_router.include_router(analytics_router)
    api_router.include_router(dashboard_router)
    api_router.include_router(websocket_router)
    api_router.include_router(charts_router)
    api_router.include_router(mqtt_logs_router)
    
    return api_router
  
