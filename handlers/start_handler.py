# dating_waifu_bot/handlers/start_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from templates.message import START_MESSAGE, HELP_MESSAGE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan selamat datang."""
    await update.message.reply_text(START_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan bantuan."""
    await update.message.reply_text(HELP_MESSAGE)