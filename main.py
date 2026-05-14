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

# Инструкция
SYSTEM_INSTRUCTION = (
    "Ты — персональный ИИ-ассистент по фитнесу для мужчины 43 лет. Вес 92 кг, рост 187 см. "
    "Цель: КБЖУ 180/210/80. Отвечай коротко, без воды."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# Принудительная установка вебхука при старте
with app.app_context():
    webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")

@app.route('/')
def home():
    return "Bot is alive", 200

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Система запущена. Жду данные (текст или фото).")

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    try:
        if message.content_type == 'photo':
            logging.info("Обработка фото...")
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            contents = [{"mime_type": "image/jpeg", "data": downloaded_file}, "Оцени КБЖУ."]
            response = model.generate_content(contents)
            bot.reply_to(message, response.text)
        else:
            logging.info(f"Обработка текста: {message.text}")
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        bot.reply_to(message, "Ошибка в ИИ-модуле. Попробуй позже.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    