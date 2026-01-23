# src/teleauto/login/login.py
import subprocess
import time
from pywinauto import Desktop
from src.teleauto.localization import tr

CREATE_NO_WINDOW = 0x08000000

def start_telemart(path):
    # --- ФИКС 2: Принудительно убиваем процессы перед стартом ---
    try:
        # Убиваем и Telemart.exe и Telemart.Client.exe (на всякий случай)
        subprocess.run(['taskkill', '/f', '/im', 'Telemart.Client.exe'],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        subprocess.run(['taskkill', '/f', '/im', 'Telemart.exe'],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(1) # Даем время системе освободить ресурсы
    except Exception:
        pass
    # ------------------------------------------------------------

    try:
        print(tr("log_tm_launching"))
        if path:
            subprocess.Popen([path], creationflags=CREATE_NO_WINDOW)
            print(tr("log_tm_launched"))
        else:
             print(tr("error_no_tm_path"))
    except Exception as e:
        print(tr("log_tm_check_err", e=e))

# Функция login_telemart остается без изменений
def login_telemart(username: str, password: str, timeout: int = 20):
    # ... (весь старый код login_telemart) ...
    def wait_for_login_box():
        print(tr("log_tm_wait_login"))
        for attempt in range(180):
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
                print(tr("log_tm_login_err", e="[REDACTED]"))

        print(tr("log_tm_timeout"))
        return None

    def perform_login(wrapper):
        print(tr("log_tm_performing_login"))
        try:
            login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                              if ctrl.element_info.automation_id == "LoginTextBox"), None)
            if not login_box:
                raise RuntimeError(tr("log_tm_err_login_field"))
            login_box.set_text(username)
            print(tr("log_tm_login_entered"))

            password_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                 if ctrl.element_info.automation_id == "PasswordBoxEdit"), None)
            if not password_box:
                raise RuntimeError(tr("log_tm_err_pass_field"))
            password_box.set_text(password)
            print(tr("log_tm_pass_entered"))

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

    max_cycles = 5
    for cycle in range(max_cycles):
        print(tr("log_tm_update_cycle", current=cycle + 1, max=max_cycles))
        wrapper = wait_for_login_box()
        if wrapper is None:
            continue
        if perform_login(wrapper):
            print(tr("log_tm_login_ok"))
            return True
        else:
            continue

    raise RuntimeError(tr("log_tm_update_fail", max=max_cycles))