import os
from telegram import File
from config import WAIFU_IMAGE_DIR

def save_waifu_image(file: File, filename: str) -> str:
    """
    Menyimpan file gambar ke direktori waifu_images.
    Mengembalikan path lengkap file yang disimpan.
    """
    os.makedirs(WAIFU_IMAGE_DIR, exist_ok=True)
    full_path = os.path.join(WAIFU_IMAGE_DIR, filename)
    file.download(full_path)
    return full_path