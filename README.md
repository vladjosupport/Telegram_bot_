# 🤖 Telegram Bot

A production-ready Telegram bot with Telethon integration.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit `.env` file with:
- `BOT_TOKEN` - Your Telegram bot token from @BotFather
- `TELEGRAM_API_ID` - From my.telegram.org
- `TELEGRAM_API_HASH` - From my.telegram.org

## Running

```bash
python bot.py
```

## Features

- `/start` - Main menu with inline buttons
- `/status` - Bot and account status
- 📋 List Channels - View all your channels and groups
- 📊 Status - Display system information
- ❌ Cancel - End session

## Architecture

- **Async/Await** - Non-blocking async operations
- **Telethon** - User session management
- **python-telegram-bot** - Bot API wrapper
- **Logging** - Detailed operation logs
- **Error Handling** - Comprehensive exception handling
