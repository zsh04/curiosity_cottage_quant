# The Council of Giants (System Personas)

The Antigravity Prime architecture is personified by five "Giants," each responsible for a critical domain of the trading lifecycle.

## 1. Feynman (The Engine)

* **Role:** Physics & Kinematics
* **File:** `app/services/feynman.py`
* **Responsibility:** Calculates the raw forces of the market (Mass, Momentum, Entropy, Nash Distance).
* **Output:** a `PhysicsVector` (Velocity, Acceleration, Regime).

## 2. Boyd (The Strategist)

* **Role:** OODA Loop & Orientation
* **File:** `app/agent/nodes/boyd.py`
* **Responsibility:** Observes the Physics Vector, Orients via Strategy (Ambush vs. Sniper), Decides functionality, and Acts (Signal Generation).
* **Output:** `TradeSignal` (Buy/Sell, Confidence).

## 3. Taleb (The Shield)

* **Role:** Risk & Convexity
* **File:** `app/agent/nodes/taleb.py`
* **Responsibility:** The "Iron Gate". Vetoes trades based on hidden risks (Entropy > 0.5), Black Swan potential (Kurtosis), and Convexity (Kelly Sizing).
* **Output:** `ApprovedSize` (Notional Amount or 0.0 for Veto).

## 4. Simons (The Executioner)

* **Role:** HFT Execution
* **File:** `app/agent/nodes/simons.py`
* **Responsibility:** Algorithmic execution. Slices orders, manages slippage, and handles the "Grim Trigger" (emergency exit).
* **Output:** `FillReport` (Price, Qty, Slippage).

## 5. Soros (The Feeler)

* **Role:** Reflexivity & Sentiment
* **File:** `app/services/soros.py`
* **Responsibility:** Asynchronously monitors news and social sentiment to detect "Reflexivity" (Feedback loops where potential affects reality).
* **Output:** `SentimentScore` (Injects into Boyd's OODA Loop).
