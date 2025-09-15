# Refactoring Plan for DeepSight Django/React Project

## Overall Goals

- **Modernize the Frontend:** Transition from Redux for server state management to React Query. This will simplify data fetching, caching, and state synchronization.
- **Clean Up Backend:** Refactor the backend to be more modular, improve code quality, and align with Django best practices.
- **Improve Code Quality:** Remove legacy code, commented-out code, and unnecessary complexity from both frontend and backend.
- **Enhance Readability and Maintainability:** Improve the structure and organization of the codebase to make it easier to understand and maintain.
- **Boost Performance:** Optimize both frontend and backend for better performance and user experience.
- **Improve Test Coverage:** Increase test coverage to ensure the stability and reliability of the application.

## Frontend Refactoring Plan

### 1. State Management

- **React Query Adoption (feature-by-feature):**
  - Migrate remaining server state from Redux Toolkit thunks to React Query hooks. Notebooks already use React Query; next focus on `reports` (replace `reportSlice` thunks) and then other features as needed.
  - Provide feature-scoped custom hooks that wrap `useQuery`/`useMutation`, encapsulating query keys, options, and success/error flows.
  - Define a centralized query keys module (e.g., `src/shared/queries/keys.ts`) to prevent cache key collisions and standardize patterns for pagination and filters (include params in keys).
  - Handle downloads/streams with `useMutation` and `blob`/stream responses; avoid forcing JSON for file endpoints.
  - Route global toasts/loading to React Query callbacks or a small helper rather than thunk lifecycles.
- **Global UI State:**
  - Keep Redux for UI-only state not tied to server data:
    - Theme (light/dark mode)
    - Sidebar state (open/closed)
    - Notifications/toasts
    - Global modal states

### 2. Component Structure

- **Component Granularity:**
  - Break down large components like `DashboardPage`, `DeepdivePage`, and `StudioPanel` into smaller, more focused components.
  - Each component should have a single responsibility.
- **Custom Hooks:**
  - Create custom hooks to encapsulate complex logic, such as:
    - `useNotebookOperations` for handling notebook CRUD operations.
    - `useFileUploader` for managing file uploads and validation.
    - `useJobStatus` for polling the status of background jobs.
- **File Organization:**
  - Organize files within each feature folder by type: `components`, `hooks`, `pages`, `services`, `types`.

### 3. API Layer

- **Consolidated API Client (fetch-based):**
  - Consolidate on the existing fetch-based client (`src/shared/api/client.ts`) and remove duplicate clients (e.g., `src/shared/utils/httpClient.ts`).
  - Manage CSRF, credentials, base URL, and error parsing centrally. Avoid introducing `axios` to minimize churn.
- **Typed API Endpoints (optional):**
  - Define typed helper functions per endpoint where helpful.
  - Optionally generate types from the OpenAPI schema (`/swagger.json` or `/openapi.json`) using `openapi-typescript`/`openapi-typescript-codegen`. If adopted, document the generation script and keep it in CI only after stabilizing schemas.

### 4. Styling

- **Consistent Styling:**
  - Enforce consistent use of Tailwind CSS utility classes.
  - Remove all inline styles and replace them with utility classes or component-specific CSS modules.
- **UI Components:**
  - Use the shared UI components from `shared/components/ui` (e.g., `Button`, `Input`, `Modal`) across the application to ensure a consistent look and feel.

## Backend Refactoring Plan

### 1. Project Structure

- **Modular Apps:**
  - The project is already organized into modular Django apps. Maintain and reinforce this structure.
- **Service Layer:**
  - Ensure views consistently delegate to existing services (e.g., reports core services, notebooks services) rather than re-implementing logic in views.
  - Add custom managers/querysets where they reduce repeated filters, keeping to the "thin views, focused services" pattern.

### 2. Code Quality

- **Remove Legacy Code:**
  - Review and remove commented-out/unused code and legacy utilities.
- **Type Hinting:**
  - Add type hints widely and enable static checks (optionally `mypy`).
- **Code Formatting and Linting:**
  - Enforce consistent style via `black` and `ruff`. Add pre-commit hooks to run them locally.

### 3. Models

- **Custom Managers and Querysets:**
  - Create custom managers and querysets for models to encapsulate common database queries (e.g., `Notebook.objects.for_user(user)`).
- **Model Mixins:**
  - Use model mixins for common fields like `created_at`, `updated_at`, and `uuid` to reduce code duplication.

### 4. Views and Serializers

- **ViewSets and Routers:**
  - Utilize DRF's `viewsets` and `routers` to simplify URL configuration and reduce boilerplate code in views.
- **Specific Serializers:**
  - Create specific serializers for different actions (e.g., `NotebookListSerializer`, `NotebookCreateSerializer`, `NotebookDetailSerializer`).
  - This improves validation, performance, and security by only exposing the necessary fields for each action.

### 5. Error Handling

- **Custom Exception Handler:**
  - Implement a DRF `EXCEPTION_HANDLER` to normalize error shapes (e.g., `detail`, field errors) across the API in a way that matches the frontend client’s parser.
  - Define custom exception classes for domain errors (e.g., `ProcessingError`) and map them to HTTP responses consistently.

### 6. Agent Architecture

- **`panel_crew` Agent:**
  - Configuration: Review `config/agents.yaml` and `config/tasks.yaml` for clarity and consistency.
  - Code Structure: If you separate agent definitions from crew assembly in `crew.py`, update imports where used (e.g., podcast service) and keep crewAI conventions.
  - Tooling: Harden `SafeSearchTool` for graceful failures.
- **`report_agent` (STORM):**
  - Complexity: Break `deep_report_generator.py` into smaller modules by concern (config, I/O, runner orchestration) while preserving public APIs used by Celery tasks.
  - Lazy imports: Preserve the existing lazy import pattern and macOS-safe environment flags to avoid heavy import-time side effects.
  - Configuration: Group related fields in `ReportGenerationConfig` via nested dataclasses as appropriate.
  - Code Quality: Remove legacy code/comments and refactor long functions.
  - Dependency Injection: Consider lightweight DI for clearer dependencies.

## Testing Strategy

- **Backend:**
  - Write integration tests for the service layer to ensure that the business logic is working correctly.
  - Use `pytest` and `pytest-django` for writing and running tests.
  - Use `factory-boy` to create test data.
  - Aim for a high test coverage for the service layer.
- **Frontend:**
  - Write unit/integration tests for components and hooks using Vitest and React Testing Library.
  - Use `msw` to mock API requests.
- **End-to-End Testing:**
  - Use a tool like `Cypress` or `Playwright` to write end-to-end tests for critical user flows.

## Performance Considerations

- **Frontend:**
  - Use `React.memo` and `useMemo` to prevent unnecessary re-renders.
  - Use code splitting to reduce the initial bundle size.
  - Use a tool like `Lighthouse` to identify performance bottlenecks.
- **Backend:**
  - Optimize database queries using `django-debug-toolbar` to identify slow queries.
  - Use caching for frequently accessed data.

## Documentation

- **README.md:**
  - Update the `README.md` file with the new architecture and instructions on how to run the project.
- **Code Comments:**
  - Add comments to the code where the logic is complex or non-obvious.
- **Storybook:**
  - Use `Storybook` to document the UI components, which will make them easier to reuse and test.
 - **API Usage & Errors:**
   - Document the consolidated API client usage and the normalized error response shape expected from the backend.

## Execution Plan

The refactoring will be carried out in the following phases:

1.  **Phase 1: Backend foundations (1–1.5 weeks)** ✅ **COMPLETED**
    - ✅ Add DRF custom exception handler and normalize error shapes.
    - ✅ Add pre-commit hooks for `black` and `ruff`; start adding type hints.
    - ✅ Ensure views consistently delegate to services; add targeted custom managers/querysets.
    - ✅ Add targeted custom managers/querysets.
    - ⏳ Optional: plan migration of reports models to shared `BaseModel` mixins (separate PR/migration window).
2.  **Phase 2: Frontend API + state (1.5–2 weeks)** ✅ **COMPLETED**
    - ✅ Consolidate to `src/shared/api/client.ts` and remove duplicate clients.
    - ✅ Introduce centralized query keys and migrate the `reports` feature from thunks to React Query (handle downloads/streams properly).
3.  **Phase 3: Components and UX (1–1.5 weeks)** ✅ **COMPLETED**
    - ✅ Split overly large components where needed; ensure shared UI components have Storybook stories.
    - ✅ Standardize toast/loading flows via React Query callbacks.
4.  **Phase 4: Tests and performance (1–1.5 weeks)** ⏳
    - ⏳ Add Vitest + MSW tests for migrated features; add a couple of E2E flows (Cypress or Playwright).
    - ⏳ Optimize obvious frontend re-render hot paths and heavy backend queries.
5.  **Phase 5: Agents refactor (0.5 week)** ⏳
    - ⏳ Modularize STORM parts while preserving lazy import + env safety; smoke test Celery integration.
6.  **Phase 6: Final cleanup and docs (0.5 week)** ⏳
    - ⏳ Final review, remove dead code, update README and API usage docs.

## Progress Log

**Phase 1 Progress (Backend Foundations):**

- ✅ **Custom Exception Handler**: Added comprehensive DRF exception handler in `core/exceptions.py` that normalizes all API error responses with consistent format (`detail`, `field_errors`, `error_code` fields). Updated `settings/base.py` to use the handler.

- ✅ **Pre-commit Setup**: Created complete development tooling setup:
  - `requirements-dev.txt` with black, ruff, mypy, pytest, etc.
  - `.pre-commit-config.yaml` with hooks for black, ruff, mypy, and common checks
  - `pyproject.toml` with tool configurations for black, ruff, mypy
  - `Makefile` with common development commands (lint, format, test, etc.)

- ✅ **Views Service Delegation**: Verified that existing views in `notebooks/views.py` and `reports/views.py` properly delegate to service classes. The architecture is already well-structured with service layer separation.

- ✅ **Custom Managers/Querysets**: Added comprehensive custom managers and querysets for both `notebooks` and `reports` models to encapsulate common query patterns and improve database efficiency.

**Phase 2 Progress (Frontend API + State):**

- ✅ **API Client Consolidation**: Successfully migrated all services (`SourceService`, `StudioService`, `SessionChatService`) from the duplicate `httpClient.ts` to the modern `apiClient` from `shared/api/client.ts`. Removed the redundant HTTP client.

- ✅ **Centralized Query Keys**: Created comprehensive query key system in `shared/queries/keys.ts` with hierarchical structure for all major entities (notebooks, reports, users, dashboard, etc.) including proper filtering and pagination support to prevent cache collisions.

- ✅ **React Query Migration**: Created modern React Query hooks for reports feature in `features/reports/hooks/useReports.ts` that replace Redux thunks with proper caching, optimistic updates, server state management, and toast notifications. Hooks include:
  - `useReportsList()` - List reports with filtering
  - `useReport()` - Single report details with auto-refresh for active jobs
  - `useReportContent()` - Report content with proper caching
  - `useCreateReport()`, `useUpdateReport()`, `useCancelReport()`, `useDeleteReport()` - Mutations with cache invalidation
  - `useReportsUtils()` - Cache utilities and helpers

**Phase 3 Progress (Components and UX):**

- ✅ **Component Decomposition**: Successfully broke down the large `DashboardPage` component into focused, reusable components:
  - `DashboardHeader` - Handles title and subtitle display
  - `ReportsSection` - Manages trending reports display with loading states
  - `PodcastsSection` - Handles podcast listing with empty states
  - `DashboardActions` - Floating action buttons with accessibility
  - `EmptyState` - Reusable empty state component with customizable content
  - `LoadingState` - Consistent loading UI component
  - `useDashboardData` - Custom hook that consolidates all data fetching logic

- ✅ **Storybook Stories**: Created comprehensive Storybook documentation for shared UI components:
  - `Button.stories.tsx` - All variants, sizes, states, and use cases
  - `Alert.stories.tsx` - Different alert types with icons and layouts
  - `Badge.stories.tsx` - Status badges, categories, and size variations
  - `LoadingSpinner.stories.tsx` - Loading states and integration examples

- ✅ **Standardized Notifications**: Built comprehensive notification system that integrates seamlessly with React Query:
  - `notifications.ts` - Centralized notification utilities for all operation types (success, error, info)
  - `operationCallbacks` - Pre-configured callbacks for common CRUD operations
  - Updated `useReports` hooks to use standardized notifications instead of custom toast implementations
  - Consistent error handling and success messaging across the application

- ✅ **Custom Hooks**: Created reusable hooks that encapsulate complex component logic:
  - `useFileUploader` - Complete file upload management with validation, progress tracking, and error handling
  - `useJobStatus` - Background job monitoring with polling, auto-refresh, and status updates
  - Existing `useNotebookOperations` - Comprehensive notebook CRUD operations with React Query integration

## Notes & Risks

- Avoid introducing axios; consolidate on the existing fetch client to reduce churn.
- When defining React Query keys, always include filters/pagination to prevent cache collisions.
- Streaming/download endpoints must not assume JSON; use `blob` handling and `useMutation`.
- Preserving lazy imports and env flags in `report_agent` is critical to avoid heavy import-time side effects and macOS issues.
- If adopting OpenAPI codegen, keep it optional initially and ensure it matches DRF error shapes to avoid breaking the client.
