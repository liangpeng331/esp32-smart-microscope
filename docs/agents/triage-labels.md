# Triage Labels

This project uses the five default canonical triage labels:

| Label | Purpose |
|-------|---------|
| `needs-triage` | New issue, awaiting maintainer evaluation |
| `needs-info` | Waiting on reporter to provide more information |
| `ready-for-agent` | Fully specified, ready for an AI agent to implement |
| `ready-for-human` | Needs human implementation |
| `wontfix` | Will not be actioned |

## State machine

```
needs-triage → needs-info → needs-triage → ready-for-agent → (closed)
             ↘ ready-for-human
             ↘ wontfix
             ↘ ready-for-agent
```
