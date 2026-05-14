import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Инициализация бота
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Ты — персональный фитнес ИИ-ассистент.
Данные: Мужчина, 43 года, Рост 187 см, Вес 92 кг.
Цель: рекомпозиция. КБЖУ: 180/210/80.
Отвечай коротко, по делу, без воды.
"""

# Используем базовое имя модели для автоматического выбора стабильной версии API
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# Установка вебхука при запуске приложения
def init_webhook():
    try:
        if RENDER_EXTERNAL_URL:
            base_url = RENDER_EXTERNAL_URL.rstrip('/')
            webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logging.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logging.error(f"Webhook setup error: {e}")

init_webhook()

@app.route("/")
def home():
    return "Bot is running", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    abort(403)

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Бот запущен. Отправь текст или фото еды.")

@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    try:
        if message.content_type == "photo":
            # Обработка фото
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            prompt = message.caption if message.caption else "Оцени КБЖУ блюда на фото."
            
            # Передаем данные напрямую в стабильном формате
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": downloaded_file}
            ])
            bot.reply_to(message, response.text)
            
        else:
            # Обработка текста
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        bot.reply_to(message, "Ошибка обработки запроса. Попробуй еще раз.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    