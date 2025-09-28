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
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()

def decrypt_data(token: str, key: bytes) -> str:
    f = Fernet(key)
    decrypted = f.decrypt(token.encode())
    return decrypted.decode()

def save_credentials(username, password, pin, secret_2fa):
    if pin:
        salt = os.urandom(16)
        key = derive_key(pin, salt)
        enc_username = encrypt_data(username, key)
        enc_password = encrypt_data(password, key)
        enc_secret_2fa = encrypt_data(secret_2fa, key)
        pin_hash = hash_password(pin).decode()
        data = {
            "username": enc_username,
            "password": enc_password,
            "secret_2fa": enc_secret_2fa,
            "pin_hash": pin_hash,
            "salt": base64.b64encode(salt).decode()
        }
    else:
        data = {
            "username": username,
            "password": password,
            "secret_2fa": secret_2fa,
            "pin_hash": None,
            "salt": None
        }
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def input_credentials():
    username = input("Логин: ")
    password = input("Пароль: ")
    secret_2fa = input("Введите секрет 2FA (BASE32): ").strip()
    pin = input("Установить PIN-код? Оставьте пустым — без PIN: ").strip()
    if pin:
        pin_confirm = input("Подтвердите PIN-код: ").strip()
        if pin != pin_confirm:
            print("PIN-коды не совпадают. Попробуйте снова.")
            return input_credentials()
    else:
        pin = None
    save_credentials(username, password, pin, secret_2fa)
    print("Данные сохранены.")
    return username, password, pin, secret_2fa

def verify_pin(stored_pin_hash, entered_pin):
    if stored_pin_hash is None:
        return True
    return check_password(entered_pin, stored_pin_hash.encode())

def decrypt_credentials(creds, pin):
    if pin and creds.get("salt"):
        salt = base64.b64decode(creds["salt"])
        key = derive_key(pin, salt)
        try:
            username = decrypt_data(creds["username"], key)
            password = decrypt_data(creds["password"], key)
            secret_2fa = decrypt_data(creds["secret_2fa"], key)
            return username, password, secret_2fa
        except Exception:
            raise ValueError("Неверный PIN-код или повреждены данные.")
    else:
        return creds["username"], creds["password"], creds["secret_2fa"]

def clear_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
        print("Данные учётных записей удалены.")
    else:
        print("Файл с учётными данными не найден.")
