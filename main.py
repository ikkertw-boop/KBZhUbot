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

# Хранилище истории: {chat_id: [список сообщений для Gemini]}
history_storage = {}

def get_history(chat_id):
    if chat_id not in history_storage:
        history_storage[chat_id] = []
    return history_storage[chat_id]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    history_storage[message.chat.id] = []  # Очищаем историю при старте
    bot.reply_to(message, "Привет! Твой персональный фитнес-помощник на связи. Задавай вопрос или скидывай фото еды.")

# Обработчик и для ТЕКСТА, и для ФОТО
@bot.message_handler(content_types=['text', 'photo'])
def handle_user_content(message):
    chat_id = message.chat.id
    history = get_history(chat_id)
    
    try:
        # Если пришло фото
        if message.content_types == 'photo' or message.photo:
            # Берем лучшее качество фото
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Подпись к фото, если она есть
            caption = message.caption if message.caption else "Что на этом фото и каков примерный состав КБЖУ?"
            
            contents = [
                {"mime_type": "image/jpeg", "data": downloaded_file},
                caption
            ]
            
            # Фото не пишем в историю чата, чтобы не перегружать контекст, отправляем напрямую
            response = model.generate_content(contents)
            bot.reply_to(message, response.text)
            return

        # Если пришел текст
        if message.text:
            # Добавляем сообщение пользователя в историю
            history.append({"role": "user", "parts": [message.text]})
            
            # Запрос к модели с учетом истории
            response = model.generate_content(history)
            
            # Добавляем ответ модели в историю
            history.append({"role": "model", "parts": [response.text]})
            
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"Ошибка при обработке: {e}")
        bot.reply_to(message, "Произошла ошибка при анализе. Попробуй еще раз.")

if __name__ == "__main__":
    logging.info("Бот запущен...")
    bot.infinity_polling()
    