from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from api.routes.system import SystemController
from api.routes.signals import SignalsController
from api.routes.actions import ActionsController


@get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
    ],
    path="/api",  # Base path for all routes
    cors_config=cors_config,
    debug=True,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
