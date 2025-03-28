import logging
from aiogram import Dispatcher, types, F
from aiogram.filters.command import Command
from config import ALLOWED_TELEGRAM_IDS, ALLOWED_PHONE_NUMBERS, OWNER_ID
from keyboards import (
    get_action_kb, get_purpose_kb, get_gem_kb, get_test_kb, get_yes_no_kb,
    get_equipment_kb, get_edan_product_kb
)
from sheets import update_stock, history_sheet, archive_history, preloaded_data, edan_sheet, getein_sheet
from utils import log_time, extract_gem_info, process_image
from enum import IntEnum
from datetime import datetime

dp = Dispatcher()

# Состояния
class States(IntEnum):
    WAITING_ACTION = 0
    WAITING_HOSPITAL = 1
    WAITING_PURPOSE = 2
    WAITING_EQUIPMENT_TYPE = 3
    WAITING_GEM = 4
    WAITING_TESTS = 5
    WAITING_EXPIRY = 6
    WAITING_QUANTITY = 7
    WAITING_ANOTHER = 8
    WAITING_ISSUER = 9
    WAITING_ADD_TYPE = 10
    WAITING_EDAN_PRODUCT = 11
    WAITING_EDAN_LOT = 12
    WAITING_EDAN_EXPIRY = 13
    WAITING_EDAN_QUANTITY = 14
    WAITING_GETEIN_ITEM = 15
    WAITING_GETEIN_EXPIRY = 16
    WAITING_GETEIN_QUANTITY = 17

state = {}
data = {}

# Обработчик команды /start
@dp.message(Command("start"))
@log_time
async def start_command(message: types.Message):
    """Запускает бота и проверяет авторизацию."""
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

@dp.message(Command("status"))
@log_time
async def status_command(message: types.Message):
    """Показывает текущие остатки Gem-картриджей."""
    if message.from_user.id not in ALLOWED_TELEGRAM_IDS:
        await message.reply("Нет доступа. Поделитесь контактом.", reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Поделиться контактом", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        ))
        return
    try:
        status_msg = "Текущие остатки Gem-картриджей:\n"
        for gem in ["3500", "4000", "5000"]:
            status_msg += f"\nGEM {gem}:\n"
            dates = preloaded_data.get(gem, {}).get("date", [])
            for test in ["150", "300", "450", "600"]:
                quantities = preloaded_data.get(gem, {}).get(test, [])
                for date, qty in zip(dates, quantities):
                    if date and qty and int(qty) > 0:
                        status_msg += f"  - {test} тестов, срок {date}: {qty} шт.\n"
        await message.reply(status_msg or "Склад пуст.")
    except Exception as e:
        logging.error(f"Error fetching status: {e}")
        await message.reply("Ошибка при получении остатков.")

# Обработчик контакта для авторизации
@dp.message(F.content_type == "contact")
@log_time
async def contact_handler(message: types.Message):
    """Проверяет номер телефона для авторизации."""
    phone_number = message.contact.phone_number
    if phone_number in ALLOWED_PHONE_NUMBERS:
        ALLOWED_TELEGRAM_IDS.add(message.from_user.id)
        data[message.chat.id] = {"user": message.from_user.full_name}
        state[message.chat.id] = States.WAITING_ACTION
        await message.reply("Доступ разрешён!\nВыберите действие:", reply_markup=get_action_kb())
    else:
        await message.reply("Доступ запрещён.")

# Обработчик выбора действия
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_ACTION)
@log_time
async def handle_action(message: types.Message):
    """Обрабатывает выбор действия: выдача или добавление."""
    if message.text == "Забираем картридж":
        data[message.chat.id]["operation"] = "issue"
        state[message.chat.id] = States.WAITING_ISSUER
        await message.reply("Кто забирает картридж?", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "Добавляем картридж":
        data[message.chat.id]["operation"] = "add"
        state[message.chat.id] = States.WAITING_ADD_TYPE
        add_kb = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Edan"), types.KeyboardButton(text="Gem")],
                [types.KeyboardButton(text="Getein")],
                [types.KeyboardButton(text="Назад")]
            ],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.reply("Выберите тип добавления картриджа:", reply_markup=add_kb)
    else:
        await message.reply("Выберите действие:", reply_markup=get_action_kb())

# Обработчик "Кто забирает"
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_ISSUER)
@log_time
async def handle_issuer(message: types.Message):
    """Сохраняет имя того, кто забирает картридж."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_ACTION
        await message.reply("Выберите действие:", reply_markup=get_action_kb())
        return
    data[message.chat.id]["issuer"] = message.text
    state[message.chat.id] = States.WAITING_HOSPITAL
    await message.reply("Введите название больницы:")

# Обработчик ввода больницы
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_HOSPITAL)
@log_time
async def handle_hospital(message: types.Message):
    """Сохраняет название больницы и переходит к выбору цели."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_ISSUER
        await message.reply("Кто забирает картридж?", reply_markup=types.ReplyKeyboardRemove())
        return
    data[message.chat.id]["hospital"] = message.text
    state[message.chat.id] = States.WAITING_PURPOSE
    await message.reply("Зачем забираем?", reply_markup=get_purpose_kb())

# Обработчик выбора цели
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_PURPOSE)
@log_time
async def handle_purpose(message: types.Message):
    """Сохраняет цель операции и переходит к выбору оборудования."""
    from config import PURPOSES
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_HOSPITAL
        await message.reply("Введите название больницы:", reply_markup=types.ReplyKeyboardRemove())
        return
    if message.text in PURPOSES:
        data[message.chat.id]["purpose"] = message.text
        state[message.chat.id] = States.WAITING_EQUIPMENT_TYPE
        await message.reply("Забираем для какого оборудования?", reply_markup=get_equipment_kb())
    else:
        await message.reply("Выберите из списка.", reply_markup=get_purpose_kb())

# Обработчик выбора типа оборудования
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EQUIPMENT_TYPE)
@log_time
async def handle_equipment_type(message: types.Message):
    """Обрабатывает выбор типа оборудования для выдачи."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_PURPOSE
        await message.reply("Зачем забираем?", reply_markup=get_purpose_kb())
        return
    elif message.text == "Gem":
        state[message.chat.id] = States.WAITING_GEM
        await message.reply("Для какого GEM?", reply_markup=get_gem_kb())
    elif message.text == "Edan":
        state[message.chat.id] = States.WAITING_EDAN_PRODUCT
        await message.reply("Выберите наименование для выдачи:", reply_markup=get_edan_product_kb())
    elif message.text == "Getein":
        if getein_sheet:
            items = sorted(set(getein_sheet.col_values(1)[1:]))
            item_kb = types.ReplyKeyboardMarkup(
                resize_keyboard=True, one_time_keyboard=True,
                keyboard=[[types.KeyboardButton(text=item)] for item in items] + [[types.KeyboardButton(text="Назад")]]
            )
            state[message.chat.id] = States.WAITING_GETEIN_ITEM
            await message.reply("Какое наименование Getein забираем?", reply_markup=item_kb)
        else:
            await message.reply("Ошибка: таблица Getein недоступна.")
    else:
        await message.reply("Выберите из списка.", reply_markup=get_equipment_kb())

# Обработчик выбора GEM
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_GEM)
@log_time
async def handle_gem(message: types.Message):
    """Сохраняет модель GEM и переходит к выбору тестов."""
    from config import GEMS
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_EQUIPMENT_TYPE if data[message.chat.id].get("operation") == "issue" else States.WAITING_ADD_TYPE
        await message.reply("Забираем для какого оборудования?" if data[message.chat.id].get("operation") == "issue" else "Выберите тип добавления:", reply_markup=get_equipment_kb())
        return
    if message.text in GEMS:
        data[message.chat.id]["gem"] = message.text
        state[message.chat.id] = States.WAITING_TESTS
        if data[message.chat.id].get("operation") == "add":
            await message.reply("Сколько тестов? (или отправьте фото картриджа)", reply_markup=get_test_kb())
        else:
            await message.reply("Сколько тестов?", reply_markup=get_test_kb())
    else:
        await message.reply("Выберите из списка.", reply_markup=get_gem_kb())

# Обработчик фото для OCR (только при добавлении GEM)
@dp.message(F.photo & (lambda m: state.get(m.chat.id) == States.WAITING_TESTS) & (lambda m: data.get(m.chat.id, {}).get("operation") == "add"))
@log_time
async def handle_photo(message: types.Message):
    """Обрабатывает фото картриджа с помощью OCR."""
    photo = message.photo[-1]  # Берем самое большое изображение
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    ocr_text = await process_image(image_bytes.read())
    gem, expiry, tests = extract_gem_info(ocr_text)

    # Проверка распознанных данных
    from config import GEMS, TESTS
    errors = []
    if gem not in GEMS:
        errors.append(f"Модель GEM ({gem}) не распознана или некорректна.")
    if tests not in TESTS:
        errors.append(f"Количество тестов ({tests}) не распознано или некорректно.")
    if not expiry:
        errors.append("Срок годности не распознан.")

    if errors:
        await message.reply(
            "Не удалось распознать данные с фото:\n" + "\n".join(errors) +
            "\nПожалуйста, введите данные вручную.\nСколько тестов?",
            reply_markup=get_test_kb()
        )
        return

    data[message.chat.id]["gem"] = gem
    data[message.chat.id]["tests"] = tests
    data[message.chat.id]["expiry"] = expiry
    state[message.chat.id] = States.WAITING_QUANTITY
    await message.reply(
        f"Распознано: GEM {gem}, {tests} тестов, срок {expiry}.\nСколько картриджей добавить?",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработчик выбора количества тестов
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_TESTS)
@log_time
async def handle_tests(message: types.Message):
    """Сохраняет количество тестов и предлагает выбрать срок годности."""
    from config import TESTS
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_GEM
        await message.reply("Для какого GEM?", reply_markup=get_gem_kb())
        return
    if message.text in TESTS:
        data[message.chat.id]["tests"] = message.text
        gem = data[message.chat.id]["gem"]
        test = message.text
        dates = preloaded_data.get(gem, {}).get("date", [])
        quantities = preloaded_data.get(gem, {}).get(test, [])
        expiry_kb = []
        for date, qty in zip(dates, quantities):
            try:
                if date and int(qty or 0) > 0:
                    expiry_kb.append([types.KeyboardButton(text=f"{date} ({qty} шт.)")])
            except ValueError:
                continue
        if not expiry_kb and data[message.chat.id].get("operation") == "issue":
            await message.reply("Нет доступных картриджей с таким количеством тестов.", reply_markup=get_test_kb())
            return
        expiry_kb.append([types.KeyboardButton(text="Ввести вручную" if data[message.chat.id].get("operation") == "add" else "Назад")])
        state[message.chat.id] = States.WAITING_EXPIRY
        await message.reply("Выберите срок годности:" if data[message.chat.id].get("operation") == "issue" else "Выберите или введите срок годности:", reply_markup=types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, keyboard=expiry_kb
        ))
    else:
        await message.reply("Выберите из списка.", reply_markup=get_test_kb())

# Обработчик выбора срока годности
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EXPIRY)
@log_time
async def handle_expiry(message: types.Message):
    """Сохраняет срок годности и запрашивает количество."""
    import re
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_TESTS
        await message.reply("Сколько тестов?", reply_markup=get_test_kb())
        return
    if message.text == "Ввести вручную" and data[message.chat.id].get("operation") == "add":
        await message.reply("Введите срок годности (дд.мм.гггг):", reply_markup=types.ReplyKeyboardRemove())
        return
    match = re.search(r"(\d{2}\.\d{2}\.\d{4}) \((\d+) шт.\)", message.text)
    if match:
        data[message.chat.id]["expiry"] = match.group(1)
        data[message.chat.id]["available_qty"] = int(match.group(2))
        operation = data[message.chat.id].get("operation", "issue")
        state[message.chat.id] = States.WAITING_QUANTITY
        await message.reply(
            f"Сколько картриджей {'выдаём' if operation == 'issue' else 'добавляем'} GEM {data[message.chat.id]['gem']} "
            f"{data[message.chat.id]['tests']} тестов со сроком {match.group(1)}? "
            f"{'(Доступно: ' + match.group(2) + ')' if operation == 'issue' else ''}",
            reply_markup=types.ReplyKeyboardRemove()
        )
    elif re.match(r"^\d{2}\.\d{2}\.\d{4}$", message.text) and data[message.chat.id].get("operation") == "add":
        data[message.chat.id]["expiry"] = message.text
        state[message.chat.id] = States.WAITING_QUANTITY
        await message.reply(
            f"Сколько картриджей добавить GEM {data[message.chat.id]['gem']} {data[message.chat.id]['tests']} тестов со сроком {message.text}?",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.reply("Выберите корректный срок или введите в формате дд.мм.гггг.")

# Обработчик ввода количества (выдача/добавление)
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_QUANTITY)
@log_time
async def handle_quantity(message: types.Message):
    """Обрабатывает количество для выдачи или добавления GEM."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_EXPIRY
        await message.reply("Выберите срок годности:", reply_markup=get_test_kb())  # Здесь нужна динамическая клавиатура
        return
    if not message.text.isdigit():
        await message.reply("Введите корректное число.")
        return
    qty = int(message.text)
    operation = data[message.chat.id].get("operation", "issue")
    gem = data[message.chat.id]["gem"]
    tests = data[message.chat.id]["tests"]
    expiry = data[message.chat.id]["expiry"]
    if operation == "issue" and qty > data[message.chat.id]["available_qty"]:
        await message.reply(f"Недостаточно картриджей. Доступно: {data[message.chat.id]['available_qty']}.")
        return
    update_stock(gem, tests, expiry, -qty if operation == "issue" else qty)
    history_sheet.append_row([
        data[message.chat.id].get("issuer", data[message.chat.id]["user"]),
        data[message.chat.id].get("hospital", "На склад" if operation == "add" else ""),
        data[message.chat.id].get("purpose", "Добавление" if operation == "add" else ""),
        gem,
        tests,
        qty,
        expiry,
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Выдача" if operation == "issue" else "Добавление"
    ])
    await message.reply(
        f"{'Выдано' if operation == 'issue' else 'Добавлено'} {qty} картриджей GEM {gem} {tests} тестов, срок {expiry}."
    )
    state[message.chat.id] = States.WAITING_ANOTHER
    await message.reply("Ещё одна операция?", reply_markup=get_yes_no_kb())

# Обработчик выбора типа добавления
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_ADD_TYPE)
@log_time
async def handle_add_type(message: types.Message):
    """Обрабатывает выбор типа оборудования для добавления."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_ACTION
        await message.reply("Выберите действие:", reply_markup=get_action_kb())
        return
    elif message.text == "Gem":
        state[message.chat.id] = States.WAITING_GEM
        await message.reply("Для какого GEM?", reply_markup=get_gem_kb())
    elif message.text == "Edan":
        state[message.chat.id] = States.WAITING_EDAN_PRODUCT
        await message.reply("Выберите наименование для добавления:", reply_markup=get_edan_product_kb())
    elif message.text == "Getein":
        if getein_sheet:
            items = sorted(set(getein_sheet.col_values(1)[1:]))
            item_kb = types.ReplyKeyboardMarkup(
                resize_keyboard=True, one_time_keyboard=True,
                keyboard=[[types.KeyboardButton(text=item)] for item in items] + [[types.KeyboardButton(text="Новое(введите вручную)"), types.KeyboardButton(text="Назад")]]
            )
            state[message.chat.id] = States.WAITING_GETEIN_ITEM
            await message.reply("Выберите наименование для добавления:", reply_markup=item_kb)
        else:
            await message.reply("Ошибка: таблица Getein недоступна.")
    else:
        await message.reply("Выберите из списка.")

# Обработчик выбора продукта Edan
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EDAN_PRODUCT)
@log_time
async def handle_edan_product(message: types.Message):
    """Сохраняет продукт Edan и запрашивает лот."""
    from config import EDAN_PRODUCTS
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_ADD_TYPE if data[message.chat.id]["operation"] == "add" else States.WAITING_EQUIPMENT_TYPE
        await message.reply("Выберите тип добавления:" if data[message.chat.id]["operation"] == "add" else "Забираем для какого оборудования?", reply_markup=get_equipment_kb())
        return
    if message.text in EDAN_PRODUCTS or message.text == "Новое(введите вручную)":
        data[message.chat.id]["edan_item"] = message.text if message.text != "Новое(введите вручную)" else None
        if message.text == "Анализатор Edan" and data[message.chat.id]["operation"] == "add":
            data[message.chat.id]["edan_lot"] = "-"
            data[message.chat.id]["edan_expiry"] = "-"
            state[message.chat.id] = States.WAITING_EDAN_QUANTITY
            await message.reply("Сколько штук добавить?")
        else:
            state[message.chat.id] = States.WAITING_EDAN_LOT
            await message.reply("Введите лот/серийный номер:" if data[message.chat.id]["operation"] == "add" else "Выберите лот:", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.reply("Выберите из списка.", reply_markup=get_edan_product_kb())

# Обработчик ввода лота Edan
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EDAN_LOT)
@log_time
async def handle_edan_lot(message: types.Message):
    """Сохраняет лот Edan и запрашивает срок годности."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_EDAN_PRODUCT
        await message.reply("Выберите наименование:", reply_markup=get_edan_product_kb())
        return
    if not data[message.chat.id].get("edan_item"):
        data[message.chat.id]["edan_item"] = message.text
        await message.reply("Теперь введите лот:")
        return
    data[message.chat.id]["edan_lot"] = message.text
    state[message.chat.id] = States.WAITING_EDAN_EXPIRY
    await message.reply("Введите срок годности (дд.мм.гггг):" if data[message.chat.id]["operation"] == "add" else "Выберите срок годности:")

# Обработчик ввода срока годности Edan
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EDAN_EXPIRY)
@log_time
async def handle_edan_expiry(message: types.Message):
    """Сохраняет срок годности Edan и запрашивает количество."""
    import re
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_EDAN_LOT
        await message.reply("Введите лот:", reply_markup=types.ReplyKeyboardRemove())
        return
    if data[message.chat.id]["operation"] == "add" and not re.match(r"^\d{2}\.\d{2}\.\d{4}$", message.text):
        await message.reply("Введите срок в формате дд.мм.гггг.")
        return
    data[message.chat.id]["edan_expiry"] = message.text
    state[message.chat.id] = States.WAITING_EDAN_QUANTITY
    await message.reply("Сколько штук " + ("выдать?" if data[message.chat.id]["operation"] == "issue" else "добавить?"))

# Обработчик ввода количества Edan
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_EDAN_QUANTITY)
@log_time
async def handle_edan_quantity(message: types.Message):
    """Обрабатывает количество для выдачи или добавления Edan."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_EDAN_EXPIRY
        await message.reply("Введите срок годности:", reply_markup=types.ReplyKeyboardRemove())
        return
    if not message.text.isdigit():
        await message.reply("Введите корректное число.")
        return
    qty = int(message.text)
    operation = data[message.chat.id]["operation"]
    item = data[message.chat.id]["edan_item"]
    lot = data[message.chat.id]["edan_lot"]
    expiry = data[message.chat.id]["edan_expiry"]
    if item == "Анализатор Edan":
        current_qty = int(edan_sheet.cell(2, 7).value or 0)
        new_qty = current_qty - qty if operation == "issue" else current_qty + qty
        edan_sheet.update_cell(2, 7, new_qty)
    else:
        all_data = edan_sheet.get_all_values()[1:]
        found = False
        for i, row in enumerate(all_data, 2):
            if row[0] == item and row[1] == lot and row[2] == expiry:
                current_qty = int(row[3] or 0)
                new_qty = current_qty - qty if operation == "issue" else current_qty + qty
                edan_sheet.update_cell(i, 4, new_qty)
                found = True
                break
        if not found and operation == "add":
            edan_sheet.append_row([item, lot, expiry, qty])
    history_sheet.append_row([
        data[message.chat.id].get("issuer", data[message.chat.id]["user"]),
        data[message.chat.id].get("hospital", "На склад" if operation == "add" else ""),
        data[message.chat.id].get("purpose", "Добавление Edan" if operation == "add" else ""),
        item,
        "-",
        qty,
        expiry,
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Выдача" if operation == "issue" else "Добавление"
    ])
    await message.reply(
        f"{'Выдано' if operation == 'issue' else 'Добавлено'} {qty} шт. Edan {item}, срок {expiry}."
    )
    state[message.chat.id] = States.WAITING_ANOTHER
    await message.reply("Ещё одна операция?", reply_markup=get_yes_no_kb())

# Обработчик выбора наименования Getein
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_GETEIN_ITEM)
@log_time
async def handle_getein_item(message: types.Message):
    """Сохраняет наименование Getein и запрашивает срок годности."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_ADD_TYPE if data[message.chat.id]["operation"] == "add" else States.WAITING_EQUIPMENT_TYPE
        await message.reply("Выберите тип добавления:" if data[message.chat.id]["operation"] == "add" else "Забираем для какого оборудования?", reply_markup=get_equipment_kb())
        return
    data[message.chat.id]["getein_item"] = message.text if message.text != "Новое(введите вручную)" else None
    state[message.chat.id] = States.WAITING_GETEIN_EXPIRY
    await message.reply("Введите наименование вручную:" if not data[message.chat.id]["getein_item"] else "Введите срок годности (дд.мм.гггг):")

# Обработчик ввода срока годности Getein
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_GETEIN_EXPIRY)
@log_time
async def handle_getein_expiry(message: types.Message):
    """Сохраняет срок годности Getein и запрашивает количество."""
    import re
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_GETEIN_ITEM
        await message.reply("Выберите наименование:", reply_markup=get_edan_product_kb())  # Заменить на Getein KB
        return
    if not data[message.chat.id].get("getein_item"):
        data[message.chat.id]["getein_item"] = message.text
        await message.reply("Теперь введите срок годности (дд.мм.гггг):")
        return
    if data[message.chat.id]["operation"] == "add" and not re.match(r"^\d{2}\.\d{2}\.\d{4}$", message.text):
        await message.reply("Введите срок в формате дд.мм.гггг.")
        return
    data[message.chat.id]["getein_expiry"] = message.text
    state[message.chat.id] = States.WAITING_GETEIN_QUANTITY
    await message.reply("Сколько штук " + ("выдать?" if data[message.chat.id]["operation"] == "issue" else "добавить?"))

# Обработчик ввода количества Getein
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_GETEIN_QUANTITY)
@log_time
async def handle_getein_quantity(message: types.Message):
    """Обрабатывает количество для выдачи или добавления Getein."""
    if message.text.lower() == "назад":
        state[message.chat.id] = States.WAITING_GETEIN_EXPIRY
        await message.reply("Введите срок годности:", reply_markup=types.ReplyKeyboardRemove())
        return
    if not message.text.isdigit():
        await message.reply("Введите корректное число.")
        return
    qty = int(message.text)
    operation = data[message.chat.id]["operation"]
    item = data[message.chat.id]["getein_item"]
    expiry = data[message.chat.id]["getein_expiry"]
    all_data = getein_sheet.get_all_values()[1:]
    found = False
    for i, row in enumerate(all_data, 2):
        if row[0] == item and row[1] == expiry:
            current_qty = int(row[2] or 0)
            new_qty = current_qty - qty if operation == "issue" else current_qty + qty
            getein_sheet.update_cell(i, 3, new_qty)
            found = True
            break
    if not found and operation == "add":
        getein_sheet.append_row([item, expiry, qty])
    history_sheet.append_row([
        data[message.chat.id].get("issuer", data[message.chat.id]["user"]),
        data[message.chat.id].get("hospital", "На склад" if operation == "add" else ""),
        data[message.chat.id].get("purpose", "Добавление Getein" if operation == "add" else ""),
        item,
        "-",
        qty,
        expiry,
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Выдача" if operation == "issue" else "Добавление"
    ])
    await message.reply(
        f"{'Выдано' if operation == 'issue' else 'Добавлено'} {qty} шт. Getein {item}, срок {expiry}."
    )
    state[message.chat.id] = States.WAITING_ANOTHER
    await message.reply("Ещё одна операция?", reply_markup=get_yes_no_kb())

# Обработчик продолжения операций
@dp.message(lambda m: state.get(m.chat.id) == States.WAITING_ANOTHER)
@log_time
async def handle_another(message: types.Message):
    """Предлагает продолжить или завершить сессию."""
    if message.text == "Да":
        operation = data[message.chat.id]["operation"]
        data[message.chat.id] = {"user": data[message.chat.id]["user"], "operation": operation}
        state[message.chat.id] = States.WAITING_ISSUER if operation == "issue" else States.WAITING_ADD_TYPE
        await message.reply(
            "Кто забирает картридж?" if operation == "issue" else "Выберите тип добавления:",
            reply_markup=types.ReplyKeyboardRemove() if operation == "issue" else get_equipment_kb()
        )
    elif message.text == "Нет":
        state.pop(message.chat.id, None)
        data.pop(message.chat.id, None)
        await message.reply("Сессия завершена. /start для перезапуска.", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.reply("Выберите 'Да' или 'Нет'.", reply_markup=get_yes_no_kb())