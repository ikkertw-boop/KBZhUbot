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

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found")

# ---------------- TELEGRAM ----------------
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# ---------------- GEMINI ----------------
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Ты — персональный фитнес ИИ-ассистент.

Данные пользователя:
- Мужчина
- 43 года
- Рост 187 см
- Вес 92 кг
- Цель: рекомпозиция тела
- КБЖУ: 180/210/80

Правила:
- Отвечай коротко
- Только по делу
- Без воды
- Практично
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Исправлено на 1.5 для бесплатного лимита
    system_instruction=SYSTEM_INSTRUCTION
)

# ---------------- FLASK ----------------
app = Flask(__name__)

# ---------------- WEBHOOK ----------------
def init_webhook():
    try:
        # Убираем слэш в конце ссылки, если он случайно есть в RENDER_EXTERNAL_URL
        base_url = RENDER_EXTERNAL_URL.rstrip('/') if RENDER_EXTERNAL_URL else ""
        webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"

        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)

        logging.info(f"Webhook установлен: {webhook_url}")

    except Exception as e:
        logging.error(f"Webhook error: {e}")

init_webhook()

# ---------------- ROUTES ----------------
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

# ---------------- COMMANDS ----------------
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Бот готов. Отправь текст или фото еды."
    )

# ---------------- TEXT + PHOTO ----------------
@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    try:
        # ---------- PHOTO ----------
        if message.content_type == "photo":
            wait_msg = bot.reply_to(message, "Анализирую фото...")
            
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            prompt = (
                message.caption
                if message.caption
                else "Оцени блюдо и примерно посчитай КБЖУ."
            )
            
            response = model.generate_content(
                [
                    prompt,
                    {
                        "mime_type": "image/jpeg",
                        "data": downloaded_file
                    }
                ]
            )
            
            bot.delete_message(message.chat.id, wait_msg.message_id)
            bot.reply_to(message, response.text)

        # ---------- TEXT ----------
        elif message.content_type == "text":
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"ERROR: {e}")
        bot.reply_to(
            message,
            "Ошибка обработки. Попробуй ещё раз."
        )

# ---------------- START ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    