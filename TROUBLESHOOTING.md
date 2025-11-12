# Troubleshooting Guide

## Current Issues & Solutions

### 1. `/ask` Command Returns Quota Error
**Problem:** "LLM API quota exceeded" message

**Root Cause:** Your OpenAI API key has reached its usage quota or billing limit.

**Solutions:**
- **Option A: Check OpenAI Account**
  1. Go to https://platform.openai.com/account/billing/usage
  2. Check your usage and billing details
  3. Add payment method if needed
  4. Refresh API key if necessary

- **Option B: Use Ollama (Free Local LLM) - Recommended**
  1. Install Ollama: https://ollama.ai
  2. Run Ollama: `ollama serve`
  3. Pull a model: `ollama pull llama2` (or mistral, neural-chat, etc.)
  4. Update `.env`:
     ```
     OLLAMA_URL=http://localhost:11434
     # Comment out or remove OPENAI_API_KEY
     ```
  5. Restart the bot: `python main.py`

### 2. `/image` Command Not Working
**Problem:** "Error handling image: File.download_to_memory() missing 1 required positional argument: 'out'"

**Status:** ✅ FIXED
- Updated to use `download_to_drive()` method
- Bot now properly downloads images for captioning

### 3. `/summarize` Command Shows "No recent interactions"
**Problem:** Summary always says no recent interactions even after using other commands

**Root Cause:** 
- Interactions are saved but `/summarize` needs actual successful interactions
- If `/ask` fails (due to LLM quota), the interaction is logged but may not show in history

**Solution:**
- Fix the LLM issue first (use Ollama)
- Then `/ask` will work and create proper history entries
- `/summarize` will then have data to work with

## Testing the Bot

### 1. Start the Bot
```bash
cd /Users/harsha/Desktop/Avivo
python main.py
```

### 2. Test Commands in Telegram

#### `/start` - Should work immediately
Shows welcome message

#### `/help` - Should work immediately  
Shows available commands

#### `/ask What are company policies?`
- **If OpenAI quota error:** Configure Ollama (see above)
- **If working:** Returns answer + sources from RAG

#### `/image` 
- Asks for image
- Upload an image
- Returns caption and tags

#### `/summarize`
- Works after `/ask` or `/image` commands
- Shows summary of last 3 interactions

## Environment Setup

### Current .env Configuration
```bash
cat .env | grep -E "^[A-Z]" | head -15
```

### Recommended Configuration for Free Use
```env
# Use Ollama instead of OpenAI
OLLAMA_URL=http://localhost:11434

# Other settings (usually fine as-is)
TELEGRAM_BOT_TOKEN=your_token_here
EMBEDDING_MODEL=all-MiniLM-L6-v2
VISION_MODEL=Salesforce/blip-image-captioning-base
RAG_TOP_K=3
LLM_MAX_TOKENS=256
```

## Installing Ollama

### macOS
```bash
# Download from https://ollama.ai
# Or via Homebrew:
brew install ollama

# Start Ollama service
ollama serve

# In another terminal, pull a model:
ollama pull mistral  # Fast and good quality
# or
ollama pull llama2   # Larger, better quality
```

### Model Recommendations
- **mistral** - Fast, good for simple Q&A
- **neural-chat** - Optimized for conversation
- **llama2** - General purpose, larger
- **dolphin-mixtral** - Excellent quality (requires more RAM)

## Common Fixes

### Bot crashes with "ModuleNotFoundError"
```bash
cd /Users/harsha/Desktop/Avivo
source venv/bin/activate
pip install -r requirements.txt
```

### Bot starts but doesn't respond
- Check bot is running: `ps aux | grep "python3 main.py"`
- Check logs: `tail -f /tmp/bot.log` (if using logging)
- Restart bot: `pkill -f "python3 main.py" && python main.py`

### Image upload fails
- Ensure image size is reasonable (< 20MB)
- Try PNG or JPG format
- Check disk space in `/tmp`

### High CPU usage
- This is normal when using local LLMs (Ollama)
- Embedding model uses CPU for all queries
- Consider using GPU if available

## Performance Tips

### Speed Up `/ask` Responses
1. Use faster model in Ollama: `ollama pull mistral`
2. Increase `RAG_TOP_K` in `.env` for more relevant context
3. Reduce `LLM_MAX_TOKENS` for shorter responses

### Speed Up `/image` Responses
1. Reduce image resolution (< 1000px)
2. Use JPEG instead of PNG
3. Simplify images when possible

### Reduce Memory Usage
1. Use smaller embedding model (not recommended)
2. Reduce `CHUNK_SIZE_TOKENS` in `.env`
3. Run on machine with more RAM

## Getting Help

### Check Logs
```bash
tail -50 /tmp/bot.log
# Or if using console output:
# Check terminal where bot is running
```

### Test Individual Components
```bash
# Test RAG retrieval
python -c "
from app.rag.rag_service import RAGService
rag = RAGService()
rag.initialize('data')
results = rag.retrieve('What are company policies?', k=3)
for r in results:
    print(f\"{r['doc_name']}: {r['score']:.2f}\")
"

# Test embedding
python -c "
from app.rag.embedder import SentenceTransformerEmbedder
embedder = SentenceTransformerEmbedder()
vec = embedder.embed_text('test')
print(f'Vector size: {len(vec)}')
"

# Test LLM (after fixing API key)
python -c "
import asyncio
from app.llm.client import LLMClient
client = LLMClient(ollama_url='http://localhost:11434')
result = asyncio.run(client.generate_async('Hello!', max_tokens=50))
print(result['text'])
"
```

## Next Steps

1. **Choose Your LLM:**
   - Keep OpenAI: Fix billing/quota issue
   - Switch to Ollama: Install and configure (recommended for free use)

2. **Update Configuration:**
   - Edit `.env` with your chosen setup
   - Restart bot

3. **Test All Commands:**
   - `/start`, `/help` (should work immediately)
   - `/ask <query>` (tests RAG + LLM)
   - `/image` (tests vision + LLM)
   - `/summarize` (tests history)

4. **Enjoy Your Bot!**
   - Use `/ask` to query documents
   - Upload images with `/image`
   - Track interactions with `/summarize`

---

**Questions?** Check the main [README.md](README.md) or [DEVELOPMENT.md](DEVELOPMENT.md) for more details.
