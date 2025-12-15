# Curiosity Cottage Capital: Phase 2 Execution Plan

## Milestone 1: The Physics of Risk (Current Sprint)
Focus: Aligning mathematical risk models with the "No Ruin" mandate.
- [x] 1.1: Implement Kinematic Kalman Filter (3-State: Pos, Vel, Acc).
- [x] 1.2: Implement Heavy Tail Estimator (Hill Alpha).
- [ ] 1.3: **Implement Bayesian Expected Shortfall (BES)**.
    - *Constraint:* Replace all Variance-based methods (Kelly) with Tail-based methods (BES).
- [ ] 1.4: Integrate "Physics Veto" into Risk Agent (Alpha <= 2.0 -> Rejection).

## Milestone 2: Architectural Integrity (BFF Injection)
Focus: Decoupling the Cognitive Engine from the User Interface.
- [ ] 2.1: Implement Node.js BFF (Backend-for-Frontend) Service.
    - *Role:* Rate limiting, Auth proxy, Request aggregation.
- [ ] 2.2: Refactor Docker Compose to include `bff` service.
- [ ] 2.3: Update Frontend to consume BFF API (`/api/...`) instead of Engine directly.

## Milestone 3: Data Fidelity & Preprocessing
Focus: Ensuring "Garbage In, Garbage Out" does not apply.
- [ ] 3.1: Finalize Tiingo Integration (Historical + Real-time).
- [ ] 3.2: Implement Fractional Differentiation (FracDiff) Loaders.
    - *Goal:* Stationary features with memory preservation.
- [ ] 3.3: Link "Failover" Logic (Tiingo -> Finnhub) for News Feeds.

## Milestone 4: Verification & Live Dry-Run
Focus: Proving the system works without risking capital.
- [ ] 4.1: Execute "Event-Driven" Backtest (100ms latency, partial fills).
- [ ] 4.2: Verify "Trade Autopsy" endpoint delivers full agent reasoning.
- [ ] 4.3: Conduct 1-week Paper Trading Burn-in.
