from app.infra.database.questdb import QuestDBClient
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestDAL:
    """
    THE LIBRARY OF HYPATIA.
    Event Sourcing DAL for Backtest Lifecycle and Equity Curves.
    """

    def __init__(self):
        # We instantiate the client directly.
        # In a larger app, this would be injected.
        self.db = QuestDBClient()

    # --- WRITER METHODS (APPEND ONLY) ---

    async def log_spawn(self, run_id: str, ticker: str, config: dict):
        """
        Log the initialization of a simulation.
        event_type: SPAWNED
        """
        await self.db.ingest_ilp(
            table_name="backtest_events",
            symbols={"run_id": run_id, "ticker": ticker, "event_type": "SPAWNED"},
            columns={"payload": json.dumps(config)},
        )
        logger.info(f"📜 Hypatia: Spawned scroll for {run_id}")

    async def log_completion(self, run_id: str, ticker: str, metrics: dict):
        """
        Log the successful completion of a simulation.
        event_type: COMPLETED
        """
        await self.db.ingest_ilp(
            table_name="backtest_events",
            symbols={"run_id": run_id, "ticker": ticker, "event_type": "COMPLETED"},
            columns={"payload": json.dumps(metrics)},
        )

    async def log_failure(self, run_id: str, ticker: str, error: str):
        """
        Log a simulation failure.
        event_type: FAILED
        """
        await self.db.ingest_ilp(
            table_name="backtest_events",
            symbols={"run_id": run_id, "ticker": ticker, "event_type": "FAILED"},
            columns={"payload": json.dumps({"error": error})},
        )

    async def log_equity_curve(self, run_id: str, equity_list: list[dict]):
        """
        Log a full equity curve in batch mode.
        equity_list: List of dicts with {"timestamp": dt, "equity": float, "drawdown": float}
        """
        rows = []
        for point in equity_list:
            rows.append(
                {
                    "symbols": {"run_id": run_id},
                    "columns": {
                        "equity": point["equity"],
                        "drawdown": point["drawdown"],
                    },
                    "timestamp": point["timestamp"],
                }
            )

        if rows:
            await self.db.ingest_batch(table_name="backtest_equity", rows=rows)
            # logger.info(f"📜 Hypatia: Ingested {len(rows)} equity points for {run_id}")

    # --- READER METHODS (LATEST BY) ---

    async def get_run_status(self, run_id: str) -> str:
        """
        Get the specific event type of the LATEST event for this run_id.
        Query: LATEST ON ts PARTITION BY run_id
        """
        sql = f"SELECT event_type FROM backtest_events WHERE run_id = '{run_id}' LATEST ON ts PARTITION BY run_id"
        result = await self.db.query(sql)

        if result and result.get("dataset"):
            # QuestDB returns dataset as list of lists.
            # Columns are in 'columns'
            # We asked for event_type only.
            return result["dataset"][0][0]
        return "UNKNOWN"

    async def get_full_report(self, run_id: str):
        """
        Reconstruct the full report from the event log.
        """
        # 1. Get Events (Config + Metrics)
        events_sql = f"SELECT event_type, payload, ts FROM backtest_events WHERE run_id = '{run_id}' ORDER BY ts"
        events_res = await self.db.query(events_sql)

        # 2. Get Equity Curve
        equity_sql = f"SELECT ts, equity, drawdown FROM backtest_equity WHERE run_id = '{run_id}' ORDER BY ts"
        equity_res = await self.db.query(equity_sql)

        return {
            "events": events_res.get("dataset", []) if events_res else [],
            "equity_curve": equity_res.get("dataset", []) if equity_res else [],
        }
