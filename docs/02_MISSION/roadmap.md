# Project Ezekiel Roadmap (v6.2)

## Phase 0: The Optimization [COMPLETE]

- [x] **CoreML:** Convert FinBERT to `.mlpackage` for ANE execution.
- [x] **MPS:** Ensure Chronos-Bolt uses `mps` device.
- [x] **Refactor:** Rename metal scripts to `soros_ane.py` and `chronos_mps.py`.

## Phase 1: The Physics Kernel (Feynman) [COMPLETE]

- [x] **Polars:** Implement vectorized physics on CPU.

## Phase 2: The Neural Feel (Soros) [IN PROGRESS]

- [ ] **Specs:** Define `TradeSignal` contract.
- [ ] **Service:** Implement `SorosService` (Reflexivity Engine).
- [ ] **Inference:** Run `soros_ane.py` on Host (Deferred/Parallel).

## Phase 3: The GPU Mind (Chronos/Boyd)

- [ ] **Forecast:** Run `chronos_mps.py` on Host.
- [ ] **Strategy:** Run Boyd via Ollama (using Metal backend).
