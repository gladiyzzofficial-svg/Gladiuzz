import os
import re
import sqlite3
import datetime
from collections import defaultdict
from dotenv import load_dotenv
import telebot
from google import genai
from google.genai.types import GenerateContentConfig

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY не найден!")

bot = telebot.TeleBot(TOKEN)

# Жёсткая очистка
bot.delete_webhook(drop_pending_updates=True)
print("✅ Webhook успешно удалён")

# Получаем информацию о боте
BOT_INFO = bot.get_me()
BOT_USERNAME = BOT_INFO.username

# ====================== GEMINI ======================
print(f"🔑 GEMINI_API_KEY загружен: {'Да ✅' if GEMINI_API_KEY.startswith('AIzaSy') else 'НЕТ ❌'}")

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
        return "😔 Gemini сейчас недоступен. Попробуй позже."

# ====================== База и модерация ======================
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
    if not message.text:
        return False
    text = message.text.lower()
    spam_keywords = ['подработка', 'зарплата', 'выплаты', 'студентам', 'молодым', 'специалистам', 'график', 'постоянно', 'найму', 'продам']
    if any(kw in text for kw in spam_keywords):
        return True
    if re.search(r'http|www|\.ru|\.com|тг|канал|@', text):
        return True
    if len(text) > 180:
        return True
    return False

# ====================== ЕДИНЫЙ ОБРАБОТЧИК ======================
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text or ""

    # Модерация в группах
    if message.chat.type in ['group', 'supergroup']:
        if is_spam(message):
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            return

    # Gemini в личных сообщениях
    if message.chat.type == "private":
        if text.startswith('/start'):
            return bot.send_message(message.chat.id, "Привет! Я Gemini. Пиши любой вопрос 😊")
        
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(text)
        try:
            bot.edit_message_text(response, message.chat.id, wait.message_id)
        except:
            pass

    # Gemini в группе
    elif message.chat.type in ['group', 'supergroup']:
        if f"@{BOT_USERNAME}" in text or any(cmd in text.lower() for cmd in ['/gemini', '/ai', '/ask']):
            clean_text = re.sub(r'^/(gemini|ai|ask)\s*', '', text).replace(f"@{BOT_USERNAME}", "").strip()
            if clean_text:
                wait = bot.reply_to(message, "💭 Думаю...")
                response = get_gemini_response(clean_text)
                try:
                    bot.edit_message_text(response, message.chat.id, wait.message_id)
                except:
                    pass


print(f"✅ Бот @{BOT_USERNAME} с Gemini успешно запущен!")
bot.infinity_polling()
