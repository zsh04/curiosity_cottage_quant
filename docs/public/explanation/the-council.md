# The Council of Giants (System Personas)

The Antigravity Prime architecture is personified by "The Council," a collective of historical and archetypal entities that govern the system's consciousness.

## 1. The Silicon Handshake (Physical Manifestation)

The Council is physically distributed across the Apple Silicon chip, creating a "Bicameral Mind":

| Giant | Domain | Silicon Residence |
| :--- | :--- | :--- |
| **Feynman** | Physics | **Performance Cores (CPU)** |
| **Chronos** | Prophecy | **MPS / GPU** |
| **Soros** | Intuition | **Neural Engine (ANE)** |
| **Simons** | Execution | **Efficiency Cores (CPU)** |
| **Hypatia** | Memory/DAL | **NVMe / RAM** |

---

## 2. The Active Council

### 🏰 The Governance Layer

#### 1. Feynman (The Physicist) - "The Engine"

* **Role:** Kinematics & Laws of Motion
* **File:** `app/services/feynman.py`
* **Philosophy:** "Markets have mass and momentum. Respect the laws."
* **Responsibilities:** Calculates Mass, Momentum, Entropy, Nash Distance.

#### 2. Taleb (The Risk Guardian) - "The Shield"

* **Role:** Convexity & Anti-Fragility
* **File:** `app/agent/nodes/taleb.py`
* **Philosophy:** "It is better to be safe than precise."
* **Philosophy:** "It is better to be safe than precise."
* **Responsibilities:** Enforces **Fractal Risk Sizing**. Calculates Heavy-Tail Alpha (α).
* **Psychology:** **Anxiety Regulation** (Halves position size when stress/consecutive losses > 0.7).

#### 3. Nash (The Auditor) - "The Game Theorist"

* **Role:** Equilibrium & Post-Mortem
* **File:** `app/agent/nash.py`
* **Philosophy:** "Every loss is a failure of game theory. Do not chase chaos."
* **Responsibilities:** VETOES trades where $(Price - Mode) > 2\sigma$. Enforces Mean Reversion.

### 🧠 The Cognitive Layer

#### 4. Boyd (The Strategist) - "The Pilot"

* **Role:** OODA Loop (Observe-Orient-Decide-Act)
* **File:** `app/agent/boyd.py`
* **Philosophy:** "Speed of orientation beats speed of movement."
* **Responsibilities:** Selects tactics (Ambush vs. Snipe) based on Feynman's physics.

#### 5. The Oracle (Chronos) - "The Seer"

* **Role:** Prophecy & Probabilistic Time-Travel
* **File:** `app/services/forecast.py`
* **Philosophy:** "The future is a probability cloud, not a point."
* **Responsibilities:** Generates P10/P50/P90 price paths using Deep Learning.
* **Constraints:** **Relativity** (Must harmonize with higher timeframe trends).
    > [!WARNING]
    > **Latency**: ~2.3s (High Cognitive Load).

#### 6. Hypatia (The Librarian) - "The Memory"

* **Role:** Unified Data Access Layer (DAL) & RAG.
* **Components:**
  * **The Scrolls of Herodotus:** Querying QuestDB (Time-Series History).
  * **The Shannon Channel:** Redis Streaming (Real-time).
  * **Memory Core:** LanceDB (Semantic Search / Vector Memory).
* **File:** `app/services/market.py` / `app/services/memory.py`
* **Philosophy:** "Knowledge is the only bridge between the infinite and the finite."
* **Responsibilities:** Retrieves top 5 historical analogs (RAG) and provides a unified interface for all data.

### ⚡ The Reflex Layer

#### 7. Soros (The Feeler) - "The Nerve"

* **Role:** Reflexivity & Sentiment
* **File:** `app/services/soros.py`
* **Philosophy:** "Perception alters reality."
* **Responsibilities:** Ingests news/sentiment via FinBERT to detect feedback loops.

#### 8. Shannon (The Signalman) - "The Wire"

* **Role:** Information Velocity & Telemetry
* **File:** `app/api/websocket.py`
* **Philosophy:** "Noise is the enemy of signal."
* **Responsibilities:** Ensures zero-loss transmission of telemetry to the Instrument Cluster.

#### 9. Simons (The Executioner) - "The Blade"

* **Role:** HFT Execution
* **File:** `app/agent/nodes/simons.py`
* **Philosophy:** "There is no alpha without capture."
* **Responsibilities:** Slices orders, manages **Friction** (Slippage/Latency), and pulls the **Grim Trigger**.
