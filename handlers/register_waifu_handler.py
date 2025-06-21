# handlers/register_waifu_handler.py
import json
import os
from utils.date import start_date_session
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
    waifus = load_waifu_list()
    if any(w['name'].lower() == name.lower() for w in waifus):
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

    waifu_data = {
        "id": update.message.from_user.id * 100 + len(load_waifu_list()),  # simple unique id
        "name": context.user_data['waifu_name'],
        "age": context.user_data['waifu_age'],
        "personality": context.user_data['waifu_personality'],
        "background": context.user_data['waifu_background'],
        "bio": f"{context.user_data['waifu_name']}, {context.user_data['waifu_age']}, "
               f"{context.user_data['waifu_personality']}, {context.user_data['waifu_background']}",
        "image_path": context.user_data['waifu_image_path'],
        "owner_id": update.message.from_user.id
    }

    waifus = load_waifu_list()
    waifus.append(waifu_data)

    with open(WAIFU_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(waifus, f, indent=2, ensure_ascii=False)

    await update.message.reply_text(
        REGISTER_BIO_RECEIVED.format(waifu_name=waifu_data["name"]),
        reply_markup=ReplyKeyboardMarkup(
            [["Ngedate Sekarang", "Nanti Saja"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    context.user_data['registered_waifu'] = waifu_data
    return CONFIRM

async def confirm_after_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    if "ngedate" in choice:
        from handlers.date_waifu_handler import start_date_with_waifu
        return await start_date_with_waifu(update, context, context.user_data["registered_waifu"])
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
