import time
import math
import logging
import os
import sys
from dotenv import load_dotenv

# Ensure app imports work
sys.path.append(os.getcwd())

# Load Env
load_dotenv()

# Force standard OTLP endpoint for verification if missing
if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
    print("⚠️  Forced OTLP Endpoint to http://localhost:4318 for verification.")

from opentelemetry import trace, metrics
from app.core.telemetry import setup_telemetry

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NervousSystemVerifier")


def main():
    print("🧠 Starting Nervous System Verification...")

    # 1. Initialize Telemetry
    if not setup_telemetry(service_name="cc-verifier-probe"):
        print("❌ Failed to setup telemetry. Check OTLP Endpoint.")
        return

    # 2. Tracing: Send a unique span
    tracer = trace.get_tracer("cc.verifier")

    print("📡 Sending Trace Span: 'system_check.ping'...")
    with tracer.start_as_current_span("system_check.ping") as span:
        span.set_attribute("status", "green")
        span.set_attribute("mode", "metal")
        span.set_attribute("check_id", str(time.time()))

        logger.info("Trace Span Active. Logging inside span context.")
        time.sleep(0.5)  # Simulate work
        span.add_event("Ping Sent")

    print("✅ Trace sent.")

    # 3. Metrics: Sine Wave Generator
    meter = metrics.get_meter("cc.verifier")

    # Create Observable Gauge for Sine Wave
    # Note: OTel Python Observable Gauge uses a callback.
    # For simple verification, we can use a Counter or Histogram, or UpDownCounter.
    # But "Sine Wave" implies a Value Recorder (Gauge).
    # Since ObservableGauge callbacks are asynchronous, we might simpler use an UpDownCounter or
    # explicitly set a callback that reads global state.

    # Let's use a standard Gauge if available (Histogram is better for distribution, UpDownCounter for sums).
    # Standard OTel "Gauge" is "ObservableGauge".
    # We will simulate "sending" a metric by using a Histogram to record values, which typically shows up as a heatmap or average.
    # Or better, an asynchronous gauge.

    print("🌊 Generating Sine Wave Metric (cc_test_sine)...")

    sine_value = 0.0

    def sine_callback(options):
        # We can't easily pass state into callback without a class or global.
        # But this runs once per export interval.
        # For verification, let's just use a Histogram loop.
        yield metrics.Observation(sine_value, {"dimension": "x"})

    # Actually, let's just use a Histogram for "Test Metric" as it's easiest to "push".
    sine_metric = meter.create_histogram(
        name="cc_test_sine", description="A test sine wave for visualization", unit="1"
    )

    # Loop to generate some data points
    # Shift sine wave to be positive (10-30 range) to avoid Histogram negative value warnings
    try:
        print("🌊 Sending Sine Wave (Positive Shifted)...")
        for i in range(10):
            val = (math.sin(i * 0.5) + 2.0) * 10
            sine_metric.record(val, {"iteration": str(i)})
            logger.info(f"Recorded Metric: {val:.2f}")
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass

    print("✅ Metrics sent.")

    # 4. Logs
    logger.warning("This is a TEST WARNING log to verify OTLP Logging.")
    logger.error("This is a TEST ERROR log to verify OTLP Logging.")
    print("✅ Logs generated.")

    # Force Flush / Shutdown
    print("⏳ Flushing Telemetry...")
    try:
        trace.get_tracer_provider().shutdown()
        metrics.get_meter_provider().shutdown()
        from opentelemetry.sdk._logs import get_logger_provider

        get_logger_provider().shutdown()
    except Exception as e:
        print(f"⚠️ Flush Warning: {e}")

    print("\n---------------------------------------------------")
    print("🎉 Verification Complete.")
    print("Check Grafana at: http://localhost:3000")
    print("Explore -> Select Data Source (Traces/Metrics/Logs)")
    print("Look for service_name='cc-verifier-probe'")
    print("---------------------------------------------------")


if __name__ == "__main__":
    main()
