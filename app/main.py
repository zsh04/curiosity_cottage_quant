import os
from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.contrib.opentelemetry import OpenTelemetryConfig

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

# Import Controllers
from api.routes.system import SystemController
from api.routes.signals import SignalsController
from api.routes.actions import ActionsController

# Database
from app.dal.database import init_db


# Observability Setup (Grafana Cloud / OTLP)
def setup_telemetry():
    service_name = os.getenv("OTEL_SERVICE_NAME", "curiosity-cottage-engine")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")

    if endpoint:
        resource = Resource(attributes={SERVICE_NAME: service_name})

        header_dict = {}
        if headers:
            try:
                for h in headers.split(","):
                    k, v = h.split("=", 1)
                    header_dict[k.strip()] = v.strip()
            except Exception as e:
                print(f"Failed to parse OTel headers: {e}")

        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces", headers=header_dict
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        # We don't need to return the config object for middleware approach
        # checks if provider is set
        return True

    return False


# Initialize OTel Global Tracer
otel_enabled = setup_telemetry()

# Initialize Database
init_db()


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
    # Use standard OTel Middleware which picks up global tracer
    middleware=[OpenTelemetryMiddleware] if otel_enabled else [],
    debug=True,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
