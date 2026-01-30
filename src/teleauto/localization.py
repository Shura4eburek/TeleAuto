# src/teleauto/localization.py
import locale

# Глобальная переменная для текущего языка
CURRENT_LANG = "ru"

LANG_CODES = {
    "Russian": "ru",
    "English": "en",
    "Ukrainian": "ua"
}

LANG_NAMES = {v: k for k, v in LANG_CODES.items()}

TRANSLATIONS = {
    "ru": {
        "window_title_setup": "Первоначальная настройка",
        "window_title_settings": "Настройки",
        "window_title_pin": "Вход",

        "lang_label": "Язык / Language",
        "group_security": "Безопасность",
        "group_vpn": "Настройки VPN (Pritunl)",
        "group_tm": "Настройки Telemart",
        "group_access": "Доступ",
        "group_time": "Синхронизация времени",

        "pin_label": "Придумайте PIN-код:",
        "pin_repeat": "Повторите PIN-код:",
        "pin_enter_msg": "PIN-код",
        "unlock_btn": "Разблокировать",

        "auto_start_tm": "Авто-запуск Telemart",
        "tm_path_label": "Путь к Telemart (.exe):",
        "login": "Логин:",
        "password": "Пароль:",

        "save_btn": "Сохранить и Запустить",
        "save_changes_btn": "Сохранить изменения",
        "delete_btn": "Сброс данных",

        "offset_label": "Ручное смещение (сек):",
        "offset_hint": "(коррекция +/- секунд)",
        "label_pin_short": "PIN:",

        "error_pin_mismatch": "PIN-коды не совпадают!",
        "error_wrong_pin": "Неверный PIN-код!",
        "error_no_tm_path": "Путь к Telemart не указан!",
        "delete_confirm": "Вы уверены? Это удалит все сохраненные данные и закроет программу.",

        "restart_title": "Язык изменен",
        "restart_msg": "Пожалуйста, перезапустите приложение, чтобы применить язык полностью.",

        "btn_start": "Start",
        "btn_cancel": "Cancel",
        "btn_disconnect": "Disconnect",
        "net_status_label": "Интернет:",
        "net_ping_label": "Ping:",

        "status_waiting": "Ожидание...",
        "status_working": "Работа...",
        "status_success": "Успешно",
        "status_error": "Ошибка",
        "status_active": "Активен",
        "status_connected": "Подключен",
        "status_off": "Отключен",
        "update_label": "Доступно обновление!",
        "update_actual": "Версия актуальна",

        "log_system_start": "--- Готов к запуску ---",
        "log_op_cancelled": "Операция отменена пользователем.",

        "error_no_profiles": "Профили не найдены. Нажмите 'Connect' в главном меню!",

        # --- TELEMART LOGS ---
        "log_tm_launching": "Запуск Telemart...",
        "log_tm_launched": "Telemart запущен.",
        "log_tm_update_cycle": "Цикл обновления Telemart...",
        "log_tm_wait_login": "Ожидание окна входа...",
        "log_tm_window_not_found": "Окно входа не найдено...",
        "log_tm_login_found": "Окно входа найдено!",
        "log_tm_performing_login": "Выполняется вход...",
        "log_tm_login_entered": "Логин введен.",
        "log_tm_pass_entered": "Пароль введен.",
        "log_tm_btn_clicked": "Кнопка нажата.",
        "log_tm_login_ok": "Успешный вход в Telemart.",

        "vpn_instruction": (
            "⚠️ Инструкция по настройке VPN:\n\n"
            "1. Завершите эту настройку и нажмите 'Сохранить'.\n"
            "2. В главном окне нажмите кнопку 'Connect'.\n"
            "3. Программа просканирует Pritunl и найдет профили.\n"
            "4. После этого зайдите в Настройки (⚙️) и\n"
            "   введите секреты 2FA для найденных профилей."
        )
    },

    "en": {
        "window_title_setup": "Initial Setup",
        "window_title_settings": "Settings",
        "window_title_pin": "Login",

        "lang_label": "Language",
        "group_security": "Security",
        "group_vpn": "VPN Settings (Pritunl)",
        "group_tm": "Telemart Settings",
        "group_access": "Access",
        "group_time": "Time Synchronization",

        "pin_label": "Create PIN:",
        "pin_repeat": "Repeat PIN:",
        "pin_enter_msg": "Enter PIN",
        "unlock_btn": "Unlock",

        "auto_start_tm": "Auto-start Telemart",
        "tm_path_label": "Telemart Path (.exe):",
        "login": "Login:",
        "password": "Password:",

        "save_btn": "Save and Launch",
        "save_changes_btn": "Save Changes",
        "delete_btn": "Reset Data",

        "offset_label": "Manual Offset (sec):",
        "offset_hint": "(+/- seconds correction)",
        "label_pin_short": "PIN:",

        "error_pin_mismatch": "PIN codes do not match!",
        "error_wrong_pin": "Invalid PIN!",
        "error_no_tm_path": "Telemart path is missing!",
        "delete_confirm": "Are you sure? This will delete all data and close the app.",

        "restart_title": "Language Changed",
        "restart_msg": "Please restart the app to apply changes fully.",

        "btn_start": "Start",
        "btn_cancel": "Cancel",
        "btn_disconnect": "Disconnect",
        "net_status_label": "Internet:",
        "net_ping_label": "Ping:",

        "status_waiting": "Waiting...",
        "status_working": "Working...",
        "status_success": "Success",
        "status_error": "Error",
        "status_active": "Active",
        "status_connected": "Connected",
        "status_off": "Disconnected",
        "update_label": "Update Available!",
        "update_actual": "Up to date",

        "log_system_start": "--- Ready to start ---",
        "log_op_cancelled": "Operation cancelled by user.",

        "error_no_profiles": "Profiles not found. Click 'Connect' in main menu first!",

        # --- TELEMART LOGS ---
        "log_tm_launching": "Launching Telemart...",
        "log_tm_launched": "Telemart launched.",
        "log_tm_update_cycle": "Telemart update cycle...",
        "log_tm_wait_login": "Waiting for login window...",
        "log_tm_window_not_found": "Login window not found...",
        "log_tm_login_found": "Login window found!",
        "log_tm_performing_login": "Performing login...",
        "log_tm_login_entered": "Login entered.",
        "log_tm_pass_entered": "Password entered.",
        "log_tm_btn_clicked": "Button clicked.",
        "log_tm_login_ok": "Telemart login successful.",

        "vpn_instruction": (
            "⚠️ VPN Setup Instructions:\n\n"
            "1. Finish this setup and click 'Save'.\n"
            "2. Click the 'Connect' button in the main window.\n"
            "3. The app will scan Pritunl and discover profiles.\n"
            "4. Go back to Settings (⚙️) and enter\n"
            "   2FA secrets for the discovered profiles."
        )
    },

    "ua": {
        "window_title_setup": "Початкове налаштування",
        "window_title_settings": "Налаштування",
        "window_title_pin": "Вхід",

        "lang_label": "Мова / Language",
        "group_security": "Безпека",
        "group_vpn": "Налаштування VPN (Pritunl)",
        "group_tm": "Налаштування Telemart",
        "group_access": "Доступ",
        "group_time": "Синхронізація часу",

        "pin_label": "Створіть PIN-код:",
        "pin_repeat": "Повторіть PIN-код:",
        "pin_enter_msg": "Введіть PIN-код",
        "unlock_btn": "Розблокувати",

        "auto_start_tm": "Авто-запуск Telemart",
        "tm_path_label": "Шлях до Telemart (.exe):",
        "login": "Логін:",
        "password": "Пароль:",

        "save_btn": "Зберегти та Запустити",
        "save_changes_btn": "Зберегти зміни",
        "delete_btn": "Скидання даних",

        "offset_label": "Ручне зміщення (сек):",
        "offset_hint": "(корекція +/- секунд)",
        "label_pin_short": "PIN:",

        "error_pin_mismatch": "PIN-коди не співпадають!",
        "error_wrong_pin": "Невірний PIN-код!",
        "error_no_tm_path": "Шлях до Telemart не вказано!",
        "delete_confirm": "Ви впевнені? Це видалить усі дані та закриє програму.",

        "restart_title": "Мову змінено",
        "restart_msg": "Будь ласка, перезапустіть програму для повного застосування мови.",

        "btn_start": "Start",
        "btn_cancel": "Cancel",
        "btn_disconnect": "Disconnect",
        "net_status_label": "Інтернет:",
        "net_ping_label": "Ping:",

        "status_waiting": "Очікування...",
        "status_working": "Робота...",
        "status_success": "Успішно",
        "status_error": "Помилка",
        "status_active": "Активний",
        "status_connected": "Підключено",
        "status_off": "Вимкнено",
        "update_label": "Є оновлення!",
        "update_actual": "Версія актуальна",

        "log_system_start": "--- Готовий до запуску ---",
        "log_op_cancelled": "Операцію скасовано користувачем.",

        "error_no_profiles": "Профілі не знайдено. Натисніть 'Connect' у головному меню!",

        # --- TELEMART LOGS ---
        "log_tm_launching": "Запуск Telemart...",
        "log_tm_launched": "Telemart запущено.",
        "log_tm_update_cycle": "Цикл оновлення Telemart...",
        "log_tm_wait_login": "Очікування вікна входу...",
        "log_tm_window_not_found": "Вікно входу не знайдено...",
        "log_tm_login_found": "Вікно входу знайдено!",
        "log_tm_performing_login": "Виконується вхід...",
        "log_tm_login_entered": "Логін введено.",
        "log_tm_pass_entered": "Пароль введено.",
        "log_tm_btn_clicked": "Кнопку натиснуто.",
        "log_tm_login_ok": "Успішний вхід у Telemart.",

        "vpn_instruction": (
            "⚠️ Інструкція з налаштування VPN:\n\n"
            "1. Завершіть це налаштування та натисніть 'Зберегти'.\n"
            "2. У головному вікні натисніть кнопку 'Connect'.\n"
            "3. Програма просканує Pritunl та знайде профілі.\n"
            "4. Поверніться до Налаштувань (⚙️) та\n"
            "   введіть секрети 2FA для знайдених профілів."
        )
    }
}


def get_system_lang():
    try:
        sys_lang = locale.getdefaultlocale()[0]
        if sys_lang:
            if "ru" in sys_lang.lower(): return "ru"
            if "uk" in sys_lang.lower() or "ua" in sys_lang.lower(): return "ua"
    except:
        pass
    return "en"


def set_language(lang_code):
    global CURRENT_LANG
    if lang_code in TRANSLATIONS:
        CURRENT_LANG = lang_code
    else:
        CURRENT_LANG = "en"


def get_language():
    return CURRENT_LANG


def tr(key, **kwargs):
    # Отримуємо переклад
    text = TRANSLATIONS.get(CURRENT_LANG, {}).get(key, key)

    # Якщо передані аргументи (наприклад, current=1), підставляємо їх
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            # Якщо підставити не вийшло (або в рядку немає placeholder-ів), повертаємо текст як є
            return text

    return text