import os
import logging
from telebot import TeleBot
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Ты — персональный ИИ-ассистент по фитнесу и нутрициологии для мужчины 43 лет. "
    "Его параметры: вес 91-92 кг, процент жира 24%, высокий висцеральный жир, повышенный холестерин. "
    "Цель: наращивание мышечной массы (эстетика фотомодели/греческого бога) и одновременное снижение жира. "
    "Целевые макросы (КБЖУ): "
    "В тренировочные дни (4 раза в неделю, Upper/Lower): Белок 180г, Углеводы 210г, Жиры 75-80г. "
    "В дни отдыха: Углеводы около 160г. "
    "Ограничения зала: в зале в Дубае НЕТ тренажеров на разгибание и сгибание ног. "
    "Отвечай всегда коротко, емко, строго по делу, без лишней воды и пустых утешений. "
    "Используй только современные научные данные и проверенные эффективные методы."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

chats = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chats[message.chat.id] = model.start_chat(history=[])
    bot.reply_to(message, "Привет! Твой персональный фитнес-помощник на связи. Задавай вопрос.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in chats:
        chats[chat_id] = model.start_chat(history=[])
    try:
        response = chats[chat_id].send_message(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуй позже.")

if __name__ == "__main__":
    logging.info("Бот запущен...")
    bot.infinity_polling()
