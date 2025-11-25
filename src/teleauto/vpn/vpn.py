# src/teleauto/vpn/vpn.py
import time
import subprocess
import psutil
import socket
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError
from src.teleauto.localization import tr

CREATE_NO_WINDOW = 0x08000000


def force_kill_pritunl():
    """Принудительно убивает процесс Pritunl"""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'pritunl.exe'],
                       capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(2)
    except Exception:
        pass


def start_pritunl(path=r"C:\Program Files (x86)\Pritunl\pritunl.exe"):
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
        process_found = 'pritunl.exe' in result.stdout.lower()
        window_found = False
        window_visible = False

        try:
            spec = Desktop(backend="uia").window(title_re=r".*Pritunl Client.*")
            window_found = spec.exists()
            if window_found:
                try:
                    wrapper = spec.wrapper_object()
                    window_visible = wrapper.is_visible()
                    print(tr("log_vpn_window_found", visible=window_visible))
                except Exception as e:
                    print(tr("log_vpn_visible_error", e=e))
        except Exception as e:
            print(tr("log_vpn_search_error", e=e))

        # Логика: если процесса нет ИЛИ (процесс есть, но окна нет/оно скрыто) -> перезапуск
        if not process_found or (process_found and not (window_found and window_visible)):
            if process_found:
                print(tr("log_vpn_restart"))
                force_kill_pritunl()  # Используем вынесенную функцию

            print(tr("log_vpn_start"))
            subprocess.Popen([path], creationflags=CREATE_NO_WINDOW)

            for attempt in range(30):
                time.sleep(1)
                try:
                    app = Desktop(backend="uia").window(title_re=".*Pritunl Client.*")
                    if app.exists():
                        if app.wrapper_object().is_visible():
                            app.wait("ready", timeout=5)
                            print(tr("log_vpn_ready"))
                            break
                except Exception:
                    continue
    except Exception as e:
        print(tr("log_vpn_check_error", e=e))


def click_pritunl_connect(profile_index=0, window_title_re=".*Pritunl Client.*"):
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible enabled", timeout=30)
        app.set_focus()

        # --- ФИКС 1: Проверка, не нажата ли уже кнопка (есть ли поле ввода кода) ---
        try:
            # Ищем поле ввода (Edit), которое появляется только после нажатия Connect
            edit_box = app.child_window(control_type="Edit")
            if edit_box.exists() and edit_box.is_visible():
                print("Поле ввода 2FA уже активно. Пропускаем нажатие Connect.")
                return True
        except:
            pass
        # ---------------------------------------------------------------------------

        for attempt in range(10):
            time.sleep(1)
            try:
                all_buttons = app.descendants(control_type="Button")
            except:
                continue

            filtered_buttons = []
            for btn in all_buttons:
                try:
                    if btn.window_text().endswith("Connect") and btn.is_visible() and btn.is_enabled():
                        parent = btn.parent()
                        if parent and "profile connect" not in parent.window_text().lower():
                            filtered_buttons.append(btn)
                except:
                    continue

            if filtered_buttons:
                if 0 <= profile_index < len(filtered_buttons):
                    filtered_buttons[profile_index].click_input()
                    print(tr("log_vpn_connect_click", idx=profile_index + 1))
                    return True
        return False
    except Exception as e:
        print(tr("log_vpn_connect_click_error", e=e))
        return False


# Остальные функции (input_2fa_code_and_reconnect, disconnect_vpn и др.) оставляем без изменений
def input_2fa_code_and_reconnect(code, window_title_re=".*Pritunl.*"):
    # ... (код тот же) ...
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready", timeout=15)
        app.set_focus()

        try:
            edit_box = app.child_window(control_type="Edit")
            edit_box.wait("exists ready visible enabled", timeout=10)
            edit_box.set_text(str(code))
            print(tr("log_vpn_totp"))
        except:
            pass

        time.sleep(0.5)
        connect_button = None
        for _ in range(5):
            try:
                btns = [b for b in app.descendants(control_type="Button") if
                        b.window_text().endswith("Connect") and b.is_visible()]
                if btns:
                    connect_button = btns[-1]
                    break
                time.sleep(1)
            except:
                pass

        if connect_button:
            connect_button.click_input()
            print(tr("log_vpn_reconnect_click"))
            return True
        return False
    except Exception as e:
        print(tr("log_vpn_error", e=e))
        return False


def disconnect_vpn(window_title_re=".*Pritunl Client.*"):
    # ... (код тот же) ...
    try:
        start_pritunl()
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible", timeout=15)
        app.set_focus()

        disconnect_button = None
        for _ in range(5):
            try:
                btns = [b for b in app.descendants(control_type="Button") if
                        b.window_text().endswith("Disconnect") and b.is_visible()]
                if btns:
                    disconnect_button = btns[0]
                    break
                time.sleep(1)
            except:
                pass

        if disconnect_button:
            disconnect_button.click_input()
            print(tr("log_vpn_disconnect_click"))
            return True
        return False
    except Exception:
        return False


def wait_for_disconnect(timeout_sec=30):
    # ... (код тот же) ...
    start_time = time.time()
    while check_vpn_connection():
        if time.time() - start_time > timeout_sec:
            return False
        time.sleep(0.5)
    print(tr("log_vpn_adapters_off"))
    return True


def check_vpn_connection():
    # ... (код тот же) ...
    keywords = ["TAP-Windows Adapter V9", "Pritunl"]
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for adapter in addrs.keys():
        for kw in keywords:
            if kw.lower() in adapter.lower():
                if adapter in stats and stats[adapter].isup:
                    for addr in addrs[adapter]:
                        if addr.family == socket.AF_INET and not addr.address.startswith("169.254"):
                            return True
    return False