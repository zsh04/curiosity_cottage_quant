import sys
from unittest.mock import MagicMock

# --- GLOBAL MOCKS FOR UNIT TESTS ---

# 1. Applicaton Modules (to cut dependency chains)
sys.modules["app.services.rag_forecast"] = MagicMock()
sys.modules["app.services.reasoning"] = MagicMock()
sys.modules["app.services.soros"] = MagicMock()
sys.modules["pydantic_ai"] = MagicMock()
sys.modules["app.dal.state"] = MagicMock()

# 2. Infrastructure
sys.modules["faststream"] = MagicMock()
sys.modules["faststream.redis"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()

# 3. Database
sys.modules["lancedb"] = MagicMock()
mock_lance_pydantic = MagicMock()


# Create dummy classes for LanceModel and Vector
class MockLanceModel:
    pass


class MockVector:
    def __init__(self, dim=None):
        pass


mock_lance_pydantic.LanceModel = MockLanceModel
mock_lance_pydantic.Vector = MockVector
sys.modules["lancedb.pydantic"] = mock_lance_pydantic

# DO NOT MOCK "pyarrow". Let pandas fail to import it and handle it gracefully.

# 4. ML / Heavy Compute
sys.modules["transformers"] = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.onnxruntime"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

import pytest
