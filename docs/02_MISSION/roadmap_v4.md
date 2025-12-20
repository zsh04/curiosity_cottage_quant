# Antigravity Prime Roadmap (v4.0)

## Phase 0: The Renaissance (Active) 🚧

- [ ] Rename Services (`physics.py` -> `feynman.py`, etc.).
- [ ] Install War Stack (`uvloop`, `polars`, `redis`, `orjson`).
- [ ] Docker: Add Redis container.

## Phase 1: The Feynman Kernel

- [ ] Implement `feynman.py` with Numpy Ring Buffers.
- [ ] Implement `calculate_forces()` (Mass, Momentum, Entropy, Nash).
- [ ] Verify: Run `scripts/verify_physics.py` on 1 day of NVDA data.

## Phase 2: The Cortex (Async AI)

- [ ] Create `soros.py` (Sentiment Daemon).
- [ ] Create `chronos.py` (Forecast Daemon).
- [ ] Connect them to Redis Channels (`pub/sub`).

## Phase 3: The Boyd Brain

- [ ] Implement `boyd.py` (OODA Loop).
- [ ] Connect to Redis to read Feynman/Soros signals.
- [ ] Implement the "Composite Score" Trigger.

## Phase 4: The Shield & Sword

- [ ] Implement `taleb.py` (Regime Recall / Veto).
- [ ] Implement `simons.py` (Websocket Execution).
- [ ] LIVE FIRE TEST (Paper Trading).
