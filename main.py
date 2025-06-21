from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from db import init_db
from handlers.start_handler import start
from handlers.date_waifu_handler import date_waifu_conv_handler
from handlers.register_waifu_handler import register_waifu_conv_handler

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Daftarkan handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(date_waifu_conv_handler)
    app.add_handler(register_waifu_conv_handler)

    print("Bot sedang berjalan...")
    app.run_polling()

if __name__ == '__main__':
    init_db()
    main()
