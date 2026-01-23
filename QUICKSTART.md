# Legal Risk & Compliance AI System - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env if you need custom settings (optional)
```

### 3. Start Ollama/Mistral
```bash
# In a separate terminal, start Ollama
ollama serve

# In another terminal, pull mistral (first time only)
ollama pull mistral
```

### 4. Start the API
```bash
uvicorn api.main:app --reload
```

The API will be available at: `http://localhost:8000`

### 5. Test the System
Open browser and go to: `http://localhost:8000/docs`

This opens the interactive Swagger UI where you can:
- Click "Try it out" on the `/chat` endpoint
- Enter a legal question
- See the response with safety verification results

## Quick Test Examples

### Example 1: Contract Question
**Question:** "What happens if someone breaches our contract?"

**Expected Response:** 
- Issue identified: contract_enforceability
- Safety checks passed
- Qualified language used
- Disclaimer included

### Example 2: Employment Question
**Question:** "Can my employer terminate me without cause?"

**Expected Response:**
- Issue identified: employment
- Safety checks passed
- Context-aware answer
- References jurisdiction differences

### Example 3: Data Protection
**Question:** "What is GDPR and how does it apply to us?"

**Expected Response:**
- Issue identified: data_protection
- Safety verification
- Appropriate disclaimers
- Guidance to consult professionals

## Command Reference

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_models.py -v

# With coverage
pytest tests/ --cov --cov-report=html
```

### Check API Health
```bash
curl http://localhost:8000/health
```

### Make Chat Request
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is contract law?"}'
```

### View API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

## Configuration

Default configuration is in `config.py`. Override with `.env` file:

```env
# Most important settings
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=mistral
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
```

See `.env.example` for all available settings.

## Troubleshooting

### "Cannot connect to LLM"
- Ensure Ollama is running: `ollama serve`
- Check `LLM_BASE_URL` in `.env` matches your Ollama address
- Verify Mistral is installed: `ollama pull mistral`

### "No module named 'fastapi'"
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: Python 3.8+

### Tests fail with import errors
- Ensure you're in the project root directory
- Install test dependencies: `pip install -r requirements.txt`

### Rate limit exceeded
- Wait 1 hour or change `RATE_LIMIT_PERIOD` in `.env`
- Or disable: `RATE_LIMIT_ENABLED=false`

## Architecture Overview

```
Question (Input Validation)
    ↓
Phase 1: Issue Extraction (7 categories)
    ↓
Phase 2: LLM Generation (Mistral/Ollama)
    ↓
Phase 3: Rule Verification (Safety rules)
    ↓
Phase 4: Model Verification (Hallucination check)
    ↓
Phase 5: Rewriting (Fix violations)
    ↓
Response (with safety checks & debug trace)
```

## Project Structure

```
legal-risk-compliance-ai/
├── config.py                 # Configuration (from .env)
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── api/
│   ├── main.py              # FastAPI app, middleware, startup
│   ├── routes.py            # Chat endpoint (5-phase pipeline)
│   └── schemas.py           # Request/response schemas
├── models/
│   ├── llm.py               # LLM client
│   ├── issue_extractor.py   # Issue categorization
│   ├── rule_verifier.py     # Safety rules
│   ├── model_verifier.py    # Hallucination detection
│   └── rewriter.py          # Safety fixes
├── tests/
│   ├── test_models.py       # Unit tests (20+ tests)
│   ├── test_api.py          # API tests (15+ tests)
│   └── README.md            # Test documentation
└── logs/
    └── app.log              # Application logs
```

## Next Steps

1. **Customize Configuration**: Edit `.env` for your settings
2. **Run Tests**: `pytest tests/ -v` to verify setup
3. **Explore API**: Visit http://localhost:8000/docs
4. **Check Logs**: View `logs/app.log` for detailed operation info
5. **Read Architecture**: See `ARCHITECTURE.md` for implementation details

## Production Deployment

See `ARCHITECTURE.md` for production considerations:
- Environment-based configuration
- Structured logging
- Comprehensive error handling
- Rate limiting enabled
- CORS configuration
- Health check monitoring

## Support

For detailed information:
- **API Endpoints**: See interactive docs at `/docs`
- **Configuration**: See `config.py` and `.env.example`
- **Architecture**: See `ARCHITECTURE.md`
- **Tests**: See `tests/README.md`
