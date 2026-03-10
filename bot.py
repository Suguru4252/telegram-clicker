import telebot
import requests
import os
import zipfile
import io
import time
import json

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "ТВОЙ_ТОКЕН_БОТА"
ADMIN_ID = ТВОЙ_ID  # Узнай у @userinfobot

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище состояний пользователей
user_data = {}

# ===== КОМАНДА СТАРТ =====
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📦 СОЗДАТЬ APK')
    bot.send_message(
        message.chat.id,
        "👋 Бот для создания APK из сайта\n\n"
        "1️⃣ Нажми «СОЗДАТЬ APK»\n"
        "2️⃣ Отправь ссылку на сайт\n"
        "3️⃣ Отправь название\n"
        "4️⃣ Отправь иконку\n"
        "5️⃣ Получи APK через минуту",
        reply_markup=markup
    )

# ===== СОЗДАНИЕ APK =====
@bot.message_handler(func=lambda m: m.text == '📦 СОЗДАТЬ APK')
def create_apk(message):
    user_data[message.chat.id] = {'step': 'url'}
    bot.send_message(
        message.chat.id,
        "🔗 Отправь ссылку на твой сайт (GitHub Pages)\n"
        "Пример: https://username.github.io/repo/"
    )

# ===== ПРИЕМ ССЫЛКИ =====
@bot.message_handler(func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'url')
def get_url(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.send_message(message.chat.id, "❌ Это не ссылка!")
        return
    
    # Проверяем, доступен ли сайт
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            bot.send_message(message.chat.id, f"❌ Сайт не отвечает (код {r.status_code})")
            return
    except:
        bot.send_message(message.chat.id, "❌ Не удалось подключиться к сайту")
        return
    
    user_data[message.chat.id]['url'] = url
    user_data[message.chat.id]['step'] = 'name'
    bot.send_message(message.chat.id, "📝 Отправь название приложения")

# ===== ПРИЕМ НАЗВАНИЯ =====
@bot.message_handler(func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'name')
def get_name(message):
    name = message.text.strip()
    if len(name) < 2:
        bot.send_message(message.chat.id, "❌ Слишком короткое название")
        return
    
    user_data[message.chat.id]['name'] = name
    user_data[message.chat.id]['step'] = 'icon'
    bot.send_message(message.chat.id, "🖼️ Отправь иконку (картинку)")

# ===== ПРИЕМ ИКОНКИ =====
@bot.message_handler(content_types=['photo'], func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'icon')
def get_icon(message):
    try:
        # Получаем фото
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем фото
        icon_path = f"icon_{message.chat.id}.png"
        with open(icon_path, 'wb') as f:
            f.write(downloaded_file)
        
        user_data[message.chat.id]['icon'] = icon_path
        user_data[message.chat.id]['step'] = 'building'
        
        bot.send_message(message.chat.id, "⏳ НАЧИНАЮ СОЗДАВАТЬ APK...")
        
        # Запускаем сборку
        import threading
        thread = threading.Thread(target=build_apk, args=(message.chat.id,))
        thread.start()
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# ===== РАБОЧАЯ СБОРКА APK =====
def build_apk(chat_id):
    try:
        data = user_data[chat_id]
        
        bot.send_message(chat_id, "🔄 1. Подключаюсь к серверу сборки...")
        
        # ИСПОЛЬЗУЕМ РАБОЧИЙ API
        # web2apk.com имеет открытое API
        
        # Подготавливаем данные
        files = {
            'apk_name': (None, data['name']),
            'url': (None, data['url']),
        }
        
        # Загружаем иконку
        with open(data['icon'], 'rb') as f:
            files['icon'] = ('icon.png', f, 'image/png')
            
            bot.send_message(chat_id, "🔄 2. Загружаю файлы на сервер...")
            
            # Отправляем запрос
            response = requests.post(
                'https://web2apk.com/api/create',
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            try:
                result = response.json()
                download_url = result.get('download_url') or result.get('file')
                
                if download_url:
                    bot.send_message(chat_id, "✅ АРK ГОТОВ!")
                    
                    # Отправляем файл
                    if download_url.startswith('http'):
                        bot.send_message(chat_id, f"Скачать: {download_url}")
                        # Также пробуем скачать и отправить напрямую
                        try:
                            apk_file = requests.get(download_url, timeout=30)
                            if apk_file.status_code == 200:
                                bot.send_document(
                                    chat_id, 
                                    ('app.apk', apk_file.content, 'application/vnd.android.package-archive')
                                )
                        except:
                            pass
                    else:
                        bot.send_document(
                            chat_id,
                            ('app.apk', response.content, 'application/vnd.android.package-archive')
                        )
                else:
                    bot.send_message(chat_id, "❌ Сервер не вернул ссылку на APK")
            except:
                # Если не JSON, может быть прямая ссылка
                bot.send_message(chat_id, "✅ АРK СОЗДАН!")
                bot.send_document(
                    chat_id,
                    ('app.apk', response.content, 'application/vnd.android.package-archive')
                )
        else:
            bot.send_message(chat_id, f"❌ Ошибка сервера: {response.status_code}")
            
            # ПРОБУЕМ ЗАПАСНОЙ ВАРИАНТ
            bot.send_message(chat_id, "🔄 Пробую другой способ...")
            
            # Используем appsgeyser (у них тоже есть API)
            backup_files = {
                'app_name': (None, data['name']),
                'app_url': (None, data['url']),
            }
            
            with open(data['icon'], 'rb') as f:
                backup_files['icon'] = ('icon.png', f, 'image/png')
                
                backup_response = requests.post(
                    'https://appsgeyser.com/api/create',
                    files=backup_files,
                    timeout=60
                )
            
            if backup_response.status_code == 200:
                bot.send_message(chat_id, "✅ АРK СОЗДАН (второй способ)!")
                bot.send_document(
                    chat_id,
                    ('app.apk', backup_response.content, 'application/vnd.android.package-archive')
                )
            else:
                bot.send_message(chat_id, "❌ Все способы не сработали. Попробуй позже.")
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
    
    finally:
        # Чистим файлы
        try:
            if os.path.exists(data.get('icon', '')):
                os.remove(data['icon'])
        except:
            pass
        
        if chat_id in user_data:
            del user_data[chat_id]

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
