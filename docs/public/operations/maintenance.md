# System Maintenance Runbook

**Audience:** System Operators / Quants  
**Scope:** Routine maintenance of the Curiosity Cottage V2.

---

## 1. Market Memory Maintenance

The **Hippocampus** (Market Memory) relies on an up-to-date vector index.

### 1.1 Ingestion

**When:** Weekly (e.g., Saturday morning) or after a significant market event.

**Command:**

```bash
# Ingest the last year of data for top symbols
python scripts/ingest_memory.py --symbols SPY,QQQ,IWM --lookback 365
```

**Verify:**
Check logs for `✅ Successfully ingested X vectors`.

### 1.2 Re-Indexing

**When:** If vector search becomes slow or accuracy drops significantly.

**Action:**
LanceDB handles indexing automatically, but you can force a cleanup by deleting the `data/lancedb` folder and re-ingesting fresh data.

---

## 2. Model Updates

The **Oracle** (Forecasting Engine) uses pre-trained models.

### 2.1 Updating Chronos

**When:** When a new `amazon/chronos-bolt` version is released on HuggingFace.

**Action:**

1. Update `app/core/config.py`:

   ```python
   CHRONOS_MODEL_NAME = "amazon/chronos-bolt-medium" # Upgrade from small
   ```

2. Verify:

   ```bash
   python scripts/verify_chronos.py
   ```

### 2.2 Updating FinBERT

**When:** Annually, or if sentiment analysis drifts.
**Action:** Re-run `scripts/convert_finbert_onnx.py` to fetch and quantize the latest base model.

---

## 3. Data Integrity Checks

**When:** Daily (Pre-market).

### 3.1 Tier 1 Data Audit

Ensure local QuestDB is in sync with providers.

**Command:**

```bash
python scripts/check_data.py --validator "gap_check"
```

**Failure Handling:**
If gaps are found > 1%, run:

```bash
python scripts/backfill_tier1.py --force
```

---

## 4. Emergency Procedures

### 4.1 "The Red Button"

If the system behaves erratically (e.g., flash crash, rogue trades):

**Deep Freeze:**

```bash
./scripts/health_check_services.sh --kill
# OR manually
docker-compose down
pkill -f "python run_agent_loop.py"
```

Refer to `docs/public/operations/emergency.md` for post-mortem steps.
