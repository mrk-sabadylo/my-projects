from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram.filters import StateFilter

import os

from database import db
from config import ADMIN_ID, MESSAGES, EVENT_NAME
from keyboards import admin_keyboard, user_keyboard
from admin_filter import IsAdmin

admin_router = Router()
admin_router.message.filter(IsAdmin())  # ← ФІЛЬТР ПРАЦЮЄ

# ================= FSM =================

class AdminStates(StatesGroup):
    waiting_event_place = State()
    waiting_event_time = State()
    waiting_event_price = State()
    waiting_for_blacklist_add = State()
    waiting_for_blacklist_remove = State()
    waiting_for_slots = State()
    waiting_for_user_remove = State()

# ================= HELPERS =================

@admin_router.message(F.text == "❌ Cancel")
async def cancel_action(message: Message, state: FSMContext):
    if await state.get_state() is None:
        return

    await state.clear()
    await message.answer(
        "❌ Дію скасовано.",
        reply_markup=admin_keyboard
    )


@admin_router.message(F.text.startswith("/set_event"))
async def set_event_start(message: Message, state: FSMContext):
    await message.answer("📍 Введіть місце проведення:")
    await state.set_state(AdminStates.waiting_event_place)


@admin_router.message(AdminStates.waiting_event_place)
async def set_event_place(message: Message, state: FSMContext):
    await state.update_data(place=message.text)
    await message.answer("🕒 Введіть час події:")
    await state.set_state(AdminStates.waiting_event_time)


@admin_router.message(AdminStates.waiting_event_time)
async def set_event_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("💰 Введіть ціну (або 0):")
    await state.set_state(AdminStates.waiting_event_price)


@admin_router.message(AdminStates.waiting_event_price)
async def set_event_price(message: Message, state: FSMContext):
    data = await state.get_data()

    db.set_event_info(
        place=data["place"],
        time=data["time"],
        price=message.text
    )

    await state.clear()
    await message.answer("✅ Подію оновлено.")

@admin_router.message(F.text.startswith("/clear_event"))
async def clear_event(message: Message):
    db.clear_event_info()
    await message.answer("🗑 Дані події очищено.")

    # ================= FULL INFO =================

@admin_router.message(F.text.startswith("/full_info"))
async def full_info(message: Message):
        event = db.get_event_info()
        registered = db.get_current_slots()
        max_slots = db.get_max_slots()
        free = db.get_free_slots()
        price = db.get_price()
        unregister_allowed = db.is_unregister_allowed()
        bl_count = len(db.get_blacklist())

        event_block = (
            "ℹ️ Подію ще не налаштовано\n"
            if not event["place"] else
            f"📍 Місце: {event['place']}\n"
            f"🕒 Час: {event['time']}\n"
            f"💰 Ціна (з події): {event['price']}\n"
        )

        text = (
            "📊 <b>ПОВНА ІНФОРМАЦІЯ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"🎤 <b>Подія:</b>\n{event_block}\n"

            f"🎫 <b>Місця:</b>\n"
            f"Ліміт: {max_slots}\n"
            f"Зареєстровано: {registered}\n"
            f"Вільно: {free}\n\n"

            f"⛔ У blacklist: {bl_count}\n"
        )

        await message.answer(text, parse_mode="HTML")


# ================= GLOBAL BUTTONS =================
@admin_router.message(F.text.casefold() == "❌ cancel")
async def cancel_action(message: Message, state: FSMContext):
    if await state.get_state() is None:
        return  # якщо стану нема — нічого скасовувати

    await state.clear()
    await message.answer(
        "❌ Дію скасовано.",
        reply_markup=admin_keyboard
    )


@admin_router.message(F.text == "⬅️ Назад")
async def back_to_user_mode(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⬅️ Ви повернулись у режим користувача.", reply_markup=user_keyboard)


# ================= ADMIN PANEL =================

@admin_router.message(F.text.startswith("/admin"))
async def cmd_admin(message: Message):



    event = db.get_event_info()
    registered = db.get_current_slots()
    max_slots = db.get_max_slots()
    free = db.get_free_slots()
    bl_count = len(db.get_blacklist())

    event_block = (
        "ℹ️ Дані події ще не задані\n" if not event["place"] else
        f"📍 {event['place']}\n🕒 {event['time']}\n💰 {event['price']}\n"
    )

    text = (
        "🔐 <b>АДМІН-ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🎤 <b>Подія:</b>\n{event_block}\n"

        f"📊 <b>Статистика:</b>\n"
        f"👥 {registered}/{max_slots} | Вільно: {free}\n"
        f"⛔ Blacklist: {bl_count}\n\n"

        "📋 <b>Команди:</b>\n\n"

        "🎤 Подія:\n"
        "/set_event — задати подію\n"
        "/clear_event — очистити подію\n"
        "/full_info — повна інформація\n\n"


        "🎫 Місця:\n"
        "/set_slots — змінити ліміт місць\n"
        "/set_max_friends — ліміт друзів на гостя\n"
        "/slots_info — завантаженість\n\n"

        "👥 Реєстрації:\n"
        "/list_users — список гостей\n"
        "/remove_user — видалити гостя\n"
        "/clear_all — стерти всі реєстрації\n\n"

        "⛔ Blacklist:\n"
        "/blacklist_add — заблокувати\n"
        "/blacklist_remove — розблокувати\n"
        "/blacklist_list — список blacklist\n\n"

        "📦 Інше:\n"
        "/export — експорт\n"
    )

    await message.answer(text, reply_markup=admin_keyboard, parse_mode="HTML")

# ================= SLOTS =================

@admin_router.message(F.text.startswith("/set_slots"))
async def set_slots(message: Message, state: FSMContext):
    await message.answer("Введіть новий ліміт місць:")
    await state.set_state(AdminStates.waiting_for_slots)

@admin_router.message(AdminStates.waiting_for_slots)
async def process_slots(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть число.")
        return

    db.set_max_slots(int(message.text))

    await state.clear()
    await message.answer("✅ Ліміт місць оновлено.")


@admin_router.message(F.text.startswith("/slots_info"))
async def slots_info(message: Message):
    await message.answer(
        f"👥 Зареєстровано: {db.get_current_slots()}\n"
        f"🎫 Ліміт: {db.get_max_slots()}\n"
        f"🟢 Вільно: {db.get_free_slots()}"
    )

# ================= USERS =================

@admin_router.message(F.text.startswith("/list_users"))
async def list_users(message: Message):
    users = db.get_all_registered()
    if not users:
        await message.answer("Список пустий.")
        return

    text = "\n".join(f"{u['name']} | ID {uid} | @{u.get('username')}" for uid, u in users.items())
    await message.answer(text)

@admin_router.message(F.text.startswith("/remove_user"))
async def remove_user(message: Message, state: FSMContext):
    await message.answer("Введіть ID користувача для видалення:")
    await state.set_state(AdminStates.waiting_for_user_remove)

@admin_router.message(AdminStates.waiting_for_user_remove)
async def process_remove_user(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Потрібен числовий ID.")
        return
    db.unregister_user(int(message.text))
    await state.clear()
    await message.answer("🗑 Користувача видалено.")

@admin_router.message(F.text.startswith("/clear_all"))
async def clear_all(message: Message):
    db.clear_all_registrations()
    await message.answer("🗑 Усі реєстрації стерто.")

# ================= BLACKLIST =================
# (без змін, працює і для ID і для @username)
@admin_router.message(F.text.startswith("/blacklist_add"))
async def bl_add(message: Message, state: FSMContext):
    await message.answer("Введіть ID або @username:")
    await state.set_state(AdminStates.waiting_for_blacklist_add)

@admin_router.message(AdminStates.waiting_for_blacklist_add)
async def bl_add_process(message: Message, state: FSMContext):
    value = message.text.replace("@", "").strip()
    try: value = int(value)
    except: value = value.lower()
    db.add_to_blacklist(value)
    await state.clear()
    await message.answer("⛔ Додано в blacklist.")

@admin_router.message(F.text.startswith("/blacklist_remove"))
async def bl_remove(message: Message, state: FSMContext):
    await message.answer("Введіть ID або @username:")
    await state.set_state(AdminStates.waiting_for_blacklist_remove)

@admin_router.message(AdminStates.waiting_for_blacklist_remove)
async def bl_remove_process(message: Message, state: FSMContext):
    value = message.text.replace("@", "").strip()
    try: value = int(value)
    except: value = value.lower()
    db.remove_from_blacklist(value)
    await state.clear()
    await message.answer("✅ Видалено з blacklist.")

@admin_router.message(F.text.startswith("/blacklist_list"))
async def bl_list(message: Message):
    bl = db.get_blacklist()
    await message.answer("Blacklist:\n" + "\n".join(map(str, bl)) if bl else "Blacklist порожній.")

# ================= EXPORT =================

@admin_router.message(F.text.startswith("/export"))
async def export_data(message: Message):
    users = db.get_all_registered()
    event = db.get_event_info()

    text = f"ЕКСПОРТ {EVENT_NAME}\n{datetime.now()}\n\n"
    for uid, u in users.items():
        text += f"{u['name']} | {uid} | @{u.get('username')}\n"

    os.makedirs("data", exist_ok=True)
    filename = "data/export.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    await message.answer_document(FSInputFile(filename))
    os.remove(filename)

    # ================= Friends =================
@admin_router.message(F.text.startswith("/set_max_friends"))
async def set_max_friends(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /set_max_friends 3")
        return

    db.set_max_friends(int(parts[1]))
    await message.answer("✅ Ліміт друзів встановлено.")
