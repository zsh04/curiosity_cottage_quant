# Database Schema Specification

**Systems:** QuestDB (Time-Series), LanceDB (Vector), Redis (K/V + Pub/Sub)

## 1. QuestDB Schemas

### 1.1 `trades` Table

**Purpose:** High-frequency tick data (intraday trades)

**DDL:**

```sql
CREATE TABLE trades (
    symbol SYMBOL CAPACITY 256 CACHE,
    price DOUBLE,
    size INT,
    timestamp TIMESTAMP,
    exchange SYMBOL CAPACITY 32 NOCACHE,
    side SYMBOL CAPACITY 2 NOCACHE  -- 'B' or 'S'
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**Field Descriptions:**

- `symbol`: Asset ticker (indexed, cached for fast lookup)
- `price`: Trade price (USD)
- `size`: Quantity traded
- `timestamp`: Nanosecond precision timestamp
- `exchange`: Venue (e.g., "NASDAQ", "NYSE")
- `side`: Buy or Sell

**Partitioning:**

- **Strategy**: Daily partitions
- **Retention**: 30 days hot, 2 years archive
- **Rationale**: Balances query performance with disk usage

**Indexes:**

```sql
-- Symbol index (automatically created via SYMBOL type)
-- Timestamp index (partition key)
```

**Estimated Size:**

- **Rows/Day**: ~1M (100 ticks/sec *10 symbols* 8 hours)
- **Size/Day**: ~50 MB (compressed)
- **30-Day Total**: ~1.5 GB

**Sample Query:**

```sql
SELECT 
    symbol,
    avg(price) as vwap,
    sum(size) as volume
FROM trades
WHERE timestamp > dateadd('h', -1, now())
  AND symbol = 'SPY'
SAMPLE BY 1m;
```

### 1.2 `ohlcv_1d` Table

**Purpose:** Daily OHLCV bars (historical backtesting)

**DDL:**

```sql
CREATE TABLE ohlcv_1d (
    symbol SYMBOL CAPACITY 10000 CACHE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume LONG,
    date DATE
) timestamp(date) PARTITION BY MONTH WAL;
```

**Field Descriptions:**

- `symbol`: Asset ticker
- `open`, `high`, `low`, `close`: Price OHLC
- `volume`: Total daily volume
- `date`: Trading date (midnight UTC)

**Partitioning:**

- **Strategy**: Monthly partitions
- **Retention**: Perpetual (small footprint)

**Estimated Size:**

- **Rows**: ~2.5M (10k symbols * 252 days/year)
- **Size**: ~200 MB/year (highly compressible)

**Sample Query:**

```sql
SELECT 
    date,
    close,
    (close - LAG(close) OVER (ORDER BY date)) / LAG(close) OVER (ORDER BY date) as return
FROM ohlcv_1d
WHERE symbol = 'SPY'
  AND date >= '2023-01-01'
ORDER BY date;
```

### 1.3 Performance Tuning

**WAL (Write-Ahead Log):**

- Enabled for durability
- Commit lag: 1 second

**SYMBOL Type:**

- Intern strings for memory efficiency
- Cache hot symbols (SPY, QQQ, etc.)

**Compression:**

- Automatic columnar compression
- ~10x compression ratio on price data

---

## 2. LanceDB Schemas

### 2.1 `market_state_embeddings` Table

**Purpose:** Vector search for similar market regimes

**Schema (Pydantic):**

```python
from lancedb.pydantic import LanceModel, Vector

class MarketStateEmbedding(LanceModel):
    vector: Vector(384)          # all-MiniLM-L6-v2 embedding
    symbol: str                  # Asset ticker
    timestamp: datetime          # State capture time
    metadata: str                # JSON-serialized state
```

**Metadata Structure (JSON):**

```json
{
    "physics": {
        "mass": 0.42,
        "momentum": 1.23,
        "friction": 0.15,
        "entropy": 0.08,
        "nash_dist": 0.05,
        "alpha": 2.8,
        "regime": "Gaussian"
    },
    "sentiment": {
        "label": "Bullish",
        "score": 0.85
    }
}
```

**Indexes:**

- **Vector Index**: IVF (Inverted File) for ANN search
- **Scalar Index**: B-tree on `timestamp` for temporal queries

**Creation:**

```python
import lancedb

db = lancedb.connect("data/lancedb")
table = db.create_table(
    "market_state_embeddings",
    schema=MarketStateEmbedding,
    mode="overwrite"
)
```

**Query (Vector Similarity):**

```python
# Find 5 most similar historical states
results = table.search(query_vector).limit(5).to_list()
```

**Estimated Size:**

- **Embeddings**: 100k states
- **Vector Size**: 384 * 4 bytes = 1.5 KB/embedding
- **Total**: ~150 MB (vectors only)
- **With Metadata**: ~300 MB

### 2.2 Index Optimization

**IVF Parameters:**

```python
table.create_index(
    metric="L2",           # Euclidean distance
    num_partitions=256,    # Cluster centers
    num_sub_vectors=96     # PQ compression (384/4)
)
```

**Trade-offs:**

- **Recall**: ~95% (acceptable for similarity search)
- **Speed**: 100x faster than brute-force
- **Memory**: 10x smaller (PQ compression)

---

## 3. Redis Schemas

### 3.1 Key Patterns

#### `physics:state:{symbol}`

**Type:** String (JSON)

**Value:**

```json
{
    "mass": 0.42,
    "momentum": 1.23,
    "friction": 0.15,
    "entropy": 0.08,
    "nash_dist": 0.05,
    "regime": "Gaussian",
    "alpha_coefficient": 2.8
}
```

**TTL:** None (persistent until overwritten)

**Access:**

```python
redis.set("physics:state:SPY", orjson.dumps(state))
state = orjson.loads(redis.get("physics:state:SPY"))
```

#### `market:snapshot:{symbol}`

**Type:** Hash

**Fields:**

```redis
HSET market:snapshot:SPY
  price 450.32
  volume 89234567
  bid 450.31
  ask 450.33
  timestamp 1703174400
```

**TTL:** 60 seconds (cache invalidation)

**Access:**

```python
redis.hset(f"market:snapshot:{symbol}", mapping={...})
redis.expire(f"market:snapshot:{symbol}", 60)
```

#### `agent:state:{agent_id}`

**Type:** String (JSON)

**Value:**

```json
{
    "context": "...",
    "last_signal": "BUY",
    "last_update": "2025-12-21T12:00:00Z"
}
```

**TTL:** 3600 seconds (1 hour)

### 3.2 Pub/Sub Channels

#### `state_update`

**Publisher:** FeynmanService, AnalystAgent

**Subscribers:** RedisBridge, StateBroadcaster

**Message Format:**

```json
{
    "event": "PHYSICS_UPDATE",
    "symbol": "SPY",
    "timestamp": "2025-12-21T12:00:00Z",
    "data": {
        "alpha": 2.8,
        "regime": "Gaussian"
    }
}
```

**Usage:**

```python
# Publish
await redis.publish("state_update", orjson.dumps(message))

# Subscribe
pubsub = redis.pubsub()
await pubsub.subscribe("state_update")
async for message in pubsub.listen():
    handle_update(message["data"])
```

#### `trade_signals` (Future)

**Purpose:** Broadcast buy/sell decisions

**Message Format:**

```json
{
    "symbol": "SPY",
    "side": "BUY",
    "confidence": 0.85,
    "timestamp": "2025-12-21T12:00:00Z"
}
```

### 3.3 Memory Management

**Max Memory:** 256 MB

**Eviction Policy:** `allkeys-lru` (Least Recently Used)

**Config:**

```redis
maxmemory 256mb
maxmemory-policy allkeys-lru
```

**Monitoring:**

```bash
redis-cli INFO memory
```

---

## 4. Database Migrations

### 4.1 QuestDB Migrations

**Tool:** SQL scripts (no ORM)

**Example: Add Column**

```sql
-- Migration: 2025-12-21_add_side_to_trades.sql
ALTER TABLE trades ADD COLUMN side SYMBOL CAPACITY 2 NOCACHE;
```

**Execution:**

```bash
questdb-cli < migrations/2025-12-21_add_side_to_trades.sql
```

### 4.2 LanceDB Migrations

**Strategy:** Schema evolution via versioning

**Example: Add Field**

```python
# New schema version
class MarketStateEmbeddingV2(LanceModel):
    vector: Vector(384)
    symbol: str
    timestamp: datetime
    metadata: str
    version: int = 2  # NEW
```

**Migration Script:**

```python
# Convert V1 → V2
old_table = db.open_table("market_state_embeddings")
new_table = db.create_table("market_state_embeddings_v2", schema=MarketStateEmbeddingV2)

for batch in old_table.to_batches():
    # Add default version
    batch["version"] = 1
    new_table.add(batch)

# Swap tables
db.drop_table("market_state_embeddings")
db.rename_table("market_state_embeddings_v2", "market_state_embeddings")
```

### 4.3 Redis Migrations

**Strategy:** Key versioning

**Example:**

```python
# Old key: physics:state:SPY
# New key: physics:state:v2:SPY

# Migration
for key in redis.scan_iter("physics:state:*"):
    if ":v2:" not in key:
        value = redis.get(key)
        new_key = key.replace("physics:state:", "physics:state:v2:")
        redis.set(new_key, value)
        redis.delete(key)
```

---

## 5. Backup & Restore Procedures

### 5.1 QuestDB Backup

**Daily Snapshot:**

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
questdb backup --output=/backup/questdb-$DATE.tar.gz
aws s3 cp /backup/questdb-$DATE.tar.gz s3://bucket/backups/
```

**Restore:**

```bash
wget s3://bucket/backups/questdb-latest.tar.gz
tar -xzf questdb-latest.tar.gz -C /data/questdb/
questdb restart
```

### 5.2 LanceDB Backup

**Incremental Backup:**

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /backup/lancedb-$DATE.tar.gz data/lancedb/
aws s3 cp /backup/lancedb-$DATE.tar.gz s3://bucket/backups/
```

**Restore:**

```bash
wget s3://bucket/backups/lancedb-latest.tar.gz
tar -xzf lancedb-latest.tar.gz -C data/
```

### 5.3 Redis Backup

**RDB Snapshot:**

```bash
redis-cli BGSAVE
cp /data/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

**AOF Backup:**

```bash
cp /data/appendonly.aof /backup/redis-aof-$(date +%Y%m%d).aof
```

**Restore:**

```bash
cp /backup/redis-latest.rdb /data/dump.rdb
redis-cli FLUSHALL
redis-cli SHUTDOWN
# Redis will load dump.rdb on restart
```

---

## 6. Monitoring Queries

### 6.1 QuestDB Health

**Check Table Size:**

```sql
SELECT 
    table_name,
    count() as row_count,
    pg_relation_size(table_name::regclass) / 1024 / 1024 as size_mb
FROM tables()
WHERE table_name IN ('trades', 'ohlcv_1d');
```

**Check Partition Size:**

```sql
SELECT 
    partition,
    rowCount,
    diskSize / 1024 / 1024 as size_mb
FROM table_partitions('trades')
ORDER BY partition DESC
LIMIT 10;
```

### 6.2 LanceDB Health

**Count Embeddings:**

```python
table = db.open_table("market_state_embeddings")
count = table.count_rows()
print(f"Total embeddings: {count}")
```

**Index Stats:**

```python
stats = table.index_stats()
print(f"Index type: {stats['type']}")
print(f"Recall: {stats['recall']}")
```

### 6.3 Redis Health

**Memory Usage:**

```bash
redis-cli INFO memory | grep used_memory_human
```

**Key Count:**

```bash
redis-cli DBSIZE
```

**Slow Queries:**

```bash
redis-cli SLOWLOG GET 10
```

---

## 7. Performance Benchmarks

### 7.1 QuestDB

**Insert Throughput:**

- Single row: 5ms
- Batch (1000 rows): 50ms (20k rows/sec)

**Query Latency:**

- Indexed symbol: 20ms
- Full table scan: 500ms (avoid)

### 7.2 LanceDB

**Vector Search:**

- Exact (brute-force): 2000ms (100k vectors)
- IVF (ANN): 130ms (100k vectors, 95% recall)

**Insert:**

- Single: 10ms
- Batch (100): 100ms (1k embeddings/sec)

### 7.3 Redis

**GET/SET:**

- Latency: <1ms (localhost)
- Throughput: 100k ops/sec

**PUBLISH:**

- Latency: <1ms
- Throughput: 50k msgs/sec

---

## 8. Future Enhancements

- [ ] **TimescaleDB** as alternative to QuestDB (PostgreSQL-compatible)
- [ ] **pgvector** for hybrid SQL + vector search
- [ ] **ClickHouse** for ultra-fast analytics
- [ ] **Dragonfly** as Redis replacement (multi-threaded)
- [ ] **Iceberg** table format for data lakehouse
