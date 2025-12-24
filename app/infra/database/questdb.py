"""QuestDB client for high-speed time-series storage.

Hypatia's Quill: Writes equity curves, backtest events, and telemetry to QuestDB.
Supports InfluxDB Line Protocol (ILP) for microsecond-latency writes and SQL for queries.

Used by:
- BacktestDAL for event sourcing
- Telemetry collectors for metrics storage
"""

import asyncio
import os
import aiohttp
import logging
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class QuestDBClient:
    """Hypatia's Quill: Client for QuestDB time-series database.

    **Architecture**: Uses dual protocol approach:
    - ILP (port 9009): Microsecond-latency writes via TCP (InfluxDB Line Protocol)
    - REST (port 9000): SQL queries via HTTP

    **Performance**: Handles 1M+ rows/sec on M1 Max (ILP batching).
    """

    def __init__(self):
        self.host = os.getenv("QUESTDB_HOST", "localhost")
        self.http_port = int(os.getenv("QUESTDB_HTTP_PORT", 9000))
        self.ilp_port = int(os.getenv("QUESTDB_ILP_PORT", 9009))
        self.http_url = f"http://{self.host}:{self.http_port}"

    async def ingest_ilp(
        self, table_name: str, symbols: dict, columns: dict, timestamp: datetime = None
    ):
        """
        Send data via InfluxDB Line Protocol over TCP.
        Format: table,symbol=val col=val timestamp
        """
        try:
            # Construct ILP string
            # 1. Table Name
            ilp = f"{table_name}"

            # 2. Symbols (Tags) - comma separated, no spaces
            if symbols:
                tag_set = ",".join([f"{k}={v}" for k, v in symbols.items()])
                ilp += f",{tag_set}"

            # 3. Columns (Fields) - space separator start, then comma
            # Strings must be quoted.
            if columns:
                field_set = []
                for k, v in columns.items():
                    if isinstance(v, str):
                        # Escape quotes (Backslashes not allowed in f-string expressions in Py3.11)
                        escaped_val = v.replace('"', '\\"')
                        val = f'"{escaped_val}"'
                        field_set.append(f"{k}={val}")
                    elif isinstance(v, bool):
                        field_set.append(f"{k}={'t' if v else 'f'}")
                    elif isinstance(v, int):
                        field_set.append(f"{k}={v}i")
                    else:
                        field_set.append(f"{k}={v}")

                ilp += f" {','.join(field_set)}"

            # 4. Timestamp (Nanoseconds)
            ts = timestamp or datetime.utcnow()
            ts_ns = int(ts.timestamp() * 1e9)
            ilp += f" {ts_ns}\n"

            # Execute TCP Send (Fire & Forget mostly, but we adhere to async)
            reader, writer = await asyncio.open_connection(self.host, self.ilp_port)
            writer.write(ilp.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            logger.error(f"QUESTDB ILP ERROR: {e}")

    async def ingest_batch(self, table_name: str, rows: list[dict]):
        """
        Send multiple rows via ILP in a single TCP connection (High Throughput).
        rows: List of dicts, each containing:
              - symbols: dict
              - columns: dict
              - timestamp: datetime (optional)
        """
        if not rows:
            return

        try:
            ilp_payload = ""

            for row in rows:
                # 1. Table
                line = f"{table_name}"

                # 2. Symbols
                syms = row.get("symbols", {})
                if syms:
                    tag_set = ",".join([f"{k}={v}" for k, v in syms.items()])
                    line += f",{tag_set}"

                # 3. Columns
                cols = row.get("columns", {})
                if cols:
                    field_set = []
                    for k, v in cols.items():
                        if isinstance(v, str):
                            escaped_val = v.replace('"', '\\"')
                            val = f'"{escaped_val}"'
                            field_set.append(f"{k}={val}")
                        elif isinstance(v, bool):
                            field_set.append(f"{k}={'t' if v else 'f'}")
                        elif isinstance(v, int):
                            field_set.append(f"{k}={v}i")
                        else:
                            field_set.append(f"{k}={v}")

                    line += f" {','.join(field_set)}"

                # 4. Timestamp
                ts = row.get("timestamp") or datetime.utcnow()
                ts_ns = int(ts.timestamp() * 1e9)
                line += f" {ts_ns}\n"

                ilp_payload += line

            # Execute Batch Send
            reader, writer = await asyncio.open_connection(self.host, self.ilp_port)
            writer.write(ilp_payload.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            logger.error(f"QUESTDB BATCH ERROR: {e}")

    async def query(self, sql: str):
        """
        Execute SQL query via REST API.
        """
        url = f"{self.http_url}/exec"
        params = {"query": sql, "fmt": "json"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    text = await resp.text()
                    logger.error(f"QUESTDB QUERY ERROR: {resp.status} - {text}")
                    return None
