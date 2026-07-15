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

# Админы
ADMINS = [1009623720, 6296059302]

# Инициализация плохих слов (добавляй сюда)
bad_words_list = []  # ← добавляй мат сюда

for word in bad_words_list:
    cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word.lower(),))

conn.commit()

warnings = defaultdict(int)


def is_spam(message):
    if not message.text:
        return False
    text = message.text.lower()

    # Ключевые слова спама
    spam_keywords = ['подработка', 'зарплата', 'выплаты', 'студентам', 'молодым', 
                     'специалистам', 'график', 'постоянно', 'найму', 'продам']
    
    if any(kw in text for kw in spam_keywords):
        return True
    
    # Ссылки, телеграм-каналы и т.д.
    if re.search(r'http|www|\.ru|\.com|тг|канал|@', text):
        return True
    
    if message.from_user.is_bot:
        return True
    
    if len(text) > 180:
        return True
    
    return False


@bot.message_handler(func=lambda m: True)
def moderate(message):
    user_id = message.from_user.id
    
    # Админы игнорируются
    if user_id in ADMINS:
        return
    
    if not message.text:
        return

    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name

    # Определяем причину
    if is_spam(message):
        warnings[user_id] += 2
        reason = "спам/реклама"
    else:
        # Проверка мата
        cursor.execute("SELECT word FROM bad_words")
        bad_words = [row[0] for row in cursor.fetchall()]
        
        if any(word in text_lower for word in bad_words):
            warnings[user_id] += 1
            reason = "мат"
        else:
            return  # ничего плохого не нашли

    # Применяем наказание
    if warnings[user_id] >= 2:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.ban_chat_member(message.chat.id, user_id)
            
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute("INSERT INTO bans (user_id, username, reason, date) VALUES (?, ?, ?, ?)",
                         (user_id, username, reason, date))
            conn.commit()
            
            bot.send_message(message.chat.id, f"🚫 {username} забанен ({reason}).")
            del warnings[user_id]
        except:
            pass
    else:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id,
                f"⚠️ Предупреждение {warnings[user_id]}/2 для {username}.\n"
                f"Не используй мат и спам.")
        except:
            pass


print("✅ Умный антиспам-бот запущен!")
bot.infinity_polling()
