from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from db import get_waifus_by_user, get_waifu_by_id, delete_waifu_by_id
from utils.date import start_date_session, create_gemini_chat_session
from utils.gemini import get_gemini_chat_response
from templates.message import (
    DATE_START_NO_WAIFU, DATE_START_CHOOSE_WAIFU, DATE_WAIFU_SELECTED,
    DATE_END_MESSAGE, DATE_ERROR_GENERAL, DATE_ERROR_GEMINI
)

CHOOSE_WAIFU, DATING, CONFIRM_DELETE = range(3)

# Start Date
async def date_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    waifu_list = get_waifus_by_user(user_id)

    if not waifu_list:
        await update.message.reply_text(
            f"{DATE_START_NO_WAIFU}\n\nSilakan pilih:\n"
            "/register_waifu - Daftarkan waifu baru\n"
            "/date_waifu - Mulai kencan"
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(f"❤️ {waifu[2]}", callback_data=f"select_waifu_{waifu[0]}"),
            InlineKeyboardButton("🗑️", callback_data=f"delete_waifu_{waifu[0]}")
        ]
        for waifu in waifu_list
    ]

    await update.message.reply_text(
        DATE_START_CHOOSE_WAIFU,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_WAIFU

# Konfirmasi Penghapusan
async def confirm_delete_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    waifu_id = query.data.split('_')[-1]
    waifu = get_waifu_by_id(waifu_id)

    if not waifu:
        await query.edit_message_text("Waifu tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['waifu_to_delete'] = waifu_id

    keyboard = [
        [InlineKeyboardButton("❗Ya, Hapus", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("Batal", callback_data="confirm_delete_cancel")]
    ]

    await query.edit_message_text(
        f"Apakah kamu yakin ingin menghapus waifu *{waifu[2]}*? 🗑️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_DELETE

# Eksekusi Penghapusan
async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_delete_yes":
        waifu_id = context.user_data.get("waifu_to_delete")
        waifu = get_waifu_by_id(waifu_id)
        if waifu:
            delete_waifu_by_id(waifu_id)
            await query.edit_message_text(
                f"✅ Waifu *{waifu[2]}* berhasil dihapus.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("Waifu tidak ditemukan.")
    else:
        await query.edit_message_text("Penghapusan dibatalkan.")

    context.user_data.pop("waifu_to_delete", None)
    return ConversationHandler.END

# Memilih Waifu
async def select_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    waifu_id = query.data.split('_')[-1]
    waifu = get_waifu_by_id(waifu_id)

    if not waifu:
        await query.edit_message_text(DATE_ERROR_GENERAL)
        return ConversationHandler.END

    waifu_data = {
        "id": waifu[0],
        "telegram_user_id": waifu[1],
        "name": waifu[2],
        "age": waifu[3],
        "personality": waifu[4],
        "background": waifu[5],
        "image_path": waifu[6]
    }

    start_date_session(context, waifu_data)
    context.user_data['current_dating_waifu'] = waifu_data
    context.user_data['gemini_chat_session'] = create_gemini_chat_session(
        waifu_data["name"],
        waifu_data["personality"],
        waifu_data["background"]
    )

    keyboard = ReplyKeyboardMarkup([["Akhiri Kencan"]], resize_keyboard=True)
    await query.edit_message_text(DATE_WAIFU_SELECTED.format(waifu_name=waifu_data['name']))
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Kamu bisa mulai ngobrol sekarang dengan {waifu_data['name']} ❤️",
        reply_markup=keyboard
    )
    return DATING

# Proses Chat Saat Dating
async def handle_dating_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    waifu = context.user_data.get('current_dating_waifu')
    chat_session = context.user_data.get('gemini_chat_session')

    if not waifu or not chat_session:
        await update.message.reply_text(DATE_ERROR_GENERAL)
        return ConversationHandler.END

    user_message = update.message.text
    gemini_response = get_gemini_chat_response(
        chat_session, user_message,
        waifu['name'], waifu['personality'], waifu['background']
    )

    if gemini_response:
        await update.message.reply_text(f"{waifu['name']}: {gemini_response[:4000]}")
    else:
        await update.message.reply_text(DATE_ERROR_GEMINI)

    return DATING

# Mengakhiri Kencan
async def end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    waifu = context.user_data.pop('current_dating_waifu', None)
    chat_session = context.user_data.pop('gemini_chat_session', None)

    if waifu and chat_session:
        try:
            farewell = get_gemini_chat_response(
                chat_session,
                "Waktunya mengakhiri sesi kencan. Sampaikan salam manis dan perpisahan kepada user.",
                waifu['name'], waifu['personality'], waifu['background']
            )
            if farewell:
                await update.message.reply_text(f"{waifu['name']}: {farewell}")
        except Exception as e:
            print(f"Gagal menyampaikan perpisahan: {e}")

    await update.message.reply_text(
        f"{DATE_END_MESSAGE}\n\nSilakan pilih:\n"
        "/register_waifu - Daftarkan waifu baru\n"
        "/date_waifu - Mulai kencan",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Handler
date_waifu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("date_waifu", date_start)],
    states={
        CHOOSE_WAIFU: [
            CallbackQueryHandler(select_waifu, pattern="^select_waifu_"),
            CallbackQueryHandler(confirm_delete_waifu, pattern="^delete_waifu_"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(handle_delete_confirmation, pattern="^confirm_delete_")
        ],
        DATING: [
            MessageHandler(filters.Regex("^Akhiri Kencan$"), end_date),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dating_message)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", end_date),
        CommandHandler("end_date", end_date)
    ],
)
