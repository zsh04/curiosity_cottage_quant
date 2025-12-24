# database.py - Purged of SQLAlchemy
# This file is a placeholder until a new QuestDB/Redis DAL is fully adopted.


def get_db():
    """Deprecated Dependency"""
    yield None


def get_async_db():
    """Deprecated Dependency"""
    yield None


def init_db():
    """Deprecated Init"""
    print("⚠️ Database (SQLAlchemy) Initializer skipped (Purged).")


# Exports to satisfy legacy imports in main.py
SessionLocal = None
async_session_maker = None
