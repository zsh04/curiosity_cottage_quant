# Operational Runbook (SOP)

## 1. Morning Pre-Flight (08:00 EST)
1. **Check Docker Health:** `docker-compose ps`. Ensure `timescaledb` and `ollama` are `Up`.
2. **Macro Check:** Query the `MacroAgent`.
    * *If US10Y is up > 5% on the day:* **Reduce Risk Settings to 0.5x.**
    * *If VIX > 30:* **Activate "Mean Reversion" strategies only.**

## 2. Deployment (The "M4" Standard)
We run on local metal.
* **Start:** `docker-compose up -d --build`
* **Logs:** `docker-compose logs -f engine | grep "ERROR"`
* **Update:** `git pull && docker-compose build`

## 3. Emergency Procedures (The Kill Switch)
If the AI hallucinates or execution loops:
1. **The "Soft" Kill:** Run `python scripts/flatten_all.py` (Closes all positions via Alpaca API).
2. **The "Hard" Kill:** `docker-compose down`. (Stops the brain).
