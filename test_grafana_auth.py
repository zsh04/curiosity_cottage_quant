import base64
import requests
import sys

# Constants
TOKEN_PART = "eyJvIjoiMTAyODkzNCIsIm4iOiJhbml0Z3Jhdml0eS1hbnRpZ3Jhdml0eTAxIiwiayI6ImNLY2x5alE2NTIyNkIwRzkxU2hzRDJxNCIsIm0iOnsiciI6InByb2QtdXMtd2VzdC0wIn19"
FULL_TOKEN = f"glc_{TOKEN_PART}"
REGION = "prod-us-west-0"
ENDPOINT = f"https://otlp-gateway-{REGION}.grafana.net/otlp/v1/traces"

# Candidate Instance IDs
# 1. Previous ID from .env
ID_CANDIDATE_1 = "830720"
# 2. Org ID (Unlikely but worth try)
ID_CANDIDATE_2 = "1028934"


def test_auth(instance_id):
    auth_str = f"{instance_id}:{FULL_TOKEN}"
    auth_bytes = auth_str.encode("ascii")
    base64_auth = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Authorization": f"Basic {base64_auth}",
        "Content-Type": "application/x-protobuf",
    }

    print(f"Testing ID: {instance_id} ...", end=" ")
    try:
        # Sending empty body might return 400 (Bad Request) if auth is good, 401 if bad.
        response = requests.post(ENDPOINT, headers=headers, data=b"", timeout=5)
        print(f"Status: {response.status_code}")
        return response.status_code != 401
    except Exception as e:
        print(f"Error: {e}")
        return False


print(f"Target: {ENDPOINT}")

if test_auth(ID_CANDIDATE_1):
    print(f"SUCCESS: Instance ID {ID_CANDIDATE_1} is valid.")
    print(f"VALID_ID={ID_CANDIDATE_1}")
elif test_auth(ID_CANDIDATE_2):
    print(f"SUCCESS: Instance ID {ID_CANDIDATE_2} is valid.")
    print(f"VALID_ID={ID_CANDIDATE_2}")
else:
    print("FAILURE: Neither ID worked. User must provide Instance ID.")
