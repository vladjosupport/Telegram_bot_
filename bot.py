#!/usr/bin/env python3
"""
Telegram Bot with Telethon Integration
A modern, async Python Telegram bot with user session management.

Features:
- Telegram Bot API integration
- Telethon client for advanced operations
- Channel listing with session persistence
- Modern async/await patterns
- Comprehensive logging and error handling
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ============================================================================
# Configuration
# ============================================================================

# Load environment variables
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME: str = os.getenv("SESSION_NAME", "user_session")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Validate configuration
if not BOT_TOKEN or not API_ID or not API_HASH:
    print("❌ Error: Missing required environment variables!")
    print("Please create a .env file with BOT_TOKEN, TELEGRAM_API_ID, and TELEGRAM_API_HASH")
    sys.exit(1)

# Conversation states
MENU, CHANNELS, STATUS = range(3)

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Telethon Client Management
# ============================================================================

class TelethonManager:
    """Manages Telethon client for Telegram user session."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str,
    ) -> None:
        """
        Initialize Telethon manager.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_name: Session name for storing user data
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self.is_authenticated = False

    async def connect(self) -> bool:
        """
        Connect to Telegram and authenticate if needed.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.connect()

            # Check if already authenticated
            if await self.client.is_user_authorized():
                self.is_authenticated = True
                logger.info("✅ Authenticated with existing session")
                return True

            logger.info("📱 No session found, starting authentication...")
            await self.client.send_code_request(None)
            return True

        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False

    async def authenticate(self, phone: str, code: str, password: Optional[str] = None) -> bool:
        """
        Authenticate user with phone number and code.

        Args:
            phone: Phone number
            code: Verification code
            password: 2FA password (if required)

        Returns:
            True if authenticated successfully, False otherwise
        """
        try:
            if not self.client:
                logger.error("Client not connected")
                return False

            await self.client.sign_in(phone, code)
            self.is_authenticated = True
            logger.info("✅ Authentication successful!")
            return True

        except SessionPasswordNeededError:
            if password:
                await self.client.sign_in(password=password)
                self.is_authenticated = True
                logger.info("✅ 2FA authentication successful!")
                return True
            else:
                logger.warning("⚠️ 2FA required")
                return False

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    async def get_dialogs(self) -> list[str]:
        """
        Get list of channels and groups.

        Returns:
            List of formatted dialog information
        """
        if not self.client or not self.is_authenticated:
            return ["❌ Not authenticated"]

        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs():
                # Get channel/group info
                if dialog.is_channel or dialog.is_group:
                    entity = dialog.entity
                    name = entity.title or "Unknown"
                    username = getattr(entity, "username", None)

                    if username:
                        display = f"📢 {name} (@{username})"
                    else:
                        display = f"🔒 {name} (Private)"

                    dialogs.append(display)

            if not dialogs:
                return ["📭 No channels or groups found"]

            return dialogs

        except Exception as e:
            logger.error(f"❌ Error fetching dialogs: {e}")
            return [f"❌ Error: {e}"]

    async def get_user_info(self) -> dict:
        """
        Get current user information.

        Returns:
            Dictionary with user info
        """
        if not self.client or not self.is_authenticated:
            return {"status": "Not authenticated"}

        try:
            me = await self.client.get_me()
            return {
                "first_name": me.first_name,
                "last_name": me.last_name or "",
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
            logger.info("Disconnected from Telegram")


# ============================================================================
# Global Telethon Manager Instance
# ============================================================================

telethon_manager = TelethonManager(API_ID, API_HASH, SESSION_NAME)


# ============================================================================
# Bot Handlers
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start command handler.
    Displays welcome menu with main buttons.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        MENU state
    """
    try:
        user = update.effective_user
        welcome_text = (
            f"👋 Welcome, {user.first_name}!\n\n"
            "🤖 This is a powerful Telegram Bot with advanced features.\n\n"
            "Choose an option from the menu below:"
        )

        # Create inline keyboard
        keyboard = [
            [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        logger.info(f"User {user.id} started the bot")
        return MENU

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
        return MENU


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Status command handler.
    Displays current bot and user session status.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        MENU state
    """
    try:
        status_text = "📊 Bot Status Report:\n\n"

        if telethon_manager.is_authenticated:
            user_info = await telethon_manager.get_user_info()
            if "error" not in user_info:
                status_text += (
                    f"✅ Telethon Status: Connected\n"
                    f"👤 User: {user_info.get('first_name', 'N/A')}\n"
                    f"📱 Username: @{user_info.get('username', 'N/A')}\n"
                    f"📞 Phone: {user_info.get('phone', 'N/A')}\n"
                )
            else:
                status_text += f"⚠️ Telethon Status: Error - {user_info.get('error')}\n"
        else:
            status_text += "❌ Telethon Status: Not authenticated\n"

        status_text += f"\n🐍 Python Version: 3.12+\n"
        status_text += f"✨ Bot is running smoothly!"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            status_text, reply_markup=reply_markup
        )
        logger.info("Status report shown")
        return STATUS

    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.callback_query.answer("❌ Error fetching status", show_alert=True)
        return MENU


async def list_channels_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    List channels handler.
    Fetches and displays user's channels and groups.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        CHANNELS state
    """
    try:
        if not telethon_manager.is_authenticated:
            await update.callback_query.answer(
                "❌ Not authenticated. Please authenticate first.", show_alert=True
            )
            return MENU

        # Show loading indicator
        await update.callback_query.answer("📋 Fetching channels...")

        dialogs = await telethon_manager.get_dialogs()
        channels_text = "📋 Your Channels & Groups:\n\n"
        channels_text += "\n".join(dialogs)
        channels_text += "\n\n(Total: {})".format(len(dialogs))

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            channels_text, reply_markup=reply_markup
        )
        logger.info("Channels list shown")
        return CHANNELS

    except Exception as e:
        logger.error(f"Error in list_channels_handler: {e}")
        await update.callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)
        return MENU


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Back button handler.
    Returns to main menu.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        MENU state
    """
    try:
        menu_text = (
            "🔄 Back to Menu\n\n"
            "Choose an option from the menu below:"
        )

        keyboard = [
            [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup)
        return MENU

    except Exception as e:
        logger.error(f"Error in back_handler: {e}")
        return MENU


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancel handler.
    Ends the conversation.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        ConversationHandler.END
    """
    try:
        goodbye_text = "👋 Goodbye! Use /start to interact with me again."
        await update.callback_query.edit_message_text(goodbye_text)
        logger.info("Conversation cancelled")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in cancel_handler: {e}")
        return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Main button callback handler.
    Routes button presses to appropriate handlers.

    Args:
        update: Telegram update
        context: Handler context

    Returns:
        New conversation state
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "list_channels":
        return await list_channels_handler(update, context)
    elif callback_data == "status":
        return await status_command(update, context)
    elif callback_data == "back":
        return await back_handler(update, context)
    elif callback_data == "cancel":
        return await cancel_handler(update, context)

    return MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Log errors caused by updates.

    Args:
        update: The update that caused the error
        context: The context object
    """
    logger.error(f"Exception while handling an update: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


# ============================================================================
# Main Application Setup
# ============================================================================

async def main() -> None:
    """
    Main entry point.
    Initializes and starts the bot.
    """
    try:
        logger.info("🚀 Starting Telegram Bot...")

        # Initialize Telethon
        logger.info("🔌 Connecting Telethon client...")
        telethon_connected = await telethon_manager.connect()

        if telethon_connected:
            if telethon_manager.is_authenticated:
                user_info = await telethon_manager.get_user_info()
                logger.info(f"✅ Telethon authenticated as {user_info.get('first_name')}")
            else:
                logger.warning("⚠️ Telethon: No existing session, awaiting user authentication")
        else:
            logger.warning("⚠️ Telethon connection failed, but bot will continue")

        # Create application
        application = Application.builder().token(BOT_TOKEN).build()

        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start_command)],
            states={
                MENU: [
                    ConversationHandler(
                        entry_points=[],
                        states={},
                        fallbacks=[],
                    ),
                ],
            },
            fallbacks=[CommandHandler("start", start_command)],
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(conv_handler)
        application.add_handler(ConversationHandler(
            entry_points=[],
            states={
                MENU: [],
                CHANNELS: [],
                STATUS: [],
            },
            fallbacks=[],
        ))

        # Simple callback handler for all buttons
        application.add_handler(
            ConversationHandler(
                entry_points=[CommandHandler("start", start_command)],
                states={
                    MENU: [ConversationHandler(
                        entry_points=[],
                        states={},
                        fallbacks=[],
                    )],
                    CHANNELS: [],
                    STATUS: [],
                },
                fallbacks=[CommandHandler("start", start_command)],
            )
        )

        # Add direct button callback
        from telegram.ext import CallbackQueryHandler
        application.add_handler(CallbackQueryHandler(button_handler))

        # Error handler
        application.add_error_handler(error_handler)

        logger.info("✅ Bot handlers configured")
        logger.info("🤖 Bot is polling for messages...")

        # Start polling
        async with application:
            await application.start()
            await application.updater.start_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
            )
            logger.info("✅ Bot is running!")
            await application.updater.idle()

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
