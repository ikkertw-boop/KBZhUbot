import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GEMINI_API_KEY)

# Инструкция с твоими актуальными параметрами
SYSTEM_INSTRUCTION = """
Ты — фитнес ИИ-ассистент. 
Мужчина, 43 года, 187 см, 92 кг. 
Цель: Рекомпозиция. КБЖУ: 180/210/80.
Отвечай коротко, по делу.
"""

# ИСПРАВЛЕНИЕ: Используем версию, к которой привязан твой ключ
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

def init_webhook():
    try:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        bot.remove_webhook()
        bot.set_webhook(url=f"{base_url}/{TELEGRAM_TOKEN}")
        logging.info("Вебхук установлен.")
    except Exception as e:
        logging.error(f"Ошибка вебхука: {e}")

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

@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    try:
        if message.content_type == "photo":
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            prompt = message.caption if message.caption else "Оцени КБЖУ."
            
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": downloaded_file}
            ])
            bot.reply_to(message, response.text)

        elif message.content_type == "text":
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"GEMINI ERROR: {e}")
        bot.reply_to(message, f"Ошибка ИИ: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    