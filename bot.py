import telebot
import sqlite3
import datetime
import re
from collections import defaultdict

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"
bot = telebot.TeleBot(TOKEN)

# Подключение к базе
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bans (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, reason TEXT, date TEXT)''')

# ==================== НАСТРОЙКИ ====================
ADMINS = [1009623720, 6296059302,1001908351016]  # ← Добавь сюда ID своего канала (начинается с -100...)

# Инициализация плохих слов
bad_words_list = []  # Добавляй мат сюда, например: ["бля", "сука", ...]

for word in bad_words_list:
    cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word.lower(),))

conn.commit()

warnings = defaultdict(int)


def is_spam(message):
    if not message.text:
        return False
    text = message.text.lower()

    spam_keywords = ['подработка', 'зарплата', 'выплаты', 'студентам', 'молодым', 
                     'специалистам', 'график', 'постоянно', 'найму', 'продам']
    
    if any(kw in text for kw in spam_keywords):
        return True
    
    if re.search(r'http|www|\.ru|\.com|тг|канал|@', text):
        return True
    
    if len(text) > 180:
        return True
    return False


# ====================== ОСНОВНАЯ МОДЕРАЦИЯ ======================
@bot.message_handler(func=lambda m: True)
def moderate(message):
    # Получаем ID отправителя и ID канала (если пишут от имени сообщества)
    user_id = message.from_user.id if message.from_user else None
    channel_id = message.sender_chat.id if message.sender_chat else None

    # Пропускаем админов и сообщения от канала
    if (user_id in ADMINS) or (channel_id in ADMINS):
        return

    if message.from_user and message.from_user.is_bot:
        return

    if not message.text:
        return

    text_lower = message.text.lower()
    username = (message.from_user.username or message.from_user.first_name 
                if message.from_user else "Канал")

    # Определяем нарушение
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

    # Применяем наказание
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
            bot.send_message(message.chat.id,
                f"⚠️ Предупреждение {warnings[target_id]}/2 — {username}")
        except:
            pass


# ====================== КОМАНДА ДЛЯ ПРОСМОТРА ИСТОРИИ ======================
@bot.message_handler(commands=['banlist'])
def ban_list(message):
    if message.from_user.id not in ADMINS:
        return
    
    cursor.execute("SELECT username, reason, date FROM bans ORDER BY id DESC LIMIT 50")
    bans = cursor.fetchall()
    
    if not bans:
        bot.send_message(message.chat.id, "📭 История банов пока пуста.")
        return

    text = "📜 **Последние баны (до 50):**\n\n"
    for username, reason, date in bans:
        text += f"• {username}\n  └ {reason} | {date}\n\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")


print("✅ Бот с историей банов запущен!")
bot.infinity_polling()
