import os
import qrcode


QR_DIR = "qr"


def ensure_qr_dir():
    os.makedirs(QR_DIR, exist_ok=True)


def generate_qr_image(token: str, user_id: int) -> str:
    """
    Генерує QR-картинку для користувача
    Повертає шлях до файлу
    """
    ensure_qr_dir()

    path = os.path.join(QR_DIR, f"{user_id}.png")

    img = qrcode.make(token)
    img.save(path)

    return path
