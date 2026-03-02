import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI

import os  # Импортируем модуль для работы с системой
import logging

from dotenv import load_dotenv  # Добавь эту строку
load_dotenv()  # И эту — она загрузит данные из файла .env в систему

# --- НАСТРОЙКИ (ТЕПЕРЬ БЕРЕМ ИЗ СИСТЕМЫ) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) 
# ------------------------------------------

# Инициализация ИИ (через OpenRouter)
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Настройка бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
user_histories = {} # Память диалогов

SYSTEM_PROMPT = (
    "Ты — Максим, экспертный менеджер студии детейлинга 'Black Gloss'. "
    "Ты фанат авто. Твоя цель: консультировать по услугам (керамика от 20к, пленка от 50к, химчистка от 10к) "
    "и брать номер телефона для записи на осмотр. "
    "ВАЖНО: Общайся на том языке, на котором пишет клиент (RU, EN, KZ, UZ и др.). "
    "Будь профессионалом, используй авто-сленг. Если клиент готов, проси номер телефона. "
    "Никогда не признавайся, что ты ИИ."
)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_histories[message.from_user.id] = [] # Сброс истории
    await message.answer("Привет! Я Максим из 'Black Gloss'. Какая у вас машина? Чем могу помочь?")

@dp.message()
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    # 1. Проверка на номер телефона (регулярка)
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}', user_text)
    if phone_match:
        await bot.send_message(ADMIN_ID, f"🚀 НОВАЯ ЗАЯВКА!\nКлиент: @{message.from_user.username}\nТекст: {user_text}")

    # 2. Работа с памятью
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({"role": "user", "content": user_text})
    user_histories[user_id] = user_histories[user_id][-10:] # Помним только 10 сообщений

    # 3. Запрос к ИИ
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
    
    try:
        response = await client.chat.completions.create(
            model="arcee-ai/trinity-large-preview:free",
            messages=messages
        )
        ai_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": ai_reply})
        await message.answer(ai_reply)
    except Exception as e:
        logging.error(e)
        await message.answer("Извините, небольшие технические неполадки. Попробуйте чуть позже!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())