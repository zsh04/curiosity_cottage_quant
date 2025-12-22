import sys
import os
import logging

# Ensure app is in path
sys.path.append(os.getcwd())

from app.services.reasoning import get_reasoning_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_mlx_loading():
    print("🧪 Verifying Reasoning Service Initialization...")

    # Initialize Service
    service = get_reasoning_service()

    print(f"🧐 Detected Mode: {service.mode}")

    if service.mode == "MLX_NATIVE":
        print("✅ SUCCESS: Reasoning Service engaged MLX Native mode.")
        if hasattr(service.agent, "model"):
            print(f"   Agent Model Adapter: {service.agent.model}")
    elif service.mode == "OLLAMA_BRIDGE":
        print("⚠️ NOTICE: Reasoning Service fell back to Ollama Bridge.")
        print("   (This is expected if not on Apple Silicon or FORCE_OLLAMA=true)")
    else:
        print(f"❌ ERROR: Unknown Mode: {service.mode}")


if __name__ == "__main__":
    verify_mlx_loading()
