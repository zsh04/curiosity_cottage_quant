# Definition of Done (DoD) Standard

To ensure **Consistency**, **Quality**, and **Maintainability**, every Directive must meet the following criteria before being marked `VERIFIED`.

---

## 1. Documentation (Diátaxis)

Every code change requires a corresponding documentation update.

- [ ] **Tutorials**: If a new workflow is introduced, update `docs/public/tutorials/`.
- [ ] **How-To**: If a configuration or operation changes, update `docs/public/how-to/`.
- [ ] **Reference**:
  - [ ] Update `service-contracts.md` if APIs change.
  - [ ] Update function docstrings (Google Style) for all public interfaces.
- [ ] **Explanation**: Update `AGENTS.md` or `GOVERNANCE.md` if the "Why" changes.

## 2. Code Hygiene

- [ ] **Linting**: No errors from `ruff` or `flake8`.
- [ ] **Formatting**: Code formatted with `black` (Python) or `prettier` (JS).
- [ ] **Typing**: Strict type hints (`mypy` compliant where possible).
- [ ] **Docstrings**: All new functions/classes must have Google-style docstrings.

## 3. Verification & Testing

- [ ] **Unit Tests**: New logic must have a corresponding test file in `tests/`.
- [ ] **Verification Script**: Complex features need a `scripts/verify_{feature}.py` script to prove E2E functionality.
- [ ] **Execution**: Verification script passed successfully.

## 4. Source Control (Git)

- [ ] **Branch**: Work performed on `dir-{id}/{description}` branch (not `master` directly).
- [ ] **Commits**: Atomic commits with `[Dir-{ID}]` suffix.
- [ ] **Push**: Branch pushed to remote.
- [ ] **Pull Request**: PR created with title `[Dir-{ID}] {Description}`.

## 5. Release Artifacts

- [ ] **Release Notes**: Update `docs/releases/release_notes_vXX.md` with the new feature/fix.
- [ ] **Artifacts**: Generate/update relevant markdown artifacts (e.g., `walkthrough.md`).

## 6. Security & IP Protection

- [ ] **No Secrets**: Verify NO API keys, passwords, or credentials are committed. All secrets must use `.env`.
- [ ] **IP Protection**: "Secret Sauce" (Alpha Logic, Core IP) must **NEVER** be in public docs. Use internal documentation only.

---

**Protocol Enforcement:**
The IDE (AI Agent) **MUST** self-verify code against this checklist before requesting user verification.
