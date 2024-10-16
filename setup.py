import os
import base64

# Функция для генерации ключей
def generate_keys():
    aes_key = base64.b64encode(os.urandom(16)).decode('utf-8')
    return aes_key

# Проверяем и создаем папку .gitignore, если ее нет
if not os.path.exists('.gitignore'):
    os.mkdir('.gitignore')

# Генерируем ключ
aes_key = generate_keys()

# Создаем файл .env и записываем ключ
with open('.gitignore/.env', 'w') as f:
    f.write(f"AES_KEY={aes_key}\n")

print("File .env is created in the folder .gitignore. Your key have been generated.")