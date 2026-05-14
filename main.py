import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# Настройка Gemini с явным указанием стабильной версии API
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Ты — фитнес ИИ-ассистент. Мужчина, 43 года, 92 кг, 187 см.
КБЖУ: 180/210/80. Отвечай максимально коротко.
"""

# Используем модель без префиксов версий API
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", 
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# --- WEBHOOK ---
def init_webhook():
    try:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"ВЕБХУК: {webhook_url}")
    except Exception as e:
        logging.error(f"Webhook error: {e}")

init_webhook()

@app.route("/")
def home():
    return "OK", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    abort(403)

# --- ОБРАБОТКА ---
@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    try:
        if message.content_type == "photo":
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Правильный формат для стабильной версии библиотеки
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": downloaded_file},
                "Оцени КБЖУ."
            ])
            bot.reply_to(message, response.text)
            
        else:
            # Генерация для текста
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        bot.reply_to(message, "Ошибка ИИ. Попробуй еще раз.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    