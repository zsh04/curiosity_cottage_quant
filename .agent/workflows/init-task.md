---
description: init-task
---

# Workflow: Initialize Task (`/task`)

## Trigger

User wants to start work on a new feature or bug.

## Steps

1. **Search:** Check Jira for existing tickets related to the topic.
2. **Create:** If none exist, ask user for details and create a ticket in project `CCQ` (using Atlassian MCP).
3. **Context:** Create a Scratchpad file `.agent/current_task.md` with the Ticket ID and Objectives.
4. **Plan:** Outline the files to be touched.
