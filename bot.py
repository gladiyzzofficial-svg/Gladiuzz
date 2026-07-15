import telebot
import sqlite3

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"

bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')

# Добавляем первого админа, если никого нет
cursor.execute("SELECT COUNT(*) FROM admins")
if cursor.fetchone()[0] == 0:
    admin_ids = [6296859382, 1009623720]  # ← твои ID
    for user_id in admin_ids:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    print(f"Добавлено {len(admin_ids)} администраторов")

conn.commit()

def get_bad_words():
    cursor.execute("SELECT word FROM bad_words")
    return [row[0] for row in cursor.fetchall()]

def get_admins():
    cursor.execute("SELECT user_id FROM admins")
    return [row[0] for row in cursor.fetchall()]

# ===================== МОДЕРАЦИЯ =====================
@bot.message_handler(func=lambda m: True)
def moderate(message):
    if not message.text:
        return
    text = message.text.lower()
    bad_words = get_bad_words()
    
    for word in bad_words:
        if word in text:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                bot.send_message(message.chat.id, f"🚫 {message.from_user.first_name} забанен за мат.")
            except:
                pass
            return

# ===================== КОМАНДЫ АДМИНОВ =====================
@bot.message_handler(commands=['addword'])
def add_word(message):
    if message.from_user.id not in get_admins():
        return
    try:
        word = message.text.split(maxsplit=1)[1].strip().lower()
        cursor.execute("INSERT INTO bad_words (word) VALUES (?)", (word,))
        conn.commit()
        bot.reply_to(message, f"✅ Слово '{word}' добавлено в чёрный список.")
    except:
        bot.reply_to(message, "❌ Слово уже существует или ошибка.")

@bot.message_handler(commands=['delword'])
def del_word(message):
    if message.from_user.id not in get_admins():
        return
    try:
        word = message.text.split(maxsplit=1)[1].strip().lower()
        cursor.execute("DELETE FROM bad_words WHERE word = ?", (word,))
        conn.commit()
        bot.reply_to(message, f"✅ Слово '{word}' удалено из чёрного списка.")
    except:
        bot.reply_to(message, "Использование: /delword слово")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if message.from_user.id not in get_admins():
        return
    try:
        new_id = int(message.text.split()[-1])
        cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (new_id,))
        conn.commit()
        bot.reply_to(message, f"✅ Пользователь {new_id} добавлен в администраторы бота.")
    except:
        bot.reply_to(message, "Использование: /addadmin 123456789")

@bot.message_handler(commands=['banlist'])
def banlist(message):
    if message.from_user.id not in get_admins():
        return
    words = get_bad_words()
    text = "📋 Чёрный список:\n" + "\n".join(words) if words else "Список пуст."
    bot.reply_to(message, text)

print("✅ Бот с базой данных и командами запущен!")
bot.infinity_polling()
