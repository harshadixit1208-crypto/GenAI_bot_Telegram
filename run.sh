#!/bin/bash
# run.sh - Simple script to run the bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Avivo Telegram RAG Bot${NC}"
echo -e "${GREEN}================================${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Python version: $PYTHON_VERSION${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Copy .env.example to .env and fill in your credentials:${NC}"
    echo -e "  cp .env.example .env"
    exit 1
fi

# Check for TELEGRAM_BOT_TOKEN
if ! grep -q "TELEGRAM_BOT_TOKEN" .env || grep "TELEGRAM_BOT_TOKEN=YOUR" .env > /dev/null; then
    echo -e "${RED}Error: TELEGRAM_BOT_TOKEN not configured in .env${NC}"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Show configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  - Database: $(grep DATABASE_PATH .env | cut -d= -f2)"
echo "  - Log Level: $(grep LOG_LEVEL .env | cut -d= -f2)"

# Run the bot
echo -e "${GREEN}Starting bot...${NC}"
python main.py
