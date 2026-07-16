import os
import re
import sqlite3
import datetime
from collections import defaultdict
from dotenv import load_dotenv
import telebot
from google import genai
from google.genai.types import GenerateContentConfig

# Загружаем переменные окружения
load_dotenv()

# Рекомендуется перенести токен в .env (например, TELEGRAM_TOKEN)
# Сейчас оставим переменную, но лучше загружать её через os.getenv
TOKEN = os.getenv("TELEGRAM_TOKEN") or "8640562446:AAF4_DDjpAv6ADTdPNwSO6L5jw6tkejckc4"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)

# Очищаем перед запуском
bot.delete_webhook(drop_pending_updates=True)
print("✅ Webhook удалён, запускаем polling...")

# Получаем юзернейм бота один раз при старте, чтобы не перегружать API
BOT_INFO = bot.get_me()
BOT_USERNAME = BOT_INFO.username

# ====================== GEMINI ======================
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

# ====================== ЕДИНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ======================
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text or ""

    # --- ЧАСТЬ 1: Модерация (только для групп и супергрупп) ---
    if message.chat.type in ['group', 'supergroup']:
        # Выполняем проверку на спам
        if is_spam(message):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                # Здесь можно добавить выдачу предупреждения или бан
            except Exception as e:
                print(f"Ошибка при удалении спама: {e}")
            return # Прерываем выполнение, чтобы спам-сообщение не обрабатывалось ИИ

        # Сюда вы можете вставить вашу остальную логику модерации
        # (например, проверку на запрещенные слова bad_words)

    # --- ЧАСТЬ 2: Общение с Gemini ИИ ---
    # Личные сообщения
    if message.chat.type == "private":
        if text.startswith('/start'):
            return bot.send_message(message.chat.id, "Привет! Я Gemini. Пиши любой вопрос 😊")
        
        wait = bot.send_message(message.chat.id, "💭 Думаю...")
        response = get_gemini_response(text)
        try:
            bot.edit_message_text(response, message.chat.id, wait.message_id)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

    # Групповые чаты (ответ на команду или упоминание бота)
    elif message.chat.type in ['group', 'supergroup']:
        if f"@{BOT_USERNAME}" in text or any(cmd in text.lower() for cmd in ['/gemini', '/ai', '/ask']):
            # Очищаем текст сообщения от команд и юзернейма бота
            clean_text = re.sub(r'^/(gemini|ai|ask)\s*', '', text).replace(f"@{BOT_USERNAME}", "").strip()
            if clean_text:
                wait = bot.reply_to(message, "💭 Думаю...")
                response = get_gemini_response(clean_text)
                try:
                    bot.edit_message_text(response, message.chat.id, wait.message_id)
                except Exception as e:
                    print(f"Ошибка отправки ответа в группе: {e}")

print(f"✅ Бот @{BOT_USERNAME} с Gemini успешно запущен!")
bot.infinity_polling()
