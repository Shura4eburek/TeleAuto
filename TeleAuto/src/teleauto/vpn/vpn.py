import ipaddress
import time
import re
import subprocess

import ifaddr
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

        # Кнопка подтверждения (Confirm/OK)
        # btn_confirm = app.child_window(control_type="Button",
        #                                title_re="(?i)подключиться|подтвердить|ok|confirm|Connect")
        # if btn_confirm.exists() and btn_confirm.is_visible() and btn_confirm.is_enabled():
        #     btn_confirm.click_input()
        #     print("Кнопка подтверждения нажата.")
        # else:
        #     print("Кнопка подтверждения не найдена или недоступна.")

        # time.sleep(1)  # Ждём обновления интерфейса

        # Поиск контейнера Profile Connect - родителя кнопок Connect
        # Ищем окно-диалог с title или auto_id Profile Connect
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



def vpn_connect_with_retries(ip, totp_code, max_attempts=3, ping_interval=3, max_pings=3):
    """
    Ждёт подключения к VPN, пингует ip каждые ping_interval секунд.
    Если с 5-й попытки пинг не успешен, вызывает input_2fa_func (максимум max_attempts раз).

    :param ip: IP-адрес для пинга
    :param totp_code: код двухфакторки
    :param max_attempts: максимальное число повторных вводов 2FA
    :param ping_interval: интервал пинга в секундах
    :param max_pings: число пингов для проверки перед повтором 2FA
    """

    attempt = 0
    while attempt < max_attempts:
        ping_fail_count = 0
        for i in range(max_pings):
            # Пинг ip один раз
            result = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            if "TTL=" in result.stdout:
                print(f"Ping {ip} успешен.")
                return True
            else:
                print(f"Ping {ip} неудачен. Попытка {i + 1} из {max_pings}.")
                ping_fail_count += 1
            time.sleep(ping_interval)

        if ping_fail_count == max_pings:
            print(f"Пинг не удался {max_pings} раз. Повтор ввода 2FA кода. Попытка {attempt + 1} из {max_attempts}.")

            click_pritunl_connect()
            input_2fa_code_and_reconnect(totp_code)
            time.sleep(5)
            ip = get_first_tap_adapter()
        attempt += 1

    print("Максимальное число попыток ввода 2FA исчерпано. Подключение не установлено.")
    return False


def get_first_tap_adapter():
    # try:
    #     import ifaddr
    # except ImportError:
    #     print("Установите библиотеку ifaddr: pip install ifaddr")
    #     return

    adapters = ifaddr.get_adapters()
    tap_adapters = []

    # Собираем все TAP-Windows Adapter V9
    for adapter in adapters:
        adapter_name = adapter.nice_name

        if "TAP-Windows Adapter V9" in adapter_name:
            for ip in adapter.ips:
                try:
                    ip_obj = ipaddress.ip_address(ip.ip)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        tap_adapters.append((adapter_name, ip.ip))
                        break
                except ValueError:
                    continue

    # Находим первый (без номера или с наименьшим номером)
    if tap_adapters:
        # Сортируем: сначала без номера, потом по номеру
        tap_adapters.sort(key=lambda x: (
            '#' in x[0],  # Сначала без #
            int(x[0].split('#')[1]) if '#' in x[0] else 0  # Потом по номеру
        ))

        first_adapter = tap_adapters[0]
        print(first_adapter[1])
        return first_adapter[1]

    print("TAP-Windows Adapter V9 не найден")
    return None