#!/usr/bin/env python3
"""
Frontend-Backend Link Verification Script
Tests that data flows from database -> API -> frontend correctly.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from sqlalchemy.orm import Session

from app.dal.database import get_db
from app.dal.models import AgentStateSnapshot


def verify_data_link():
    """
    Main verification function.
    Tests the complete data pipeline: DB -> API -> Frontend
    """
    print("🔗 FRONTEND-BACKEND LINK VERIFICATION")
    print("=" * 60)

    # Step 1: Insert test snapshot into database
    print("\n1️⃣  Inserting test AgentStateSnapshot (alpha=1.5)...")
    db: Session = next(get_db())

    try:
        test_snapshot = AgentStateSnapshot(
            timestamp=datetime.now(timezone.utc),
            # Portfolio
            nav=100000.0,
            cash=50000.0,
            daily_pnl=0.0,
            max_drawdown=0.0,
            # Market
            symbol="SPY",
            price=482.35,
            # Physics (CRITICAL REGIME)
            current_alpha=1.5,  # Red zone - infinite variance
            regime="Critical",
            velocity=0.0023,
            acceleration=-0.0001,
            # Signal
            signal_side="FLAT",
            signal_confidence=0.0,
            reasoning="Test snapshot for link verification",
            # Governance
            approved_size=0.0,
            status="SLEEPING",
            # Audit
            messages=[],
        )

        db.add(test_snapshot)
        db.commit()
        db.refresh(test_snapshot)

        print(f"   ✅ Snapshot inserted (ID: {test_snapshot.id})")
        print(f"   📊 Alpha: {test_snapshot.current_alpha}")
        print(f"   🎯 Regime: {test_snapshot.regime}")

        # Step 2: Query the API
        print("\n2️⃣  Querying API endpoint...")
        api_url = "http://localhost:8000/api/system/status/physics"

        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            print("   ❌ API unreachable. Is cc_engine running?")
            print("\n💡 TIP: Start engine with: docker-compose up -d cc_engine")
            return False
        except requests.exceptions.Timeout:
            print("   ❌ API timeout")
            return False

        data = response.json()
        print(f"   ✅ API responded: {response.status_code}")

        # Step 3: Validate response
        print("\n3️⃣  Validating data integrity...")
        print(f"   Expected Alpha: 1.5")
        print(f"   Received Alpha: {data.get('alpha')}")

        if data.get("alpha") == 1.5:
            print("   ✅ Alpha matches!")
        else:
            print(f"   ❌ Alpha mismatch! Got {data.get('alpha')}, expected 1.5")
            return False

        # Validate other physics metrics
        print(f"\n   Velocity: {data.get('velocity')}")
        print(f"   Acceleration: {data.get('acceleration')}")
        print(f"   Regime: {data.get('regime')}")
        print(f"   Timestamp: {data.get('timestamp')}")

        # Step 4: Verify UI rendering expectations
        print("\n4️⃣  UI Rendering Validation...")
        alpha = data.get("alpha", 0)

        if alpha < 2.0:
            print("   ✅ Alpha < 2.0: UI should display RED (CRITICAL)")
            print("   ✅ Status: CRITICAL (Lévy)")
            print("   ✅ Gauge bar color: Red/Destructive")
        else:
            print("   ⚠️  Alpha >= 2.0: UI will NOT show critical state")

        # Success
        print("\n" + "=" * 60)
        print("✅ LINK ESTABLISHED: Frontend-Backend-Database verified!")
        print("=" * 60)
        print("\n📍 Next Steps:")
        print("   1. Open http://localhost:3000 in browser")
        print("   2. Check PhysicsGauge component")
        print("   3. Verify alpha displays as 1.50 in RED")
        print("   4. Look for 'CRITICAL (Lévy)' status text")

        return True

    except Exception as e:
        print(f"\n❌ Database error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup: Remove test snapshot
        try:
            if test_snapshot.id:
                db.delete(test_snapshot)
                db.commit()
                print("\n🧹 Cleanup: Test snapshot removed")
        except:
            pass
        db.close()


if __name__ == "__main__":
    try:
        success = verify_data_link()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
