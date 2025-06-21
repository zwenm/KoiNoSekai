import json
import os
from pathlib import Path
from utils.date import start_date_session, create_gemini_chat_session
from utils.gemini import get_gemini_chat_response
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from templates.message import (
    DATE_START_NO_WAIFU, DATE_START_CHOOSE_WAIFU, DATE_WAIFU_SELECTED,
    DATE_END_MESSAGE, DATE_ERROR_GENERAL, DATE_ERROR_GEMINI
)
from config import WAIFU_DATA_FILE

CHOOSE_WAIFU, DATING, CONFIRM_DELETE = range(3)

def load_waifu_data():
    if os.path.exists(WAIFU_DATA_FILE):
        with open(WAIFU_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

async def date_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    waifu_list = load_waifu_data()

    if not waifu_list:
        await update.message.reply_text(
            f"{DATE_START_NO_WAIFU}\n\nSilakan pilih:\n"
            "/register_waifu - Daftarkan waifu baru\n"
            "/date_waifu - Mulai kencan"
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(f"❤️ {waifu['name']}", callback_data=f"select_waifu_{waifu['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"delete_waifu_{waifu['id']}")
        ]
        for waifu in waifu_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(DATE_START_CHOOSE_WAIFU, reply_markup=reply_markup)
    return CHOOSE_WAIFU

def save_waifu_data(data):
    with open(WAIFU_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_delete_yes":
        waifu_id = context.user_data.get("waifu_to_delete")
        waifu_list = load_waifu_data()

        waifu_index = next((i for i, w in enumerate(waifu_list) if str(w['id']) == waifu_id), None)
        if waifu_index is None:
            await query.edit_message_text("Waifu tidak ditemukan.")
            return ConversationHandler.END

        deleted_waifu = waifu_list.pop(waifu_index)
        save_waifu_data(waifu_list)

        await query.edit_message_text(f"✅ Waifu *{deleted_waifu['name']}* berhasil dihapus.", parse_mode="Markdown")
        context.user_data.pop("waifu_to_delete", None)
        return ConversationHandler.END

    elif query.data == "confirm_delete_cancel":
        await query.edit_message_text("❎ Penghapusan dibatalkan.")
        context.user_data.pop("waifu_to_delete", None)
        return ConversationHandler.END

async def delete_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    waifu_id = query.data.split('_')[-1]
    waifu_list = load_waifu_data()

    waifu_index = next((i for i, w in enumerate(waifu_list) if str(w['id']) == waifu_id), None)
    if waifu_index is None:
        await query.edit_message_text("Waifu tidak ditemukan.")
        return ConversationHandler.END

    deleted_waifu = waifu_list.pop(waifu_index)
    save_waifu_data(waifu_list)

    await query.edit_message_text(f"✅ Waifu *{deleted_waifu['name']}* berhasil dihapus.", parse_mode='Markdown')
    return ConversationHandler.END

async def confirm_delete_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    waifu_id = query.data.split('_')[-1]
    waifu_list = load_waifu_data()
    waifu = next((w for w in waifu_list if str(w['id']) == waifu_id), None)

    if not waifu:
        await query.edit_message_text("Waifu tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['waifu_to_delete'] = waifu_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❗Ya, Hapus", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("Batal Hapus", callback_data="confirm_delete_cancel")]
    ])
    await query.edit_message_text(
        f"Apakah kamu yakin ingin menghapus waifu *{waifu['name']}*? 🗑️",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CONFIRM_DELETE

async def select_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    waifu_id = query.data.split('_')[-1]
    waifu_list = load_waifu_data()
    selected_waifu = next((w for w in waifu_list if str(w['id']) == waifu_id), None)

    if not selected_waifu:
        await query.edit_message_text(DATE_ERROR_GENERAL)
        return ConversationHandler.END

    start_date_session(context, selected_waifu)

    context.user_data['current_dating_waifu'] = selected_waifu
    context.user_data['gemini_chat_session'] = create_gemini_chat_session(
        selected_waifu['name'],
        selected_waifu['personality'],
        selected_waifu['background']
    )

    keyboard = ReplyKeyboardMarkup([["Akhiri Kencan"]], resize_keyboard=True, one_time_keyboard=False)
    await query.edit_message_text(DATE_WAIFU_SELECTED.format(waifu_name=selected_waifu['name']))
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Kamu bisa mulai ngobrol sekarang dengan {selected_waifu['name']} ❤️",
        reply_markup=keyboard
    )
    return DATING

async def handle_dating_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    selected_waifu = context.user_data.get('current_dating_waifu')
    chat_session = context.user_data.get('gemini_chat_session')

    if not selected_waifu or not chat_session:
        await update.message.reply_text(DATE_ERROR_GENERAL)
        return ConversationHandler.END

    gemini_response = get_gemini_chat_response(
        chat_session,
        user_message,
        selected_waifu['name'],
        selected_waifu['personality'],
        selected_waifu['background']
    )

    if gemini_response:
        MAX_LENGTH = 4000
        await update.message.reply_text(f"{selected_waifu['name']}: {gemini_response[:MAX_LENGTH]}")
    else:
        await update.message.reply_text(DATE_ERROR_GEMINI)

    return DATING

async def end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    selected_waifu = context.user_data.get('current_dating_waifu')
    chat_session = context.user_data.get('gemini_chat_session')

    if selected_waifu and chat_session:
        farewell_prompt = (
            "Waktunya mengakhiri sesi kencan hari ini. "
            "Sampaikan salam perpisahan yang manis dan bersahabat kepada pengguna."
        )
        try:
            farewell_response = get_gemini_chat_response(
                chat_session,
                farewell_prompt,
                selected_waifu['name'],
                selected_waifu['personality'],
                selected_waifu['background']
            )
            if farewell_response:
                await update.message.reply_text(f"{selected_waifu['name']}: {farewell_response}")
        except Exception as e:
            print(f"Gagal mengirim pesan perpisahan: {e}")

    context.user_data.pop('current_dating_waifu', None)
    context.user_data.pop('gemini_chat_session', None)

    await update.message.reply_text(
        f"{DATE_END_MESSAGE}\n\nSilakan pilih:\n"
        "/register_waifu - Daftarkan waifu baru\n"
        "/date_waifu - Mulai kencan",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

date_waifu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("date_waifu", date_start)],
    states={
        CHOOSE_WAIFU: [
            CallbackQueryHandler(select_waifu, pattern='^select_waifu_'),
            CallbackQueryHandler(confirm_delete_waifu, pattern='^delete_waifu_'),
        ],
        DATING: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex("^Akhiri Kencan$"), end_date),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dating_message),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(handle_delete_confirmation, pattern="^confirm_delete_"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", end_date),
        CommandHandler("end_date", end_date),
    ],
)