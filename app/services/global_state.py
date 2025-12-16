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
