# Startup Guide (Ops)

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (Poetry or pip)
- Redis running (`docker run -d -p 6379:6379 redis`)

## Boot Sequence

1. **Start Infrastructure**

   ```bash
   docker-compose up -d redis timescaledb
   ```

2. **Initialize Feynman (Physics)**

   ```bash
   python scripts/init_physics.py
   ```

3. **Ignite The Core**

   ```bash
   python main.py
   ```
