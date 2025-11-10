# import ipaddress
import time
import subprocess
import psutil
import socket
# import ifaddr
from pywinauto import Desktop


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
                # Проверяем видимость окна
                try:
                    wrapper = spec.wrapper_object()
                    window_visible = wrapper.is_visible()
                    print(f"Окно Pritunl найдено, видимость: {window_visible}")
                except Exception as e:
                    print(f"Ошибка проверки видимости окна: {e}")
                    window_visible = False
        except Exception as e:
            print(f"Ошибка поиска окна Pritunl: {e}")

        # Условие запуска: нет процесса ИЛИ (есть процесс, но нет видимого окна)
        if not process_found or (process_found and not (window_found and window_visible)):
            if process_found and not window_visible:
                print("Процесс Pritunl найден, но окно не видимо. Перезапускаем...")
                # Убиваем процесс если он есть но окно невидимо
                try:
                    subprocess.run(['taskkill', '/f', '/im', 'pritunl.exe'],
                                   capture_output=True, text=True)
                    time.sleep(2)  # Ждем завершения процесса
                except Exception as e:
                    print(f"Ошибка при завершении процесса Pritunl: {e}")

            print("Запускаем Pritunl...")
            subprocess.Popen([path])

            # Ждём появления и готовности окна
            for attempt in range(30):  # 30 секунд максимум
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

        # Ждем появления кнопок Connect с повторными попытками
        for attempt in range(10):  # 10 попыток с интервалом 1 сек
            buttons = app.descendants(control_type="Button")
            connect_buttons = []

            for btn in buttons:
                try:
                    text = btn.window_text().lower()
                    if "connect" in text and btn.is_visible() and btn.is_enabled():
                        connect_buttons.append(btn)
                except Exception:
                    continue

            if connect_buttons:
                # Найдена хотя бы одна кнопка Connect
                btn = connect_buttons[0]
                rect = btn.rectangle()
                x = (rect.left + rect.right) // 2
                y = (rect.top + rect.bottom) // 2
                btn.click_input(coords=(x - rect.left, y - rect.top))
                print("Кнопка Connect нажата.")
                return True
            else:
                print(f"Кнопки Connect не найдены, попытка {attempt + 1}/10")
                time.sleep(1)

        print("Кнопка Connect не найдена после всех попыток.")
        return False

    except Exception as e:
        print(f"Ошибка при нажатии кнопки Connect: {e}")
        return False


def input_2fa_code_and_reconnect(code, window_title_re=".*Pritunl.*"):
    try:
        app = Desktop(backend="uia").window(title_re=window_title_re, control_type="Pane")
        app.wait("exists ready", timeout=15)
        app.set_focus()

        # Поле ввода TOTP
        edit_box = app.child_window(control_type="Edit")
        if not edit_box.exists() or not edit_box.is_visible() or not edit_box.is_enabled():
            print("Поле ввода кода не найдено или недоступно.")
            return False
        edit_box.set_text(str(code))
        print("TOTP код введён.")

        profile_connect_dialog = app.child_window(title_re=".*Profile Connect.*", control_type="Window")
        if not profile_connect_dialog.exists():
            # Альтернативно ищем Custom или GroupBox с названием Profile Connect
            profile_connect_dialog = app.child_window(title_re=".*Profile Connect.*", control_type="Custom")
        if not profile_connect_dialog.exists():
            print("Контейнер Profile Connect не найден, ищем кнопки по стандарту.")

        container = profile_connect_dialog if profile_connect_dialog.exists() else edit_box.parent()
        buttons = container.children(control_type="Button")

        connect_buttons = [btn for btn in buttons if
                           "connect" in btn.window_text().lower() and btn.is_visible() and btn.is_enabled()]

        if len(connect_buttons) >= 2:
            connect_buttons[1].click_input()
            print("Вторая кнопка Connect в Profile Connect нажата.")
            return True
        elif len(connect_buttons) == 1:
            connect_buttons[0].click_input()
            print("Найдена только одна кнопка Connect в контейнере, она нажата.")
            return True
        else:
            print("Кнопка Connect в контейнере не найдена.")
            return False

    except Exception as e:
        print(f"Ошибка при вводе 2FA и повторном нажатии Connect: {e}")
        return False


def vpn_connect_check(ip, attempts=2, interval=0.5):
    """
    Пингует IP-адрес с заданным количеством попыток и интервалом.

    :param ip: IP-адрес для пинга
    :param attempts: количество попыток (по умолчанию 3)
    :param interval: интервал между попытками в секундах (по умолчанию 1)
    :return: True если хотя бы один пинг успешен, False если все неудачны
    """

    for attempt in range(1, attempts + 1):

        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if "TTL=" in result.stdout:
            print(f"Ping {ip} успешен.")
            return True
        else:
            print(f"Ping {ip} неудачен.")
            if attempt < attempts:
                time.sleep(interval)

    print(f"Все {attempts} попытки пинга {ip} неудачны.")
    return False


# # def vpn_connect_with_retries(ip, totp_code, max_attempts=3, ping_interval=0.5, max_pings=3):
#     """
#     :param ip: IP-адрес для пинга
#     :param totp_code: код двухфакторки
#     :param max_attempts: максимальное число повторных вводов 2FA
#     :param ping_interval: интервал пинга в секундах
#     :param max_pings: число пингов для проверки перед повтором 2FA
#     """
#
#     attempt = 0
#     while attempt < max_attempts:
#         ping_fail_count = 0
#         for i in range(max_pings):
#             # Пинг ip один раз
#             result = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], stdout=subprocess.PIPE,
#                                     stderr=subprocess.PIPE, text=True)
#             if "TTL=" in result.stdout:
#                 print(f"Ping {ip} успешен.")
#                 return True
#             else:
#                 print(f"Ping {ip} неудачен. Попытка {i + 1} из {max_pings}.")
#                 ping_fail_count += 1
#             time.sleep(ping_interval)
#
#         if ping_fail_count == max_pings:
#             print(f"Пинг не удался {max_pings} раз. Повтор ввода 2FA кода. Попытка {attempt + 1} из {max_attempts}.")
#
#             click_pritunl_connect()
#             input_2fa_code_and_reconnect(totp_code)
#             time.sleep(5)
#             ip = get_first_tap_adapter()
#         attempt += 1
#
#     print("Максимальное число попыток ввода 2FA исчерпано. Подключение не установлено.")
#     return False

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
    keywords = ["TAP-Windows Adapter V9", "Pritunl"]  # шаблоны адаптеров VPN
    adapters = find_adapters_by_keyword(keywords)
    status = check_adapters_status(adapters)
    return any(state == "Connected" for state in status.values())

# # def get_first_tap_adapter():
#
#     adapters = ifaddr.get_adapters()
#     tap_adapters = []
#
#     # Собираем все TAP-Windows Adapter V9
#     for adapter in adapters:
#         adapter_name = adapter.nice_name
#
#         if "TAP-Windows Adapter V9" in adapter_name:
#             for ip in adapter.ips:
#                 try:
#                     ip_obj = ipaddress.ip_address(ip.ip)
#                     if isinstance(ip_obj, ipaddress.IPv4Address):
#                         tap_adapters.append((adapter_name, ip.ip))
#                         break
#                 except ValueError:
#                     continue
#
#     # Находим первый (без номера или с наименьшим номером)
#     if tap_adapters:
#         # Сортируем: сначала без номера, потом по номеру
#         tap_adapters.sort(key=lambda x: (
#             '#' in x[0],  # Сначала без #
#             int(x[0].split('#')[1]) if '#' in x[0] else 0  # Потом по номеру
#         ))
#
#         first_adapter = tap_adapters[0]
#         print(first_adapter[1])
#         return first_adapter[1]
#
#     print("TAP-Windows Adapter V9 не найден")
#     return None
