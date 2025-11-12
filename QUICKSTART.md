# QUICKSTART.md
# Avivo Bot - Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Configure (1 min)

```bash
cd /Users/harsha/Desktop/Avivo
cp .env.example .env
```

Edit `.env` and add:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
OPENAI_API_KEY=your_openai_key_OR_set_OLLAMA_URL
```

### Step 2: Install (2 min)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run (1 min)

```bash
python main.py
```

The bot will:
- Load documents from `data/`
- Build embeddings (first run ~30 seconds)
- Start listening for Telegram messages

### Step 4: Test (1 min)

In Telegram with the bot:
```
/start
/ask What are the company policies?
/image (upload a photo)
/summarize
```

---

## 🐳 Docker Setup (Even Faster)

```bash
cp .env.example .env
# Edit .env with your token

docker-compose up -d
docker-compose logs -f bot
```

That's it! Bot is running.

---

## 📖 Key Files to Know

| File | Purpose |
|------|---------|
| `.env` | Your secrets (don't commit!) |
| `app/bot.py` | Telegram command handlers |
| `app/rag/` | Document search engine |
| `app/vision/` | Image captioning |
| `data/` | Your documents |
| `requirements.txt` | Dependencies |

---

## 🧪 Run Tests

```bash
pytest -v
```

All 27 tests should pass ✓

---

## 🚨 Troubleshooting

### Bot won't start
```bash
# Check token is set
echo $TELEGRAM_BOT_TOKEN

# Check internet
curl https://api.telegram.org
```

### ModuleNotFoundError
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Model download fails
```bash
# BLIP will download on first use (~2GB)
# Be patient or check internet connection
```

---

## 💡 Common Commands

```bash
# Format code
black app/

# Lint code
ruff check app/

# Run tests with coverage
pytest --cov=app

# View logs
tail -f data/bot.log

# Clear cache & rebuild
rm data/embeddings.db data/faiss_index.bin
```

---

## 📚 Full Documentation

- **README.md** - Complete user guide
- **DEVELOPMENT.md** - Advanced development
- **PROJECT_SUMMARY.md** - Technical overview
- **MANIFEST.md** - Complete file listing

---

## ✨ Features Available

### Text Search
```
/ask What is the return policy?
```
→ Searches documents, generates answer with sources

### Image Captioning
```
/image
(upload photo)
```
→ Caption + 3 tags

### Summarization
```
/summarize
```
→ Summarizes last 3 interactions

---

## 🔧 Configuration Examples

### Use Local Ollama Only
```env
# Don't set OPENAI_API_KEY
OLLAMA_URL=http://localhost:11434
```

### Bigger Embedding Model
```env
EMBEDDING_MODEL=all-mpnet-base-v2
```

### More RAG Context
```env
RAG_TOP_K=5
RAG_MAX_CONTEXT_TOKENS=5000
```

---

## 🎯 Next Steps

1. ✅ Setup complete
2. 📝 Add your documents to `data/`
3. 🧪 Run tests: `pytest`
4. 🚀 Deploy: `docker-compose up`
5. 📊 Monitor: `docker-compose logs -f bot`

---

**Everything is ready to go!** 🎉

See README.md for detailed documentation.
