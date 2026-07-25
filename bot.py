#!/usr/bin/env python3
"""
🤖 Telegram Bot with Telethon Integration

A production-ready bot featuring:
- Telegram Bot API (python-telegram-bot v22+)
- Telethon client for user session management
- Async/await for non-blocking operations
- Comprehensive logging and error handling
- Type hints and clean architecture
"""

import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ============================================================================
# Configuration & Setup
# ============================================================================

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME: str = os.getenv("SESSION_NAME", "user_session")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

if not BOT_TOKEN or not API_ID or not API_HASH:
    print("❌ Error: Missing required environment variables in .env")
    print("Required: BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH")
    sys.exit(1)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Conversation states
MENU, CHANNELS, STATUS = range(3)


# ============================================================================
# Telethon Manager
# ============================================================================

class TelethonManager:
    """Manages Telethon client for user session operations."""

    def __init__(self, api_id: int, api_hash: str, session_name: str) -> None:
        """Initialize Telethon manager."""
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self.is_authenticated = False

    async def connect(self) -> bool:
        """Connect to Telegram and check authentication."""
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.connect()

            if await self.client.is_user_authorized():
                self.is_authenticated = True
                logger.info("✅ Telethon: Authenticated with existing session")
                return True

            logger.info("📱 Telethon: No session found")
            return True

        except Exception as e:
            logger.error(f"❌ Telethon connection error: {e}")
            return False

    async def get_dialogs(self) -> list[str]:
        """Get list of channels and groups."""
        if not self.client or not self.is_authenticated:
            return ["❌ Not authenticated"]

        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    entity = dialog.entity
                    name = entity.title or "Unknown"
                    username = getattr(entity, "username", None)

                    if username:
                        dialogs.append(f"📢 {name} (@{username})")
                    else:
                        dialogs.append(f"🔒 {name} (Private)")

            return dialogs if dialogs else ["📭 No channels found"]

        except Exception as e:
            logger.error(f"❌ Error fetching dialogs: {e}")
            return [f"❌ Error: {str(e)[:50]}"]

    async def get_user_info(self) -> dict:
        """Get current user information."""
        if not self.client or not self.is_authenticated:
            return {"status": "Not authenticated"}

        try:
            me = await self.client.get_me()
            return {
                "first_name": me.first_name,
                "username": me.username or "None",
                "phone": me.phone,
            }
        except Exception as e:
            logger.error(f"❌ Error fetching user info: {e}")
            return {"error": str(e)}

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()


telethon_manager = TelethonManager(API_ID, API_HASH, SESSION_NAME)


# ============================================================================
# Bot Handlers
# ============================================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command."""
    try:
        user = update.effective_user
        text = f"👋 Welcome, {user.first_name}!\n\nChoose an option:"

        keyboard = [
            [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        logger.info(f"User {user.id} started the bot")
        return MENU

    except Exception as e:
        logger.error(f"Error in start_handler: {e}")
        await update.message.reply_text("❌ An error occurred")
        return MENU


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle status button."""
    try:
        query = update.callback_query
        await query.answer()

        text = "📊 Bot Status:\n\n"

        if telethon_manager.is_authenticated:
            user_info = await telethon_manager.get_user_info()
            if "error" not in user_info:
                text += (
                    f"✅ Telethon: Connected\n"
                    f"👤 User: {user_info.get('first_name', 'N/A')}\n"
                    f"📱 Username: @{user_info.get('username', 'N/A')}\n"
                )
            else:
                text += f"⚠️ Telethon: {user_info.get('error', 'Error')}\n"
        else:
            text += "❌ Telethon: Not authenticated\n"

        text += "\n✨ Bot is running"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATUS

    except Exception as e:
        logger.error(f"Error in status_handler: {e}")
        await update.callback_query.answer("❌ Error", show_alert=True)
        return MENU


async def list_channels_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle list channels button."""
    try:
        query = update.callback_query
        await query.answer()

        if not telethon_manager.is_authenticated:
            await query.answer("❌ Not authenticated", show_alert=True)
            return MENU

        dialogs = await telethon_manager.get_dialogs()
        text = "📋 Channels & Groups:\n\n" + "\n".join(dialogs)
        text += f"\n\n(Total: {len(dialogs)})"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CHANNELS

    except Exception as e:
        logger.error(f"Error in list_channels_handler: {e}")
        await update.callback_query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
        return MENU


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back button."""
    try:
        query = update.callback_query
        await query.answer()

        text = "🔄 Back to Menu\n\nChoose an option:"
        keyboard = [
            [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MENU

    except Exception as e:
        logger.error(f"Error in back_handler: {e}")
        return MENU


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button."""
    try:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("👋 Goodbye! Use /start to interact again.")
        logger.info("Conversation cancelled")
        return -1

    except Exception as e:
        logger.error(f"Error in cancel_handler: {e}")
        return -1


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route button callbacks to appropriate handlers."""
    query = update.callback_query
    callback = query.data

    if callback == "status":
        return await status_handler(update, context)
    elif callback == "list_channels":
        return await list_channels_handler(update, context)
    elif callback == "back":
        return await back_handler(update, context)
    elif callback == "cancel":
        return await cancel_handler(update, context)

    return MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Exception: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ An error occurred")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


# ============================================================================
# Main Application
# ============================================================================

async def main() -> None:
    """Initialize and start the bot."""
    try:
        logger.info("🚀 Starting Telegram Bot...")

        # Connect Telethon
        logger.info("🔌 Initializing Telethon...")
        telethon_ok = await telethon_manager.connect()

        if telethon_ok and telethon_manager.is_authenticated:
            user_info = await telethon_manager.get_user_info()
            logger.info(f"✅ Telethon authenticated as {user_info.get('first_name')}")
        elif telethon_ok:
            logger.warning("⚠️ Telethon: Waiting for authentication on first login")
        else:
            logger.warning("⚠️ Telethon connection failed, bot will continue")

        # Create bot application
        app = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_error_handler(error_handler)

        logger.info("✅ Bot handlers configured")
        logger.info("🤖 Bot is polling for messages...")

        async with app:
            await app.start()
            await app.updater.start_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
            )
            logger.info("✅ Bot is running!")
            await app.updater.idle()

    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        await telethon_manager.disconnect()
        logger.info("🔌 Cleanup completed")


if __name__ == "__main__":
    try:
        import asyncio

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped")
        sys.exit(0)
