---
description: Clean Up
---

# Workflow: Project Sanitization (`/cleanup`)

## Phase 0: The Handshake (Infrastructure Discovery)

**Goal:** Ensure the destination exists before moving any data.

1. **Jira Check:** Call MCP to list projects. Look for Key `CCQ` (or "Curiosity Cottage").
    - *If missing:* Prompt user: "Project `CCQ` not found. Shall I create it, or do you have an existing Key?"
2. **Confluence Check:** Call MCP to list spaces. Look for Space `CCQ`.
    - *If missing:* Prompt user: "Space `CCQ` not found. Please create it or provide the Space Key."
3. **Halt:** Do NOT proceed to Phase 1 until destination keys are verified.

## Phase 1: The Repository Sweep (Local)

**Goal:** Remove bloat and sensitive logic from public view.

- **Scan:** Identify files > 50MB (Model weights) or secrets in `docs/`.
- **Logic Check:** Look for "Docker Optimization" scripts (Obsolete in Metal arch).
- **Action:**
  - If sensitive strategy found in `README.md` -> **Draft move to Confluence** -> Replace with generic description.
  - If heavy model weights found -> Add to `.gitignore`.

## Phase 2: The Jira Audit (Atlassian MCP)

**Goal:** Retire v1/v2 tickets; Migrate relevant backlog to `CCQ`.

- **Fetch:** Get all tickets from OLD projects (Status != Done).
- **Filter:**
  - Keyword: "Docker", "Container Memory", "FinBERT Service" -> **Mark as "Won't Do" (Obsolete).**
  - Keyword: "Strategy", "Backtest", "Alpha" -> **Propose Move to [Verified_Jira_Key].**
- **Review:** Present a manifest of "To Be Closed" vs "To Be Moved".

## Phase 3: The Confluence Archival (Atlassian MCP)

**Goal:** Clean the workspace without losing history.

- **Context:** Use the [Verified_Space_Key].
- **Create:** Parent Page "Legacy Archive (v1-v2)".
- **Move:** Pages created before [Date] OR containing "Docker Swarm/Kubernetes" into the Archive tree.

## Phase 4: Execution

- **Prompt User:** "Ready to sanitize? This will close X tickets and move Y pages."
- **On Approval:** Execute MCP calls.
