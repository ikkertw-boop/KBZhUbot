import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO)

# Загрузка ключей из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = "https://kbzhubot.onrender.com"

# Инициализация бота и ИИ
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)
genai.configure(api_key=GEMINI_API_KEY)

# Инструкция: строгие параметры пользователя
SYSTEM_INSTRUCTION = (
    "Ты — персональный ИИ-ассистент по фитнесу и нутрициологии для мужчины 43 лет. "
    "Параметры: вес 92 кг, рост 187 см, процент жира 24%, высокий висцеральный жир. "
    "Цель: мышечная масса + снижение жира. "
    "КБЖУ: Белок 180г, Углеводы 210г (160г в отдых), Жиры 80г. "
    "Зал в Дубае: НЕТ тренажеров на разгибание/сгибание ног. "
    "Отвечай максимально коротко, емко, только факты, без воды."
)

# Используем актуальное имя модели
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

app = Flask(__name__)

# --- Настройка вебхука ---
@app.before_first_request
def setup_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")

@app.route('/')
def home():
    return "Bot is running...", 200

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

# --- Обработка команд ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот готов. Присылай фото еды или задавай вопрос.")

# --- Основная логика ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
    try:
        if message.content_type == 'photo':
            logging.info("Получено фото. Начинаю анализ...")
            
            # Получаем файл
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Подготовка для Gemini
            prompt = message.caption if message.caption else "Оцени КБЖУ этого блюда."
            image_parts = [
                {"mime_type": "image/jpeg", "data": downloaded_file}
            ]
            
            # Генерация ответа (модель ожидает список: текст + картинка)
            response = model.generate_content([prompt, image_parts[0]])
            bot.reply_to(message, response.text)
            
        elif message.content_type == 'text':
            logging.info(f"Получен текст: {message.text}")
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        bot.reply_to(message, "Ошибка обработки. Попробуй еще раз.")

# --- Запуск ---
if __name__ == "__main__":
    # Render передает PORT автоматически
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    