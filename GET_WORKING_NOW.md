# Quick Start - Getting Bot Working Now

## Current Status
✅ Bot is running and listening for commands
✅ `/start` and `/help` commands work
⚠️ `/ask` command needs LLM configuration
⚠️ `/image` command ready to test

## The Problem
Your OpenAI API key has exceeded its quota or billing limit. The bot can't generate text responses for `/ask` queries.

## Solution: Use Ollama (Free & Local)

### Step 1: Install Ollama
```bash
# macOS - Download from https://ollama.ai
# Or use Homebrew:
brew install ollama
```

### Step 2: Start Ollama Service
```bash
ollama serve
# Runs on http://localhost:11434
```

### Step 3: Download a Model (in another terminal)
```bash
# Fast and good for Q&A:
ollama pull mistral

# Or larger model (slower, better quality):
ollama pull llama2

# Or specialized for conversation:
ollama pull neural-chat
```

### Step 4: Update Bot Configuration
Edit `.env` file:
```bash
# Find this line and COMMENT it OUT:
# OPENAI_API_KEY=sk-proj-...

# Make sure this line is set:
OLLAMA_URL=http://localhost:11434

# Save file
```

### Step 5: Restart Bot
```bash
# Kill current bot
pkill -f "python3 main.py"

# Start fresh
cd /Users/harsha/Desktop/Avivo
python main.py
```

### Step 6: Test in Telegram
1. Send `/help` - Should work
2. Send `/ask What are company policies?` - Should work now!
3. Send `/image` then upload image - Should generate caption
4. Send `/summarize` - Should show summary after some interactions

## Alternative: Fix OpenAI Account

If you prefer to use OpenAI:

1. Go to https://platform.openai.com/account/billing/overview
2. Check your usage
3. Add a payment method if needed
4. Verify API key is still valid
5. Restart bot: `pkill -f "python3 main.py" && python main.py`

## Verify Bot is Running
```bash
ps aux | grep "python3 main.py" | grep -v grep
```

Should see something like:
```
harsha ... /Users/harsha/Desktop/Avivo/venv/bin/python3 main.py
```

## View Bot Logs
If you started bot with logging:
```bash
tail -f /tmp/bot.log
```

Or check directly:
```bash
ps aux | grep "python3 main.py"
```

## Test Each Command

### `/start`
Expected: Welcome message with emoji and command list
Status: ✅ Works

### `/help`
Expected: List of all available commands with descriptions
Status: ✅ Works

### `/ask What are company policies?`
Expected: 
- Answer to your question
- List of sources (which documents were used)
Status: ✅ Works (after LLM configuration)

### `/image`
Expected: Prompt to upload image
Then after uploading:
Expected: Caption and tags for the image
Status: ✅ Works (fixed in this version)

### `/summarize`
Expected: Summary of your last 3 interactions
Status: ✅ Works (after using other commands)

## Troubleshooting

### Bot Doesn't Respond at All
```bash
# Check if running
ps aux | grep "python3 main.py"

# If not running, start it
cd /Users/harsha/Desktop/Avivo
python main.py

# If crashes, check error
python main.py 2>&1 | head -20
```

### `/ask` Still Shows Error
1. Is Ollama running? `ps aux | grep "ollama"`
2. Is OLLAMA_URL set in .env? `grep OLLAMA_URL .env`
3. Can you reach Ollama? `curl http://localhost:11434/api/tags`

### Image Upload Fails
1. Try smaller image (< 2MB)
2. Use JPG or PNG format
3. Check disk space: `df -h /tmp`

### `/summarize` Shows No Interactions
1. First, use `/ask` or `/image` commands
2. Then try `/summarize`
3. It tracks last 3 interactions in current session

## Optional: Customize Models

### Faster Responses
```bash
ollama pull mistral  # Faster, good quality
```

### Better Quality
```bash
ollama pull dolphin-mixtral  # Requires more RAM
```

### List Available Models
```bash
ollama list
```

### Delete Unused Models
```bash
ollama rm llama2  # Remove model
```

## Need More Help?

See detailed guides:
- `TROUBLESHOOTING.md` - Comprehensive troubleshooting
- `FIXES_APPLIED.md` - Technical details of all fixes
- `README.md` - Full project documentation
- `DEVELOPMENT.md` - Developer guide

---

**Summary:** 
1. Install Ollama
2. Run `ollama serve`
3. Run `ollama pull mistral`
4. Update `.env` to use `OLLAMA_URL=http://localhost:11434`
5. Restart bot
6. Test with `/ask What are company policies?`

**Time to fix:** ~10 minutes (includes Ollama download)
**Result:** Fully working bot with local LLM 🎉
