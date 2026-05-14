import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

# ---------------- НАСТРОЙКИ ЛОГОВ ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Проверка наличия ключей
if not all([TELEGRAM_TOKEN, GEMINI_API_KEY, RENDER_EXTERNAL_URL]):
    logging.error("ОШИБКА: Не все переменные окружения (TOKEN, KEY, URL) заданы в Render!")

# ---------------- ИНИЦИАЛИЗАЦИЯ ----------------
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GEMINI_API_KEY)

# Инструкция для ИИ (твои параметры из профиля)
SYSTEM_INSTRUCTION = """
Ты — фитнес ИИ-ассистент. 
Пользователь: Мужчина, 43 года, 187 см, 92 кг. 
Цель: Рекомпозиция. КБЖУ: 180/210/80.
Отвечай кратко, профессионально и только по делу.
"""

# Используем модель 1.5 Flash (у нее больше бесплатных лимитов)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# ---------------- ВЕБХУК ----------------
def init_webhook():
    """Установка связи между Telegram и сервером Render"""
    try:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")
    except Exception as e:
        logging.error(f"ОШИБКА ВЕБХУКА: {e}")

# Запуск установки вебхука
init_webhook()

# ---------------- РОУТЫ ----------------
@app.route("/")
def home():
    return "Бот работает", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    abort(403)

# ---------------- ОБРАБОТКА СООБЩЕНИЙ ----------------
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Бот КБЖУ готов. Пришли текст или фото еды.")

@bot.message_handler(content_types=["text", "photo"])
def handle_all(message):
    try:
        if message.content_type == "photo":
            # 1. Показываем пользователю, что начали работу
            wait_msg = bot.reply_to(message, "Анализирую фото...")
            
            # 2. Скачиваем фото из Telegram
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # 3. Формируем запрос к Gemini
            prompt = message.caption if message.caption else "Оцени КБЖУ этого блюда."
            
            # Важно: используем стабильный формат передачи картинки
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": downloaded_file}
            ])
            
            # 4. Удаляем временное сообщение и шлем ответ
            bot.delete_message(message.chat.id, wait_msg.message_id)
            bot.reply_to(message, response.text)
            
        elif message.content_type == "text":
            # Обработка обычного текста
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"ОШИБКА GEMINI: {e}")
        bot.reply_to(message, "Произошла ошибка при обращении к ИИ. Попробуй позже.")

# ---------------- ЗАПУСК ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    