from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from qr_utils import generate_qr_image
from database import db
from config import MESSAGES, EVENT_NAME
from keyboards import user_keyboard, confirm_keyboard, yes_no_keyboard

user_router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    confirm_unregister = State()
    ask_about_friends = State()
    waiting_friend_count = State()
    waiting_friend_name = State()
    waiting_friend_username = State()


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

    if not info["place"] and not info["time"] and not info["price"]:
        await message.answer("ℹ️ Організатори ще не оголосили деталі на рахунок наступної події")
        return

    text = (
        f"🎸 Інформація про подію\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 Місце: {info['place'] or 'ще не вказано'}\n"
        f"🕒 Час: {info['time'] or 'ще не вказано'}\n"
        f"💰 Ціна: {info['price'] or 'не вказано'}\n\n"
        f"🎫 Вільних місць: {db.get_free_slots()}"
    )

    await message.answer(text)


# ----------------REGISTER---------------
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

    success = db.register_user(message.from_user.id, name, message.from_user.username)
    if not success:
        await message.answer("❌ Помилка реєстрації.")
        await state.clear()
        return

    await state.update_data(main_name=name)

    max_friends = db.get_max_friends()

    if max_friends > 0:
        await message.answer(
            "👥 Хочете привести друзів?",
            reply_markup=yes_no_keyboard
        )
        await state.set_state(RegistrationStates.ask_about_friends)
    else:
        await finish_registration(message, state)


async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("main_name")

    token = f"{message.from_user.id}:{EVENT_NAME}"
    qr_path = generate_qr_image(token, message.from_user.id)

    await message.answer(
        MESSAGES["registered"].format(event=EVENT_NAME, name=name),
        reply_markup=user_keyboard
    )

    await message.answer_photo(
        FSInputFile(qr_path),
        caption="🎫 Ваш QR-код для входу. Збережіть його."
    )

    await state.clear()

# ===== FRIENDS SYSTEM =====

@user_router.message(RegistrationStates.ask_about_friends, F.text == "Ні")
async def no_friends(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Реєстрацію завершено.", reply_markup=user_keyboard)


@user_router.message(RegistrationStates.ask_about_friends, F.text == "Так")
async def ask_friend_count(message: Message, state: FSMContext):
    max_friends = db.get_max_friends()
    await message.answer(f"Скільки друзів приведете? (максимум {max_friends})")
    await state.set_state(RegistrationStates.waiting_friend_count)


@user_router.message(RegistrationStates.waiting_friend_count)
async def process_friend_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть число.")
        return

    count = int(message.text)
    max_friends = db.get_max_friends()

    if count < 1 or count > max_friends:
        await message.answer("Невірна кількість.")
        return

    if db.get_free_slots() < count:
        await message.answer("Недостатньо вільних місць.")
        await state.clear()
        return

    await state.update_data(friends_total=count, current_friend=1)
    await message.answer("Введіть ім’я та прізвище друга №1:")
    await state.set_state(RegistrationStates.waiting_friend_name)


@user_router.message(RegistrationStates.waiting_friend_name)
async def process_friend_name(message: Message, state: FSMContext):
    await state.update_data(friend_name=message.text)
    data = await state.get_data()
    await message.answer(f"Введіть Telegram тег друга №{data['current_friend']} (@username або -):")
    await state.set_state(RegistrationStates.waiting_friend_username)


@user_router.message(RegistrationStates.waiting_friend_username)
async def process_friend_username(message: Message, state: FSMContext):
    data = await state.get_data()
    username = message.text.replace("@", "").strip()
    if username == "-":
        username = None

    db.add_friend_to_user(
        user_id=message.from_user.id,
        name=data["friend_name"],
        username=username
    )

    current = data["current_friend"]
    total = data["friends_total"]

    if current >= total:
        await message.answer("✅ Усі друзі додані!")
        await finish_registration(message, state)
        return

    await state.update_data(current_friend=current + 1)
    await message.answer(f"Введіть ім’я та прізвище друга №{current+1}:")
    await state.set_state(RegistrationStates.waiting_friend_name)


# MY QR
@user_router.message(F.text == "🎫 Мій QR")
async def cmd_my_qr(message: Message):
    if not db.is_user_registered(message.from_user.id):
        await message.answer("ℹ️ Ви ще не зареєстровані.")
        return

    token = f"{message.from_user.id}:{EVENT_NAME}"
    qr_path = generate_qr_image(token, message.from_user.id)

    await message.answer_photo(FSInputFile(qr_path), caption="🎫 Ось ваш QR-код для входу.")


# STATUS
@user_router.message(Command("status"))
@user_router.message(F.text == "📋 Мій статус")
async def cmd_status(message: Message):
    if db.is_user_registered(message.from_user.id):
        user_info = db.get_all_registered()[str(message.from_user.id)]
        friends = user_info.get("friends", [])
        await message.answer(f"✅ Ви зареєстровані як {user_info['name']}\n👥 Друзів: {len(friends)}")
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
