#!/bin/sh
# Strip "Authorization=" prefix if present
clean_token=$(echo "$HEADERS" | sed 's/Authorization=//')

# Replace placeholder in template. 
# We use | as delimiter assuming token is safe (Base64 is safe).
sed "s|\${GRAFANA_AUTH}|$clean_token|g" /work/collector-config.template.yml > /work/collector-config-generated.yml

echo "Config generated with token length: ${#clean_token}"
chmod 644 /work/collector-config-generated.yml
