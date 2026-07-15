import telebot
from telebot import types

TOKEN = "8640562446:AAHMHBTGoGwAPwFp4N90AM11HHMJQY1dnGA"

bot = telebot.TeleBot(TOKEN)

# Расширенный список плохих слов (можно дополнять)
BAD_WORDS = [
    "бля", "сука", "хуй", "пизд", "еб", "муд", "нахуй", "гандон", 
    "еблан", "pidor", "fuck", "shit", "asshole", "cunt", "nigger"
]

@bot.message_handler(func=lambda message: True)
def moderate(message):
    if not message.text:
        return

    text_lower = message.text.lower()

    for word in BAD_WORDS:
        if word in text_lower:
            try:
                # Удаляем сообщение
                bot.delete_message(message.chat.id, message.message_id)
                
                # Баним пользователя навсегда
                bot.ban_chat_member(message.chat.id, message.from_user.id)
                
                # Уведомляем чат
                bot.send_message(
                    message.chat.id,
                    f"🚫 Пользователь {message.from_user.first_name} (@{message.from_user.username}) забанен за мат."
                )
                print(f"Забанен: {message.from_user.id} за слово {word}")
            except Exception as e:
                print(f"Ошибка: {e}")
            return  # выходим после первого совпадения

print("✅ Бот запущен и готов к работе!")
bot.infinity_polling()
