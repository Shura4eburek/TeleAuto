import sys
from pywinauto import Desktop
import readchar

OPTIONS = [
    ("Telemart.Client", r"^Telemart\.Client", "telemart_tree.txt"),
    ("Pritunl", r".*Pritunl.*", "pritunl_tree.txt")
]

def print_windows():
    print("Сейчас открыты окна:")
    for w in Desktop(backend="uia").windows():
        print(" -", w.window_text())

def save_tree(title_regex, filename):
    spec = Desktop(backend="uia").window(title_re=title_regex)
    wrapper = spec.wait("exists ready", timeout=20)
    with open(filename, "w", encoding="utf-8") as f:
        old_stdout = sys.stdout
        sys.stdout = f
        try:
            spec.print_control_identifiers(depth=None)
        finally:
            sys.stdout = old_stdout
    print(f"Дерево элементов для {filename} записано.")

def choose_option(prompt, options):
    print(prompt)
    index = 0
    while True:
        for i, (name, _, _) in enumerate(options):
            prefix = "→ " if i == index else "  "
            print(prefix + name)
        key = readchar.readkey()
        if key == readchar.key.UP:
            index = (index - 1) % len(options)
        elif key == readchar.key.DOWN:
            index = (index + 1) % len(options)
        elif key == readchar.key.ENTER:
            return index
        print("\033c", end="")  # очистка экрана

def main():
    print_windows()
    first_choice = choose_option("Выберите программу для сохранения дерева (стрелками ↑ ↓, Enter - подтвердить):", OPTIONS)
    title1, filename1 = OPTIONS[first_choice][1], OPTIONS[first_choice][2]
    save_tree(title1, filename1)

    print("Хотите вывести дерево второго приложения тоже?")
    second_choice = choose_option("Выберите второе приложение (стрелками ↑ ↓, Enter - подтвердить):", OPTIONS)
    if second_choice == first_choice:
        second_choice = (second_choice + 1) % len(OPTIONS)
    title2, filename2 = OPTIONS[second_choice][1], OPTIONS[second_choice][2]
    save_tree(title2, filename2)

if __name__ == "__main__":
    main()
