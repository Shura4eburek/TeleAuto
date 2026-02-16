# src/teleauto/credentials.py
import os
import json
import base64
import ctypes
import logging
import bcrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from argon2.low_level import hash_secret_raw, Type

logger = logging.getLogger(__name__)

CREDENTIALS_FILE = "credentials.json"


def secure_zero(buf: bytearray):
    """Best-effort zeroing of sensitive memory."""
    if buf and len(buf) > 0:
        ctypes.memset((ctypes.c_char * len(buf)).from_buffer(buf), 0, len(buf))


class SecureData:
    """Wrapper for decrypted credentials with secure cleanup."""

    def __init__(self, username, password, secrets_dict, start_telemart, language, telemart_path, manual_offset):
        self.username = username
        self.password = password
        self.secrets = secrets_dict
        self.start_telemart = start_telemart
        self.language = language
        self.telemart_path = telemart_path
        self.manual_offset = manual_offset

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()

    def clear(self):
        """Zero out string fields (best-effort in CPython)."""
        self.username = ""
        self.password = ""
        self.telemart_path = ""
        if self.secrets:
            for key in list(self.secrets.keys()):
                self.secrets[key] = ""
            self.secrets.clear()

    def __del__(self):
        self.clear()

    def __getitem__(self, index):
        """Backward-compatible index access."""
        return (self.username, self.password, self.secrets,
                self.start_telemart, self.language, self.telemart_path, self.manual_offset)[index]

    def __len__(self):
        return 7


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def derive_key(pin: str, salt: bytes) -> bytearray:
    key = hash_secret_raw(
        secret=pin.encode(),
        salt=salt,
        time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, type=Type.ID
    )
    return bytearray(key)


def encrypt_field(data: str, key: bytes) -> str:
    if not data: return ""
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + ct).decode()


def decrypt_field(encrypted_data: str, key: bytes) -> str:
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
        return ""

    # --- ОБНОВЛЕННАЯ ЛОГИКА ---


def save_credentials(username, password, pin, secrets_dict, start_telemart_flag=False, language="ru", telemart_path="",
                     manual_offset=0):
    """
    Добавлен аргумент manual_offset (int)
    """
    base_data = {
        "start_telemart": start_telemart_flag,
        "language": language,
        "manual_offset": manual_offset  # Сохраняем в открытом виде (это не секрет)
    }

    if pin:
        salt = os.urandom(16)
        key = derive_key(pin, salt)

        try:
            encrypted_secrets = {}
            for name, secret in secrets_dict.items():
                if secret.strip():
                    encrypted_secrets[name] = encrypt_field(secret.strip(), key)

            data = {
                **base_data,
                "username": encrypt_field(username, key),
                "password": encrypt_field(password, key),
                "secrets": encrypted_secrets,
                "telemart_path": encrypt_field(telemart_path, key),
                "pin_hash": hash_password(pin).decode(),
                "salt": base64.b64encode(salt).decode(),
            }
        finally:
            secure_zero(key)
    else:
        data = {
            **base_data,
            "username": username,
            "password": password,
            "secrets": secrets_dict,
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
    Returns SecureData with: username, password, secrets_dict, start_telemart, language, telemart_path, manual_offset.
    SecureData supports both index access (data[0]) and attribute access (data.username).
    """
    start_telemart_flag = creds.get("start_telemart", False)
    language = creds.get("language", "ru")
    manual_offset = creds.get("manual_offset", 0)

    try:
        if pin and creds.get("salt"):
            salt = base64.b64decode(creds["salt"])
            key = derive_key(pin, salt)

            try:
                username = decrypt_field(creds.get("username", ""), key)
                password = decrypt_field(creds.get("password", ""), key)
                telemart_path = decrypt_field(creds.get("telemart_path", ""), key)

                raw_secrets = creds.get("secrets", {})
                secrets_dict = {}
                if isinstance(raw_secrets, dict):
                    for name, enc_val in raw_secrets.items():
                        dec_val = decrypt_field(enc_val, key)
                        if dec_val:
                            secrets_dict[name] = dec_val
            finally:
                secure_zero(key)

        else:
            username = creds.get("username", "")
            password = creds.get("password", "")
            secrets_dict = creds.get("secrets", {})
            telemart_path = creds.get("telemart_path", "")

        return SecureData(username, password, secrets_dict, start_telemart_flag,
                          language, telemart_path, manual_offset)

    except Exception as e:
        logger.error("Decryption error: %s", e)  # internal, before language is set
        raise ValueError("Invalid PIN or corrupted data.")


def clear_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)