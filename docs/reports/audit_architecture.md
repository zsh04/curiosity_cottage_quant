# Audit Report: Architecture & Telemetry

**Date:** 2025-12-20
**Auditor:** Antigravity (Infrastructure Architect)
**Status:** 🔴 **CRITICAL FAIL**

## 1. Docker Composition Check

**Verdict:** **BROKEN**

- **Missing Service:** The `otel-collector` (often named `cc_pulse` in our configs) is **COMPLETELY MISSING** from `docker-compose.yml`.
  - There is a `cc_config_gen` service (Alpine), but this appears to be a helper script, not the actual collector process.
- **Networking:** Without the collector service, `cc_app` has nowhere to send telemetry.

## 2. Telemetry Pipeline Verification

**Verdict:** **DISCONNECTED**

- **App Config (`telemetry.py` & `config.py`):**
  - `config.py` logic: If `IS_DOCKER=true`, target `http://cc_pulse:4318`.
  - `docker-compose.yml`: **Does NOT set `IS_DOCKER=true`** for the `cc_app` service.
  - **Result:** `cc_app` defaults to `localhost:4318` (inside the container), resulting in `Connection Refused`.
- **Collector Config (`infra/otel/collector-config.yml`):**
  - File exists and looks correct (receivers: 4317/4318, exporters: Grafana).
  - However, it relies on env vars `${GRAFANA_ENDPOINT}` and `${GRAFANA_AUTH}` which must be passed to the (missing) collector container.

## 3. Recommended Fixes (Critical Path)

1. **Add `cc_pulse` to `docker-compose.yml`**:

    ```yaml
    cc_pulse:
      image: otel/opentelemetry-collector-contrib:latest
      container_name: cc_pulse
      command: ["--config=/etc/otel/config.yaml"]
      volumes:
        - ./infra/otel/collector-config.yml:/etc/otel/config.yaml
      environment:
        - GRAFANA_ENDPOINT=${GRAFANA_CLOUD_ENDPOINT}
        - GRAFANA_AUTH=${GRAFANA_CLOUD_AUTH}
      ports:
        - "4317:4317"
        - "4318:4318"
      networks:
        - cc_net
    ```

2. **Update `cc_app` definition**:

    ```yaml
    cc_app:
      environment:
        - IS_DOCKER=true
        - OTEL_EXPORTER_OTLP_ENDPOINT=http://cc_pulse:4318
    ```
