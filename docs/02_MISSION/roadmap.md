# Project Ezekiel Roadmap (v6.2)

## Phase 0: The Optimization [COMPLETE]

- [x] **CoreML:** Convert FinBERT to `.mlpackage` for ANE execution.
- [x] **MPS:** Ensure Chronos-Bolt uses `mps` device.
- [x] **Refactor:** Rename metal scripts to `soros_ane.py` and `chronos_mps.py`.

## Phase 1: The Physics Kernel (Feynman) [COMPLETE]

- [x] **Polars:** Implement vectorized physics on CPU.

## Phase 2: The Neural Feel (Soros) [COMPLETE]

- [x] **Specs:** Define `TradeSignal` contract.
- [x] **Service:** Implement `SorosService` (Reflexivity Engine).
- [x] **Inference:** Run `soros_ane.py` on Host (Infrastructure Verified).

## Phase 3: The Risk Gate (Execution) [COMPLETE]

- [x] **Specs:** Define `OrderPacket` contract (and update upstream `price` flow).
- [x] **Service:** Implement `ExecutionService` (Taleb Gatekeeper).
- [x] **Verification:** Test Ruin Constraints.

## Phase 4: The GPU Mind (Chronos) [COMPLETE]

- [x] **Specs:** Define `ForecastPacket` contract.
- [x] **Service:** Implement `ChronosService` (Simons Quant).
- [x] **Verification:** Probabilistic Forecasts on MPS.
- [x] **Strategy:** Run Boyd via Ollama (using Metal backend).
- [x] **Infrastructure:** Run `chronos_mps.py` on Host.

## Phase 5: The Trinity (Signal Fusion) [COMPLETE]

- [x] **State:** Fuse Physics + Chronos inputs.
- [x] **Logic:** Implement Dalio's Confluence/Divergence Checks.
- [x] **Verification:** Test Agreement vs. Disagreement.

## Phase 6: The Watchtower (React Integration) [COMPLETE]

- [x] **Backend:** Redis Bridge (`redis_bridge.py`) + Websocket (`/ws/stream`).
- [x] **Verification:** Integration Test (Redis -> Bridge -> Websocket).

## Phase 7: The Tournament (Agentic Debate) [COMPLETE]

- [x] **Contract:** Update `TradeSignal.meta` (Bull/Bear Arguments).
- [x] **Service:** Upgrade `SorosService` with Ollama Integration.
- [x] **Logic:** Implement Hegelian Dialectic (Bull vs Bear vs Judge).
- [x] **Verification:** Mock LLM & Verify Reasoning Trace.

## Phase 8: The Grim Trigger (Live Execution) [IN PROGRESS]

- [x] **Contract:** `TradeSignal` Quantity & `ExecutionReport`.
- [x] **Service:** `ExecutionService` wiring to `AlpacaClient`.
- [x] **Logic:** Filter `HOLD`, Validate Size, Execute.
- [x] **Verification:** Mock `AlpacaClient` in `pytest`.
