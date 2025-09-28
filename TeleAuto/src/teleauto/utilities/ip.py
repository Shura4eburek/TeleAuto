import subprocess
import time


# def get_first_tap_adapter():
#     # try:
#     #     import ifaddr
#     # except ImportError:
#     #     print("Установите библиотеку ifaddr: pip install ifaddr")
#     #     return
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
#         print(f"{first_adapter[1]}")
#         return first_adapter
#
#     print("TAP-Windows Adapter V9 не найден")
#     return None

def vpn_connect_with_retries(ip, max_attempts=3, ping_interval=3, max_pings=5):
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
            # if not input_2fa_func(totp_code):
            #     print("Повторный ввод 2FA не удался.")
            #     attempt += 1
            #     continue
            # else:
            #     print("Повторный ввод 2FA успешен.")
            # click_pritunl_connect()
            # input_2fa_code_and_reconnect(totp_code)
        attempt += 1

    print("Максимальное число попыток ввода 2FA исчерпано. Подключение не установлено.")
    return False


if __name__ == "__main__":
    # get_first_tap_adapter()
    vpn_connect_with_retries("192.168.252.143")