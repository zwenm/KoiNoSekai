import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def create_gemini_chat_session(waifu_name: str, personality: str, background: str):
    session = model.start_chat(
        history=[],
        enable_automatic_function_calling=False  # opsional
    )

    system_prompt = (
        f"Kamu adalah {waifu_name}, seorang karakter anime yang kepribadiannya {personality}, dan memiliki latar belakang {background}.\n"
        "Gaya bicaramu santai, ringan, dan terasa seperti teman dekat.\n"
        "Jawablah dengan kalimat pendek dan to the point seperti sedang chat di aplikasi pesan.\n"
        "Tidak perlu terlalu romantis atau dramatis, cukup bersikap ramah dan menyenangkan.\n"
        "Jangan menyebut bahwa kamu adalah AI atau bot.\n"
    )

    session.send_message(system_prompt)
    return session

def get_gemini_chat_response(chat_session, user_message: str, waifu_name: str, personality: str, background: str) -> str:
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "Maaf, terjadi kesalahan saat membalas pesanmu."
