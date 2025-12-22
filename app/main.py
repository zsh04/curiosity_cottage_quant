from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
from api.routes.orders import OrdersController
from api.routes.market import MarketController
from app.api.routes.telemetry import TelemetryController
from app.api.routes.websocket import BrainStream
from app.api.routes.backtest import BacktestController, BacktestStream

# Database & State
from app.dal.database import init_db, SessionLocal, async_session_maker
from app.services.global_state import initialize_global_state_service
import logging

logger = logging.getLogger(__name__)

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
    # 1. WAKE UP THE DB SERVICE
    logger.info("🔌 Initializing Global State Service...")
    # Fix: Pass the factory, not a session instance
    try:
        initialize_global_state_service(SessionLocal)
        logger.info("✅ Global State Service Connected")
    except Exception as e:
        logger.error(f"❌ Failed to init Global State: {e}")

    # 2. START THE HEART
    logger.info("🧠 Starting Cognitive Engine...")
    task = asyncio.create_task(run_agent_service())

    try:
        yield
    finally:
        # 3. STOP THE HEART
        logger.info("🛑 Lifespan: Stopping Agent Service...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("✅ Agent Service Stopped Cleanly")

        # Close the DB session held by global state (if possible/needed)
        # db.close() # Factory used now


# Configure CORS
cors_config = CORSConfig(
    allow_origins=["*"],
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
        OrdersController,
        MarketController,
        TelemetryController,
        BrainStream,
        BacktestController,
        BacktestStream,
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
