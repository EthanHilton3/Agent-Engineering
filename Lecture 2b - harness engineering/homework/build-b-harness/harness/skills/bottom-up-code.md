# Skill: Bottom-up coding

*Adapted for TypeScript from `beanlab/rosters` (`_experimental/bean/bottom-up-code.md`).*

**Goal:** cleaner, self-documenting code.

## Process

**Write the usage before the definition.** In each file, put the higher-level functions **above** the functions they call. Write each function body as close to pseudocode as you can, calling helper functions that don't exist yet, then implement those helpers below it.

- **Modules:** write the exported (public) functions first, then the private helpers they need.
- **Classes:** start with the public methods. Implement private helpers as you discover you need them. Write the constructor and fields last.
- **The application:** start from the entry point, imagining the components that would make it clear and simple. Then build out each dependency as it's referenced, working down the stack.

**Imports:** don't stop to manage imports while you write. Once the file is complete, add all the imports at the top.

**Duplication:** while writing, don't worry about it. Once the file is done, look for logic that **must stay consistent** (the same business rule) and pull it into a shared helper. Two blocks that merely look alike today but represent different rules should stay separate.

## Also

- Give every exported function a one-line doc comment saying what it is for.
