import telebot
import requests
import os
import zipfile
import io
import time
from github import Github
from github import GithubException

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8633962057:AAHURLKcS7fYytFzrCuQx4xPfynryYh8pKA"
GITHUB_TOKEN = "ТВОЙ_ТОКЕН_ГИТХАБ"  # Создай на github.com → Settings → Developer settings → Personal access tokens
ADMIN_ID = 5596589260  # Узнай у @userinfobot

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище состояний пользователей
user_data = {}

# ===== КОМАНДА СТАРТ =====
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📦 Создать APK')
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я бот для создания APK из GitHub Pages.\n\n"
        "Нажми «Создать APK» и отправь мне:\n"
        "1️⃣ Ссылку на GitHub Pages\n"
        "2️⃣ Название приложения\n"
        "3️⃣ Иконку (картинку)\n\n"
        "Я сделаю APK, который работает точно как твой сайт!",
        reply_markup=markup
    )

# ===== СОЗДАНИЕ APK =====
@bot.message_handler(func=lambda m: m.text == '📦 Создать APK')
def create_apk(message):
    user_data[message.chat.id] = {'step': 'url'}
    bot.send_message(
        message.chat.id,
        "🔗 Отправь ссылку на GitHub Pages\n"
        "Пример: https://username.github.io/repo/"
    )

# ===== ПРИЕМ ССЫЛКИ =====
@bot.message_handler(func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'url')
def get_url(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.send_message(message.chat.id, "❌ Это не ссылка! Отправь ссылку на GitHub Pages")
        return
    
    user_data[message.chat.id]['url'] = url
    user_data[message.chat.id]['step'] = 'name'
    bot.send_message(message.chat.id, "📝 Отправь название приложения (например: Мой Кликер)")

# ===== ПРИЕМ НАЗВАНИЯ =====
@bot.message_handler(func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'name')
def get_name(message):
    name = message.text.strip()
    if len(name) < 2:
        bot.send_message(message.chat.id, "❌ Слишком короткое название")
        return
    
    user_data[message.chat.id]['name'] = name
    user_data[message.chat.id]['step'] = 'icon'
    bot.send_message(message.chat.id, "🖼️ Отправь иконку (картинку 512×512 PNG)")

# ===== ПРИЕМ ИКОНКИ =====
@bot.message_handler(content_types=['photo'], func=lambda m: m.chat.id in user_data and user_data[m.chat.id]['step'] == 'icon')
def get_icon(message):
    try:
        # Получаем фото
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем фото
        icon_path = f"icons/{message.chat.id}.png"
        os.makedirs("icons", exist_ok=True)
        with open(icon_path, 'wb') as f:
            f.write(downloaded_file)
        
        user_data[message.chat.id]['icon'] = icon_path
        user_data[message.chat.id]['step'] = 'building'
        
        bot.send_message(message.chat.id, "⏳ Начинаю сборку APK... Это займет 1-2 минуты")
        
        # Запускаем сборку в отдельном потоке
        import threading
        thread = threading.Thread(target=build_apk, args=(message.chat.id,))
        thread.start()
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# ===== СБОРКА APK =====
def build_apk(chat_id):
    try:
        data = user_data[chat_id]
        
        # 1. Создаем временную папку
        folder = f"builds/{chat_id}"
        os.makedirs(folder, exist_ok=True)
        
        # 2. Скачиваем HTML с GitHub Pages
        bot.send_message(chat_id, "📥 Скачиваю файлы...")
        response = requests.get(data['url'])
        if response.status_code != 200:
            raise Exception("Не удалось загрузить сайт")
        
        # Сохраняем index.html
        with open(f"{folder}/index.html", 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # 3. Создаем простой шаблон WebView приложения
        bot.send_message(chat_id, "🔧 Собираю приложение...")
        
        # Создаем AndroidManifest.xml
        manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.{data['name'].lower().replace(' ', '')}.app">
    
    <uses-permission android:name="android.permission.INTERNET" />
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="{data['name']}"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize"
            android:launchMode="singleTask">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
        
        with open(f"{folder}/AndroidManifest.xml", 'w') as f:
            f.write(manifest)
        
        # 4. Упаковываем в APK (используем бесплатный онлайн-билдер)
        bot.send_message(chat_id, "📦 Компилирую APK...")
        
        # Создаем ZIP с файлами
        import zipfile
        zip_path = f"{folder}/source.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(f"{folder}/index.html", "index.html")
            zipf.write(f"{folder}/AndroidManifest.xml", "AndroidManifest.xml")
            if os.path.exists(data['icon']):
                zipf.write(data['icon'], "ic_launcher.png")
        
        # Отправляем на компиляцию (используем pwa2apk API)
        with open(zip_path, 'rb') as f:
            files = {'file': f}
            response = requests.post('https://pwa2apk.com/api/upload', files=files)
        
        if response.status_code == 200:
            result = response.json()
            apk_url = result.get('download_url')
            
            if apk_url:
                bot.send_message(chat_id, f"✅ APK готов!\n\nСкачать: {apk_url}")
                bot.send_document(chat_id, apk_url)
            else:
                raise Exception("Не удалось получить ссылку на APK")
        else:
            raise Exception("Ошибка компиляции")
        
        # Очищаем временные файлы
        import shutil
        shutil.rmtree(folder)
        if os.path.exists(data['icon']):
            os.remove(data['icon'])
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка сборки: {e}")
    
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
