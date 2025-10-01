# Repository Guidelines

## Project Structure & Module Organization
- `frontend/` (Vue 3 + Vite) hosts the UI; group pages under `src/views/`, share stores in `src/store/`, and reuse assets from `src/assets/`.
- `backend/` (Flask) serves REST/WebSocket APIs; register blueprints in `routes/`, common helpers in `utils/`, and keep packaged artifacts in `dist/`.
- `electron/` drives the desktop main process; adjust bootstrapping in `main.js` when wiring new channels.
- `assets/` supplies icons and build resources, `scripts/` holds automation such as `build_backend.py`, and `dist/` is disposable output.

## Build, Test, and Development Commands
- `npm run dev` installs dependencies, clears ports, and boots backend, frontend, and Electron together.
- `npm run frontend:dev` and `npm run backend:dev` run each layer independently for targeted debugging.
- `npm run build` triggers `frontend:build` plus backend packaging; follow with `npm run dist` for installers or `npm run release` to publish.
- `npm run kill-ports` frees ports 3000/5001/5002 when hot reload fails to clean up.

## Coding Style & Naming Conventions
- Vue/JavaScript: two-space indent, components in PascalCase (`AgentPanel.vue`), composables and utilities in camelCase, routed files in kebab-case.
- Python: follow PEP 8, keep modules snake_case, classes CapWords, and async helpers suffixed `_task` for clarity.
- Config files stay English-commented; prefer descriptive option names over abbreviations to help triage builds.
- Make code consise and readable; avoid deep nesting, large functions, and complex one-liners. Make each file small and focused. If existing files work, avoid unnecessary refactors.

## Testing Guidelines
- Automated suites are not yet checked in; add backend coverage under `backend/tests/` with `pytest` and frontend specs under `frontend/src/__tests__/` using `vitest` or Playwright.
- Name test files after the feature (`agents_api_test.py`, `AgentPanel.spec.ts`) and document invocation commands in the PR description.
- Exercise critical flows with `npm run dev` until CI lands; attach logs or screenshots when verifying UI changes.

## Commit & Pull Request Guidelines
- Keep commit subjects short and imperative, mirroring history (`fix signing password`, `0.6.8`); add optional scope prefixes (`frontend:`, `backend:`) when they clarify impact.
- PRs must explain intent, list manual or automated checks, and flag configuration or dependency updates; include UI captures for visual changes.
- Prefer focused PRs; coordinate cross-layer updates in a single review when backend, frontend, and Electron touch the same feature.

## Security & Configuration Tips
- Never commit credentials; store API keys and SSH data in ignored local `.env` files or machine-specific `backend/settings.json` variants.
- Review `backend/settings.json` defaults (paths, ports, model choices) before packaging releases or sharing sample configs.
- Never run rm -rf / or similar commands anywhere in the codebase. Never commit or push code to the main branch. If commit is necessary, commit to a separate branch.
