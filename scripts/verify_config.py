from app.core.config import settings

print(f"ENDPOINT: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
print(f"IS_DOCKER: {settings.IS_DOCKER}")
