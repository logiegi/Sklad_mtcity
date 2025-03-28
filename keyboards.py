from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import GEMS, TESTS, PURPOSES, EDAN_PRODUCTS, EQUIPMENT_TYPES

def get_purpose_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text=purpose)] for purpose in PURPOSES] + [[KeyboardButton(text="Назад")]]
    )

def get_gem_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text=gem)] for gem in GEMS] + [[KeyboardButton(text="Назад")]]
    )

def get_test_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text=test)] for test in TESTS] + [[KeyboardButton(text="Назад")]]
    )

def get_edan_product_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text=product)] for product in EDAN_PRODUCTS] + [[KeyboardButton(text="Назад")]]
    )

def get_equipment_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text=eq)] for eq in EQUIPMENT_TYPES] + [[KeyboardButton(text="Назад")]]
    )

def get_yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text="Да")], [KeyboardButton(text="Нет")]]
    )

def get_action_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True,
        keyboard=[[KeyboardButton(text="Забираем картридж"), KeyboardButton(text="Добавляем картридж")]]
    )