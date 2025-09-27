import time
import subprocess
from pywinauto import Desktop


def start_pritunl(path=r"C:\Program Files (x86)\Pritunl\pritunl.exe"):
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        if "pritunl.exe" not in result.stdout.lower():
            print("Запускаем Pritunl...")
            subprocess.Popen([path])
            time.sleep(5)  # Можно увеличить время ожидания
        else:
            print("Pritunl уже запущен")
    except Exception as e:
        print(f"Ошибка при проверке/запуске Pritunl: {e}")


def connect_vpn():
    try:
        print("Подключаемся к VPN через pritunl CLI...")
        proc = subprocess.Popen(["pritunl", "connect"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc
    except Exception as e:
        print(f"Ошибка при запуске 'pritunl connect': {e}")
        return None


def click_pritunl_connect(window_title_re=".*Pritunl Client.*"):
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible enabled", timeout=30)
        app.set_focus()

        buttons = app.descendants(control_type="Button")

        for btn in buttons:
            try:
                text = btn.window_text().lower()
                if "connect" in text and btn.is_visible() and btn.is_enabled():
                    rect = btn.rectangle()
                    x = (rect.left + rect.right) // 2
                    y = (rect.top + rect.bottom) // 2
                    btn.click_input(coords=(x - rect.left, y - rect.top))
                    print("Кнопка Connect нажата.")
                    return True
            except Exception:
                continue
        print("Кнопка Connect не найдена.")
        return False
    except Exception as e:
        print(f"Ошибка при нажатии кнопки Connect: {e}")
        return False


def input_2fa_code_and_reconnect(code, window_title_re=".*Pritunl.*"):
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible enabled", timeout=30)
        app.set_focus()

        edit_box = app.child_window(control_type="Edit")
        if not edit_box.exists() or not edit_box.is_visible() or not edit_box.is_enabled():
            print("Поле ввода кода не найдено или недоступно.")
            return False
        edit_box.set_text(str(code))
        print("TOTP код введён.")

        btn_confirm = app.child_window(control_type="Button", title_re="(?i)подключиться|подтвердить|ok|confirm")
        if btn_confirm.exists() and btn_confirm.is_visible() and btn_confirm.is_enabled():
            btn_confirm.click_input()
            print("Кнопка подтверждения нажата.")
        else:
            print("Кнопка подтверждения не найдена или недоступна.")

        time.sleep(1)  # Ждём обновления интерфейса

        container = edit_box.parent()
        buttons = container.children(control_type="Button")

        connect_buttons = [btn for btn in buttons if
                           "connect" in btn.window_text().lower() and btn.is_visible() and btn.is_enabled()]

        if len(connect_buttons) >= 2:
            btn = connect_buttons[1]
            rect = btn.rectangle()
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2
            btn.click_input(coords=(x - rect.left, y - rect.top))
            print("Вторая кнопка Connect нажата.")
            return True
        elif len(connect_buttons) == 1:
            btn = connect_buttons[0]
            rect = btn.rectangle()
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2
            btn.click_input(coords=(x - rect.left, y - rect.top))
            print("Найдена только одна кнопка Connect, она нажата.")
            return True
        else:
            print("Вторая кнопка Connect в контейнере не найдена.")
            return False

    except Exception as e:
        print(f"Ошибка при вводе 2FA и повторном нажатии Connect: {e}")
        return False


def wait_for_connection(timeout=60):
    print("Ожидаем подключения к VPN...")
    time.sleep(timeout)
    print("VPN подключен.")
