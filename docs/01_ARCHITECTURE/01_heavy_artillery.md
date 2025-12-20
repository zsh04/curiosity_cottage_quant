# Heavy Artillery (M4 Pro Stack v6.2)

## 1. Silicon Allocation

* **ANE (Neural Engine):** Sentiment Inference (FinBERT CoreML).
* **MPS (GPU):** Forecast & Strategy (Chronos, Gemma 2).
* **CPU (Performance):** Physics & Event Loop (Polars, uvloop).
* **CPU (Efficiency):** I/O & Database (QuestDB, Dragonfly).

## 2. The Software Stack

### Metal (Host)

* `coremltools`: For converting PyTorch models to ANE-optimized `.mlpackage`.
* `torch` (MPS): For GPU-accelerated forecasting.
* `numpy`: Accelerated via Accelerate framework.

### Container (Docker)

* `FastStream`: Redis-based Event Bus.
* `Pydantic AI`: Agentic Framework.
* `Polars`: Rust-based Dataframes.

## 3. The Bridge

* **Host Gateway:** `host.docker.internal` allows Docker to offload AI tasks to the bare metal host ports.
