# src/teleauto/vpn/vpn.py
import time
import subprocess
import psutil
import socket
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError


def start_pritunl(path=r"C:\Program Files (x86)\Pritunl\pritunl.exe"):
    try:
        # Проверяем процессы
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        process_found = 'pritunl.exe' in result.stdout.lower()

        # Проверяем окна
        window_found = False
        window_visible = False
        try:
            spec = Desktop(backend="uia").window(title_re=r".*Pritunl Client.*")
            window_found = spec.exists()
            if window_found:
                try:
                    wrapper = spec.wrapper_object()
                    window_visible = wrapper.is_visible()
                    print(f"Окно Pritunl найдено, видимость: {window_visible}")
                except Exception as e:
                    print(f"Ошибка проверки видимости окна: {e}")
                    window_visible = False
        except Exception as e:
            print(f"Ошибка поиска окна Pritunl: {e}")

        if not process_found or (process_found and not (window_found and window_visible)):
            if process_found and not window_visible:
                print("Процесс Pritunl найден, но окно не видимо. Перезапускаем...")
                try:
                    subprocess.run(['taskkill', '/f', '/im', 'pritunl.exe'],
                                   capture_output=True, text=True)
                    time.sleep(2)
                except Exception as e:
                    print(f"Ошибка при завершении процесса Pritunl: {e}")

            print("Запускаем Pritunl...")
            subprocess.Popen([path])

            for attempt in range(30):
                time.sleep(1)
                try:
                    app = Desktop(backend="uia").window(title_re=".*Pritunl Client.*")
                    if app.exists():
                        wrapper = app.wrapper_object()
                        if wrapper.is_visible():
                            app.wait("ready", timeout=5)
                            print("Pritunl успешно запущен и готов")
                            break
                        else:
                            print(f"Окно существует но не видимо, попытка {attempt + 1}/30")
                    else:
                        print(f"Окно не найдено, попытка {attempt + 1}/30")
                except Exception as e:
                    print(f"Ошибка ожидания окна, попытка {attempt + 1}/30: {e}")
                    continue
        else:
            print("Pritunl уже запущен и окно видимо")

    except Exception as e:
        print(f"Ошибка при проверке/запуске Pritunl: {e}")


def click_pritunl_connect(profile_index=0, window_title_re=".*Pritunl Client.*"):
    """
    Нажимает кнопку "Connect" для ВЫБРАННОГО профиля.
    (Ищет ВСЕ кнопки и фильтрует в Python)
    """
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible enabled", timeout=30)
        app.set_focus()

        for attempt in range(10):
            time.sleep(1)

            try:
                all_buttons = app.descendants(control_type="Button")
            except ElementNotFoundError:
                print(f"Кнопки (control_type='Button') не найдены, попытка {attempt + 1}/10")
                continue

            filtered_buttons = []
            for btn in all_buttons:
                try:
                    btn_name = btn.window_text()
                    if not (btn_name and btn_name.endswith("Connect")):
                        continue

                    if not (btn.is_visible() and btn.is_enabled()):
                        continue

                    parent = btn.parent()
                    parent_text = ""
                    if parent:
                        try:
                            parent_text = parent.window_text().lower()
                        except Exception:
                            pass

                    if parent_text and "profile connect" in parent_text:
                        continue

                    filtered_buttons.append(btn)
                except Exception:
                    continue

            if filtered_buttons:
                if not (0 <= profile_index < len(filtered_buttons)):
                    print(
                        f"Ошибка: Индекс профиля {profile_index} вне диапазона. Найдено {len(filtered_buttons)} кнопок.")
                    print("Возможно, в Pritunl меньше профилей, чем вы указали.")
                    return False

                btn = filtered_buttons[profile_index]
                btn.click_input()
                print(f"Кнопка 'Connect' для профиля #{profile_index + 1} нажата.")
                return True
            else:
                print(f"Подходящие кнопки '...Connect' не найдены, попытка {attempt + 1}/10")

        print("Кнопка 'Connect' не найдена после всех попыток.")
        return False

    except Exception as e:
        print(f"Ошибка при нажатии кнопки 'Connect': {e}")
        return False


def input_2fa_code_and_reconnect(code, window_title_re=".*Pritunl.*"):
    """
    Надежный ввод 2FA. Нажимает ПОСЛЕДНЮЮ активную кнопку 'Connect'
    после ввода 2FA кода.
    """
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready", timeout=15)
        app.set_focus()

        edit_box = None
        try:
            edit_box = app.child_window(control_type="Edit")
            edit_box.wait("exists ready visible enabled", timeout=10)
            edit_box.set_text(str(code))
            print("TOTP код введён.")
        except (ElementNotFoundError, RuntimeError):
            print("Поле ввода 2FA кода не появилось. (Возможно, не требуется).")
            return True

        time.sleep(0.5)

        connect_button = None
        for attempt in range(5):
            try:
                all_buttons = app.descendants(control_type="Button")
                active_connect_buttons = []

                for btn in all_buttons:
                    btn_name = btn.window_text()
                    if btn_name and btn_name.endswith("Connect"):
                        if btn.is_visible() and btn.is_enabled():
                            active_connect_buttons.append(btn)

                if active_connect_buttons:
                    connect_button = active_connect_buttons[-1]
                    break
                else:
                    print(f"Активная кнопка 'Connect' (в 2FA) не найдена, попытка {attempt + 1}/5")
                    time.sleep(1)

            except Exception as e:
                print(f"Ошибка при поиске кнопок 2FA: {e}")
                time.sleep(1)

        if not connect_button:
            print("Не удалось найти *активную* кнопку 'Connect' в диалоге 2FA.")
            return False

        connect_button.click_input()
        print("Кнопка 'Connect' в диалоге 2FA (последняя активная) нажата.")
        return True

    except Exception as e:
        print(f"Критическая ошибка при вводе 2FA: {e}")
        return False


# --- ИЗМЕНЕННАЯ ФУНКЦИЯ ---
def disconnect_vpn(window_title_re=".*Pritunl Client.*"):
    """
    Находит и нажимает АКТИВНУЮ кнопку 'Disconnect'.
    Сначала проверяет, видимо ли окно, и перезапускает, если нужно.
    """
    try:
        # 1. УБЕДИМСЯ, ЧТО ОКНО ЗАПУЩЕНО И ВИДИМО
        print("Проверка окна Pritunl перед отключением...")
        start_pritunl()  # Эта функция перезапустит Pritunl, если он невидимый

        # 2. ТЕПЕРЬ ИЩЕМ КНОПКУ
        app = Desktop(backend="uia").window(title_re=window_title_re)
        app.wait("exists ready visible", timeout=15)
        app.set_focus()

        disconnect_button = None
        for attempt in range(5):  # Ищем 5 сек
            try:
                all_buttons = app.descendants(control_type="Button")
                for btn in all_buttons:
                    btn_name = btn.window_text()
                    if btn_name and btn_name.endswith("Disconnect"):
                        if btn.is_visible() and btn.is_enabled():
                            disconnect_button = btn
                            break
                if disconnect_button:
                    break
                else:
                    print(f"Активная кнопка 'Disconnect' не найдена, попытка {attempt + 1}/5")
                    time.sleep(1)
            except Exception as e:
                print(f"Ошибка поиска кнопки Disconnect: {e}")
                time.sleep(1)

        if disconnect_button:
            disconnect_button.click_input()
            print("Кнопка 'Disconnect' нажата.")
            return True
        else:
            print("Активная кнопка 'Disconnect' не найдена.")
            return False

    except Exception as e:
        print(f"Ошибка при нажатии 'Disconnect': {e}")
        return False


def wait_for_disconnect(timeout_sec=30):
    """
    Ждет, пока check_vpn_connection не вернет False.
    """
    print("Ожидание отключения сетевых адаптеров...")
    start_time = time.time()
    while check_vpn_connection():
        if time.time() - start_time > timeout_sec:
            print(f"Ошибка: Адаптеры не отключились за {timeout_sec} сек.")
            return False
        time.sleep(0.5)
    print("Сетевые адаптеры отключены.")
    return True


def find_adapters_by_keyword(keyword_list):
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    found_adapters = []
    for adapter in addrs.keys():
        for kw in keyword_list:
            if kw.lower() in adapter.lower():
                found_adapters.append(adapter)
                break
    return found_adapters


def check_adapters_status(adapter_names):
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    results = {}
    for adapter in adapter_names:
        if adapter not in stats:
            results[adapter] = "Not found"
            continue
        stat = stats[adapter]
        is_up = stat.isup
        has_valid_ip = False
        for addr in addrs.get(adapter, []):
            if addr.family == socket.AF_INET and not addr.address.startswith("169.254"):
                has_valid_ip = True
                break
        if is_up and has_valid_ip:
            results[adapter] = "Connected"
        else:
            results[adapter] = "Disconnected"
    return results


def check_vpn_connection():
    keywords = ["TAP-Windows Adapter V9", "Pritunl"]
    adapters = find_adapters_by_keyword(keywords)
    status = check_adapters_status(adapters)
    return any(state == "Connected" for state in status.values())