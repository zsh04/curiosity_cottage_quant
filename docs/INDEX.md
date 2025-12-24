# 📚 Documentation Index

**Diátaxis-Organized Knowledge Base**

---

## 📂 Structure

```text
docs/
├── public/                  🟢 External: For Users/Deployers
│   ├── tutorials/           "Get Started in 10 Minutes"
│   ├── how-to/              "How to Add a Ticker"
│   ├── reference/           "API Schema", "Config Vars"
│   ├── explanation/         "Architecture Overview"
│   └── operations/          "Runbooks"
│
└── internal/                🔴 Internal: For The Council/Core Team
    ├── math/                "Kalman, Hill, Kelly formulas"
    ├── architecture/        "Data Flow, Backtest Engine"
    ├── api/                 "WebSocket, Redis protocols"
    ├── strategies/          "The Power Law Alpha Logic"
    ├── research/            "Benchmarks with P&L"
    ├── adr/                 "Architecture Decision Records"
    └── templates/           "Document Templates"
```

> [!CAUTION]
> **`docs/internal/` is git-ignored.** This content never leaves your machine. All mathematical specifications, thresholds, and alpha logic reside there.

---

## 🟢 Public Documentation

### Tutorials (Learning-Oriented)

| Tutorial | Description | Time |
|----------|-------------|------|
| [01-quickstart.md](./public/tutorials/01-quickstart.md) | Get Started in 10 Minutes | 10 min |

---

### How-To Guides (Task-Oriented)

| Guide | Description | Time |
|-------|-------------|------|
| [01-run-backtest.md](./public/how-to/01-run-backtest.md) | How to Run a Backtest | 5 min |
| [02-add-strategy.md](./public/how-to/02-add-strategy.md) | How to Add a New Strategy | 15 min |
| [03-deploy-production.md](./public/how-to/03-deploy-production.md) | How to Deploy to Production | 30 min |

---

### Reference (Information-Oriented)

#### Architecture (Public-Safe)

| Document | Description |
|----------|-------------|
| [stack.md](./public/reference/architecture/stack.md) | Technology stack |
| [domain-models.md](./public/reference/architecture/domain-models.md) | Pydantic schemas |
| [frontend-components.md](./public/reference/architecture/frontend-components.md) | React components |
| [frontend-state.md](./public/reference/architecture/frontend-state.md) | Frontend state management |

#### API (Public-Safe)

| Document | Description |
|----------|-------------|
| [rest-endpoints.md](./public/reference/api/rest-endpoints.md) | REST API Reference |

#### General

| Document | Description |
|----------|-------------|
| [TECHNICAL_REFERENCE.md](./public/reference/TECHNICAL_REFERENCE.md) | System overview |

---

### Explanation (Understanding-Oriented)

| Document | Description |
|----------|-------------|
| [the-council.md](./public/explanation/the-council.md) | Governance model |
| [ezekiel-protocol.md](./public/explanation/ezekiel-protocol.md) | Emergency protocols |

---

### Operations

| Document | Description |
|----------|-------------|
| [startup.md](./public/operations/startup.md) | System startup |
| [emergency.md](./public/operations/emergency.md) | Emergency procedures |

---

## 🔴 Internal Documentation (Git-Ignored)

> **Location:** `docs/internal/` — **NEVER COMMITTED**

### Math (Alpha Logic)

- `kalman-filter.md` — 3-State Kinematic Filter specs
- `hill-estimator.md` — Tail exponent (α) estimation
- [BES Sizing](./internal/math/bes-sizing.md) — BES position sizing
- `physics-engine.md` — 5-Pillar Physics Model
- [Performance Metrics](./internal/metrics/PERFORMANCE_METRICS.md) — 27-metric performance suite

### Architecture (Implementation Details)

- `backtest-engine.md` — Vectorized simulation
- `market-scanner.md` — Universe selection thresholds
- `data-flow.md` — System sequence diagrams
- `service-contracts.md` — Service SLAs
- `chronos.md` — Forecasting service
- `council.md` — Strategy voting

### API (Protocols)

- **`protos/`** — **The Rosetta Stone** (gRPC Contracts)
- `websocket-protocol.md` — TELEMETRY packet schema
- `redis-protocol.md` — Key patterns, Pub/Sub

### Database

- `schemas.md` — QuestDB, LanceDB, Redis

### Other

- `glossary.md` — Term definitions (60+ terms)

### Templates

- `01-directive.md` — Task assignment
- `02-adr.md` — Architecture Decision Record
- `03-incident-report.md` — Post-mortem
- `04-tutorial.md` — Tutorial template
- `05-how-to.md` — How-to template

---

## 🔒 Security Policy: The Black Box Doctrine

| Category | Public? | Internal? | Examples |
|----------|:-------:|:---------:|----------|
| **Usage Docs** | ✅ | — | Tutorials, How-To Guides |
| **API Endpoints** | ✅ | — | REST paths (no thresholds) |
| **Math Formulas** | ❌ | ✅ | Kalman, Hill, Kelly |
| **Threshold Values** | ❌ | ✅ | α < 2.0, λ scaling |
| **Strategy Logic** | ❌ | ✅ | Alpha generation |
| **Backtest Results** | ❌ | ✅ | P&L, Sharpe ratios |

---

## 🔗 Governance

| Document | Location |
|----------|----------|
| [GOVERNANCE.md](../GOVERNANCE.md) | Project Constitution |
| [PROJECT_MANAGEMENT.md](../PROJECT_MANAGEMENT.md) | Directive Workflow |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Developer Guide |

---

*Last Updated: 2025-12-21*
