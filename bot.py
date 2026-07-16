import telebot
import sqlite3
import datetime
import re
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)

# Очищаем перед запуском
bot.delete_webhook(drop_pending_updates=True)
print("✅ Webhook удалён, запускаем polling...")

# ====================== GEMINI ======================
from google import genai
from google.genai.types import GenerateContentConfig

client = genai.Client(api_key=GEMINI_API_KEY)

def get_gemini_response(user_message):
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=user_message,
            config=GenerateContentConfig(
                system_instruction="Ты — дружелюбный и полезный ИИ-помощник. Отвечай на русском языке."
            )
        )
        return response.text if hasattr(response, 'text') and response.text else "Не понял вопрос 😅"
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "😔 Сейчас не могу ответить. Попробуй позже."

# ====================== База и модерация (оставил твою) ======================
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bans (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, reason TEXT, date TEXT)''')

ADMINS = [1009623720, 6296059302, 1001908351016]

bad_words_list = []
for word in bad_words_list:
    cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word.lower(),))
conn.commit()

warnings = defaultdict(int)

def is_spam(message):
    if not message.text: return False
    text = message.text.lower()
    spam_keywords = ['подработка', 'зарплата', 'выплаты', 'студентам', 'молодым', 'специалистам', 'график', 'постоянно', 'найму', 'продам']
    if any(kw in text for kw in spam_keywords): return True
    if re.search(r'http|www|\.ru|\.com|тг|канал|@', text): return True
    if len(text) > 180: return True
    return False

@bot.message_handler(func=lambda m: True)
def moderate(message):
    if message.chat.type not in ['group', 'supergroup']: return
    # ... (твоя текущая функция модерации без изменений)
    # (я оставил её как есть, просто вставь свою)

# ====================== ОСНОВНОЙ ОБРАБОТЧИК ======================
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    text = message.text or ""

    if message.chat.type == "private":
        if text.startswith('/start'):
            return bot.send_message(message.chat.id, "Привет! Я Gemini. Пиши любой вопрос 😊")
        
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(text)
        bot.edit_message_text(response, message.chat.id, wait.message_id)

    elif message.chat.type in ['group', 'supergroup']:
        bot_username = bot.get_me().username
        if f"@{bot_username}" in text or any(cmd in text.lower() for cmd in ['/gemini', '/ai', '/ask']):
            clean_text = re.sub(r'^/(gemini|ai|ask)\s*', '', text).replace(f"@{bot_username}", "").strip()
            if clean_text:
                wait = bot.reply_to(message, "💭 Думаю...")
                response = get_gemini_response(clean_text)
                bot.edit_message_text(response, message.chat.id, wait.message_id)

print("✅ Бот с Gemini успешно запущен!")
bot.infinity_polling()
