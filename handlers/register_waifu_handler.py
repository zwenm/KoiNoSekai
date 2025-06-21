# handlers/register_waifu_handler.py
import json
import os
from utils.date import start_date_session, create_gemini_chat_session
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackContext, ConversationHandler,
    MessageHandler, CommandHandler, filters
)
from templates.message import (
    REGISTER_START_MESSAGE, REGISTER_PHOTO_RECEIVED, REGISTER_NAME_MESSAGE, REGISTER_AGE_MESSAGE,
    REGISTER_PERSONALITY_MESSAGE, REGISTER_BACKGROUND_MESSAGE, REGISTER_BIO_RECEIVED,
    REGISTER_CANCELLED, REGISTER_ERROR_NO_PHOTO, REGISTER_ERROR_GENERAL
)
from config import WAIFU_DATA_FILE
from db import save_waifu, get_waifus_by_user

PHOTO, NAME, AGE, PERSONALITY, BACKGROUND, CONFIRM = range(6)

def load_waifu_list():
    if os.path.exists(WAIFU_DATA_FILE):
        with open(WAIFU_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(REGISTER_START_MESSAGE)
    return PHOTO

async def receive_photo(update: Update, context: CallbackContext) -> int:
    if not update.message.photo:
        await update.message.reply_text(REGISTER_ERROR_NO_PHOTO)
        return PHOTO

    photo_file = await update.message.photo[-1].get_file()
    filename = f"waifu_{update.message.from_user.id}_{photo_file.file_unique_id}.jpg"

    try:
        image_dir = os.path.join(os.path.dirname(__file__), "..", "images")
        os.makedirs(image_dir, exist_ok=True)
        file_path = os.path.join(image_dir, filename)
        await photo_file.download_to_drive(file_path)

        context.user_data['waifu_image_path'] = file_path
        await update.message.reply_text(REGISTER_PHOTO_RECEIVED)
        await update.message.reply_text(REGISTER_NAME_MESSAGE)
        return NAME
    except Exception as e:
        print(f"Error saving photo: {e}")
        await update.message.reply_text(REGISTER_ERROR_GENERAL)
        return ConversationHandler.END

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    waifus = get_waifus_by_user(update.message.from_user.id)
    if any(w[2].lower() == name.lower() for w in waifus):  # index 2 = name
        await update.message.reply_text("Nama waifu sudah digunakan. Masukkan nama lain:")
        return NAME

    context.user_data['waifu_name'] = name
    await update.message.reply_text(REGISTER_AGE_MESSAGE)
    return AGE

async def receive_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['waifu_age'] = update.message.text.strip()
    await update.message.reply_text(REGISTER_PERSONALITY_MESSAGE)
    return PERSONALITY

async def receive_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['waifu_personality'] = update.message.text.strip()
    await update.message.reply_text(REGISTER_BACKGROUND_MESSAGE)
    return BACKGROUND

async def receive_background(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['waifu_background'] = update.message.text.strip()

    try:
        save_waifu(
            update.message.from_user.id,
            context.user_data['waifu_name'],
            context.user_data['waifu_age'],
            context.user_data['waifu_personality'],
            context.user_data['waifu_background'],
            context.user_data['waifu_image_path']
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
        return NAME  # minta ulang nama

    await update.message.reply_text(
        REGISTER_BIO_RECEIVED.format(waifu_name=context.user_data["waifu_name"]),
        reply_markup=ReplyKeyboardMarkup(
            [["Ngedate Sekarang", "Nanti Saja"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CONFIRM

async def confirm_after_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    if "ngedate" in choice:
        # Ambil waifu terakhir yang baru saja disimpan oleh user
        waifus = get_waifus_by_user(update.message.from_user.id)
        latest_waifu = waifus[-1] if waifus else None

        if not latest_waifu:
            await update.message.reply_text("Waifu tidak ditemukan.")
            return ConversationHandler.END

        selected_waifu = {
            "id": latest_waifu[0],
            "telegram_user_id": latest_waifu[1],
            "name": latest_waifu[2],
            "age": latest_waifu[3],
            "personality": latest_waifu[4],
            "background": latest_waifu[5],
            "image_path": latest_waifu[6],
        }

        start_date_session(context, selected_waifu)
        context.user_data['current_dating_waifu'] = selected_waifu
        context.user_data['gemini_chat_session'] = create_gemini_chat_session(
            selected_waifu['name'],
            selected_waifu['personality'],
            selected_waifu['background']
        )

        await update.message.reply_text(
            f"Kamu sekarang sedang kencan dengan {selected_waifu['name']} ❤️\n"
            f"Silakan mulai ngobrol dengannya sekarang!",
            reply_markup=ReplyKeyboardMarkup([["Akhiri Kencan"]], resize_keyboard=True)
        )
        return 1  # DATING state
    else:
        await update.message.reply_text("Oke, waifumu tersimpan. Kamu bisa mulai ngedate kapan saja pakai /date_waifu.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(REGISTER_CANCELLED)
    if 'waifu_image_path' in context.user_data:
        try:
            os.remove(context.user_data['waifu_image_path'])
        except:
            pass
    return ConversationHandler.END

register_waifu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("register_waifu", register_start)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_age)],
        PERSONALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_personality)],
        BACKGROUND: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_background)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_after_register)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
