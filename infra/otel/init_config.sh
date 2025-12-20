#!/bin/sh
# Strip "Authorization=" prefix if present
clean_token=$(echo "$HEADERS" | sed 's/Authorization=//')

# Replace placeholders in template
# Use | as delimiter (Base64 tokens are safe)
sed "s|\${GRAFANA_AUTH}|$clean_token|g; s|\${GRAFANA_ENDPOINT}|$OTEL_EXPORTER_OTLP_ENDPOINT|g" \
  /work/collector-config.template.yml > /work/collector-config-generated.yml

echo "✅ Config generated:"
echo "  - Endpoint: $OTEL_EXPORTER_OTLP_ENDPOINT"
echo "  - Token length: ${#clean_token}"
chmod 644 /work/collector-config-generated.yml
