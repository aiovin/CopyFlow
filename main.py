from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
from tinydb import TinyDB, Query
import logging
from logging import FileHandler
import time
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import signal
import sys
from hashlib import sha256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

app = Flask(__name__)

# Загрузка переменных виртуального окружения
load_dotenv(dotenv_path='.gitignore/.env')

# Инициализируем БД
db = TinyDB('cf_data/cf_data.json', indent=4, separators=(',', ': '))
data_table = db.table('data')

# Время хранения записей в секундах
time2storage = 600

# Частота проверки записей на удаление в секундах
expiration_check_timeout = 60

# Максимальная длина Ключа
MAX_FIELD1_LENGTH = 64

# Максимальная длина сохраняемого текста
MAX_TEXT_LENGTH = 50000

# Ключ шифрования
AES_KEY = base64.b64decode(os.getenv('AES_KEY'))

# Меняем уровень логгирования для планировщика, чтобы каждую минуту не сыпал сообщениями
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# Кастомный форматтер
class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        tz = pytz.timezone('Europe/Moscow')
        dt = datetime.fromtimestamp(record.created, tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def format(self, record):
        http_methods = ['GET', 'POST']
        if any(method in record.getMessage() for method in http_methods):
            return record.getMessage()
        return super().format(record)

# Настройка корневого логгера
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Обработчик для корневого логгера
root_handler = FileHandler('cf_data/system.log', mode='a', encoding='utf-8')
root_handler.setFormatter(CustomFormatter('%(asctime)s - %(levelname)s - %(message)s'))
root_logger.addHandler(root_handler)

# Настройка логгера для копирования и вставки
copypaste_logger = logging.getLogger('copypaste')
copypaste_logger.setLevel(logging.INFO)

copypaste_logger.propagate = False  # Отключаем наследование логов от корневого логгера

copypaste_handler = FileHandler('cf_data/data_history.log', mode='a', encoding='utf-8')
copypaste_handler.setFormatter(CustomFormatter('%(asctime)s - %(levelname)s - %(message)s'))
copypaste_logger.addHandler(copypaste_handler)

# Хешируем ключ для записи в cf_data.json
def hash_key(key):
    return sha256(key.encode()).hexdigest()

def encrypt(plain_text):
    cipher = AES.new(AES_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return iv, ct

def decrypt(iv, cipher_text):
    iv = base64.b64decode(iv)
    cipher_text = base64.b64decode(cipher_text)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(cipher_text), AES.block_size).decode('utf-8')
    return pt

# Функция чтобы зацензорить ключ для логов
def censor_key(text):
    if len(text) == 1:
        return '*'
    elif len(text) <= 4:
        return text[:-1] + '*'
    else:
        return text[:4] + '*' * (len(text) - 4)

# ФУНКЦИЯ ДЛЯ УДАЛЕНИЯ ХРАНЯЩИХСЯ ЗАПИСЕЙ ИЗ БД
def remove_expired_data():
    current_time = time.time()
    try:
        deleted_count = data_table.remove(Query().timestamp < (current_time - time2storage))
        if len(deleted_count) > 0:
            # Выводим не id удаленных записей а их количесво (len)
            copypaste_logger.info(f"S.E.R.V.E.R - [EXPIRATION-CHECK] - {len(deleted_count)} - outdated records.")
    except Exception as e:
        copypaste_logger.error(f"Error deleting outdated records: {e}")

# Создание экземпляра планировщика
scheduler = BackgroundScheduler()

# ЗАДАЧА НА АВТОМАТИЧЕСКУЮ ПРОВЕРКУ УСТАРЕВШИХ ЗАПИСЕЙ
scheduler.add_job(remove_expired_data, 'interval', seconds=expiration_check_timeout)
scheduler.start()

@app.route('/')
def copypaste():
    return render_template('copyflow.html')

# ФУНКЦИЯ ДЛЯ ДОБАВЛЕНИЯ ДАННЫХ В cf_data.json
@app.route('/submit_json', methods=['POST'])
def submit_json():
    data = request.json

    key = data.get('field1')
    field2 = data.get('field2')

    user_ip = request.remote_addr

    key_char_count = len(key)
    data_char_count = len(field2)

    if len(key) > MAX_FIELD1_LENGTH:
        copypaste_logger.warning(f"{user_ip} - [TOO-MUCH-FOR-KEY] - len: {key_char_count} char")
        return f"<span style='color: red;'>Error:</span> The key is too long.<br><br>Maximum length is {MAX_FIELD1_LENGTH} characters.", 400

    if len(field2) > MAX_TEXT_LENGTH:
       copypaste_logger.warning(f"{user_ip} - [TOO-MUCH-FOR-DATA] - len: {data_char_count} char")
       return f"<span style='color: red;'>Error:</span> The text is too long.<br><br>Maximum length is {MAX_TEXT_LENGTH} characters.", 400

    # Хешируем ключ
    hashed_key = hash_key(key)

    # Удаляем старую запись, если существует, используя хешированный ключ
    data_table.remove(Query().field1 == hashed_key)

    # Шифруем field2 перед сохранением
    iv, encrypted_field2 = encrypt(field2)

    # Сохраняем новую запись в базе данных
    data_table.insert({
        'field1': hashed_key,
        'field2': encrypted_field2,
        'iv': iv,
        'timestamp': time.time()
    })

    # Считаем сколько будет хранится информация в минутах
    time_left = int(time2storage / 60)
    # Считаем time_left плюс время задержки проверки данных на удаление в минутах, т.к. данные удаляются не строго через 10 минут, а при проверке раз в минуту
    time_left_with_delay = time_left + int(expiration_check_timeout / 60)

    # Зацензурить ключ для логов
    censored_key = censor_key(key)

    copypaste_logger.info(f"{user_ip} - [SAVE-DATA] - {censored_key} - data: {data_char_count} char")
    return f"<span style='color: green;'>Done.</span> Your data has been saved.<br><br>For security reasons, it <span style='color: red;'>will be deleted in {time_left} - {time_left_with_delay} minutes.</span>"

# ФУНКЦИЯ ДЛЯ СЧИТЫВАНИЯ ДАННЫХ ИЗ cf_data.json
@app.route('/get_field2', methods=['POST'])
def get_field2():
    field1_value = request.json.get('field1')

    # Хешируем значение перед поиском
    hashed_key = hash_key(field1_value)

    # Ищем запись в базе данных
    result = data_table.search(Query().field1 == hashed_key)

    user_ip = request.remote_addr

    if result:
        # Дешифруем значение
        iv = result[0]['iv']
        encrypted_field2 = result[0]['field2']
        decrypted_field2 = decrypt(iv, encrypted_field2)

        censored_field1_value = censor_key(field1_value)
        copypaste_logger.info(f"{user_ip} - [CREATE-BUTTON] - {censored_field1_value}")
        return jsonify({"field2": decrypted_field2})
    else:
        copypaste_logger.warning(f"{user_ip} - [THERE-IS-NO-BUTTON] - {field1_value}")
        return jsonify({"message": "Records with this key do not exist."}), 404

# Функция для корректного завершения веб сервера
def signal_handler(sig, frame):
    print(f"Received signal: {sig}. Shutting down CopyFlow..")
    if scheduler.running:
        scheduler.shutdown()  # Остановка планировщика
    sys.exit(0)  # Завершение процесса

if __name__ == '__main__':
    # Обработка сигналов
    signal.signal(signal.SIGINT, signal_handler)  # Обработка SIGINT (Ctrl+C)
    signal.signal(signal.SIGTERM, signal_handler)  # Обработка SIGTERM (для Unix)

    print("Starting CopyFlow..")

    try:
        app.run(debug=False, host='0.0.0.0', port=1212)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        if scheduler.running:
            scheduler.shutdown()  # Остановка планировщика при завершении приложения