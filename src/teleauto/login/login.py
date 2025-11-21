# telemart_login.py
import subprocess
import time
from pywinauto import Desktop
from src.teleauto.localization import tr

def start_telemart(path):
    try:
        # Проверяем процессы
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        process_found = 'telemart' in result.stdout.lower()

        # Проверяем окна
        window_found = False
        try:
            spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
            window_found = spec.exists()
        except:
            pass

        if not (process_found or window_found):
            print(tr("log_tm_launching"))
            if path:
                subprocess.Popen([path])
                print(tr("log_tm_launched"))
            else:
                 print(tr("error_no_tm_path"))
        else:
            print(tr("log_tm_already_running"))
    except Exception as e:
        print(tr("log_tm_check_err", e=e))


def login_telemart(username: str, password: str, timeout: int = 20):
    """
    Вводит логин и пароль в Telemart.Client и нажимает кнопку Вход.
    """

    def wait_for_login_box():
        """Ждем появления поля логина"""
        print(tr("log_tm_wait_login"))
        for attempt in range(180):  # range - секунды
            try:
                spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
                if spec.exists():
                    wrapper = spec.wrapper_object()
                    login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                      if ctrl.element_info.automation_id == "LoginTextBox"), None)

                    if login_box:
                        print(tr("log_tm_login_found"))
                        return wrapper
                    else:
                        print(tr("log_tm_login_not_found", attempt=attempt + 1))
                        time.sleep(1)
                else:
                    print(tr("log_tm_window_not_found", attempt=attempt + 1))
                    time.sleep(1)
            except Exception as e:
                print(tr("log_tm_search_err", e=e))
                time.sleep(1)

        print(tr("log_tm_timeout"))
        return None

    def perform_login(wrapper):
        """Выполняем вход"""
        print(tr("log_tm_performing_login"))
        try:
            # --- Логин ---
            login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                              if ctrl.element_info.automation_id == "LoginTextBox"), None)
            if not login_box:
                raise RuntimeError(tr("log_tm_err_login_field"))
            login_box.set_text(username)
            print(tr("log_tm_login_entered"))

            # --- Пароль ---
            password_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                 if ctrl.element_info.automation_id == "PasswordBoxEdit"), None)
            if not password_box:
                raise RuntimeError(tr("log_tm_err_pass_field"))
            password_box.set_text(password)
            print(tr("log_tm_pass_entered"))

            # --- Кнопка Вход ---
            login_button = next((ctrl for ctrl in wrapper.descendants(control_type="Button")
                                 if ctrl.element_info.name == "Вход"), None)
            if not login_button:
                raise RuntimeError(tr("log_tm_err_btn"))
            login_button.click_input()
            print(tr("log_tm_btn_clicked"))
            return True

        except Exception as e:
            print(tr("log_tm_login_err", e=e))
            return False

    # Основной алгоритм
    max_cycles = 5

    for cycle in range(max_cycles):
        print(tr("log_tm_update_cycle", current=cycle + 1, max=max_cycles))

        # Ждем появления поля логина
        wrapper = wait_for_login_box()
        if wrapper is None:
            continue

        # Выполняем вход
        if perform_login(wrapper):
            print(tr("log_tm_login_ok"))
            return True
        else:
            continue

    raise RuntimeError(tr("log_tm_update_fail", max=max_cycles))