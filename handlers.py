from aiogram import Dispatcher, types, F
from aiogram.filters.command import Command
from config import ALLOWED_TELEGRAM_IDS, ALLOWED_PHONE_NUMBERS, OWNER_ID
from keyboards import get_action_kb, get_purpose_kb, get_gem_kb, get_test_kb, get_yes_no_kb, get_equipment_kb
from sheets import update_stock, history_sheet, archive_history, preloaded_data
from utils import log_time, extract_gem_info
from enum import IntEnum

dp = Dispatcher()

class States(IntEnum):
    WAITING_ACTION = 0
    WAITING_HOSPITAL = 1
    WAITING_PURPOSE = 2
    WAITING_GEM = 3
    WAITING_TESTS = 4
    WAITING_EXPIRY = 5
    WAITING_QUANTITY = 6
    WAITING_ANOTHER = 7

state = {}
data = {}

@dp.message(Command("start"))
@log_time
async def start_command(message: types.Message):
    data[message.chat.id] = {}
    await archive_history()
    if message.from_user.id in ALLOWED_TELEGRAM_IDS:
        data[message.chat.id]["user"] = message.from_user.full_name
        state[message.chat.id] = States.WAITING_ACTION
        await message.reply("Выберите действие:", reply_markup=get_action_kb())
    else:
        await message.reply("Поделитесь контактом для доступа.", reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Поделиться контактом", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        ))

@dp.message(F.content_type == "contact")
@log_time
async def contact_handler(message: types.Message):
    phone_number = message.contact.phone_number
    if phone_number in ALLOWED_PHONE_NUMBERS:
        ALLOWED_TELEGRAM_IDS.add(message.from_user.id)
        data[message.chat.id] = {"user": message.from_user.full_name}
        state[message.chat.id] = States.WAITING_HOSPITAL
        await message.reply("Доступ разрешён!\nВведите название больницы:", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.reply("Доступ запрещён.")

@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_ACTION)
@log_time
async def handle_action(message: types.Message):
    if message.text == "Забираем картридж":
        state[message.chat.id] = States.WAITING_HOSPITAL
        await message.reply("Введите название больницы:", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "Добавляем картридж":
        state[message.chat.id] = States.WAITING_GEM
        await message.reply("Для какого GEM?", reply_markup=get_gem_kb())
    else:
        await message.reply("Выберите действие:", reply_markup=get_action_kb())

# Добавь остальные обработчики по аналогии