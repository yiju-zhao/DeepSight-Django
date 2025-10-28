OpenAPI and Type Generation

Overview
- Backend exposes an OpenAPI schema via drf-spectacular:
  - Raw schema (JSON): `/api/schema/`
  - Swagger UI: `/api/schema/swagger-ui/`
  - ReDoc: `/api/schema/redoc/`

Generate TypeScript types
- Install the generator once (locally):
  - Using pnpm: `pnpm dlx openapi-typescript http://127.0.0.1:8000/api/schema/ -o frontend/src/shared/types/api.generated.ts`
  - Using npx: `npx openapi-typescript http://127.0.0.1:8000/api/schema/ -o frontend/src/shared/types/api.generated.ts`

Front-end helper script
- From `frontend/` directory you can run (after installing the tool globally or via npx):
  - `npm run gen:types`

Notes
- Ensure backend is running locally at `http://127.0.0.1:8000` (or pass a different `API_URL` env var).
- Generated types should be imported where appropriate (e.g. replacing hand-written request/response types over time).
- Keep the generated file out of manual edits. Re-generate as backend API evolves.
