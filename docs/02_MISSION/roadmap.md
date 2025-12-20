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

## Phase 4: The GPU Mind (Chronos) [IN PROGRESS]

- [ ] **Specs:** Define `ForecastPacket` contract.
- [ ] **Service:** Implement `ChronosService` (Simons Quant).
- [ ] **Verification:** Probabilistic Forecasts on MPS._mps.py` on Host.
- [ ] **Strategy:** Run Boyd via Ollama (using Metal backend).
