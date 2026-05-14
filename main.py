import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Твой адрес на Render
RENDER_EXTERNAL_URL = "https://kbzhubot.onrender.com"

bot = TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GEMINI_API_KEY)

# Настройка модели Gemini
SYSTEM_INSTRUCTION = (
    "Ты — персональный ИИ-ассистент по фитнесу и нутрициологии для мужчины 43 лет. "
    "Его параметры: вес 92 кг, рост 187 см. Цель: эстетика, КБЖУ 180/210/80. "
    "Отвечай коротко и по делу."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# Функция установки вебхука
def set_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")

# Ставим вебхук сразу при импорте/запуске файла
set_webhook()

@app.route('/')
def home():
    return "Бот активен"

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
    bot.reply_to(message, "Привет! Присылай фото еды или задавай вопрос по тренировкам.")

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            contents = [{"mime_type": "image/jpeg", "data": downloaded_file}, "Проанализируй КБЖУ этого блюда."]
            response = model.generate_content(contents)
            bot.reply_to(message, response.text)
        else:
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

if __name__ == "__main__":
    # Для локального запуска
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    