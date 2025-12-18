---
description: update-docs
---

# Workflow: Documentation Update (`/doc`)

## Trigger

User invokes `/doc` or asks to document a change.

## Steps

1. **Classify Content:** - Is this sensitive logic (Alpha, Math, Strategy)? -> **GO TO STEP 2 (Confluence)**
   - Is this usage info (How to run, API endpoints)? -> **GO TO STEP 3 (Repo)**

2. **Step 2: Private Documentation (Confluence)**
   - **Action:** Draft the content in Markdown format.
   - **Instruction:** "I have drafted the internal documentation. Please paste this into Confluence Page: [Insert Page Name]." (Or use MCP if active to publish directly).

3. **Step 3: Public Documentation (Repo)**
   - **Check:** Ensure no vital logic is exposed.
   - **Action:** Update `README.md` or `docs/explanation/`.
   - **Lint:** Run `vale` to ensure Google Developer Style.
