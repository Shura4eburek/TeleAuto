# src/teleauto/credentials.py
import os
import json
import base64
import bcrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

CREDENTIALS_FILE = "../../credentials.json"


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
    if not data:  # Не шифруем пустые строки
        return ""
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()


def decrypt_data(token: str, key: bytes) -> str:
    if not token:  # Не расшифровываем пустые строки
        return ""
    f = Fernet(key)
    decrypted = f.decrypt(token.encode())
    return decrypted.decode()


def save_credentials(username, password, pin, secrets_list, start_telemart_flag=False):
    """
    Сохраняет учетные данные.
    secrets_list: список из 3-х секретов (могут быть пустые строки)
    """
    if len(secrets_list) != 3:
        raise ValueError("secrets_list должен содержать 3 элемента")

    if pin:
        salt = os.urandom(16)
        key = derive_key(pin, salt)
        enc_username = encrypt_data(username, key)
        enc_password = encrypt_data(password, key)
        enc_secrets = [encrypt_data(s, key) for s in secrets_list]
        pin_hash = hash_password(pin).decode()
        data = {
            "username": enc_username,
            "password": enc_password,
            "secret_2fa_1": enc_secrets[0],
            "secret_2fa_2": enc_secrets[1],
            "secret_2fa_3": enc_secrets[2],
            "pin_hash": pin_hash,
            "salt": base64.b64encode(salt).decode(),
            "start_telemart": start_telemart_flag
        }
    else:
        data = {
            "username": username,
            "password": password,
            "secret_2fa_1": secrets_list[0],
            "secret_2fa_2": secrets_list[1],
            "secret_2fa_3": secrets_list[2],
            "pin_hash": None,
            "salt": None,
            "start_telemart": start_telemart_flag
        }
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_pin(stored_pin_hash, entered_pin):
    if stored_pin_hash is None:
        return True
    return check_password(entered_pin, stored_pin_hash.encode())


def decrypt_credentials(creds, pin):
    """
    Расшифровывает данные.
    Возвращает: (username, password, secrets_list, start_telemart_flag)
    """
    start_telemart_flag = creds.get("start_telemart", False)
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
            # PIN не используется или его нет
            username = creds.get("username", "")
            password = creds.get("password", "")
            secrets_list.append(creds.get("secret_2fa_1", ""))
            secrets_list.append(creds.get("secret_2fa_2", ""))
            secrets_list.append(creds.get("secret_2fa_3", ""))

        return username, password, secrets_list, start_telemart_flag

    except Exception as e:
        print(f"Ошибка расшифровки: {e}")
        raise ValueError("Неверный PIN-код или повреждены данные.")


def clear_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
        print("Данные учётных записей удалены.")
    else:
        print("Файл с учётными данными не найден.")

# input_credentials() больше не используется GUI и может быть удалена