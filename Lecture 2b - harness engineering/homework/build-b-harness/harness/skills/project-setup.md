# Skill: Project setup (Vite + TypeScript + Vitest)

- `package.json` scripts must be exactly:
  - `"dev": "vite"` (for humans only; never run it yourself)
  - `"build": "tsc --noEmit && vite build"`
  - `"test": "vitest run"` (the `run` keeps it out of watch mode)
  - `"typecheck": "tsc --noEmit"`
- Install dev dependencies with one command: `npm install --save-dev typescript vite vitest`. Give it a shell timeout of about 240 seconds.
- `tsconfig.json`: `"strict": true`, `"module": "ESNext"`, `"moduleResolution": "bundler"`, `"target": "ES2022"`, `"lib": ["ES2022", "DOM"]`, `"noEmit": true`, and include `src` and `tests`.
- The game rules must run under Vitest's default Node environment, with no DOM. If the rules import anything from the UI or reference `document` or `window`, the module boundaries are wrong.
- `index.html` sits in the project root and loads `/src/main.ts` with `<script type="module">`.
- Add a `.gitignore` containing `node_modules/` and `dist/`.
- After any config change, run `npm test`, `npm run typecheck`, and `npm run build` to confirm the setup still works.
