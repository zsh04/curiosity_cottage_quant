# 🏥 Deep Architectural Audit: Curiosity Cottage V2

**Evaluator:** Antigravity (Chief Systems Architect)
**Date:** 2025-12-16
**Subject:** CC-V2 "Services over Scripts" Transition Readiness

---

## 1. Executive Summary
The CC-V2 codebase currently suffers from **"Prototype-itis."** While the infrastructure foundations (Docker, Timescale, OpenTelemetry) are remarkably solid, the application layer is fractured. We are maintaining two separate realities (Script vs. API), three different ways to fetch data, and a "God Node" (Analyst) that tries to do everything at once.

**Global Verdict:** 🔴 **NOT PRODUCTION READY**
**Primary Risk:** **Observability Black Hole.** The embedded agent service in `main.py` fails to initialize the Global State Service, meaning the "Production" agent will run silently without saving any metrics to the database.

---

## 2. Vector Analysis

### 🚨 Vector 1: The "Split Brain" Risk
**Context:** `app/main.py` (API) vs. `scripts/run_agent_loop.py` (Script).

*   **Findings:**
    *   **Logic Divergence:** Both run `app_graph.ainvoke`, but they use completely different entry points. The script manually loads `.env` and prints to stdout. The Service (`app/agent/loop.py`) runs in a background task.
    *   **The "Silent" Bug (CRITICAL):** The Service (`app/agent/loop.py`) uses `get_global_state_service()` to define where to save metrics. However, `app/main.py` **never calls `initialize_global_state_service(db)`**.
    *   **Consequence:** When you run the production backend, the Agent will run, but `analyst_node` will likely crash or silently fail to save metrics because `_global_state_service` is `None`. The Dashboard will be empty.
    *   **Visibility:** The Script prints heavily to console. The Service relies on `StateBroadcaster`, but if the node logic fails (due to missing State Service), the broadcast might contain error states or nothing.

**Severity:** 🟥 **CRITICAL**
**Verdict:** **Broken Integration.** The Service loop is currently a zombie process—alive but disconnected from the brain (DB/State).

### 👯 Vector 2: The "Data Schizophrenia" Risk
**Context:** `app/adapters/` vs. `app/data/` vs. Direct SDK usage.

*   **Findings:**
    *   **Triplication:**
        1.  `app/data/alpaca.py`: Defines `AlpacaProvider` (Unused).
        2.  `app/adapters/alpaca.py`: Defines `AlpacaAdapter` (Unused).
        3.  `app/adapters/market.py`: **Bypasses both** and instantiates `alpaca.data.historical.StockHistoricalDataClient` directly.
    *   **Source of Truth:** There is no single source of truth. `MarketAdapter` is the de-facto "Live" adapter, but it mixes high-level logic with raw SDK calls.
    *   **Fragility:** `MarketAdapter` fetches Returns, then `AnalystAgent` manually reconstructs Prices from those Returns. This is mathematically fragile and redundant (`alpaca-py` gives prices directly!).

**Severity:** 🟧 **HIGH**
**Verdict:** **Spaghetti Data Layer.** We are maintaining dead code (`app/data`) and inconsistent active code (`app/adapters`).

### 🐘 Vector 3: The "Fat Node" Syndrome
**Context:** `app/agent/nodes/analyst.py`.

*   **Findings:**
    *   **Overloaded Responsibilities:** The `AnalystAgent` does: Data Fetching (IO) + Data Transformation (Math) + Strategy Tournament (Heavy Compute) + Signal Generation (Logic) + Metric Saving (DB IO).
    *   **The "Tournament" Bottleneck:** It runs a micro-backtest on *every single tick* (looping through strategies, calculating pandas dataframes). This works for a prototype but is disastrous for a production event loop. It will block the async loop if not carefully managed (pandas is CPU bound).
    *   **Testability:** Low. It instantiates 5 different adapters in `__init__`, making it a nightmare to mock for unit tests.

**Severity:** 🟧 **HIGH**
**Verdict:** **Monolithic Node.** This node is a "Big Ball of Mud" scaling bottleneck.

### 🏗️ Vector 4: Infrastructure Integrity
**Context:** `docker-compose.yml`, `app/lib/`.

*   **Findings:**
    *   **Strong Foundation:** The `docker-compose.yml` is the strongest part of the system. TimescaleDB, Ollama, and OpenTelemetry are correctly wired.
    *   **Good Dependencies:** `app/lib/` contains reusable math/physics components.
    *   **Orphaned Service:** The API (`main.py`) initializes the DB connection but fails to pass it to the Agent layer.

**Severity:** 🟩 **LOW** (Infrastructure is fine, Wiring is bad)
**Verdict:** **Solid Base.** The problems are in application wiring, not the stack itself.

---

## 3. Decision Matrix

| Option | Description | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **A. The Patch** | Fix `main.py` to init state. Delete `app/data`. | Fast (1-2 hours). Gets it running. | Leaves "Fat Node" and "Data Triplication" partially solved. | ❌ No |
| **B. Nuclear** | Rewrite Agent into Microservices. | Perfect architecture. | Weeks of work. High risk of regression. | ❌ No |
| **C. Strangler** | Fix critical wiring -> Merge Data Layer -> Refactor Node internally. | **Risk-managed.** specific fixes for specific problems. | Requires disciplined step-by-step execution. | ✅ **YES** |

---

## 4. Final Recommendation: The "Strangler Fig" Plan

We will fix the system in **3 Surgical Strikes**, prioritizing the "Broken Integration" first.

### Phase 1: Brain Surgery (Fix Split Brain)
*   **Goal:** Connect the Service (`main.py`) to the Global State so metrics work.
*   **Action:** Modify `app/main.py` lifespan to call `initialize_global_state_service(db_session)`.
*   **Action:** Update `app/agent/loop.py` to ensure it gracefully handles missing state if looked up too early.

### Phase 2: Unify the Data Layer (Fix Data Schizophrenia)
*   **Goal:** One way to get data.
*   **Action:** Delete `app/data/` entirely.
*   **Action:** Refactor `app/adapters/market.py` to act as the SINGLE facade. It should likely import/use `app/adapters/alpaca.py` (refactored) instead of raw SDK calls, OR we verify `alpaca.py` is useless and delete it too, letting `market.py` own the SDK. (Recommendation: Let `market.py` be the high-level facade, keep SDK usage inside it for now to save time, delete the unused wrapper files).

### Phase 3: Slim the Analyst (Fix Fat Node)
*   **Goal:** Make `AnalystAgent` testable and faster.
*   **Action:** Inject dependencies into `AnalystAgent` (pass adapters in `__init__`, don't create them there).
*   **Action:** (Future/Post-Audit) Move the "Tournament" logic to a scheduled background job. The Analyst should just 'read' the winning strategy from a cache/state, not re-run the tournament every minute.

---

**Next Immediate Step:**
Execute **Phase 1** & **Phase 2**.
1.  Add `initialize_global_state_service` to `app/main.py`.
2.  Delete `app/data/` directory.
3.  Delete unused `app/adapters/alpaca.py` (since `market.py` uses SDK directly).
