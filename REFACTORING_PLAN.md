# Refactoring Plan for DeepSight Django/React Project

## Overall Goals

- **Modernize the Frontend:** Transition from Redux for server state management to React Query. This will simplify data fetching, caching, and state synchronization.
- **Clean Up Backend:** Refactor the backend to be more modular, improve code quality, and align with Django best practices.
- **Improve Code Quality:** Remove legacy code, commented-out code, and unnecessary complexity from both frontend and backend.
- **Enhance Readability and Maintainability:** Improve the structure and organization of the codebase to make it easier to understand and maintain.

## Frontend Refactoring Plan

### 1. State Management

- **React Query Adoption:**
  - Replace all instances of Redux Toolkit's `createAsyncThunk` with React Query's `useQuery` and `useMutation` hooks for server state management.
  - This applies to features like `auth`, `notebooks`, `reports`, and `podcasts`.
  - Create custom hooks that wrap `useQuery` and `useMutation` for each feature to encapsulate query keys and logic.
- **Global UI State:**
  - Retain Redux for managing global UI state that is not tied to server data. This includes:
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

- **Centralized API Client:**
  - Create a centralized API client (e.g., using `axios`) to handle all API requests.
  - This client should manage authentication tokens, base URLs, and error handling.
- **Typed API Endpoints:**
  - Define typed functions for each API endpoint to ensure type safety and provide better autocompletion.
  - Consider using a tool like `openapi-typescript-codegen` to generate the API client from the backend's OpenAPI schema.

### 4. Styling

- **Consistent Styling:**
  - Enforce consistent use of Tailwind CSS utility classes.
  - Remove all inline styles and replace them with utility classes or component-specific CSS modules.
- **UI Components:**
  - Use the shared UI components from `shared/components/ui` (e.g., `Button`, `Input`, `Modal`) across the application to ensure a consistent look and feel.

## Backend Refactoring Plan

### 1. Project Structure

- **Modular Apps:**
  - The project is already well-organized into modular Django apps. This structure should be maintained and reinforced.
- **Service Layer:**
  - Move business logic from views into a dedicated `services` layer within each app.
  - Each service should be responsible for a specific domain of business logic (e.g., `NotebookService`, `ReportService`).
  - This follows the "fat models, thin views, and services" pattern.

### 2. Code Quality

- **Remove Legacy Code:**
  - Conduct a thorough review of the codebase to identify and remove any commented-out code, unused variables, and legacy functions.
- **Type Hinting:**
  - Add type hints to all function and method signatures to improve code clarity and enable static analysis with tools like `mypy`.
- **Code Formatting and Linting:**
  - Enforce a consistent code style using `black` for formatting and `ruff` for linting.
  - Integrate these tools into the development workflow (e.g., pre-commit hooks).

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
  - Implement a custom exception handler in DRF to provide consistent and well-structured error responses across the API.
  - Define custom exception classes for different types of errors (e.g., `ValidationError`, `ProcessingError`).

### 6. Agent Architecture

- **`panel_crew` Agent:**
    - **Configuration:** Review `config/agents.yaml` and `config/tasks.yaml` for clarity and consistency.
    - **Code Structure:** Refactor `crew.py` to separate agent definitions from the crew definition for better modularity.
    - **Tooling:** Review the `SafeSearchTool` in `tools.py` to ensure robustness and graceful error handling.
- **`report_agent` (STORM):**
    - **Complexity:** Break down the large `deep_report_generator.py` file into smaller, more manageable modules.
    - **Modularity:** Make the connections between the `knowledge_storm`, `prompts`, and `utils` packages more explicit.
    - **Configuration:** Group related fields in the `ReportGenerationConfig` dataclass into nested dataclasses to improve readability.
    - **Code Quality:** Remove legacy code, commented-out code, and refactor long functions.

## Execution Plan

The refactoring will be carried out in the following phases:

1.  **Phase 1: Backend Cleanup and Refactoring (2 weeks)**
    - Implement the service layer and move business logic from views.
    - Add type hints and enforce code style.
    - Refactor models to use custom managers and mixins.
    - Refactor the `report_agent` and `panel_crew` agents.
2.  **Phase 2: Frontend State Management Migration (3 weeks)**
    - Introduce React Query and create custom hooks for data fetching.
    - Migrate one feature at a time from Redux to React Query, starting with `notebooks`.
3.  **Phase 3: Component and API Layer Refactoring (2 weeks)**
    - Refactor large components into smaller ones.
    - Implement the centralized API client.
4.  **Phase 4: Final Cleanup and Review (1 week)**
    - Perform a final review of the codebase to ensure all goals have been met.
    - Update documentation to reflect the new architecture.