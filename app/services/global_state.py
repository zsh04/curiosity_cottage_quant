"""
Global State Manager - Singleton pattern for observability.
Provides a single StateService instance accessible to all agent nodes.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.state_service import StateService
    from sqlalchemy.orm import Session

_global_state_service: Optional["StateService"] = None
_current_snapshot_id: Optional[int] = None
_halt_flag: bool = False  # Emergency Halt Flag


def initialize_global_state_service(db: "Session"):
    """Initialize the global state service. Call this from run.py before graph execution."""
    from app.services.state_service import StateService

    global _global_state_service
    _global_state_service = StateService(db)


def get_global_state_service() -> Optional["StateService"]:
    """Get the global state service instance."""
    return _global_state_service


def set_current_snapshot_id(snapshot_id: int):
    """Set the current snapshot ID for metric tracking."""
    global _current_snapshot_id
    _current_snapshot_id = snapshot_id


def get_current_snapshot_id() -> Optional[int]:
    """Get the current snapshot ID."""
    return _current_snapshot_id


def reset_global_state():
    """Reset global state (useful for testing)."""
    global _global_state_service, _current_snapshot_id, _halt_flag
    _global_state_service = None
    _current_snapshot_id = None
    _halt_flag = False


def set_system_halt(halted: bool):
    """
    Set the emergency halt flag.
    When True, the agent loop will pause and not execute trades.
    """
    global _halt_flag
    _halt_flag = halted


def is_system_halted() -> bool:
    """
    Check if the system is in emergency halt mode.
    Returns True if halted, False if operational.
    """
    return _halt_flag


def save_model_checkpoint(agent_name: str, blob: bytes):
    """
    Save a model checkpoint to the database.
    """
    if not _global_state_service:
        return

    try:
        from sqlalchemy import text
        # Using raw SQL for simplicity if model definition is not yet in codebase O/R mapping
        # Ideally should use SQLAlchemy Core or ORM.
        # Assuming table 'model_checkpoints' exists.

        # We need to access the session from the service
        session = _global_state_service.db

        query = text("""
            INSERT INTO model_checkpoints (agent_name, blob, created_at)
            VALUES (:agent, :blob, NOW())
        """)

        session.execute(query, {"agent": agent_name, "blob": blob})
        session.commit()
    except Exception as e:
        # Avoid crashing the trading loop on DB error
        print(f"ERROR: Failed to save checkpoint for {agent_name}: {e}")


def load_latest_checkpoint(agent_name: str) -> Optional[bytes]:
    """
    Load the latest model checkpoint from the database.
    """
    if not _global_state_service:
        return None

    try:
        from sqlalchemy import text

        session = _global_state_service.db

        query = text("""
            SELECT blob FROM model_checkpoints
            WHERE agent_name = :agent
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = session.execute(query, {"agent": agent_name}).fetchone()
        if result:
            return result[0]  # Returns bytes
        return None
    except Exception as e:
        print(f"ERROR: Failed to load checkpoint for {agent_name}: {e}")
        return None
