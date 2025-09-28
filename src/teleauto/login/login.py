# telemart_login.py
import subprocess
from datetime import time

from pywinauto import Desktop


def start_telemart(path=r"C:\Users\Mamoru\Downloads\TelemartClient\TelemartClient\Telemart.Client.exe"):
    try:
        # Проверяем процессы
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        process_found = 'telemart' in result.stdout.lower()

        # Проверяем окна
        window_found = False
        try:
            from pywinauto import Desktop
            spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
            window_found = spec.exists()
        except:
            pass

        if not (process_found or window_found):
            print("Запускаем Telemart Client...")
            subprocess.Popen([path])
            time.sleep(5)
        else:
            print("Telemart.Client уже запущен")
    except Exception as e:
        print(f"Ошибка при проверке/запуске Telemart Client: {e}")


def login_telemart(username: str, password: str, timeout: int = 20):
    """
    Вводит логин и пароль в Telemart.Client и нажимает кнопку Вход.

    :param username: Строка для логина
    :param password: Строка для пароля
    :param timeout: Время ожидания появления окна (по умолчанию 20 секунд)
    """
    # Получаем WindowSpecification
    spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")

    # Ждём готовности окна
    wrapper = spec.wait("exists ready", timeout=timeout)

    # --- Логин ---
    login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                      if ctrl.element_info.automation_id == "LoginTextBox"), None)
    if not login_box:
        raise RuntimeError("Поле логина не найдено!")
    login_box.set_text(username)

    # --- Пароль ---
    password_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                         if ctrl.element_info.automation_id == "PasswordBoxEdit"), None)
    if not password_box:
        raise RuntimeError("Поле пароля не найдено!")
    password_box.set_text(password)

    # --- Кнопка Вход ---
    login_button = next((ctrl for ctrl in wrapper.descendants(control_type="Button")
                         if ctrl.element_info.name == "Вход"), None)
    if not login_button:
        raise RuntimeError("Кнопка Вход не найдена!")
    login_button.click_input()
