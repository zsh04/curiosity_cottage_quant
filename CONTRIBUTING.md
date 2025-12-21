# Contributing Guide

**The Rules of Engagement for Curiosity Cottage Quant**

---

## Quick Reference

| Section | What You Learn |
|---------|----------------|
| [Workflow](#workflow) | How to submit contributions |
| [Style Guide](#style-guide) | Writing and code standards |
| [Documentation](#documentation) | Diátaxis classification |
| [Security](#security) | What you can and cannot commit |

---

## Before You Start

Read these governance documents:

- [GOVERNANCE.md](./GOVERNANCE.md) — The Constitution
- [PROJECT_MANAGEMENT.md](./PROJECT_MANAGEMENT.md) — Directive Workflow

---

## Workflow

### 1. Check for Existing Work

Search GitHub Issues for existing Directives before starting.

### 2. Create a Directive

If no Directive exists, create one:

```markdown
## Directive-{ID}: {Title}

**Identity:** The IDE
**Context:** @{files}
**Objective:** {Definition of Done}
**Status:** DRAFT
```

### 3. Wait for Approval

> **Do not write code until the Directive enters REVIEW or ACTIVE status.**

### 4. Create a Branch

```bash
git checkout -b dir-{id}/{short-description}
```

### 5. Make Changes

Follow the style guides below.

### 6. Commit

```bash
git commit -m "feat: implement feature X [Dir-{ID}]"
```

### 7. Submit Pull Request

Title format: `[Dir-{ID}] {Description}`

---

## Style Guide

### Writing Style (Google Developer Style)

Follow these rules:

| Rule | Example |
|------|---------|
| Use **second person** ("you") | "You configure the API key..." |
| Use **present tense** | "This function returns..." |
| Use **active voice** | "Run the script" not "The script should be run" |
| Be **direct** | "Configure X" not "Please kindly configure X" |
| **Avoid** "please" and "kindly" | Just state the instruction |
| **One idea** per sentence | Keep sentences short and clear |

**Good:**

> You set the `REDIS_URL` environment variable in the `.env` file. The engine connects to Redis on startup.

**Bad:**

> We would like you to please set up the Redis URL environment variable in the .env file, which is located in the root directory of the project, so that the engine can connect.

### Code Style

#### Python

| Tool | Purpose |
|------|---------|
| **Black** | Formatter |
| **Ruff** | Linter |
| **Type hints** | Required for all functions |
| **Docstrings** | Google style |

```python
def calculate_alpha(returns: list[float], tail_fraction: float = 0.05) -> float:
    """Calculate the Hill estimator for tail exponent.

    Args:
        returns: List of log returns.
        tail_fraction: Fraction of data to use for tail estimation.

    Returns:
        The estimated tail exponent alpha.

    Raises:
        ValueError: If returns has fewer than 20 observations.
    """
    ...
```

#### TypeScript / React

| Tool | Purpose |
|------|---------|
| **Prettier** | Formatter |
| **ESLint** | Linter |
| **Functional components** | With hooks |

```typescript
interface PhysicsGaugeProps {
  alpha: number;
  regime: string;
}

export function PhysicsGauge({ alpha, regime }: PhysicsGaugeProps): JSX.Element {
  return <div>{regime}: {alpha}</div>;
}
```

### Commit Messages

```text
<type>: <description> [Dir-{ID}]
```

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructure (no behavior change) |
| `test` | Tests |
| `chore` | Build/tooling |
| `perf` | Performance improvement |

---

## Documentation

### Diátaxis Classification

All documentation changes must classify content into one of four quadrants:

| Quadrant | Purpose | Location |
|----------|---------|----------|
| **Tutorial** | Learning-oriented (step-by-step) | `docs/public/tutorials/` |
| **How-To** | Task-oriented (solve a problem) | `docs/public/how-to/` |
| **Reference** | Information-oriented (technical specs) | `docs/public/reference/` |
| **Explanation** | Understanding-oriented (why decisions) | `docs/public/explanation/` |

### PR Checklist

When submitting documentation changes, include in your PR description:

```markdown
**Diátaxis Classification:** Tutorial / How-To / Reference / Explanation
**Target Audience:** Beginners / Intermediate / Advanced / Internal
**Security Review:** ✅ No alpha logic or parameters exposed
```

---

## Security

### The Black Box Doctrine

> **NEVER commit alpha logic or specific parameter weights to `docs/public/`.**

### What You CAN Commit (Public)

- Architecture overviews
- API schemas (not implementation logic)
- Installation instructions
- Configuration variable names (not values)
- High-level explanations

### What You CANNOT Commit (Internal Only)

- Mathematical derivations that reveal trading edge
- Strategy parameters and hyperparameters
- Backtest results with P&L
- Research benchmarks
- Architecture Decision Records with alpha details

### Enforcement

The `.gitignore` file blocks `docs/internal/` from being committed. If you need to document sensitive content:

1. Write it in `docs/internal/`
2. It stays on your local machine
3. Share via Confluence or encrypted channels

---

## Testing

### Run Tests

```bash
# All tests
pytest tests/

# Specific module
pytest tests/test_physics.py

# With coverage
pytest --cov=app tests/
```

### Requirements

- All new features require tests
- Maintain >80% coverage on critical paths
- Include edge cases and failure modes

---

## Getting Help

- **Documentation:** `docs/INDEX.md`
- **Issues:** GitHub Issues
- **Questions:** GitHub Discussions

---

## Recognition

Contributors are recognized in:

- Release notes
- README acknowledgments

---

*"Good documentation is better than good excuses."*
