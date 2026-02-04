from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from config import MESSAGES, EVENT_NAME
from keyboards import user_keyboard, confirm_keyboard

user_router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    confirm_unregister = State()


# START
@user_router.message(Command("start"))
@user_router.message(F.text == "⬅️ Назад")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MESSAGES["welcome"], reply_markup=user_keyboard, parse_mode="Markdown")


# EVENT INFO
@user_router.message(F.text == "ℹ️ Інформація про подію")
async def event_info_user(message: Message):
    info = db.get_event_info()
    price = db.get_price()


    if not info["place"] and not info["time"] and not info["price"]:
        await message.answer("ℹ️ Організатори ще не оголосили деталі на рахунок наступної події")
        return

    text = (
        f"🎸 **Інформація про подію**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 Місце: {info['place'] or 'ще не вказано'}\n"
        f"🕒 Час: {info['time'] or 'ще не вказано'}\n"
        f"💰 Ціна: {info['price'] or 'не вказано'}\n\n"
        f"🎫 Вільних місць: {db.get_free_slots()}"
    )

    await message.answer(text, parse_mode="HTML")




# REGISTER
@user_router.message(Command("register"))
@user_router.message(F.text == "📝 Реєстрація")
async def cmd_register(message: Message, state: FSMContext):
    if db.is_in_blacklist(message.from_user.id):
        await message.answer(MESSAGES["blacklist"])
        return

    if db.is_user_registered(message.from_user.id):
        await message.answer("ℹ️ Ви вже зареєстровані.")
        return

    if not db.has_free_slots():
        await message.answer(MESSAGES["no_slots"])
        return

    await message.answer("✍️ Введіть ваше імʼя та прізвище:")
    await state.set_state(RegistrationStates.waiting_for_name)


@user_router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name.split()) < 2:
        await message.answer(MESSAGES["invalid_name"])
        return

    db.register_user(message.from_user.id, name, message.from_user.username)
    await message.answer(MESSAGES["registered"].format(event=EVENT_NAME, name=name))
    await state.clear()


# STATUS
@user_router.message(Command("status"))
@user_router.message(F.text == "📋 Мій статус")
async def cmd_status(message: Message):
    if db.is_user_registered(message.from_user.id):
        user_info = db._load_data()["registered_users"][str(message.from_user.id)]
        await message.answer(f"✅ Ви зареєстровані як {user_info['name']}")
    else:
        await message.answer("ℹ️ Ви ще не зареєстровані.")


# UNREGISTER
@user_router.message(Command("unregister"))
@user_router.message(F.text == "❌ Скасувати бронь")
async def ask_unregister_confirm(message: Message, state: FSMContext):

    if not db.is_unregister_allowed():
        await message.answer("🚫 Зараз скасування броні вимкнене адміністратором.")
        return

    if not db.is_user_registered(message.from_user.id):
        await message.answer("ℹ️ Ви не маєте активної реєстрації.")
        return

    await message.answer("❗ Ви впевнені, що хочете скасувати бронювання?", reply_markup=confirm_keyboard)
    await state.set_state(RegistrationStates.confirm_unregister)


@user_router.message(RegistrationStates.confirm_unregister, F.text == "✅ Так")
async def confirm_yes(message: Message, state: FSMContext):
    db.unregister_user(message.from_user.id)
    await message.answer("❌ Вашу бронь скасовано.", reply_markup=user_keyboard)
    await state.clear()


@user_router.message(RegistrationStates.confirm_unregister, F.text == "❌ Ні")
async def confirm_no(message: Message, state: FSMContext):
    await message.answer("👍 Скасування відмінено.", reply_markup=user_keyboard)
    await state.clear()

