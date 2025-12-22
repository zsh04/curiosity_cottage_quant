import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from app.infra.database.questdb import QuestDBClient


async def init_schema():
    print("📜 Hypatia: Initializing QuestDB Schema...")
    client = QuestDBClient()

    # Path to SQL file
    sql_path = Path("infra/db/init/006_backtest_audit.sql")
    if not sql_path.exists():
        print(f"❌ Error: Schema file not found at {sql_path}")
        return

    # Read SQL
    with open(sql_path, "r") as f:
        sql_content = f.read()

    # Split by semicolon to handle multiple statements (rudimentary)
    # QuestDB REST /exec usually handles one statement, or we can iterate.
    # The file has comments and 2 CREATE TABLE statements.

    # Simple parser: remove comments, split by ';'
    statements = []
    current_stmt = []

    for line in sql_content.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        current_stmt.append(line)
        if line.endswith(";"):
            statements.append(" ".join(current_stmt))
            current_stmt = []

    # Execute
    for stmt in statements:
        # cleanup
        stmt = stmt.strip().rstrip(";")
        if not stmt:
            continue

        print(f"Executing: {stmt[:50]}...")
        result = await client.query(stmt)
        if result and "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("✅ Success")

    print("📜 Schema Initialization Complete.")


if __name__ == "__main__":
    asyncio.run(init_schema())
