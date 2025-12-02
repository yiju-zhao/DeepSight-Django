# Datasets App - Semantic Search with Lotus

This Django app provides general-purpose semantic search capabilities using the Lotus library for AI-powered data filtering and ranking.

## Features

- **Semantic search on publications** using natural language queries
- **Configurable LLM models** (OpenAI GPT-4o-mini, GPT-4o, etc.)
- **Flexible filtering** - Frontend pre-filters data, backend applies semantic search
- **Production-ready** with comprehensive error handling and logging

## Installation

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment variables:**
Add to your `.env` file:
```bash
# Required: OpenAI API key (already exists in base.py)
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Lotus configuration
LOTUS_LLM_MODEL=gpt-4o-mini           # Default model
LOTUS_HELPER_MODEL=                    # Optional helper model for cascades
LOTUS_TIMEOUT=30                       # Timeout in seconds
LOTUS_MAX_PUBLICATIONS=1000            # Max publications per request
```

3. **Run migrations** (no database migrations needed for this app):
```bash
python manage.py migrate
```

## API Usage

### Endpoint
```
POST /api/v1/datasets/semantic-search/publications/
```

### Authentication
Requires authenticated user (session or basic auth).

### Request Format
```json
{
  "publication_ids": ["uuid-1", "uuid-2", "uuid-3", ...],
  "query": "papers about artificial intelligence in healthcare",
  "topk": 10
}
```

**Parameters:**
- `publication_ids` (required): List of publication UUIDs (1-1000)
- `query` (required): Natural language semantic query (3-500 chars)
- `topk` (optional): Number of top results to return (1-100, default: 10)

### Response Format (Success)
```json
{
  "success": true,
  "query": "papers about artificial intelligence in healthcare",
  "total_input": 450,
  "total_results": 8,
  "results": [
    {
      "id": "uuid-here",
      "title": "AI for Medical Diagnosis",
      "abstract": "This paper presents...",
      "authors": "John Doe; Jane Smith",
      "keywords": "AI; Healthcare; Deep Learning",
      "rating": 4.5,
      "venue": "CVPR",
      "year": 2024,
      "relevance_score": 0.95
    }
  ],
  "metadata": {
    "llm_model": "gpt-4o-mini",
    "processing_time_ms": 1234
  }
}
```

### Response Format (Error)
```json
{
  "success": false,
  "query": "...",
  "total_input": 450,
  "total_results": 0,
  "results": [],
  "error": "LLM_API_ERROR",
  "detail": "Failed to connect to LLM API. Check API key and network connection.",
  "metadata": {
    "llm_model": "gpt-4o-mini",
    "processing_time_ms": 0
  }
}
```

## Testing

### Run Unit Tests
```bash
cd backend
python manage.py test datasets.tests.test_lotus_service
```

### Run Integration Tests
```bash
python manage.py test datasets.tests.test_views
```

### Run All Tests
```bash
python manage.py test datasets
```

### Manual Testing (Django Shell)
```python
from django.contrib.auth import get_user_model
from conferences.models import Publication
from datasets.services import lotus_semantic_search_service

# Get some publication IDs
pub_ids = list(Publication.objects.values_list('id', flat=True)[:20])
pub_ids_str = [str(id) for id in pub_ids]

# Test semantic search
result = lotus_semantic_search_service.semantic_filter(
    publication_ids=pub_ids_str,
    query="papers about deep learning and computer vision",
    topk=5
)

# Print results
print(f"Success: {result['success']}")
print(f"Total results: {result['total_results']}")
for r in result['results']:
    print(f"- {r['title']} (score: {r['relevance_score']})")
```

### Test via cURL
```bash
# First, get a session cookie by logging in
curl -X POST http://localhost:8000/api/v1/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}' \
  -c cookies.txt

# Then make semantic search request
curl -X POST http://localhost:8000/api/v1/datasets/semantic-search/publications/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "publication_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "query": "papers about AI in healthcare",
    "topk": 5
  }'
```

## Architecture

### Components

1. **Service Layer** (`services/lotus_service.py`):
   - `LotusSemanticSearchService`: Core Lotus integration
   - Lazy initialization for macOS compatibility
   - DataFrame conversion and semantic operations
   - Comprehensive error handling

2. **API Layer** (`views.py`):
   - `SemanticSearchViewSet`: REST API endpoint
   - Request validation and authentication
   - Response formatting and logging

3. **Serializers** (`serializers.py`):
   - `SemanticSearchRequestSerializer`: Input validation
   - `PublicationResultSerializer`: Result formatting
   - `SemanticSearchResponseSerializer`: Response validation

4. **URL Routing** (`urls.py`):
   - `/api/v1/datasets/semantic-search/publications/`

### Data Flow

```
Frontend
  ↓
  Applies traditional filters (venue, year, rating, etc.)
  ↓
  Gets publication IDs
  ↓
  POST /api/v1/datasets/semantic-search/publications/
  {publication_ids, query, topk}
  ↓
Backend (datasets app)
  ↓
  Validates request
  ↓
  Loads publications by IDs
  ↓
  Converts to DataFrame
  ↓
  Lotus sem_filter (filters by query)
  ↓
  Lotus sem_topk (ranks top K)
  ↓
  Returns ranked results with relevance scores
```

## Error Codes

- `VALIDATION_ERROR`: Invalid request parameters
- `LLM_API_ERROR`: Failed to connect to LLM API
- `RATE_LIMIT_ERROR`: LLM API rate limit exceeded
- `TIMEOUT_ERROR`: Semantic search timed out
- `SEMANTIC_SEARCH_ERROR`: Generic semantic search failure
- `INTERNAL_ERROR`: Unexpected server error

## Performance

**Expected response times:**
- 10 publications: ~1-2 seconds
- 100 publications: ~3-5 seconds
- 1000 publications: ~8-12 seconds

**Cost estimates (OpenAI):**
- Each query: ~$0.001-0.01 depending on model and data size

## Future Enhancements

1. **Caching**: Redis cache for repeated queries
2. **Async Processing**: Celery tasks for large queries (>500 publications)
3. **Vector Search**: Pre-compute embeddings, use Milvus for faster search
4. **Multi-entity Support**: Extend to notebooks, reports, etc.
5. **Explain Relevance**: Return LLM reasoning for top results

## Troubleshooting

### "lotus-ai library is not installed"
```bash
pip install lotus-ai
```

### "OpenAI API key not found"
Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

### "Semantic search timed out"
Try:
- Reducing number of publication IDs
- Increasing `LOTUS_TIMEOUT` in settings
- Using faster model (gpt-4o-mini)

### Tests failing with import errors
Make sure you're in the backend directory:
```bash
cd backend
python manage.py test datasets
```

## Support

For issues or questions:
1. Check logs: `backend/logs/`
2. Review test cases for examples
3. Consult Lotus documentation: https://github.com/lotus-data/lotus
