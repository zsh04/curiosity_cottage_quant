import logging
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())

from app.agent.nodes.analyst import (
    AnalystAgent,
    save_model_checkpoint,
    load_latest_checkpoint,
)
from app.services.global_state import (
    _global_state_service,
    initialize_global_state_service,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_PERSISTENCE")


def test_persistence_logic():
    print("🚀 Starting Persistence Verification...")

    # 1. Mock DB Session
    mock_db = MagicMock()

    # Initialize global state with mock db
    initialize_global_state_service(mock_db)

    # 2. Mock Logic for Save
    # When save is called, it should execute SQL
    save_model_checkpoint("test_agent", b"DEADBEEF")

    print("Checking SAVE call...")
    mock_db.execute.assert_called()
    call_args = mock_db.execute.call_args
    # We can check if 'INSERT INTO' is in the query text
    query_obj = call_args[0][0]
    if "INSERT INTO model_checkpoints" in str(query_obj):
        print("✅ SQL INSERT confirmed.")
    else:
        print(f"❌ SQL INSERT Missing. Got: {query_obj}")

    # 3. Mock Logic for Load
    # Setup mock to return a result
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (b"DEADBEEF",)
    mock_db.execute.return_value = mock_result

    blob = load_latest_checkpoint("test_agent")
    print(f"Loaded Blob: {blob}")

    if blob == b"DEADBEEF":
        print("✅ BLOB Load confirmed.")
    else:
        print("❌ BLOB Load failed.")

    # 4. Agent Integration Test (Dry Run)
    print("\nTesting Analyst Integration...")
    # Mock load_latest to return None (trigger fallback/init) or return blob
    with patch("app.agent.nodes.analyst.load_latest_checkpoint") as mock_load:
        mock_load.return_value = None  # Simulate fresh start

        # Initialize agent (should try to load)
        # We have to patch MarketService etc to avoid real init
        with (
            patch("app.agent.nodes.analyst.MarketService"),
            patch("app.agent.nodes.analyst.PhysicsService"),
            patch("app.agent.nodes.analyst.ForecastingService"),
            patch("app.agent.nodes.analyst.ReasoningService"),
            patch("app.agent.nodes.analyst.MemoryService"),
        ):
            agent = AnalystAgent()
            # Check if it tried to load
            mock_load.assert_called_with("analyst_lstm")
            print("✅ Analyst attempted to load from DB on init.")


if __name__ == "__main__":
    test_persistence_logic()
