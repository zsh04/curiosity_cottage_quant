# Service Specification: The Tournament (Agentic Debate)

**Type:** Logic Module (Soros Extension)
**Role:** The Ultimate Arbiter (Hegelian Dialectic)
**Cycle:** On-Demand (Triggered by Valid Physics Signal)

## Philosophy

"One man's signal is another man's noise. Truth is found in the conflict."
The system does not blindly trust the mathematical signal. It subjects it to a debate.

## Architecture

### 1. The Agents (LLM Prompts)

* **Model:** `llama3` (via Ollama on Host).
* **Context:** Current `ForceVector` (Physics) + `ForecastPacket` (Quant).

#### The Bull (Thesis)

* **Role:** Advocate for Momentum and Trend Continuation.
* **Prompt:** "Argue why this price action represents a sustainable trend."

#### The Bear (Antithesis)

* **Role:** Advocate for Protection and Mean Reversion.
* **Prompt:** "Argue why this move is overextended or risky. Cite Entropy and Alpha."

#### The Judge (Synthesis)

* **Role:** Neutral Arbiter.
* **Task:** Weigh the arguments. Output a final Verdict and Confidence.
* **Power:** Can **VETO** a valid signal (Soft Veto) but cannot initiate a trade against Physics (Hard Veto exists upstream).

## Data Flow

1. **Trigger:** `SorosService` detects valid `strength > 0` signal (after Physics & Chronos Gates).
2. **Action:** `conduct_debate(force, forecast)` is called.
3. **Execution:** Async HTTP Post to Ollama (`/api/generate`).
4. **Resolution:** Judge's Verdict parses into `TradeSignal.meta`.
   * `meta["judge_verdict"]`
   * `meta["bull_argument"]`
   * `meta["bear_argument"]`

## Failover

* If Ollama is offline or returns invalid JSON:
  * Log Error.
  * Proceed with `strength = 0.5` (Penalty for lack of consensus).
