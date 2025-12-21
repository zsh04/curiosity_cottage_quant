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
    ├── strategies/          "The Power Law Alpha Logic"
    ├── research/            "Chronos vs. T5 Benchmarks"
    ├── adr/                 "Architecture Decision Records"
    └── templates/           "Document Templates"
```

> [!CAUTION]
> **`docs/internal/` is git-ignored.** This content never leaves your machine.

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

#### Architecture

| Document | Description |
|----------|-------------|
| [stack.md](./public/reference/architecture/stack.md) | Technology stack |
| [data-flow.md](./public/reference/architecture/data-flow.md) | Data flow diagrams |
| [service-contracts.md](./public/reference/architecture/service-contracts.md) | Service SLAs |
| [backtest-engine.md](./public/reference/architecture/backtest-engine.md) | Backtest methodology |
| [market-scanner.md](./public/reference/architecture/market-scanner.md) | Universe selection |
| [domain-models.md](./public/reference/architecture/domain-models.md) | Pydantic schemas |
| [chronos.md](./public/reference/architecture/chronos.md) | Forecasting service |
| [council.md](./public/reference/architecture/council.md) | Strategy voting |
| [frontend-components.md](./public/reference/architecture/frontend-components.md) | React components |
| [frontend-state.md](./public/reference/architecture/frontend-state.md) | Frontend state management |

#### API

| Document | Description |
|----------|-------------|
| [rest-endpoints.md](./public/reference/api/rest-endpoints.md) | REST API Reference |
| [websocket-protocol.md](./public/reference/api/websocket-protocol.md) | WebSocket TELEMETRY |
| [redis-protocol.md](./public/reference/api/redis-protocol.md) | Redis patterns |

#### Math

| Document | Description |
|----------|-------------|
| [kalman-filter.md](./public/reference/math/kalman-filter.md) | 3-State Kinematic Kalman Filter |
| [hill-estimator.md](./public/reference/math/hill-estimator.md) | Tail Exponent Estimation |
| [kelly-sizing.md](./public/reference/math/kelly-sizing.md) | BES Position Sizing |
| [physics-engine.md](./public/reference/math/physics-engine.md) | 5-Pillar Physics Model |

#### Database

| Document | Description |
|----------|-------------|
| [schemas.md](./public/reference/database/schemas.md) | QuestDB, LanceDB, Redis |

#### General

| Document | Description |
|----------|-------------|
| [glossary.md](./public/reference/glossary.md) | Term definitions (60+ terms) |
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

## 🔴 Internal Documentation

> **Location:** `docs/internal/` (git-ignored)

### Strategies

- Alpha generation logic
- Strategy parameter configurations
- Edge-specific implementations

### Research

- Model benchmarks (Chronos vs. T5)
- Backtest results with P&L
- Parameter optimization studies

### ADRs (Architecture Decision Records)

- Decisions with alpha implications
- Trade-off analysis with sensitive data

### Templates

- [01-directive.md](./internal/templates/01-directive.md) — Task assignment
- [02-adr.md](./internal/templates/02-adr.md) — Architecture Decision Record
- [03-incident-report.md](./internal/templates/03-incident-report.md) — Post-mortem
- [04-tutorial.md](./internal/templates/04-tutorial.md) — Tutorial template
- [05-how-to.md](./internal/templates/05-how-to.md) — How-to template

---

## 📊 Coverage Matrix

| System | Logic | Math | Flow | Technical | Code | API | Architecture |
|--------|:-----:|:----:|:----:|:---------:|:----:|:---:|:------------:|
| Backtest Engine | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Market Scanner | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kalman Filter | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Hill Estimator | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| BES Sizing | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| REST API | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| WebSocket | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Redis | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Frontend | ✅ | — | ✅ | ✅ | ✅ | — | ✅ |

---

## 📈 Statistics

| Metric | Count |
|--------|-------|
| **Tutorial Files** | 1 |
| **How-To Guides** | 3 |
| **Reference Docs** | 19 |
| **Explanation Docs** | 2 |
| **Operations Docs** | 2 |
| **Templates** | 5 |
| **Total Files** | **32+** |

---

## 🔗 Governance

| Document | Location |
|----------|----------|
| [GOVERNANCE.md](../GOVERNANCE.md) | Project Constitution |
| [PROJECT_MANAGEMENT.md](../PROJECT_MANAGEMENT.md) | Directive Workflow |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Developer Guide |

---

*Last Updated: 2025-12-21*
