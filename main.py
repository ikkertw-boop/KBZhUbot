import os
import logging
from flask import Flask, request, abort
from telebot import TeleBot, types
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = "https://kbzhubot.onrender.com"

SYSTEM_INSTRUCTION = (
    "Ты — персональный ИИ-ассистент по фитнесу и нутрициологии для мужчины 43 лет. "
    "Его параметры: вес 91-92 кг, процент жира 24%, высокий висцеральный жир, повышенный холестерин. "
    "Цель: наращивание мышечной массы (эстетика фотомодели/греческого бога) и одновременное снижение жира. "
    "Целевые макросы (КБЖУ): "
    "В тренировочные дни (4 раза в неделю, Upper/Lower): Белок 180г, Углеводы 210г, Жиры 75-80г. "
    "В дни отдыха: Углеводы около 160г. "
    "Ограничения зала: в зале в Дубае НЕТ тренажеров на разгибание и сгибание ног. "
    "Отвечай всегда коротко, емко, строго по делу, без лишней воды и пустых утешений. "
    "Используй только современные научные данные и проверенные эффективные методы."
)

bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

history_storage = {}

def get_history(chat_id):
    if chat_id not in history_storage:
        history_storage[chat_id] = []
    return history_storage[chat_id]

app = Flask(__name__)

@app.route('/')
def home():
    webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logging.info(f"ВЕБХУК УСТАНОВЛЕН: {webhook_url}")
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

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    history_storage[message.chat.id] = []
    bot.reply_to(message, "Привет! Твой персональный фитнес-помощник на связи. Задавай вопрос или скидывай фото еды.")

@bot.message_handler(content_types=['text', 'photo'])
def handle_user_content(message):
    chat_id = message.chat.id
    history = get_history(chat_id)

    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            caption = message.caption if message.caption else "Что на этом фото и каков примерный состав КБЖУ?"
            contents = [
                {"mime_type": "image/jpeg", "data": downloaded_file},
                caption
            ]
            response = model.generate_content(contents)
            bot.reply_to(message, response.text)
            return

        if message.text:
            logging.info(f"Сообщение: {message.text}")
            history.append({"role": "user", "parts": [message.text]})
            response = model.generate_content(history)
            history.append({"role": "model", "parts": [response.text]})
            bot.reply_to(message, response.text)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.reply_to(message, "Ошибка. Попробуй ещё раз.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)