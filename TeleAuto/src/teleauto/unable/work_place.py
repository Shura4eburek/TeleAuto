from pywinauto import Desktop
import time

def work_place():
    app_window = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
    app_window.wait("exists ready", timeout=20)

    # ====== Место работы ======
    place_combo = app_window.child_window(title="Место работы", control_type="ComboBox")
    place_combo.click_input()  # раскрываем список
    time.sleep(0.3)
    place_item = place_combo.child_window(title="Киев (Космополит)", control_type="ListItem")
    place_item.click_input()   # выбираем элемент
    time.sleep(0.3)

    # ====== Тип устройства ======
    type_combo = app_window.child_window(title="Тип устройства", control_type="ComboBox")
    type_combo.click_input()
    time.sleep(0.3)
    type_item = type_combo.child_window(title="ПК", control_type="ListItem")
    type_item.click_input()

    # ====== Нажимаем кнопку OK ======
    #ok_button = app_window.child_window(title="OK", control_type="Button")
    #ok_button.click_input()
