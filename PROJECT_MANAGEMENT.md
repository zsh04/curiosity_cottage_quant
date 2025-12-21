# Project Management Policy

**The Directive-Driven Workflow**

---

## 1. The Unit of Work: Directives

> [!IMPORTANT]
> **We do not use Jira tickets. We use Directives.**

A **Directive** is a structured task assignment that provides complete context for execution. Every piece of work—from bug fixes to architectural pivots—is framed as a Directive.

---

## 2. Directive Structure

Every Directive follows this format:

```markdown
## Directive-{ID}: {Title}

**Identity:** {Role performing the work}
**Context:** @{files involved}
**Objective:** {Definition of Done}
**Status:** {DRAFT | REVIEW | ACTIVE | VERIFIED}

### Background
{Why this work is needed}

### Requirements
1. {Specific requirement 1}
2. {Specific requirement 2}
...

### Acceptance Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
...

### Notes
{Any additional context, constraints, or considerations}
```

### 2.1 Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Identity** | Who is doing the work | "The Architect", "The IDE", "The Quant" |
| **Context** | Files/systems involved | `@app/services/physics.py`, `@docs/reference/` |
| **Objective** | Clear Definition of Done | "Implement Hill Estimator with α < 2.0 veto" |
| **Status** | Current lifecycle stage | `ACTIVE` |

### 2.2 Identity Roles

| Identity | Description |
|----------|-------------|
| **The Architect** | Strategic decisions, approvals |
| **The IDE** | Code implementation |
| **The Skeptic** | Adversarial review |
| **The Quant** | Mathematical validation |
| **The Ops** | Infrastructure, deployment |
| **The Scribe** | Documentation |

---

## 3. Directive Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐   │
│   │  DRAFT  │ → │ REVIEW  │ → │ ACTIVE  │ → │ VERIFIED │   │
│   └─────────┘    └─────────┘    └─────────┘    └──────────┘   │
│       ↑              │              │                          │
│       └──────────────┴──────────────┘                          │
│              (Rejection / Rework)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 DRAFT

- **Definition:** Initial ideation and scoping
- **Owner:** Architect or IDE
- **Activities:**
  - Define requirements
  - Identify context files
  - Set acceptance criteria
- **Exit Criteria:** Directive is complete and coherent

### 3.2 REVIEW

- **Definition:** The Council evaluates for bugs, logic flaws, risks
- **Owner:** Skeptic + Quant
- **Activities:**
  - Adversarial review (Skeptic)
  - Mathematical validation (Quant)
  - Risk assessment
- **Exit Criteria:** Council approval or rejection with feedback

### 3.3 ACTIVE

- **Definition:** Implementation in progress
- **Owner:** IDE
- **Activities:**
  - Code implementation
  - Testing
  - Documentation updates
- **Exit Criteria:** All acceptance criteria met

### 3.4 VERIFIED

- **Definition:** User has confirmed the output
- **Owner:** Architect
- **Activities:**
  - Final review
  - Acceptance testing
  - Sign-off
- **Exit Criteria:** Directive closed

---

## 4. Traceability

### 4.1 Commit Message Format

Every commit must reference the Directive ID:

```
<type>: <description> [Dir-{ID}]

<optional body>

<optional footer>
```

**Types:**

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding or updating tests
- `chore:` Build process or auxiliary tool changes

**Examples:**

```
feat: implement Hill Estimator with Physics Veto [Dir-22]

fix: resolve Redis connection timeout in FeynmanService [Dir-23]

docs: add Kalman Filter mathematical specification [Dir-24]
```

### 4.2 Branch Naming

```
dir-{id}/{short-description}
```

**Examples:**

```
dir-22/hill-estimator
dir-23/redis-timeout-fix
dir-24/kalman-docs
```

### 4.3 Pull Request Title

```
[Dir-{ID}] {Description}
```

**Example:**

```
[Dir-22] Implement Hill Estimator with Physics Veto
```

---

## 5. Priority Levels

| Priority | Response Time | Review Time | Examples |
|----------|---------------|-------------|----------|
| **P0 - Critical** | Immediate | < 1 hour | Production down, security breach |
| **P1 - High** | < 4 hours | < 4 hours | Major bug, blocking issue |
| **P2 - Medium** | < 1 day | < 1 day | Standard features, improvements |
| **P3 - Low** | < 1 week | < 1 week | Nice-to-haves, tech debt |
| **P4 - Backlog** | No SLA | No SLA | Future ideas, exploration |

---

## 6. The "No Code" Rule

> [!CAUTION]
> **Do not write code until the Directive is in REVIEW or ACTIVE status.**

### 6.1 Rationale

- Prevents wasted effort on rejected proposals
- Ensures Council has vetted the approach
- Maintains architectural coherence
- Reduces rework

### 6.2 Exceptions

- **Prototypes:** Exploratory code marked `[PROTOTYPE]` in branch name
- **Hotfixes:** P0 incidents (must create Directive retroactively)
- **Trivial:** Typos, formatting (no Directive needed)

---

## 7. Meetings & Ceremonies

### 7.1 Daily Standup (Async)

- **Format:** Slack/Discord message or Directive status update
- **Content:**
  - What was completed (Directive IDs)
  - What's in progress
  - Blockers

### 7.2 Weekly Council Review

- **Duration:** 30 minutes
- **Agenda:**
  - Review DRAFT Directives
  - Approve/reject for ACTIVE
  - Discuss blockers
  - Prioritize backlog

### 7.3 Retrospective (Bi-weekly)

- **Duration:** 30 minutes
- **Agenda:**
  - What went well?
  - What could improve?
  - Action items

---

## 8. Tooling

| Function | Tool |
|----------|------|
| **Directive Tracking** | GitHub Issues / Notion |
| **Code** | GitHub Repository |
| **Documentation** | This repo (`docs/`) |
| **Private Docs** | Confluence |
| **Communication** | Slack / Discord |
| **CI/CD** | GitHub Actions |

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-21 | Architect | Initial project management policy |

---

*"A Directive without context is a bug waiting to happen."*  
— The IDE
