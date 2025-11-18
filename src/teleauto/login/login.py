# telemart_login.py
import subprocess
import time

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
            print("Telemart Client успешно запущен")
        else:
            print("Telemart.Client уже запущен")
    except Exception as e:
        print(f"Ошибка при проверке/запуске Telemart Client: {e}")


def login_telemart(username: str, password: str, timeout: int = 20):
    """
    Вводит логин и пароль в Telemart.Client и нажимает кнопку Вход.
    Обрабатывает процесс обновления программы с перезапуском.
    """

    def wait_for_login_box():
        """Ждем появления поля логина"""
        print("Ждем появления поля логина...")
        for attempt in range(180):  # range - секунды
            try:
                spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
                if spec.exists():
                    wrapper = spec.wrapper_object()
                    # Используем ваш старый метод поиска
                    login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                      if ctrl.element_info.automation_id == "LoginTextBox"), None)

                    if login_box:
                        print("Поле логина найдено")
                        return wrapper
                    else:
                        print(f"Поле логина не найдено, ждем... ({attempt + 1}/180)")
                        time.sleep(1)
                else:
                    print(f"Окно не найдено, ждем... ({attempt + 1}/180)")
                    time.sleep(1)
            except Exception as e:
                print(f"Ошибка при поиске поля логина: {e}")
                time.sleep(1)

        print("Поле логина не появилось за 3 минуты")
        return None

    def perform_login(wrapper):
        """Выполняем вход"""
        print("Выполняем вход...")
        try:
            # --- Логин ---
            login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                              if ctrl.element_info.automation_id == "LoginTextBox"), None)
            if not login_box:
                raise RuntimeError("Поле логина не найдено!")
            login_box.set_text(username)
            print("Логин введен")

            # --- Пароль ---
            password_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                 if ctrl.element_info.automation_id == "PasswordBoxEdit"), None)
            if not password_box:
                raise RuntimeError("Поле пароля не найдено!")
            password_box.set_text(password)
            print("Пароль введен")

            # --- Кнопка Вход ---
            login_button = next((ctrl for ctrl in wrapper.descendants(control_type="Button")
                                 if ctrl.element_info.name == "Вход"), None)
            if not login_button:
                raise RuntimeError("Кнопка Вход не найдена!")
            login_button.click_input()
            print("Кнопка Вход нажата")
            return True

        except Exception as e:
            print(f"Ошибка при выполнении входа: {e}")
            return False

    # Основной алгоритм
    max_cycles = 5  # Количество циклов обновления

    for cycle in range(max_cycles):
        print(f"Цикл обработки обновления {cycle + 1}/{max_cycles}")

        # Ждем появления поля логина
        wrapper = wait_for_login_box()
        if wrapper is None:
            continue

        # Пункт 5: Выполняем вход
        if perform_login(wrapper):
            print("Вход выполнен успешно")
            return True
        else:
            continue

    raise RuntimeError(f"Не удалось выполнить вход после {max_cycles} циклов обработки обновления")
