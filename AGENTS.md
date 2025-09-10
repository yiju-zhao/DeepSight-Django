# Repository Guidelines

## Project Structure & Module Organization
- Backend (Django): `backend/` with project module in `backend/backend/` and apps like `reports/`, `podcast/`, `conferences/`, `notebooks/`, `users/`, `core/`, `infrastructure/`. Settings live in `backend/backend/settings/`. Entry point: `backend/manage.py`.
- Frontend (React + Vite + TS): `frontend/` with source in `frontend/src/` and tests/utilities under `frontend/src/test-utils/`.
- Ops & assets: `docker/` for local services, `backend/env.template` for env vars, `backend/logs/` for runtime logs.

## Build, Test, and Development Commands
- Backend
  - Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`
  - Run dev: `DJANGO_ENVIRONMENT=development python backend/manage.py migrate && DJANGO_ENVIRONMENT=development python backend/manage.py runserver 0.0.0.0:8000`
  - Test: `DJANGO_ENVIRONMENT=testing python backend/manage.py test`
- Frontend
  - Setup: `cd frontend && npm install`
  - Run dev: `npm run dev`  • Build: `npm run build`
  - Test/Lint: `npm test` • `npm run test:coverage` • `npm run lint` • `npm run type-check`

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, snake_case modules, PascalCase classes. Keep business logic in services (e.g., `reports/core/*`). DRF views/serializers live in app folders. Add module/class/function docstrings where behavior isn’t obvious.
- TypeScript/React: Follow ESLint rules; components in PascalCase (e.g., `ReportListSection.tsx`), utilities in camelCase/kebab-case (`utils/filePreview.ts`). Prefer functional components and hooks.

## Testing Guidelines
- Backend: Place tests in `tests.py` or `tests/` with `test_*.py`. Use Django `TestCase` and DRF API client. Mock external services (MinIO, Redis, Milvus) and avoid network I/O.
- Frontend: Vitest + Testing Library. Colocate `*.test.ts(x)` with code. Cover store slices, services, and critical UI flows.

## Commit & Pull Request Guidelines
- Commits: Use concise, imperative messages (e.g., “fix API error handling”, “optimize notebook service”). Include scope when helpful: `frontend:`, `backend:reports:`.
- PRs: Provide context, linked issues, repro steps, and screenshots/GIFs for UI. Note env/config needed to test. Ensure `npm test` and `manage.py test` pass.

## Security & Configuration Tips
- Create `backend/.env` from `backend/env.template`; do not commit secrets. Set `DJANGO_ENVIRONMENT` (defaults to development). For local deps (MinIO/Redis/Milvus), use `docker/` or `./start_dev_dockers.sh`.

