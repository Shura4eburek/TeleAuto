import sys

# Размеры и геометрия
ROW_HEIGHT = 35
CORNER_RADIUS = 6

# Цвета
FRAME_BG = "#181818"
BORDER_COLOR = "#333333"

# Шрифты
EMOJI_FONT_FAMILY = "Segoe UI Emoji" if sys.platform == "win32" else "Apple Color Emoji"
EMOJI_FONT = (EMOJI_FONT_FAMILY, 12)