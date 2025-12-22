#!/usr/bin/env python3.11
"""
Production Verification Script
Validates all critical components are working correctly.
"""

import psycopg2
import requests
import os
from datetime import datetime


class ProductionVerifier:
    def __init__(self):
        self.results = {}

    def check_database(self):
        """Verify DB connection and recent metrics"""
        try:
            conn = psycopg2.connect(
                dbname="quant_db",
                user="postgres",
                password="password",
                host="localhost",
                port=5432,
            )
            cursor = conn.cursor()

            # Check recent agent metrics
            cursor.execute("""
                SELECT COUNT(*) FROM agent_performance 
                WHERE timestamp > NOW() - INTERVAL '10 minutes'
            """)
            recent_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            self.results["database"] = {
                "status": "PASS" if recent_count > 0 else "WARN",
                "recent_metrics": recent_count,
                "message": f"{recent_count} metrics in last 10 min",
            }
        except Exception as e:
            self.results["database"] = {"status": "FAIL", "error": str(e)}

    def check_api_health(self):
        """Verify API is responding"""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            self.results["api"] = {
                "status": "PASS" if response.status_code == 200 else "FAIL",
                "status_code": response.status_code,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
            }
        except Exception as e:
            self.results["api"] = {"status": "FAIL", "error": str(e)}

    def check_llm_config(self):
        """Verify LLM model is configured"""
        model = os.getenv("LLM_MODEL", "NOT_SET")
        valid_models = ["gemma2:9b", "google/gemma-2-9b-it"]
        is_valid = model in valid_models

        self.results["llm_config"] = {
            "status": "PASS" if is_valid else "WARN",
            "model": model,
            "message": "Correct" if is_valid else f"Expected one of {valid_models}",
        }

    def check_otel_config(self):
        """Verify OTel is configured"""
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self.results["otel"] = {
            "status": "PASS" if endpoint else "WARN",
            "endpoint": endpoint or "NOT_SET",
            "message": "Enabled" if endpoint else "Disabled (optional)",
        }

    def run_all(self):
        """Run all checks"""
        print("🔍 PRODUCTION VERIFICATION\n")
        print(f"Timestamp: {datetime.now()}\n")

        print("Running checks...")
        self.check_database()
        self.check_api_health()
        self.check_llm_config()
        self.check_otel_config()

        self.print_results()

    def print_results(self):
        """Print formatted results"""
        print("\n" + "=" * 60)
        print("VERIFICATION RESULTS")
        print("=" * 60)

        for check_name, result in self.results.items():
            status = result["status"]
            icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")

            print(f"\n{icon} {check_name.upper()}: {status}")
            for key, value in result.items():
                if key != "status":
                    print(f"   {key}: {value}")

        # Overall status
        print("\n" + "=" * 60)
        all_pass = all(r["status"] in ["PASS", "WARN"] for r in self.results.values())
        critical_pass = all(
            r["status"] == "PASS"
            for k, r in self.results.items()
            if k in ["database", "api"]
        )

        if all_pass and critical_pass:
            print("✅ OVERALL: PRODUCTION READY")
        elif critical_pass:
            print("⚠️  OVERALL: PRODUCTION READY (with warnings)")
        else:
            print("❌ OVERALL: NOT READY - Fix critical issues")
        print("=" * 60)


if __name__ == "__main__":
    verifier = ProductionVerifier()
    verifier.run_all()
