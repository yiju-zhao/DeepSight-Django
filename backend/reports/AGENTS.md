# Reports Module – Full Refactor Plan (No Migration)

This document defines the end-to-end refactor plan for the `backend/reports` module. The project is still under development, so this plan targets a clean replacement rather than incremental migration. Follow this as an execution guide for the code agent.

## Goals
- Radical simplification (Ockham’s razor): remove unnecessary indirection and duplication.
- First principles design: clear responsibilities, minimal layers, predictable data flow.
- Eliminate circular imports by defining a clean dependency direction.
- Unify image handling into a single pipeline and insertion step.
- Centralize result publishing (content + files) in one place.
- Keep public REST API behavior stable (endpoints/serializers) unless explicitly noted.

## Target Architecture
- Layers with one-way dependency flow: presentation → application → domain → infrastructure.
- Composition root wires concrete implementations once (no factory sprawl).

### Modules
- Presentation (keep DRF views): `views.py` calls application services.
- Application
  - `application/use_cases/generate_report.py` – GenerateReportUseCase (primary orchestration).
  - `application/services/job_status.py` – lightweight job status/progress updates.
  - `application/services/task_state_sync.py` – Celery state mapping + termination.
  - `application/services/result_publisher.py` – stores artifacts to storage, updates Report fields.
  - `application/services/image_coordinator.py` – prepares ReportImage(s) + performs final content insertion once.
- Domain
  - `domain/figure_data.py` – figure data access/helpers (trimmed from current figure_service).
  - `domain/types.py` – TypedDicts/dataclasses for config and results.
  - Reuse `image_utils` intact (extractors/formatters/insertion_service/url_providers).
- Infrastructure
  - `infrastructure/report_generator_adapter.py` – adapter over DeepReportGenerator.
  - `infrastructure/storage.py` – storage abstraction(s), MinIO default.
  - `infrastructure/input_processor.py` – knowledge base input processing.
  - `infrastructure/config_provider.py` – wraps report config (replaces module-level globals).
  - `infrastructure/celery_gateway.py` – thin access to AsyncResult/revoke.
- Composition
  - `container.py` – creates and provides wired instances for use cases and services.

## Directory Layout (proposed)
- backend/reports/
  - application/
    - use_cases/generate_report.py
    - services/job_status.py
    - services/task_state_sync.py
    - services/result_publisher.py
    - services/image_coordinator.py
  - domain/
    - figure_data.py
    - types.py
  - infrastructure/
    - report_generator_adapter.py
    - storage.py
    - input_processor.py
    - config_provider.py
    - celery_gateway.py
  - image_utils/ (keep existing)
  - views.py (updated to call new use case/services)
  - container.py (new composition root)
  - models.py (keep; optional small cleanups)
  - serializers.py (keep)
  - urls.py (keep)

## Core Components (responsibilities)
- GenerateReportUseCase
  - Input: `report_id`.
  - Steps: load report → prepare inputs → (optional) figure data prep → call agent → publish artifacts → perform single image insertion pass → persist final content → return result DTO.
- JobStatusService
  - Update `progress` and state transitions (`pending`/`running`/`completed`/`failed`/`cancelled`) in DB and cache.
- TaskStateSyncService
  - Map Celery task state to Report state, extract error info, terminate tasks on failure/cancel.
  - Remove regex-based log parsing; rely on Celery result state only.
- ResultPublisher
  - Store generated files to MinIO, set `generated_files`, `main_report_object_key`, `file_metadata`.
  - Determine main report file via a single utility.
- ImageCoordinator
  - Derive figure IDs (from cached figure data or parsed content).
  - Copy KB images to report and create `ReportImage` records.
  - Insert images into content once using `ImageInsertionService + DatabaseUrlProvider`.
- ReportGeneratorAdapter
  - Adapter over `DeepReportGenerator`; holds no global/stateful caches; receives config from `ConfigProvider`.
- Storage (MinIO)
  - Provide methods for directory/object key resolution, upload, main-file detection, signed URL.
- InputProcessor
  - Produce `content_data` and (optionally) `selected_file_ids` from knowledge base selections.
- ConfigProvider
  - Provide provider/retriever/generation config; no module-level globals.

## Execution Flow (GenerateReportUseCase)
1) Load Report by `report_id`; set status to `running`.
2) Prepare inputs via InputProcessor; if `include_image`, resolve/compute figure data (domain/figure_data).
3) Build generator config via ConfigProvider + report fields + content data + figure_data.
4) Validate config via ReportGeneratorAdapter.
5) Generate via adapter (`generate_report(config)`), get `report_content`, `generated_files`, `logs`, `article_title`.
6) Publish artifacts via ResultPublisher (upload files, set `generated_files` keys, `main_report_object_key`).
7) ImageCoordinator: ensure `ReportImage` records exist, perform single content insertion pass to produce final content.
8) Persist `result_content` and set job to `completed` (or `failed` on exceptions), store error details.

## Decomposition Map (what to remove/replace)
- Remove/replace:
  - `core/generation_service.py` → superseded by `GenerateReportUseCase`.
  - `core/job_service.py` → split into `job_status.py` and `task_state_sync.py`; remove CriticalErrorDetector.
  - `core/report_image_service.py` → keep DB+copy bits inside `ImageCoordinator`; use `image_utils` for insertion.
  - All `factories/*.py` → replaced by `container.py` and `infrastructure/*` modules.
  - `orchestrator.py` → replaced by container + use case; optionally keep a thin facade calling container.
- Keep:
  - `image_utils` as-is.
  - `models.py`, `serializers.py`, `urls.py`, `views.py` (updated to call the new use case/services).

## Step-by-Step Refactor Plan (do this order)
1) Create new directories and empty modules per the Directory Layout.
2) Implement `infrastructure/config_provider.py` to wrap current `config.report_config` logic without globals; expose: `get_model_provider_config`, `get_retriever_config`, `get_generation_config`.
3) Implement `infrastructure/storage.py` (MinIO only). Methods: `store_generated_files`, `get_main_report_file`, `get_presigned_url` passthrough, and helper path/key builders.
4) Implement `infrastructure/report_generator_adapter.py` as a thin adapter over `agents.report_agent.deep_report_generator.DeepReportGenerator` with `validate_configuration`, `generate_report`, `get_supported_providers`, `cancel_generation`.
5) Implement `infrastructure/input_processor.py` using current `InputProcessorInterface` behavior to produce `content_data` (no temp files by default).
6) Implement `domain/figure_data.py` to:
   - create and fetch combined figure data for a report.
   - extract figure IDs.
7) Implement `application/services/result_publisher.py` to upload files and set model fields.
8) Implement `application/services/image_coordinator.py` to:
   - find KB images by figure IDs (query), copy to report folder, create `ReportImage` records.
   - invoke `ImageInsertionService(DatabaseUrlProvider())` to insert figures once.
9) Implement `application/services/task_state_sync.py` to map Celery `AsyncResult.state` to our `Report` states and terminate tasks as needed. Remove regex-based log parsing.
10) Implement `application/services/job_status.py` for DB+cache updates.
11) Implement `application/use_cases/generate_report.py` orchestrating the full flow described in Execution Flow.
12) Implement `container.py` to wire concrete implementations and expose handles for views.
13) Update `views.py` to call into the new container/use case for:
    - job creation (create `Report` instance with `job_id`), enqueue Celery task as before, but progress/status use `JobStatusService`.
    - status checks: use `TaskStateSyncService` for on-demand sync; otherwise return DB-backed status.
    - cancellation: use `TaskStateSyncService` to revoke + update DB status.
    - downloads: unchanged; use `Report.get_report_url`.
14) Delete old modules under `core/` and `factories/`, and `orchestrator.py` once new code compiles.
15) Ensure imports are updated; run linters/formatters.
16) Add unit tests for: `GenerateReportUseCase`, `ResultPublisher`, `ImageCoordinator`, `TaskStateSyncService`.

## Coding Conventions
- Keep functions/classes small and single-purpose.
- Use explicit exceptions; avoid broad bare `except Exception` except at app boundaries (views/use case) where needed.
- No dynamic/runtime imports to avoid circular dependencies—fix imports by layering.
- Use TypedDicts or dataclasses for config/result payloads between layers.
- Logging: info for major phase transitions, warning for recoverable cases, error for failures.

## Acceptance Criteria
- Endpoints keep returning the same shapes for list/detail/download/cancel.
- Generating a report with `include_image=True` results in:
  - Uploaded files persisted in MinIO and `main_report_object_key` set.
  - `result_content` contains inserted figure images exactly once.
- Cancelling a job sets status to `cancelled` and attempts to revoke the task.
- Celery failures are reflected in job status without regex-inspection of log lines.

## Notes and Risks
- If local storage is still required for dev, implement a second storage class behind the same interface; default to MinIO in composition.
- If `DeepReportGenerator` signature changes, only `report_generator_adapter.py` should be updated.
- Large files and binary operations should remain in infrastructure to keep application/services pure and testable.

---

Action: proceed to create the new directories/files and port logic following the Step-by-Step Refactor Plan. When done, remove deprecated modules and update imports.

