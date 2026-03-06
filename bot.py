import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command

# ВСТАВЬ СЮДА СВОЙ ТОКЕН ОТ BOTFATHER
TOKEN = "8698388173:AAFrWmLuN91hIWHmy-9l7JLhmQX46fiJdbI"  # Замени на свой токен!

# ВСТАВЬ СЮДА СВОЮ ССЫЛКУ С GITHUB PAGES
WEB_APP_URL = "https://suguru4252.github.io/telegram-clicker/"  # Замени на свою ссылку!

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот с кликером.\n"
        "Нажми кнопку ниже, чтобы начать игру!"
    )

# Команда /play - открывает кликер
@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    # Создаем кнопку с Web App
    web_app_button = KeyboardButton(
        text="🎮 Играть в кликер",
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    
    # Создаем клавиатуру с этой кнопкой
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[web_app_button]],
        resize_keyboard=True
    )
    
    await message.answer(
        "Нажми кнопку ниже, чтобы открыть кликер:",
        reply_markup=keyboard
    )

# Запуск бота
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
