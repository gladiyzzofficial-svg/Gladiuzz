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

# Удаляем webhook
bot.delete_webhook(drop_pending_updates=True)
print("✅ Webhook удалён, запускаем polling...")

# ====================== GEMINI AI ======================
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

# ====================== База данных ======================
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

# ====================== МОДЕРАЦИЯ ======================
@bot.message_handler(func=lambda m: True)
def moderate(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    user_id = message.from_user.id if message.from_user else None
    if user_id in ADMINS or (message.sender_chat and message.sender_chat.id in ADMINS):
        return
    if message.from_user and message.from_user.is_bot:
        return
    if not message.text:
        return

    # ... (твоя логика модерации остаётся без изменений)
    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name if message.from_user else "Пользователь"

    if is_spam(message):
        warnings[user_id] += 2
        reason = "спам/реклама"
    else:
        cursor.execute("SELECT word FROM bad_words")
        bad_words = [row[0] for row in cursor.fetchall()]
        if any(word in text_lower for word in bad_words):
            warnings[user_id] += 1
            reason = "мат"
        else:
            return

    # ... (остальная часть модерации)
    target_id = user_id
    if warnings[target_id] >= 2:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.ban_chat_member(message.chat.id, target_id)
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute("INSERT INTO bans (user_id, username, reason, date) VALUES (?, ?, ?, ?)",
                         (target_id, username, reason, date))
            conn.commit()
            bot.send_message(message.chat.id, f"🚫 {username} забанен ({reason}).")
            del warnings[target_id]
        except:
            pass
    else:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, f"⚠️ Предупреждение {warnings[target_id]}/2 — {username}")
        except:
            pass

# ====================== GEMINI ОБРАБОТЧИК ======================
@bot.message_handler(func=lambda message: True)
def gemini_handler(message):
    if message.chat.type != "private":
        return  # Пока только в личке

    text = (message.text or "").strip().lower()

    # Пропускаем команды меню
    if text in ['/start', '/help', 'старт', 'меню', 'привет', 'бот'] or len(text) < 3:
        return  # пусть работает твоя основная логика

    # Если человек явно хочет ИИ
    if any(word in text for word in ['ии', 'gemini', 'ai', 'гемини', 'чат', 'вопрос', 'расскажи', 'что ты', 'шутк']):
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(message.text)
        bot.edit_message_text(response, message.chat.id, wait.message_id)
    else:
        # Можно сделать, чтобы отвечал на всё в личке
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(message.text)
        bot.edit_message_text(response, message.chat.id, wait.message_id)


print("✅ Бот с Gemini запущен!")
bot.infinity_polling()
