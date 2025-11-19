# src/teleauto/credentials.py
import os
import json
import base64
import bcrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

CREDENTIALS_FILE = "credentials.json"  # Убрал ../.. для надежности, путь зависит от запуска


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def derive_key(pin: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    key = kdf.derive(pin.encode())
    return base64.urlsafe_b64encode(key)


def encrypt_data(data: str, key: bytes) -> str:
    if not data: return ""
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()


def decrypt_data(token: str, key: bytes) -> str:
    if not token: return ""
    f = Fernet(key)
    return f.decrypt(token.encode()).decode()


def save_credentials(username, password, pin, secrets_list, start_telemart_flag=False, language="ru"):
    """
    Сохраняет данные, включая язык.
    """
    if len(secrets_list) != 3:
        raise ValueError("secrets_list must have 3 elements")

    base_data = {
        "start_telemart": start_telemart_flag,
        "language": language  # Сохраняем язык
    }

    if pin:
        salt = os.urandom(16)
        key = derive_key(pin, salt)
        data = {
            **base_data,
            "username": encrypt_data(username, key),
            "password": encrypt_data(password, key),
            "secret_2fa_1": encrypt_data(secrets_list[0], key),
            "secret_2fa_2": encrypt_data(secrets_list[1], key),
            "secret_2fa_3": encrypt_data(secrets_list[2], key),
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
    Возвращает: (username, password, secrets_list, start_telemart_flag, language)
    """
    start_telemart_flag = creds.get("start_telemart", False)
    language = creds.get("language", "ru")  # По умолчанию русский
    secrets_list = []

    try:
        if pin and creds.get("salt"):
            salt = base64.b64decode(creds["salt"])
            key = derive_key(pin, salt)

            username = decrypt_data(creds.get("username", ""), key)
            password = decrypt_data(creds.get("password", ""), key)
            secrets_list.append(decrypt_data(creds.get("secret_2fa_1", ""), key))
            secrets_list.append(decrypt_data(creds.get("secret_2fa_2", ""), key))
            secrets_list.append(decrypt_data(creds.get("secret_2fa_3", ""), key))
        else:
            username = creds.get("username", "")
            password = creds.get("password", "")
            secrets_list.append(creds.get("secret_2fa_1", ""))
            secrets_list.append(creds.get("secret_2fa_2", ""))
            secrets_list.append(creds.get("secret_2fa_3", ""))

        return username, password, secrets_list, start_telemart_flag, language

    except Exception as e:
        print(f"Decryption error: {e}")
        raise ValueError("Invalid PIN or corrupted data.")


def clear_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)