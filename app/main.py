from contextlib import asynccontextmanager
from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

from app.core.telemetry import setup_telemetry
import asyncio
from app.agent.loop import run_agent_service

# Import Controllers
from api.routes.system import SystemController
from api.routes.signals import SignalsController
from api.routes.actions import ActionsController
from app.api.routes.telemetry import TelemetryController

# Database
from app.dal.database import init_db


# Observability Setup (Grafana Cloud / OTLP)


# Initialize OTel Global Tracer
otel_enabled = setup_telemetry()

# Initialize Database
init_db()


@get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@asynccontextmanager
async def lifespan(app: Litestar):
    """
    Lifespan context manager to handle startup and shutdown events.
    Starts the Agent Service background task.
    """
    print("🔄 Lifespan: Starting Agent Service...")
    task = asyncio.create_task(run_agent_service())
    try:
        yield
    finally:
        print("🛑 Lifespan: Stopping Agent Service...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("✅ Agent Service Stopped Cleanly")


# Configure CORS
cors_config = CORSConfig(
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize App
app = Litestar(
    route_handlers=[
        health_check,
        SystemController,
        SignalsController,
        ActionsController,
        TelemetryController,
    ],
    path="/api",  # Base path for all routes
    cors_config=cors_config,
    # Use standard OTel Middleware which picks up global tracer
    middleware=[OpenTelemetryMiddleware] if otel_enabled else [],
    debug=True,
    lifespan=[lifespan],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
