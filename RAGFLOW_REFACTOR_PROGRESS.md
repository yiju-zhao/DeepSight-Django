# RAGFlow SDK to HTTP Refactor - Progress Tracker

**Start Date**: 2025-10-31
**Status**: IN PROGRESS

## Plan Review ✅

**Strengths**:
- Clear layered architecture (exceptions → models → http_client → service)
- Backward compatibility via compatibility shim
- Phased approach minimizes risk
- Comprehensive endpoint coverage
- Test coverage at each layer

**Confirmed Approach**:
- Phase 1-6 execution
- Keep client.py temporarily with deprecation warnings
- Use Pydantic for validation
- httpx for HTTP client (better async support than requests)

---

## Phase 1: Foundation and Scaffolding ✅ COMPLETED

### 1.1 Create exceptions.py ✅
- [x] Base RagFlowError
- [x] RagFlowAPIError (HTTP errors)
- [x] RagFlowDatasetError
- [x] RagFlowDocumentError
- [x] RagFlowChatError
- [x] RagFlowSessionError
- [x] RagFlowRateLimitError
- [x] RagFlowConfigurationError
- [x] RagFlowTimeoutError
- [x] RagFlowConnectionError

### 1.2 Create models.py ✅
- [x] APIResponse[T] generic
- [x] Paginated[T] generic
- [x] CompletionData
- [x] CompletionResponse
- [x] CompletionStreamEvent
- [x] ChatSession
- [x] Chunk
- [x] Dataset (placeholder)
- [x] Document (placeholder)
- [x] Chat (placeholder)
- [x] ReferenceChunk, CompletionReference
- [x] RelatedQuestionsData
- [x] DocumentInfo, ChunkListData, SessionListData

### 1.3 Create http_client.py ✅
- [x] RagFlowHttpClient class
- [x] Constructor with base_url, api_key, login_token
- [x] request() method with retry logic
- [x] get(), post(), put(), delete() helpers
- [x] upload() for multipart
- [x] Stream iterator support (stream(), stream_json())
- [x] Timeout configuration (connect, read, stream timeouts)
- [x] Error mapping to exceptions
- [x] Exponential backoff for retries
- [x] Context manager support

### 1.4 Create service.py ✅
- [x] RagflowService class
- [x] Constructor with http_client
- [x] conversation() - streaming and non-streaming
- [x] create_chat_session(), list_chat_sessions(), update_chat_session(), delete_chat_sessions()
- [x] related_questions()
- [x] list_chunks()
- [x] health_check()
- [x] Method stubs for Phase 3 (datasets, documents, chats)
- [x] get_ragflow_service() factory function

### 1.5 Tests ✅
- [x] test_exceptions.py (comprehensive tests for all exceptions)
- [x] test_models.py (Pydantic model validation tests)
- [x] test_http_client.py (mocked httpx tests)
- [x] test_service.py (mocked service tests)

---

## Phase 2: Migrate Existing Direct-HTTP Flows

### 2.1 Completions ⏳
- [ ] Implement conversation() in service
- [ ] Non-streaming support
- [ ] Streaming support
- [ ] Tests

### 2.2 Chat Sessions CRUD ⏳
- [ ] create_chat_session()
- [ ] list_chat_sessions()
- [ ] update_chat_session()
- [ ] delete_chat_sessions()
- [ ] Tests

### 2.3 Related Questions ⏳
- [ ] related_questions()
- [ ] Tests

### 2.4 List Chunks ⏳
- [ ] list_chunks()
- [ ] Tests

### 2.5 Update client.py ⏳
- [ ] Replace direct HTTP with service calls
- [ ] Add deprecation warnings

---

## Phase 3: Replace SDK Flows

### 3.1 Datasets ⏳
- [ ] create_dataset()
- [ ] delete_dataset()
- [ ] update_dataset()
- [ ] get_dataset()
- [ ] list_datasets()
- [ ] Tests

### 3.2 Documents ⏳
- [ ] upload_document_text()
- [ ] upload_document_file()
- [ ] async_parse_documents()
- [ ] get_document_status()
- [ ] Tests

### 3.3 Chats ⏳
- [ ] create_chat()
- [ ] delete_chat()
- [ ] list_chats()
- [ ] Tests

---

## Phase 4: Integration and Call-Site Refactor

### 4.1 Service Provider ⏳
- [ ] Create get_ragflow_service() function
- [ ] Update dependency injection

### 4.2 Update Call Sites ⏳
- [ ] backend/notebooks/services/chat_service.py (lines 269, 286, 339)
- [ ] backend/notebooks/services/notebook_service.py (lines 152, 500, 513, 523)
- [ ] backend/notebooks/views.py (lines 739, 759)
- [ ] backend/notebooks/tasks/ragflow_tasks.py (lines 91, 141, 153, 251)
- [ ] backend/notebooks/signals.py (lines 96, 106)
- [ ] backend/core/management/commands/cleanup_ragflow.py (lines 60, 107, etc.)

---

## Phase 5: Tests and Validation

### 5.1 Unit Tests ⏳
- [ ] Complete http_client.py tests
- [ ] Complete service.py tests
- [ ] Mock coverage for all endpoints

### 5.2 Integration Tests ⏳
- [ ] Smoke tests for key flows
- [ ] End-to-end validation

---

## Phase 6: Cleanup

### 6.1 Deprecation ⏳
- [ ] Add migration guide
- [ ] Document new usage patterns
- [ ] Update README

### 6.2 Remove Old Code ⏳
- [ ] Remove or archive client.py
- [ ] Remove SDK dependency
- [ ] Final cleanup

---

## Notes

- Using httpx for better async/streaming support
- Pydantic v2 for validation
- Keep RAGFLOW_USE_SDK_FALLBACK flag temporarily
- Maintain backward compatibility for one release cycle

---

## Current Phase: Phase 2 - Migrate Existing Direct-HTTP Flows
**Status**: Ready to start Phase 2

**Phase 1 Summary**: ✅ COMPLETED
- Created comprehensive exception hierarchy (10 exception types)
- Created Pydantic models for all API responses
- Created RagFlowHttpClient with retry logic, streaming, and error handling
- Created RagflowService with conversation, sessions, related_questions, list_chunks
- Created comprehensive test suite (4 test files, 40+ tests)
- All files pass Python syntax validation
