import asyncio
import os
import asyncpg
from typing import Optional


class DatabaseSchema:
    """
    Manages TimescaleDB Schema and Initialization.
    """

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/quant_db"
        )

    async def init_db(self):
        """
        Initialize database schema and Hypertables.
        """
        conn = await asyncpg.connect(self.dsn)
        try:
            # 1. Market Bars Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_bars (
                    time        TIMESTAMPTZ NOT NULL,
                    symbol      TEXT NOT NULL,
                    open        DOUBLE PRECISION,
                    high        DOUBLE PRECISION,
                    low         DOUBLE PRECISION,
                    close       DOUBLE PRECISION,
                    volume      BIGINT
                );
            """)

            # Convert to Hypertable (TimescaleDB specific)
            # We catch error in case it's already a hypertable
            try:
                await conn.execute(
                    "SELECT create_hypertable('market_bars', 'time', if_not_exists => TRUE);"
                )
            except Exception as e:
                print(f"Hypertable creation note: {e}")

            # 2. Trade Decisions Table (Log)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_decisions (
                    id              SERIAL PRIMARY KEY,
                    timestamp       TIMESTAMPTZ DEFAULT NOW(),
                    symbol          TEXT,
                    regime          TEXT,
                    alpha           DOUBLE PRECISION,
                    decision        TEXT,
                    risk_score      DOUBLE PRECISION 
                );
            """)

            print("Database Schema Initialized Successfully.")

        finally:
            await conn.close()


if __name__ == "__main__":
    schema = DatabaseSchema()
    asyncio.run(schema.init_db())
