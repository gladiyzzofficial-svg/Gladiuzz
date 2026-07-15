import telebot
import sqlite3

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"

bot = telebot.TeleBot(TOKEN)

# ================== БАЗА ДАННЫХ ==================
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')

# === ТВОИ АДМИНЫ ===
admin_ids = [1009623720, 6296059302]   # ← твои ID

for uid in admin_ids:
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))

# === СЛОВА ДЛЯ БАНА (добавляй сюда) ===
bad_words_list = [
    "Халтура без опыта. 4 человека на завтра. Заплачу 7300 в день. Могу взять работать постоянно. Возможны авансы. Вопросы в ЛС!", "сука", "хуй", "пизд", "еб", "муд", "нахуй", 
    "гандон", "еблан", "pidor", "fuck", "shit", "тварь", 
    "мразь", "урод", "дебил", "идиот", "руина"
]

for word in bad_words_list:
    cursor.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word.lower(),))

conn.commit()

# =================================================

@bot.message_handler(func=lambda m: True)
def moderate(message):
    if not message.text:
        return
    text = message.text.lower()
    
    cursor.execute("SELECT word FROM bad_words")
    bad_words = [row[0] for row in cursor.fetchall()]
    
    for word in bad_words:
        if word in text:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                bot.send_message(message.chat.id, f"🚫 {message.from_user.first_name} забанен за мат.")
            except:
                pass
            return

print("✅ Бот запущен с админами и базой данных!")
bot.infinity_polling()
