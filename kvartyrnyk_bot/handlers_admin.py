from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import os

from database import db
from config import ADMIN_ID, MESSAGES, EVENT_NAME
from keyboards import admin_keyboard, user_keyboard

admin_router = Router()

# ================= FSM =================

class AdminStates(StatesGroup):
    waiting_for_slots = State()
    waiting_for_user_remove = State()
    waiting_for_blacklist_add = State()
    waiting_for_blacklist_remove = State()

    waiting_event_place = State()
    waiting_event_time = State()
    waiting_event_price = State()

# ================= HELPERS =================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def stop_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Дію скасовано.")

# ================= GLOBAL BUTTONS =================

@admin_router.message(F.text == "Cancel")
async def cancel_action(message: Message, state: FSMContext):
    await stop_state(message, state)

@admin_router.message(F.text == "⬅️ Назад")
async def back_to_user_mode(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⬅️ Ви повернулись у режим користувача.", reply_markup=user_keyboard)

# ================= ADMIN PANEL =================

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(MESSAGES["admin_only"])
        return
    registered_count = db.get_current_slots()
    max_slots = db.get_max_slots()
    free_slots = db.get_free_slots()
    blacklist_count = len(db.get_blacklist())

    text = (
        f"🔐 Адмін-панель\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Статистика:\n"
        f"├ Зареєстровано: {registered_count}\n"
        f"├ Максимум місць: {max_slots}\n"
        f"├ Вільних місць: {free_slots}\n"
        f"└ У blacklist: {blacklist_count}\n\n"
        f"📋 Команди:\n\n"

        f"🎫 Місця:\n"
        f"/set_slots — змінити максимальну кількість місць\n"
        f"/slots_info — переглянути завантаженість\n\n"

        f"👥 Реєстрації:\n"
        f"/list_users — список всіх гостей\n"
        f"/remove_user — видалити гостя по ID\n"
        f"/clear_all — очистити всі реєстрації\n\n"

        f"⛔️ Blacklist:\n"
        f"/blacklist_add — заборонити користувачу реєстрацію\n"
        f"/blacklist_remove — дозволити користувачу реєстрацію\n"
        f"/blacklist_list — список заблокованих\n\n"

        f"📊 Інше:\n"
        f"/stats — повна статистика\n"
        f"/export — експорт гостей у файл\n\n"
    )

    await message.answer(text, reply_markup=admin_keyboard)

# ================= EVENT INFO =================

@admin_router.message(Command("set_event"))
async def set_event(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📍 Введіть місце:")
    await state.set_state(AdminStates.waiting_event_place)

@admin_router.message(AdminStates.waiting_event_place)
async def set_event_place(message: Message, state: FSMContext):
    await state.update_data(place=message.text)
    await message.answer("🕒 Введіть дату і час:")
    await state.set_state(AdminStates.waiting_event_time)

@admin_router.message(AdminStates.waiting_event_time)
async def set_event_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("💰 Введіть ціну:")
    await state.set_state(AdminStates.waiting_event_price)

@admin_router.message(AdminStates.waiting_event_price)
async def set_event_price(message: Message, state: FSMContext):
    data = await state.get_data()
    db.set_event_info(data["place"], data["time"], message.text)
    await message.answer("✅ Подію збережено.")
    await state.clear()

@admin_router.message(Command("clear_event"))
async def clear_event(message: Message):
    if is_admin(message.from_user.id):
        db.clear_event_info()
        await message.answer("🗑 Дані події очищено.")

# ================= EXPORT =================

@admin_router.message(Command("export"))
async def export_data(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = db.get_all_registered()
    event = db.get_event_info()
    blacklist = db.get_blacklist()

    text = f"ЕКСПОРТ: {EVENT_NAME}\n"
    text += f"Дата: {datetime.now()}\n"
    text += "=" * 40 + "\n\n"

    text += "ІНФОРМАЦІЯ ПРО ПОДІЮ\n"
    text += f"Місце: {event['place']}\n"
    text += f"Час: {event['time']}\n"
    text += f"Ціна: {event['price']}\n\n"

    text += f"ЗАРЕЄСТРОВАНІ ({len(users)})\n"
    text += "-" * 40 + "\n"
    for uid, info in users.items():
        text += f"{info['name']} | ID {uid} | @{info.get('username')}\n"

    text += "\nBLACKLIST\n"
    text += "-" * 40 + "\n"
    for uid in blacklist:
        text += f"{uid}\n"

    os.makedirs("data", exist_ok=True)
    filename = f"data/export_{datetime.now().timestamp()}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    await message.answer_document(FSInputFile(filename))
    os.remove(filename)


