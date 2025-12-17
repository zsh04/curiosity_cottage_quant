import logging
import os
from opentelemetry import trace, metrics, _logs
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor


def setup_telemetry(service_name: str = "curiosity-cottage-engine"):
    """
    Sets up OpenTelemetry Tracing, Metrics, and Logging.
    Sends data to local OTel collector (cc_pulse) which forwards to Grafana Cloud.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not endpoint:
        print("Telemetry: OTLP Endpoint not set. Skipping setup.")
        return False

    print(f"Telemetry: Initializing for {service_name} at {endpoint}")

    # Resource
    resource = Resource(attributes={SERVICE_NAME: service_name})

    # --- TRACING ---
    trace_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # --- METRICS ---
    metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- LOGGING ---
    log_exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs")
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    _logs.set_logger_provider(logger_provider)

    # Hijack Python Standard Logging
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    print("Telemetry: OTLP Setup Complete (Trace, Metrics, Logs)")
    return True
