# Quick Reference Card

## 🤖 Avivo Bot - Quick Commands

### Setup (Do This First)
```bash
# Choose ONE:

# Option 1: Install Ollama (FREE)
brew install ollama
ollama serve &
ollama pull mistral
# Edit .env: OLLAMA_URL=http://localhost:11434

# Option 2: Use OpenAI (PAID)
# Fix billing at: https://platform.openai.com/account/billing
# .env should have: OPENAI_API_KEY=sk-...
```

### Start Bot
```bash
cd /Users/harsha/Desktop/Avivo
python main.py
```

### Telegram Commands

| Command | Usage | Example | Response |
|---------|-------|---------|----------|
| `/start` | Start bot | `/start` | Welcome message |
| `/help` | Show commands | `/help` | List of commands |
| `/ask` | Ask question | `/ask What are company policies?` | Answer + sources |
| `/image` | Upload image | `/image` → upload photo | Caption + tags |
| `/summarize` | Summary | `/summarize` | Summary of last 3 actions |

### Verify Bot Running
```bash
ps aux | grep "python3 main.py" | grep -v grep
```

### View Logs
```bash
tail -f /tmp/bot.log  # If using background logging
```

### Restart Bot
```bash
pkill -f "python3 main.py"
python main.py
```

### Kill Bot
```bash
pkill -f "python3 main.py"
```

---

## ⚙️ Configuration

### File: `.env`

**Critical Settings:**
```env
# Bot Token (required)
TELEGRAM_BOT_TOKEN=your_token

# Choose ONE:
# Option 1: Ollama (FREE)
OLLAMA_URL=http://localhost:11434

# Option 2: OpenAI (PAID)
# OPENAI_API_KEY=sk-proj-...
```

**Optional Settings:**
```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
VISION_MODEL=Salesforce/blip-image-captioning-base
RAG_TOP_K=3  # Number of documents to retrieve
LLM_MAX_TOKENS=256  # Max response length
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| `/ask` shows quota error | Use Ollama instead or fix OpenAI billing |
| Bot doesn't respond | Is it running? `ps aux \| grep python3` |
| Image upload fails | Reduce image size, use JPG format |
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| No recent interactions | Use `/ask` or `/image` first, then `/summarize` |
| Bot crashes on start | Check `.env` file exists and has TELEGRAM_BOT_TOKEN |

---

## 📊 Performance

### Speed
- Bot startup: 5-10 seconds (after first run)
- `/ask` response: 2-15 seconds (depends on LLM)
- `/image` response: 2-5 seconds
- `/summarize`: 2-5 seconds

### Hardware
- RAM needed: 2-3GB minimum
- Disk space: 500MB+ for models
- CPU: Standard modern CPU fine
- GPU: Not required but helps

---

## 🔍 Check Status

```bash
# Is bot running?
ps aux | grep "python3 main.py"

# Is Ollama running? (if using Ollama)
ps aux | grep ollama

# Can you reach Ollama? (if using Ollama)
curl http://localhost:11434/api/tags

# Check config
cat .env | grep -E "^[A-Z]"
```

---

## 📚 Documentation

- `GET_WORKING_NOW.md` - Setup guide
- `TROUBLESHOOTING.md` - Problem solving
- `FIXES_APPLIED.md` - Technical details
- `SESSION_SUMMARY.md` - Session overview
- `README.md` - Full documentation
- `DEVELOPMENT.md` - Developer guide

---

## 💡 Pro Tips

1. **Faster responses:** Use Ollama with `mistral` model
2. **Better quality:** Use Ollama with `llama2` or `dolphin-mixtral`
3. **Save money:** Use Ollama locally instead of OpenAI
4. **Debug mode:** Run without `&` to see logs: `python main.py`
5. **Custom docs:** Add markdown files to `data/` folder and restart

---

## 📋 Setup Checklist

- [ ] Clone/download repo to `/Users/harsha/Desktop/Avivo`
- [ ] Virtual environment created: `venv/`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with token
- [ ] Ollama OR OpenAI configured
- [ ] Bot tested with `/start` command
- [ ] Bot tested with `/ask` command
- [ ] All features working ✅

---

## 🎯 Common Workflows

### Workflow 1: Answer Questions About Documents
```
User → /ask What are company policies?
Bot → Retrieves from docs → Generates answer → Shows sources
```

### Workflow 2: Analyze Images
```
User → /image
Bot → Waits for photo
User → Uploads photo
Bot → Generates caption → Returns caption + tags
```

### Workflow 3: Summarize Conversation
```
User → /ask Question 1
User → /image Upload image
User → /ask Question 2
User → /summarize
Bot → Shows summary of all 3 interactions
```

---

## ⏱️ Time Estimates

| Task | Time |
|------|------|
| Setup Ollama | 10 min |
| Configure bot | 2 min |
| Test all commands | 5 min |
| **Total** | **~17 min** |

---

## 🚀 You're All Set!

✅ Bot is ready to use  
✅ All bugs are fixed  
✅ Documentation is complete  

**Next:** Follow `GET_WORKING_NOW.md` to get your LLM working!

---

**Questions?** Check `TROUBLESHOOTING.md`  
**Technical details?** See `FIXES_APPLIED.md`  
**Full docs?** Read `README.md` and `DEVELOPMENT.md`

Happy bot-ing! 🤖
