from utils.gemini import create_gemini_chat_session

def start_date_session(context, selected_waifu):
    """Menyimpan waifu dan membuat sesi Gemini Chat."""
    context.user_data['current_dating_waifu'] = selected_waifu
    session = create_gemini_chat_session(
        waifu_name=selected_waifu['name'],
        personality=selected_waifu['personality'],
        background=selected_waifu['background']
    )
    context.user_data['gemini_chat_session'] = session
