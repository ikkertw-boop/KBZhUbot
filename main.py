import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = "https://kbzhubot.onrender.com"

bot = TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GEMINI_API_KEY)

# Настройка модели
SYSTEM_INSTRUCTION = "Ты — персональный ИИ-ассистент по фитнесу... (сократил для краткости, оставь свою версию)"
model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

history_storage = {}

app = Flask(__name__)

# СРАЗУ ПРИ ЗАПУСКЕ СТАВИМ ВЕБХУК
webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
bot.remove_webhook()
bot.set_webhook(url=webhook_url)
logging.info(f"ВЕБХУК УСТАНОВЛЕН ПРИ СТАРТЕ: {webhook_url}")

@app.route('/')
def home():
    return "Бот работает!"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я готов.")

@bot.message_handler(content_types=['text', 'photo'])
def handle_user_content(message):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            response = model.generate_content([{"mime_type": "image/jpeg", "data": downloaded_file}, "Что тут?"])
            bot.reply_to(message, response.text)
        else:
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    