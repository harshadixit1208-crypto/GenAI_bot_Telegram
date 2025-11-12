# DEVELOPMENT.md
# Development Guide

## Project Structure

```
Avivo/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── bot.py                   # Telegram bot handlers (async)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── extractor.py         # Document extraction & chunking
│   │   ├── embedder.py          # Embedding generation & caching
│   │   ├── vector_store.py      # FAISS index management
│   │   └── rag_service.py       # RAG orchestration
│   ├── vision/
│   │   ├── __init__.py
│   │   └── blip_service.py      # BLIP-2 image captioning
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py            # OpenAI/Ollama wrapper
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration loading
│   │   ├── logging.py           # Logging setup
│   │   └── history.py           # User interaction history
│   └── tests/
│       ├── __init__.py
│       ├── test_chunking.py
│       ├── test_embedding_cache.py
│       ├── test_faiss_retrieval.py
│       └── test_vision_stub.py
├── data/                         # Documents & embeddings
│   ├── company_policies.md
│   ├── technical_documentation.md
│   ├── product_features.md
│   ├── embeddings.db            # SQLite cache (auto-created)
│   └── faiss_index.bin          # FAISS index (auto-created)
├── main.py                       # Entry point
├── run.sh                        # Bash run script
├── requirements.txt
├── .env.example                  # Environment template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── pyproject.toml               # Black & Ruff config
├── README.md
└── DEVELOPMENT.md               # This file
```

## Getting Started

### 1. Setup

```bash
# Clone repository
git clone <url>
cd Avivo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### 2. Run Locally

**Option A: Using run.sh**

```bash
chmod +x run.sh
./run.sh
```

**Option B: Direct Python**

```bash
source venv/bin/activate
python main.py
```

**Option C: Using Docker**

```bash
docker-compose up
```

## Development Workflow

### Code Style

The project uses **black** for formatting and **ruff** for linting.

```bash
# Format code
black app/

# Lint code
ruff check app/

# Fix linting issues automatically
ruff check --fix app/
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest app/tests/test_chunking.py

# Specific test class
pytest app/tests/test_embedding_cache.py::TestEmbeddingCache

# With verbose output
pytest -v

# With coverage report
pytest --cov=app

# Watch mode (requires pytest-watch)
ptw
```

### Adding New Features

#### 1. New RAG Component

Example: Adding a new document format handler

```python
# app/rag/extractor.py

def load_pdf_documents(self, data_dir: str) -> List[Tuple[str, str]]:
    """Load PDF documents."""
    # Implementation
    pass
```

Update `extract_and_chunk_documents()` to call it.

#### 2. New Telegram Command

Example: Adding `/stats` command

```python
# app/bot.py

async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command."""
    stats = self.rag_service.get_stats()
    response = f"Total vectors: {stats['vector_store']['total_vectors']}"
    await update.message.reply_text(response)

# In main():
app.add_handler(CommandHandler("stats", bot.stats_command))
```

#### 3. New Test

```python
# app/tests/test_new_feature.py

import pytest

class TestNewFeature:
    """Tests for new feature."""
    
    def setup_method(self):
        """Setup."""
        # Initialize test fixtures
        pass
    
    def test_example(self):
        """Test example."""
        assert True
```

Run with: `pytest app/tests/test_new_feature.py`

## Configuration Management

### Environment Variables

All configuration is loaded from environment variables (via `.env`):

```python
# app/utils/config.py
from app.utils.config import config

# Access anywhere
print(config.telegram_bot_token)
print(config.embedding_model)
```

### Adding New Configuration

1. Add to `.env.example`:
   ```env
   NEW_SETTING=default_value
   ```

2. Add to `app/utils/config.py`:
   ```python
   self.new_setting = os.getenv("NEW_SETTING", "default_value")
   ```

3. Use in code:
   ```python
   from app.utils.config import config
   value = config.new_setting
   ```

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python main.py
```

### Debug Specific Module

```python
# In code
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Debug info: {variable}")
```

### Inspect Database

```bash
sqlite3 data/embeddings.db

# List all embeddings
SELECT COUNT(*) FROM embeddings;

# Find embeddings for specific doc
SELECT chunk_index, LENGTH(chunk_text) FROM embeddings WHERE doc_name='policies.md';

# Exit
.quit
```

### Test RAG Pipeline

```python
# Quick test script
from app.rag.rag_service import RAGService

service = RAGService()
service.initialize("data")

results = service.retrieve("What are policies?", k=3)
for r in results:
    print(f"{r['doc_name']}: {r['score']:.2f}")
```

## Performance Profiling

### Profile Bot Startup

```bash
python -m cProfile -s cumtime main.py 2>&1 | head -20
```

### Profile Memory Usage

```bash
# Install memory profiler
pip install memory-profiler

# Profile
python -m memory_profiler main.py
```

## Deployment

### Docker Image

```bash
# Build
docker build -t avivo-bot:latest .

# Run
docker run -e TELEGRAM_BOT_TOKEN=xxx -v $(pwd)/data:/app/data avivo-bot:latest

# Push to registry
docker tag avivo-bot:latest myregistry/avivo-bot:latest
docker push myregistry/avivo-bot:latest
```

### Docker Compose

```bash
# Development
docker-compose -f docker-compose.yml up

# Production (with specific services)
docker-compose up -d bot

# View logs
docker-compose logs -f bot

# Rebuild
docker-compose up --build
```

### Kubernetes (Optional)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: avivo-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: avivo-bot
  template:
    metadata:
      labels:
        app: avivo-bot
    spec:
      containers:
      - name: bot
        image: avivo-bot:latest
        env:
        - name: TELEGRAM_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: avivo-secrets
              key: token
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: avivo-data-pvc
```

## Troubleshooting Development Issues

### Import Errors

```bash
# Ensure app package is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python main.py
```

### Model Download Issues

```bash
# Download BLIP model manually
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Salesforce/blip-image-captioning-base')"

# Disable HF SSL
pip install --upgrade certifi
```

### Port Already in Use (Docker)

```bash
# Change port in docker-compose.yml
ports:
  - "11435:11434"  # Map to different port
```

### Database Locks

```bash
# Remove old database and rebuild
rm data/embeddings.db data/faiss_index.bin
# Bot will recreate on next run
```

## Performance Optimization Tips

1. **Embedding Caching**
   - Documents are cached in SQLite
   - Delete cache to re-embed: `rm data/embeddings.db`

2. **FAISS Indexing**
   - Use `IndexFlatIP` for small datasets
   - Use `IndexIVFFlat` for large datasets (100K+ vectors)

3. **LLM Response Time**
   - Use `gpt-3.5-turbo` for speed (default)
   - Use local `ollama` for offline/lower cost

4. **Chunk Size Tuning**
   - Larger chunks = faster search but less relevant
   - Smaller chunks = slower search but more precise

## Contributing

1. Create feature branch: `git checkout -b feature/awesome`
2. Make changes and test: `pytest`
3. Format code: `black app/`
4. Lint: `ruff check app/`
5. Commit with meaningful message
6. Push and create pull request

## Useful Commands

```bash
# Fresh start
rm -rf venv data/*.db data/*.bin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Format all
black app/ main.py

# Lint all
ruff check app/ main.py

# Full test suite
pytest -v --cov=app

# Run single module test
python -m app.rag.extractor

# Check imports
python -c "from app import TelegramRAGBot"
```

## References

- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [Sentence Transformers](https://www.sbert.net/)
- [FAISS GitHub](https://github.com/facebookresearch/faiss)
- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [Pytest Documentation](https://docs.pytest.org/)

---

Happy developing! 🚀
