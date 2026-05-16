# Domain Docs — Single-Context

This project uses a single-context layout.

## File locations

- **Domain glossary**: `CONTEXT.md` at the repository root
- **Architecture Decision Records**: `docs/adr/` at the repository root

## Consumer rules

Skills that read domain docs (`improve-codebase-architecture`, `diagnose`, `tdd`) will:

1. Read `CONTEXT.md` for the project's domain language and glossary
2. Read `docs/adr/` for past architectural decisions
3. Use the project's vocabulary throughout their output
