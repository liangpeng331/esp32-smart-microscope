# Issue Tracker — GitHub

Issues are tracked in GitHub Issues of this repository.

## How to interact

- **Read an issue**: `gh issue view <number>`
- **Create an issue**: `gh issue create --title "..." --body "..." --label "needs-triage"`
- **List issues**: `gh issue list --label "ready-for-agent"`
- **Comment on an issue**: `gh issue comment <number> --body "..."`

## Required setup

- The repository must have a GitHub remote configured
- `gh` CLI must be authenticated (`gh auth login`)
- The repository must exist on GitHub with Issues enabled
