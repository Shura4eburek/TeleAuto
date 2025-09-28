from pywinauto import Desktop

app = Desktop(backend="uia").window(title_re=".*Pritunl Client.*")
app.wait("exists ready", timeout=20)
app.set_focus()

# Вывести все кнопки с их названиями
buttons = app.descendants(control_type="Button")
for idx, btn in enumerate(buttons):
    print(f"#{idx} - '{btn.window_text()}' - {btn}")

# Попробовать найти кнопку Connect со сниженой точностью
for btn in buttons:
    if "connect" in btn.window_text().lower():
        print(f"Найдена кнопка для connect: '{btn.window_text()}'")
        btn.click_input()
        print("Нажали кнопку Connect")
        break
else:
    print("Кнопка Connect не найдена")
