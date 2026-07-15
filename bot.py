import telebot
import sqlite3
import re

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')

# Слова для бана (добавляй сюда)
bad_words_list = ["бля", "сука", "хуй", "пизд", "еб", "муд", "нахуй", "гандон", "еблан"]

for word in bad_words_list:
    cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word.lower(),))
conn.commit()

def is_spam(message):
    text = (message.text or "").lower()
    # Признаки спама / рекламы
    if re.search(r'http|www|\.ru|\.com|тг|канал|реклама|найм|работа|зарплата|найму|продам', text):
        return True
    if len(text) > 150:  # длинные сообщения
        return True
    if message.from_user.is_bot:  # если сообщение от бота
        return True
    return False

@bot.message_handler(func=lambda m: True)
def moderate(message):
    if not message.text:
        return
    
    text_lower = message.text.lower()
    
    # Проверяем на спам/рекламу
    if is_spam(message):
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.ban_chat_member(message.chat.id, message.from_user.id)
            bot.send_message(message.chat.id, f"🚫 Спам/реклама от {message.from_user.first_name} — забанен.")
        except:
            pass
        return

    # Проверяем мат (только если не спам)
    cursor.execute("SELECT word FROM bad_words")
    bad_words = [row[0] for row in cursor.fetchall()]
    
    for word in bad_words:
        if word in text_lower and len(word) > 2:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                bot.send_message(message.chat.id, f"🚫 {message.from_user.first_name} забанен за мат.")
            except:
                pass
            return

print("✅ Бот с фильтром спама запущен!")
bot.infinity_polling()
