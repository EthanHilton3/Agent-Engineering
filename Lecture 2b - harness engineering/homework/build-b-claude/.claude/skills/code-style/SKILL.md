---
name: code-style
description: Code style rules for this project. Use whenever writing, changing, or reviewing TypeScript code.
---

# Skill: Code style

*Adapted from `beanlab/rosters` (`dev/feature_flow/code-style.md`).*

- Write self-documenting code: break functions into smaller functions with clear, concise names. A reader should understand a function from its name and its first few lines.
- Make names accurate and helpful, but not tied too closely to the current context.
- Use TypeScript types for every exported function, type, and public field. Don't use `any`.
- **Pragmatic engineering:** don't build more than is needed right now.
- **Incremental complexity:** don't add abstractions, configuration, or extension points until something actually needs them. Don't scaffold for the future.
- **Craftsmanship:** write clean, correct, maintainable code. Don't cut corners on correctness to save time.
- Keep files focused. If a file grows past about 300 lines or takes on a second responsibility, split it along the line the plan's module list suggests.
- Keep game rules out of UI code. UI code reads state and calls rule functions; it never re-implements a rule.
- Write comments to explain *why* something is done when it isn't obvious. Don't narrate *what* the code does.
