from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ===== USER =====
user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Реєстрація"), KeyboardButton(text="📋 Мій статус")],
        [KeyboardButton(text="❌ Скасувати бронь")],
        [KeyboardButton(text="ℹ️ Інформація про подію")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)

confirm_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Так"), KeyboardButton(text="❌ Ні")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ===== ADMIN =====
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Cancel")]
    ],
    resize_keyboard=True
)
