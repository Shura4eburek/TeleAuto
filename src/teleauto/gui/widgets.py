import sys
import customtkinter as ctk
from PIL import Image, ImageDraw
from src.teleauto.localization import tr
from .constants import ROW_HEIGHT, CORNER_RADIUS, FRAME_BG, BORDER_COLOR


# --- Icon Generator ---
class IconGenerator:
    @staticmethod
    def get_icon(lang_code, size=(30, 20)):
        scale = 4
        w, h = size[0] * scale, size[1] * scale
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if lang_code == "ua":
            draw.rectangle((0, 0, w, h / 2), fill="#0057B8")
            draw.rectangle((0, h / 2, w, h), fill="#FFD700")
        elif lang_code == "en":
            for i in range(7):
                color = "#B22234" if i % 2 == 0 else "white"
                step = h / 7
                draw.rectangle((0, i * step, w, (i + 1) * step), fill=color)
            draw.rectangle((0, 0, w * 0.4, h * 0.5), fill="#3C3B6E")
        elif lang_code == "ru":
            c = "#8B4513"
            draw.ellipse((w * 0.1, h * 0.5, w * 0.9, h * 0.95), fill=c)
            draw.ellipse((w * 0.2, h * 0.3, w * 0.8, h * 0.7), fill=c)
            draw.ellipse((w * 0.35, h * 0.1, w * 0.65, h * 0.4), fill=c)
            draw.ellipse((w * 0.35, h * 0.45, w * 0.45, h * 0.55), fill="white")
            draw.ellipse((w * 0.55, h * 0.45, w * 0.65, h * 0.55), fill="white")
            draw.point((w * 0.4, h * 0.5), fill="black")
            draw.point((w * 0.6, h * 0.5), fill="black")

        img = img.resize(size, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)


# --- Language Selector ---
class LanguageSelector(ctk.CTkFrame):
    def __init__(self, master, current_lang, callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.callback = callback
        self.buttons = {}

        langs = ["ru", "en", "ua"]
        for i, lang in enumerate(langs):
            icon = IconGenerator.get_icon(lang)
            color = "#3B8ED0" if lang == current_lang else "#2B2B2B"
            hover = "#36719F" if lang == current_lang else "#3A3A3A"
            btn = ctk.CTkButton(self, text="", image=icon, width=50, height=30,
                                fg_color=color, hover_color=hover,
                                command=lambda l=lang: self.on_click(l))
            btn.grid(row=0, column=i, padx=5)
            self.buttons[lang] = btn

    def on_click(self, lang):
        for l, btn in self.buttons.items():
            if l == lang:
                btn.configure(fg_color="#3B8ED0", hover_color="#36719F")
            else:
                btn.configure(fg_color="#2B2B2B", hover_color="#3A3A3A")
        self.callback(lang)


# --- LED Circle ---
class LEDCircle(ctk.CTkLabel):
    def __init__(self, master, size=15, fg_color="transparent", **kwargs):
        super().__init__(master, text="", width=size, height=size, fg_color=fg_color, **kwargs)
        self.size = size
        self.colors = {
            "off": "#151515", "shadow": "#111111",
            "working": "#FFD700", "working_dim": "#8B7500",
            "success": "#00DD00", "error": "#FF4444"
        }
        self._state = "off"
        self._blink_job = None
        self._blink_state = False
        self._images = {}
        for k, c in self.colors.items():
            if k != "shadow": self._images[k] = self._draw_circle(c)
        self.set_state("off")

    def _draw_circle(self, color):
        scale = 4;
        s = int(self.size * scale);
        pad = int(4 * scale)
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, s - 1, s - 1), fill=self.colors["shadow"])
        draw.ellipse((pad, pad, s - pad - 1, s - pad - 1), fill=color)
        img = img.resize((self.size, self.size), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(self.size, self.size))

    def start_blinking(self):
        if self._blink_job is None: self._blink_loop()

    def stop_blinking(self):
        if self._blink_job: self.after_cancel(self._blink_job); self._blink_job = None

    def _blink_loop(self):
        key = "working" if self._blink_state else "working_dim"
        self.configure(image=self._images[key])
        self._blink_state = not self._blink_state
        self._blink_job = self.after(600, self._blink_loop)

    def set_state(self, state):
        self.stop_blinking();
        self._state = state
        if state == "waiting":
            self.start_blinking()
        else:
            self.configure(image=self._images.get(state, self._images["off"]))


# --- Title & Status Boxes ---
class TitleBox(ctk.CTkFrame):
    def __init__(self, master, title, **kwargs):
        super().__init__(master, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                         fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR, **kwargs)
        self.pack_propagate(False)
        self.led = LEDCircle(self, size=15, fg_color=FRAME_BG)
        self.led.place(x=10, rely=0.5, anchor="w")
        self.label = ctk.CTkLabel(self, text=title, text_color="#E0E0E0", font=ctk.CTkFont(size=13, weight="bold"))
        self.label.place(x=33, rely=0.53, anchor="w")

    def set_led(self, state): self.led.set_state(state)


class StatusBox(ctk.CTkFrame):
    def __init__(self, master, text_key="status_waiting", **kwargs):
        super().__init__(master, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                         fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR, **kwargs)
        self.pack_propagate(False)
        self.text_key = text_key
        self.label = ctk.CTkLabel(self, text=tr(text_key), text_color="#777777", font=ctk.CTkFont(size=12))
        self.label.place(relx=0.5, rely=0.53, anchor="center")

    def set_text_key(self, key, state):
        self.text_key = key
        self.label.configure(text=tr(key))
        if state == "success":
            self.label.configure(text_color="#44DD44")
        elif state == "error":
            self.label.configure(text_color="#FF5555")
        elif state == "working":
            self.label.configure(text_color="#FFD700")
        else:
            self.label.configure(text_color="#777777")


# --- Settings Group ---
class SettingsGroup(ctk.CTkFrame):
    def __init__(self, master, title_key, **kwargs):
        super().__init__(master, fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR,
                         corner_radius=CORNER_RADIUS, **kwargs)
        self.title_key = title_key
        self.grid_columnconfigure(1, weight=1)
        self.label = ctk.CTkLabel(self, text=tr(title_key), text_color="#AAAAAA",
                                  font=ctk.CTkFont(size=11, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 5))

    def refresh_text(self):
        self.label.configure(text=tr(self.title_key))


# --- Logger ---
class TextboxLogger:
    def __init__(self, textbox):
        self.textbox = textbox
        self.stdout = sys.stdout

    def write(self, message):
        self.stdout.write(message)
        self.textbox.after(0, self.write_to_gui, message)

    def write_to_gui(self, message):
        try:
            if self.textbox.winfo_exists():
                self.textbox.insert(ctk.END, message)
                self.textbox.see(ctk.END)
        except:
            pass

    def flush(self):
        self.stdout.flush()