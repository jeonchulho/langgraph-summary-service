# Testing Guide

## Running Tests

### Unit Tests

Run all tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

Run specific test file:
```bash
pytest tests/test_summarizer.py -v
```

### Expected Test Results

```
tests/test_summarizer.py::test_summarizer_initialization PASSED
tests/test_summarizer.py::test_workflow_creation PASSED
tests/test_summarizer.py::test_summarize_basic SKIPPED (requires OpenAI API key)
tests/test_summarizer.py::test_summarize_different_styles SKIPPED (requires OpenAI API key)
tests/test_summarizer.py::test_batch_summarization PASSED
tests/test_summarizer.py::test_preprocess_email PASSED
tests/test_summarizer.py::test_preprocess_chat PASSED
```

## Manual Testing

### 1. Start the Application

Using Docker:
```bash
docker-compose up -d
```

Local development:
```bash
uvicorn app.main:app --reload
```

### 2. Test Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "timestamp": "2026-01-05T08:00:00"
}
```

### 3. Test User Registration

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123"
  }'
```

### 4. Test Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123"
  }'
```

Save the returned token for next steps.

### 5. Test Summarization

```bash
export TOKEN="your-token-here"

curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your long text here that needs to be summarized. Make sure it is at least 50 characters long to pass validation.",
    "type": "document",
    "style": "brief"
  }'
```

### 6. Test Batch Summarization

```bash
curl -X POST "http://localhost:8000/api/v1/summarize/batch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "First text to summarize with at least 50 characters...",
      "Second text to summarize with at least 50 characters...",
      "Third text to summarize with at least 50 characters..."
    ],
    "type": "document",
    "style": "bullet"
  }'
```

### 7. Test Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

### 8. Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Integration Testing

### Test Full Workflow

1. Register user
2. Login and get token
3. Create summary
4. List summaries
5. Get specific summary
6. Check usage stats

### Test Error Cases

1. Invalid email format
2. Password too short
3. Text too short (< 50 chars)
4. Invalid token
5. Rate limiting (> 10 requests/min)

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install ab (Apache Bench)
sudo apt-get install apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test authenticated endpoint (replace TOKEN)
ab -n 100 -c 5 -H "Authorization: Bearer TOKEN" \
   -p summary_request.json -T application/json \
   http://localhost:8000/api/v1/summarize
```

## Debugging

### View Logs

Docker:
```bash
docker-compose logs -f app
```

Local:
```bash
tail -f logs/app.log
```

### Check Database

```bash
docker-compose exec postgres psql -U postgres -d summary_db
```

### Check Redis

```bash
docker-compose exec redis redis-cli
```

## Continuous Integration

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
name: Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Test Coverage Goals

- Unit tests: > 80%
- Integration tests: Key workflows
- API tests: All endpoints
- Error handling: Edge cases
