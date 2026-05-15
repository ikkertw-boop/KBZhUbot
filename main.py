import os
import logging
from flask import Flask, request
import telebot
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

# Настройка Gemini - используем стабильный API
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Ты — профессиональный фитнес-ассистент. 
Твой клиент: Мужчина, 43 года, 187 см, 92 кг (жир 24%).
Цель: греческий бог / фотомодель (рекомпозиция: мышцы вверх, висцеральный жир вниз).
КБЖУ: Белок 180г, Углеводы 210г (в дни отдыха 160г), Жиры 80г.
Контекст зала в Дубае: нет тренажеров на разгибание/сгибание ног.
ПРАВИЛА: Отвечай очень коротко, только факты, без воды. Говори правду.
При анализе еды по фото — давай примерную оценку КБЖУ.
"""

# Используем полный путь к модели, чтобы избежать ошибки 404 (v1beta)
model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        bot.reply_to(message, "Ошибка ИИ. Попробуй позже.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.reply_to(message, "Анализирую фото...")
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_parts = [{"mime_type": "image/jpeg", "data": downloaded_file}]
        
        # Промпт для фото
        prompt = "Что на этом фото? Оцени КБЖУ, если это еда. Коротко."
        response = model.generate_content([prompt, image_parts[0]])
        
        bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка при анализе фото: {e}")
        bot.reply_to(message, "Не удалось прочитать фото.")

def init_webhook():
    try:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        bot.remove_webhook()
        bot.set_webhook(url=f"{base_url}/{TELEGRAM_TOKEN}")
        logging.info("Вебхук успешно установлен")
    except Exception as e:
        logging.error(f"Ошибка установки вебхука: {e}")

# ИСПРАВЛЕНИЕ: Вызываем установку вебхука напрямую, так как before_first_request удален в Flask 2.3+
if __name__ == "__main__":
    init_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    # Для запуска через Gunicorn на Render
    init_webhook()
    