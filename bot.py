import telebot
import sqlite3
import datetime
import re
from collections import defaultdict
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"
GEMINI_API_KEY = os.getenv("AQ.Ab8RN6LHEVIRMrGugfGgUniYW9LTPaX6TD1ymPJeKT70Fw5LqQ")

bot = telebot.TeleBot(TOKEN)

# Удаляем webhook перед запуском polling
bot.delete_webhook(drop_pending_updates=True)
print("✅ Webhook удалён, запускаем polling...")

# ====================== Gemini ======================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',   # можно поменять на 'gemini-1.5-pro'
    system_instruction="Ты — дружелюбный и полезный ИИ-помощник. Отвечай на русском языке."
)

def get_gemini_response(user_message):
    try:
        chat = model.start_chat()
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "😔 Извини, сейчас не могу ответить. Попробуй позже."

# ====================== База данных ======================
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bans (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, reason TEXT, date TEXT)''')

ADMINS = [1009623720, 6296059302, 1001908351016]

# Инициализация плохих слов
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
    user_id = message.from_user.id if message.from_user else None
    channel_id = message.sender_chat.id if message.sender_chat else None

    if (user_id in ADMINS) or (channel_id in ADMINS):
        return
    if message.from_user and message.from_user.is_bot:
        return
    if not message.text:
        return

    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name if message.from_user else "Пользователь"

    if is_spam(message):
        warnings[user_id or channel_id] += 2
        reason = "спам/реклама"
    else:
        cursor.execute("SELECT word FROM bad_words")
        bad_words = [row[0] for row in cursor.fetchall()]
        if any(word in text_lower for word in bad_words):
            warnings[user_id or channel_id] += 1
            reason = "мат"
        else:
            return

    target_id = user_id or channel_id

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

# ====================== ОСНОВНОЙ ХЕНДЛЕР ======================
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    if message.chat.type in ['group', 'supergroup']:
        moderate(message)  # Сначала модерация

    user_id = message.from_user.id
    text = message.text or ""

    # Gemini в личке
    if message.chat.type == "private":
        if text.startswith('/start'):
            bot.send_message(message.chat.id, "Привет! Я Gemini. Задавай любой вопрос 😊")
            return
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(text)
        bot.edit_message_text(response, message.chat.id, wait.message_id)

    # Gemini в группе
    elif message.chat.type in ['group', 'supergroup']:
        bot_username = bot.get_me().username
        if f"@{bot_username}" in text or text.startswith(('/gemini', '/ai', '/ask')):
            clean_text = re.sub(r'^/(gemini|ai|ask)\s*', '', text).replace(f"@{bot_username}", "").strip()
            if not clean_text:
                return bot.reply_to(message, "Напиши вопрос после команды.")
            
            wait = bot.reply_to(message, "💭 Думаю...")
            response = get_gemini_response(clean_text)
            bot.edit_message_text(response, message.chat.id, wait.message_id)

# ====================== GEMINI AI ======================
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="Ты — дружелюбный ИИ-помощник. Отвечай коротко и по делу на русском."
)

def get_gemini_response(text):
    try:
        chat = gemini_model.start_chat()
        response = chat.send_message(text)
        return response.text
    except:
        return "😔 Сейчас не могу ответить. Попробуй позже."

# Обработчик для Gemini (добавляется отдельно)
@bot.message_handler(func=lambda m: True)
def gemini_handler(message):
    text = (message.text or "").lower().strip()
    bot_username = bot.get_me().username.lower()

    # В личных сообщениях — отвечаем почти на всё
    if message.chat.type == "private":
        if text in ['/start', '/help', 'старт', 'меню']:
            return  # пусть работает твоя основная команда
        if any(word in text for word in ['ии', 'ai', 'гемини', 'gemini', 'чат', 'вопрос']):
            wait = bot.send_message(message.chat.id, "💭 Пишу ответ...")
            response = get_gemini_response(message.text)
            bot.edit_message_text(response, message.chat.id, wait.message_id)

    # В группе — только по упоминанию
    elif message.chat.type in ['group', 'supergroup']:
        if f"@{bot_username}" in (message.text or "") or text.startswith(('/ai', '/gemini', '/ask')):
            clean = (message.text or "").replace(f"@{bot_username}", "").strip()
            clean = re.sub(r'^/(ai|gemini|ask)', '', clean).strip()
            if clean:
                wait = bot.reply_to(message, "💭 Думаю...")
                response = get_gemini_response(clean)
                bot.edit_message_text(response, message.chat.id, wait.message_id)

print("✅ Бот с Gemini запущен!")
bot.infinity_polling()
