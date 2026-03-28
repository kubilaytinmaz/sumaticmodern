"""
Sumatic Modern IoT - API v1 Endpoints
"""
from app.api.v1.auth import router as auth_router
from app.api.v1.devices import router as devices_router
from app.api.v1.readings import router as readings_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.charts import router as charts_router

__all__ = [
    "auth_router",
    "devices_router",
    "readings_router",
    "analytics_router",
    "dashboard_router",
    "websocket_router",
    "charts_router",
]
