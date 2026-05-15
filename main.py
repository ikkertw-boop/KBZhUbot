import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- ENV ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# ---------------- TELEGRAM ----------------
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# ---------------- GEMINI SETUP ----------------
genai.configure(api_key=GEMINI_API_KEY)

# Логируем доступные модели (поможет, если 404 повторится)
try:
    logging.info("Доступные модели:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            logging.info(f"Модель: {m.name}")
except Exception as e:
    logging.error(f"Не удалось получить список моделей: {e}")

SYSTEM_INSTRUCTION = """
Ты — фитнес ИИ-ассистент. 
Параметры пользователя: Мужчина, 43 года, Рост 187 см, Вес 92 кг.
Цель: рекомпозиция. КБЖУ: 180/210/80.
Отвечай коротко, по делу.
"""

# Инициализация модели
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Используем стандартное имя
    system_instruction=SYSTEM_INSTRUCTION
)

# ---------------- FLASK ----------------
app = Flask(__name__)

def init_webhook():
    try:
        if RENDER_EXTERNAL_URL:
            base_url = RENDER_EXTERNAL_URL.rstrip('/')
            webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")
    except Exception as e:
        logging.error(f"Ошибка вебхука: {e}")

init_webhook()

@app.route("/")
def home():
    return "Bot status: OK", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    abort(403)

# ---------------- HANDLERS ----------------
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Бот готов к работе.")

@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    try:
        if message.content_type == "photo":
            wait_msg = bot.reply_to(message, "Анализирую фото...")
            
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            prompt = message.caption if message.caption else "Оцени КБЖУ."
            
            # Стабильный формат запроса
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": downloaded_file}
            ])
            
            bot.delete_message(message.chat.id, wait_msg.message_id)
            bot.reply_to(message, response.text)

        elif message.content_type == "text":
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"GEMINI ERROR: {e}")
        bot.reply_to(message, "Ошибка связи с ИИ. Попробуй еще раз.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    