# The Evolution of Curiosity Cottage Quant

**A Context-Heavy History of the Architecture**

> *"Architecture is the frozen history of decision making."*

This document serves as the **Narrative Source of Truth**, explaining the *Why* behind the system's critical pivots. It is strictly internal and adheres to the [Diátaxis](https://diataxis.fr/) "Explanation" quadrant.

---

## 🏛️ v36.0: The Constitutional Era (Law Zero)

**Context:**
The system was functional but fragile. "Silent failures" were common—latency would spike, but the bot would continue trying to trade, resulting in stale data execution.

**The Pivot:**
We realized that **Latency is Physics**. A bot cannot trade reflexivity if its own observation of time is flawed.

**Changes:**

1. **Law Zero (System Health)**: We implemented a `SystemHealth` monitor. If tick-to-trade latency jitter exceeds 50ms, the system *must* halt.
2. **Vector Contracts**: Agents stopped passing loose dictionaries (`dict`) and began exchanging strict **Pydantic Vectors** (e.g., `PhysicsVector`, `OODAVector`).
    * *Effect*: If `Mass` is missing, the system crashes loudly rather than trading blindly.

---

## 🛡️ v43.0: Production Hardening

**Context:**
The bot was trading effectively in simulation, but "Magic Numbers" (hardcoded assumptions) were scattered everywhere. Fees were assumed to be $0, and risk-free rates were static constants.

**The Pivot:**
We adopted the mantra: **"Trust Nothing, Verify Everything."**

**Changes:**

1. **FRED Integration**: We killed the hardcoded `4.0%` risk-free rate. The bot now fetches dynamic Treasury yields (e.g., 4.16%) daily from the St. Louis Fed.
2. **Broker Abstraction**: We moved fee logic out of the code and into Environment Variables (`COMMISSION_PER_SHARE`).
3. **No Mocks in PROD**: We added strict guards (`if ENV == "PROD" and model is None: raise Error`) to ensure we never trade on mock data in production.

---

## 🧹 Phase 43.5: The Great Consolidation

**Context:**
We discovered a "Split Brain" architecture. We had an `api/` directory (Legacy) and an `app/api/` directory (Modern). This created confusion about which controller owned the "Kill Switch."

**The Action:**
We executed a ruthless cleanup.

* **Deleted**: `api/` (Legacy)
* **Merged**: All endpoints into `app/api/` (Canonical)
* Result: A Single Source of Truth for system control.

---

## 👁️ v44.0: The Glass Engine (Observability)

**Context:**
The agents were working, but they were "Black Boxes." We saw the Input (Tick) and the Output (Order), but the reasoning—the *OODA Loop*—was invisible.

**The Pivot:**
We decided to "Illuminate the Inner Loop."

**Changes:**

1. **Inner Loop Telemetry**: We added granular `[INNER LOOP]` logs for every cognitive step:
    * `🌀 SOROS`: Scanning Regime...
    * `🤔 BOYD`: Calculate Urgency (Momentum -> Jerk)...
    * `🗳️ COUNCIL`: Voting Breakdown (Trend=Buy, LSTM=Sell)...
    * `⚖️ NASH`: Equilibrium Audit...
2. **Orjson Serialization**: We optimized the API layer to use `orjson`, reducing serialization latency by 5x to handle the high volume of telemetry data.

---

## 🔭 Phase 44.5: The Kepler Protocol (Unique Pulse)

**Context:**
We identified a critical flaw: **Echo Trading**.
If the "Scanner" (Soros) took 5 seconds to run, but the "Loop" ran every 1 second, the agent would process the *exact same market snapshot* 5 times, potentially placing duplicate trades.

**The Pivot:**
We decoupled the **Data Pulse** from the **Execution Loop**.

**Changes:**

1. **The Payload**: We defined a `KeplerPayload` with a unique UUID4 `scan_id`.
2. **The Veto**: The Soros agent was taught to remember the `last_scan_id`. If it sees the same ID again, it **VETOES** the cycle and sleeps.
3. *Result*: The bot only expends energy on fresh information (Entropy reduction).

---

*Verified against Project Baseline: Dec 24, 2025*
