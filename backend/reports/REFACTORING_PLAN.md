# Refactoring Plan for the `reports` Module

## 1. Investigation Summary

The `backend/reports` module is currently complex due to the use of multiple advanced software design patterns like Dependency Injection, Factories, and a Service-Oriented Architecture. These patterns have led to unnecessary layers of abstraction and boilerplate code, making the system difficult to understand and maintain.

The main issues identified are:

- **Over-abstraction:** The use of factories and interfaces for components that have only a single implementation (e.g., the report generator and input processor).
- **Scattered Logic:** Business logic is spread across numerous files and directories, including `orchestrator.py`, `core/`, `factories/`, and `interfaces/`. This makes tracing the execution flow challenging.
- **Overly Complex Image Handling:** The logic for managing images and figures is fragmented across `core/figure_service.py`, `core/report_image_service.py`, and a large `image_utils` package with its own sub-modules.
- **Redundant Configuration:** A custom configuration system in `reports/config/` exists alongside Django's standard settings, creating two sources of truth for configuration.

### Assumptions & Constraints

- No backward compatibility is required; breaking changes are acceptable.
- No database/model schema changes are planned or necessary.

## 2. Refactoring Plan

The goal of this refactoring is to simplify the codebase by applying the principles of Occam's Razor and first-principles thinking, reducing complexity while preserving core functionality.

### 2.1. Consolidate Core Services

- **Action:** Merge the responsibilities of `GenerationService`, `InputService`, and `StorageService` into a single, more focused `ReportGenerationService`.
- **Rationale:** This new service will manage the end-to-end process of generating a report, from processing inputs to storing the final results, reducing the number of service classes.
- **Action:** Retain `JobService` to handle the lifecycle of report jobs (creation, status updates, cancellation).
- **Rationale:** Its responsibilities are distinct from report generation logic.
- **Action:** The `ReportOrchestrator` will be simplified, delegating tasks primarily to the new `ReportGenerationService` and the existing `JobService`.
- **Rationale:** This clarifies the role of the orchestrator as a high-level coordinator.

### 2.2. Simplify Image Handling

- **Action:** Create a new, unified `ImageService` within `reports/core/`.
- **Rationale:** This service will absorb the responsibilities of both `FigureDataService` and `ReportImageService`, centralizing all image-related logic.
- **Action:** The `image_utils` package will be refactored into a single `reports/image_utils.py` file containing only essential helper functions.
- **Rationale:** This will significantly reduce the number of files and modules involved in image processing.

### 2.3. Eliminate Unnecessary Abstractions

- **Action:** Remove `ReportGeneratorFactory` and `InputProcessorFactory`, along with their corresponding interfaces in `reports/interfaces/`.
- **Rationale:** These abstractions are not currently providing value as there is only one implementation for each.
- **Action:** Directly instantiate `DeepReportGeneratorAdapter` and `KnowledgeBaseInputProcessor` within the new `ReportGenerationService`.
- **Rationale:** This removes a layer of indirection.
- **Action:** The `StorageFactory` will be retained.
- **Rationale:** It correctly manages multiple storage backends (local file system and MinIO), which is a valid use case for a factory.

### 2.4. Unify Configuration

- **Action:** Remove the custom `reports/config` module and update all imports to use Django settings.
- **Rationale:** Eliminates a redundant configuration system and consolidates configuration into a single source of truth.
- **Action:** Migrate logic for loading API keys and other settings (previously from `secrets.toml`) into the main Django settings (e.g., `backend/settings/base.py`) using a standard library (e.g., `django-environ` or `python-decouple`).
- **Rationale:** Centralizes configuration and simplifies environment management across web and worker processes.

### 2.5. Testing Plan

Introduce comprehensive tests to protect core behavior during and after refactor. No compatibility shims are required; tests target only the new structure.

- Unit tests
  - `services/generation.py`: cover end-to-end flow orchestration using fakes/mocks for `ImageService`, `PdfService`, and storage interactions; verify status updates via `JobService` hooks.
  - `services/image.py`: validate image ingestion, formatting, URL generation, and error cases (invalid type, oversized image); ensure filename/path sanitization.
  - `services/pdf.py`: verify PDF creation from representative inputs; confirm metadata and that output bytes are non-empty and parsable; guard against memory overuse on large inputs via chunked processing where applicable.
  - `storage.py`: exercise local filesystem backend with temp directories; mock MinIO/S3 client for upload, download, and pre-signed URL paths.
  - Utilities (new `image_utils.py`): unit test helpers for extract/format/validate behavior and edge cases.

- Integration tests
  - Orchestrated report generation happy path: from inputs to persisted artifacts, asserting file existence/paths and job status transitions.
  - API-level tests (views/serializers): verify current response shapes and status codes remain consistent post-refactor.

- Testing standards
  - Target >=80% coverage for `reports/services/*`, `reports/storage.py`, and `reports/image_utils.py`.
  - Add factory data/helpers for images and sample inputs.
  - Run tests in CI with deterministic seeds and temp dirs; avoid network by mocking external clients.

This refactoring will result in a simpler, more intuitive structure for the `reports` app, making it easier to develop and maintain.

## 3. Proposed Code Structure

The refactoring will result in a flatter and more intuitive directory structure.

### Current Structure

```
reports/
├── __init__.py
├── admin.py
├── apps.py
├── managers.py
├── models.py
├── orchestrator.py
├── serializers.py
├── tasks.py
├── tests.py
├── urls.py
├── views.py
├── config/
│   ├── __init__.py
│   ├── model_providers.py
│   ├── report_config.py
│   └── retriever_configs.py
├── core/
│   ├── __init__.py
│   ├── figure_service.py
│   ├── generation_service.py
│   ├── input_service.py
│   ├── job_service.py
│   ├── pdf_service.py
│   ├── report_image_service.py
│   └── storage_service.py
├── factories/
│   ├── __init__.py
│   ├── input_processor_factory.py
│   ├── report_generator_factory.py
│   └── storage_factory.py
├── image_utils/
│   ├── __init__.py
│   ├── extractors.py
│   ├── formatters.py
│   ├── insertion_service.py
│   ├── url_providers.py
│   └── validators.py
├── interfaces/
│   ├── __init__.py
│   ├── configuration_interface.py
│   ├── file_storage_interface.py
│   ├── input_processor_interface.py
│   └── report_generator_interface.py
└── migrations/
    └── ...
```

### Proposed New Structure

```
reports/
├── __init__.py
├── admin.py
├── apps.py
├── managers.py
├── models.py
├── orchestrator.py
├── serializers.py
├── tasks.py
├── tests.py
├── urls.py
├── views.py
├── image_utils.py          # <-- Simplified from the image_utils package
├── storage.py              # <-- Contains StorageFactory and implementations
├── migrations/
│   └── ...
└── services/
    ├── __init__.py
    ├── generation.py     # <-- Contains new ReportGenerationService
    ├── image.py          # <-- Contains new unified ImageService
    ├── job.py            # <-- Contains JobService
    └── pdf.py            # <-- Contains PdfService
```

This new structure reduces the number of directories from 6 to 2 (excluding `migrations`) and consolidates related logic into single, cohesive service modules.

## 4. Execution Plan (Cutover)

Since backward compatibility is out of scope, proceed with a single cutover refactor guarded by tests:

- Implement new modules under `reports/services/`, `reports/storage.py`, and `reports/image_utils.py`.
- Replace usages across `reports/` to call the new services directly; remove factories/interfaces and old `core/` modules absorbed into the new services.
- Remove `reports/config/` and update all references to use Django settings; delete obsolete files.
- Update imports in `orchestrator.py`, `tasks.py`, `views.py`, and any other call sites.
- Add and run unit/integration tests; iterate until green with coverage targets met.
- Perform a clean run of report generation locally (including images and PDF) to validate outputs.
