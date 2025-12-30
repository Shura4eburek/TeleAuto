# src/teleauto/credentials.py
import os
import json
import base64
import bcrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from argon2.low_level import hash_secret_raw, Type

CREDENTIALS_FILE = "credentials.json"


def hash_password(password: str) -> bytes:
    """Хеширование пароля (PIN) для проверки при входе"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def check_password(password: str, hashed: bytes) -> bool:
    """Проверка PIN-кода"""
    return bcrypt.checkpw(password.encode(), hashed)


def derive_key(pin: str, salt: bytes) -> bytes:
    """
    Генерация ключа шифрования с использованием Argon2id.
    """
    key = hash_secret_raw(
        secret=pin.encode(),
        salt=salt,
        time_cost=3,  # Количество итераций
        memory_cost=65536,  # Использование 64 МБ оперативной памяти
        parallelism=4,  # Использование 4 потоков
        hash_len=32,  # Длина ключа для AES-256
        type=Type.ID  # Тип Argon2id
    )
    return key  # Для низкоуровневого AES возвращаем сырые байты


# --- НОВЫЕ ФУНКЦИИ ШИФРОВАНИЯ ПОЛЕЙ ---

def encrypt_field(data: str, key: bytes) -> str:
    """Шифрует поле с уникальным вектором инициализации (IV)"""
    if not data: return ""
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()

    # Сохраняем как base64(IV + Ciphertext)
    return base64.b64encode(iv + ct).decode()


def decrypt_field(encrypted_data: str, key: bytes) -> str:
    """Расшифровывает поле, извлекая IV из начала строки"""
    if not encrypted_data: return ""
    try:
        raw_data = base64.b64decode(encrypted_data)
        iv = raw_data[:16]
        ct = raw_data[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ct) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode()
    except:
        raise ValueError("Field decryption failed")


# --- ОСНОВНАЯ ЛОГИКА ---

def save_credentials(username, password, pin, secrets_list, start_telemart_flag=False, language="ru", telemart_path=""):
    if len(secrets_list) != 3:
        raise ValueError("secrets_list must have 3 elements")

    base_data = {
        "start_telemart": start_telemart_flag,
        "language": language
    }

    if pin:
        salt = os.urandom(16)
        key = derive_key(pin, salt)
        data = {
            **base_data,
            "username": encrypt_field(username, key),
            "password": encrypt_field(password, key),
            "secret_2fa_1": encrypt_field(secrets_list[0], key),
            "secret_2fa_2": encrypt_field(secrets_list[1], key),
            "secret_2fa_3": encrypt_field(secrets_list[2], key),
            "telemart_path": encrypt_field(telemart_path, key),
            "pin_hash": hash_password(pin).decode(),
            "salt": base64.b64encode(salt).decode(),
        }
    else:
        data = {
            **base_data,
            "username": username,
            "password": password,
            "secret_2fa_1": secrets_list[0],
            "secret_2fa_2": secrets_list[1],
            "secret_2fa_3": secrets_list[2],
            "telemart_path": telemart_path,
            "pin_hash": None,
            "salt": None,
        }

    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def verify_pin(stored_pin_hash, entered_pin):
    if stored_pin_hash is None: return True
    return check_password(entered_pin, stored_pin_hash.encode())


def decrypt_credentials(creds, pin):
    """
    Возвращает список: [username, password, secrets_list, start_telemart, language, telemart_path]
    """
    start_telemart_flag = creds.get("start_telemart", False)
    language = creds.get("language", "ru")

    try:
        if pin and creds.get("salt"):
            salt = base64.b64decode(creds["salt"])
            key = derive_key(pin, salt)

            username = decrypt_field(creds.get("username", ""), key)
            password = decrypt_field(creds.get("password", ""), key)
            secrets_list = [
                decrypt_field(creds.get("secret_2fa_1", ""), key),
                decrypt_field(creds.get("secret_2fa_2", ""), key),
                decrypt_field(creds.get("secret_2fa_3", ""), key)
            ]
            telemart_path = decrypt_field(creds.get("telemart_path", ""), key)
        else:
            username = creds.get("username", "")
            password = creds.get("password", "")
            secrets_list = [
                creds.get("secret_2fa_1", ""),
                creds.get("secret_2fa_2", ""),
                creds.get("secret_2fa_3", "")
            ]
            telemart_path = creds.get("telemart_path", "")

        return [username, password, secrets_list, start_telemart_flag, language, telemart_path]

    except Exception as e:
        print(f"Decryption error: {e}")
        raise ValueError("Invalid PIN or corrupted data.")


def clear_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)