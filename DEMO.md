# Demo Script

Run these three instructions live during the walkthrough. Memory must **not** be wiped between runs 1 and N for the learning demo.

Repository prep:

- Use a sandbox repo with a few open issues
- Include at least 2 unassigned issues with different labels/priorities
- Ensure the token has `repo` scope

## Instruction 1 — Simple

**Prompt:**

```text
Create a bug report for the login timeout issue
```

**Expected behaviour:**

- Agent creates a new GitHub issue with an appropriate title/body
- Execution report status = `success`
- One write API call (+ optional label/list checks)

## Instruction 2 — Compound

**Prompt:**

```text
Find all open issues assigned to nobody, group them by priority label, and post a weekly triage summary as a comment on issue #1
```

**Expected behaviour:**

- Agent lists open issues
- Filters unassigned issues
- Groups by priority labels (`priority: high`, etc.)
- Posts a structured summary comment
- If issue #1 does not exist, report partial failure clearly instead of silently skipping

## Instruction 3 — Learning + synthesis

**Prompt (run multiple times):**

```text
List all open milestones for this repository
```

**Expected behaviour:**

- Run 1: agent detects missing capability, calls `request_new_capability`, synthesizes `GET /repos/{owner}/{repo}/milestones`, registers it
- Run 2+: agent reuses the synthesized capability directly
- Show `api_calls` and `duration_ms` decreasing in the execution report
- Show new entry in `GET /memory` under `capabilities`

## Before/after proof points

Show on the call:

1. `GET /memory` before instruction 3
2. Run instruction 3 once — note synthesis + API call count
3. Run instruction 3 again — note reused capability and lower API call count
4. Compare `learning_notes` in both execution reports

## Suggested talking points

- Partial failure handling: intentionally pass a bad issue number and show `partial`/`failed` status
- Memory is active: point to decomposition changes between run 1 and run 5 for a similar list/triage instruction
- Synthesis is real: show the new capability record and the live GitHub API response
