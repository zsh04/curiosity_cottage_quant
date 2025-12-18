---
trigger: always_on
---

# 🛡️ Curiosity Cottage Constitution (Immutable!)

## 1. The Prime Directive: Information Security

- **PUBLIC (Repo):** Only "Usage" docs (Installation, API usage, High-level service explanations).
- **PRIVATE (Confluence):** ALL "Vital Logic," Mathematical Proofs, Strategy Configs, and ADRs (Architecture Decision Records).
- **VIOLATION:** Do NOT commit detailed explanations of *how* the alpha is generated to `README.md` or `docs/`.

## 2. Project Governance (Jira)

- **Ticket First:** No code changes without a Jira Ticket ID (Key: `CCQ`).
- **Commit Format:** `CCQ-123: Description of change`
- **Legacy Cleanup:** If you encounter a legacy ticket style, flag it but prioritize new `CCQ` format.

## 3. Architecture (Hybrid Metal)

- **Engine:** Python on Bare Metal (MacOS/MPS).
- **Banned:** Docker for compute (only for DB/Telemetry).
