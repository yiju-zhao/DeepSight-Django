# RAGFlow Infrastructure Tests - Guide

## Quick Start

### Run All RAGFlow Tests

```bash
# From backend directory
cd backend

# Using Django test runner
python manage.py test infrastructure.ragflow.tests

# Using pytest (recommended)
pytest infrastructure/ragflow/tests/

# With verbose output
pytest infrastructure/ragflow/tests/ -v

# With coverage
pytest infrastructure/ragflow/tests/ --cov=infrastructure.ragflow --cov-report=html
```

### Run Specific Test Files

```bash
# Test exceptions only
pytest infrastructure/ragflow/tests/test_exceptions.py -v

# Test models only
pytest infrastructure/ragflow/tests/test_models.py -v

# Test HTTP client only
pytest infrastructure/ragflow/tests/test_http_client.py -v

# Test service layer only
pytest infrastructure/ragflow/tests/test_service.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run a specific test class
pytest infrastructure/ragflow/tests/test_exceptions.py::TestRagFlowError -v

# Run a specific test method
pytest infrastructure/ragflow/tests/test_models.py::TestAPIResponse::test_success_response -v
```

## Test Organization

```
infrastructure/ragflow/tests/
├── __init__.py
├── README.md (this file)
├── test_exceptions.py      # Exception hierarchy tests (12 test classes)
├── test_models.py           # Pydantic model tests (7 test classes)
├── test_http_client.py      # HTTP client tests with mocks (6 test classes)
└── test_service.py          # Service layer tests with mocks (6 test classes)
```

## Prerequisites

Make sure you have the required packages installed:

```bash
cd backend
pip install pytest pytest-cov pytest-django httpx pydantic
```

Or if using requirements.txt:
```bash
pip install -r requirements.txt
```

## Test Modes

### 1. Unit Tests (Current - Mocked)

All current tests use mocked HTTP responses and don't require a running RAGFlow instance:

```bash
# Fast unit tests with mocks
pytest infrastructure/ragflow/tests/ -v
```

**Advantages:**
- Fast execution (~1-2 seconds)
- No external dependencies
- Can run in CI/CD
- Tests logic and error handling

### 2. Integration Tests (Future - Phase 5)

To test against a real RAGFlow instance:

```bash
# Set up environment
export RAGFLOW_BASE_URL=http://localhost:9380
export RAGFLOW_API_KEY=your-api-key
export RAGFLOW_LOGIN_TOKEN=your-login-token

# Run integration tests (when available)
pytest infrastructure/ragflow/tests/ -m integration -v
```

## Common Test Commands

### Run with Stop on First Failure

```bash
pytest infrastructure/ragflow/tests/ -x
```

### Run with Detailed Output

```bash
pytest infrastructure/ragflow/tests/ -vv
```

### Run Only Failed Tests from Last Run

```bash
pytest infrastructure/ragflow/tests/ --lf
```

### Run Tests in Parallel (if pytest-xdist installed)

```bash
pytest infrastructure/ragflow/tests/ -n auto
```

### Generate Coverage Report

```bash
# Terminal report
pytest infrastructure/ragflow/tests/ --cov=infrastructure.ragflow

# HTML report (opens in browser)
pytest infrastructure/ragflow/tests/ --cov=infrastructure.ragflow --cov-report=html
open htmlcov/index.html
```

## Test Structure

### test_exceptions.py
Tests for custom exception hierarchy:
- Base error with details
- API errors with status codes
- Specialized errors (dataset, document, chat, session)
- Network errors (timeout, connection, rate limit)

### test_models.py
Tests for Pydantic models:
- Generic response wrappers (APIResponse, Paginated)
- Completion models (streaming and non-streaming)
- Session, Chunk, and Related Questions models
- Model validation and serialization

### test_http_client.py
Tests for HTTP client layer:
- Request/response handling
- Retry logic with exponential backoff
- Error mapping to exceptions
- Streaming support
- Timeout handling

### test_service.py
Tests for service orchestration:
- Conversation (streaming and non-streaming)
- Session management (CRUD operations)
- Related questions generation
- Chunk listing with pagination
- Health checks

## Debugging Tests

### Run with Print Statements Visible

```bash
pytest infrastructure/ragflow/tests/ -s
```

### Run with Python Debugger (pdb)

```bash
pytest infrastructure/ragflow/tests/ --pdb
```

### Run with ipdb (enhanced debugger)

```bash
pip install ipdb
pytest infrastructure/ragflow/tests/ --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Fast check (no coverage)
pytest infrastructure/ragflow/tests/ -v --tb=short

# With coverage and XML report for CI
pytest infrastructure/ragflow/tests/ \
    --cov=infrastructure.ragflow \
    --cov-report=xml \
    --cov-report=term \
    --junitxml=test-results.xml
```

## Expected Test Results (Phase 1)

All tests should pass:

```
infrastructure/ragflow/tests/test_exceptions.py .............  [33%]
infrastructure/ragflow/tests/test_models.py ...............    [67%]
infrastructure/ragflow/tests/test_http_client.py ..........    [83%]
infrastructure/ragflow/tests/test_service.py ..............    [100%]

======== 40+ tests passed in 1-2s ========
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the backend directory:

```bash
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest infrastructure/ragflow/tests/
```

### Django Settings Issues

If tests fail due to Django settings:

```bash
# Set Django settings module
export DJANGO_SETTINGS_MODULE=backend.settings
pytest infrastructure/ragflow/tests/
```

Or use pytest-django:

```bash
pytest infrastructure/ragflow/tests/ --ds=backend.settings
```

### Missing Dependencies

```bash
# Install all test dependencies
pip install pytest pytest-cov pytest-django pytest-mock httpx pydantic
```

## Next Steps (Phase 2+)

After Phase 2 implementation, you'll be able to test:
- Integration with existing client.py compatibility layer
- End-to-end flows with real RAGFlow instance
- Performance benchmarks
- Load testing

## Resources

- Django Testing: https://docs.djangoproject.com/en/stable/topics/testing/
- Pytest Documentation: https://docs.pytest.org/
- Pytest-Django: https://pytest-django.readthedocs.io/
- httpx Testing: https://www.python-httpx.org/advanced/#mocking
