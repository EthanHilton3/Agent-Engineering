# Skill: UI code

- The UI is a thin layer: it **renders game state** and **calls game actions**. It never decides whether a move is legal; it asks the rules engine.
- Highlight legal spots by asking the engine for the list of legal corners or edges. Never re-compute legality in the UI.
- When an action fails, show the engine's error message to the player. Never fail silently.
- Split the UI by screen area (board, player panels, action bar, log, debug panel, modals) rather than writing one giant render function.
- Use SVG for the board. Give every clickable corner, edge, and hex a `data-` attribute holding its ID, so the debug "show IDs" option and click handling share one source of truth.
- You can't open a browser. Verify UI work with `npm run build` (type errors and bundling) and by keeping the UI logic thin enough that the tested engine does the real work.
