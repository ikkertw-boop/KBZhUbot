import os
import logging
from flask import Flask, request, abort

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/debug')
def debug():
    try:
        from telebot import TeleBot
        import google.generativeai as genai
        
        token = os.environ.get("TELEGRAM_TOKEN", "НЕТУ")
        gemini = os.environ.get("GEMINI_API_KEY", "НЕТУ")
        
        bot = TeleBot(token, threaded=False)
        genai.configure(api_key=gemini)
        
        return f"OK. Token: {token[:8]}... Gemini: {gemini[:8]}..."
    except Exception as e:
        return f"ОШИБКА: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)