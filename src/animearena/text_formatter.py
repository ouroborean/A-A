from dataclasses import dataclass
import importlib.resources
from PIL import ImageFont


with importlib.resources.path('animearena.resources', "Basic-Regular.ttf") as path:
    FONT = ImageFont.truetype(str(path), size = 16)

loaded_fonts = {}

@dataclass
class WordData:
    length: int
    word: str

def load_fontsize(fontsize):
    with importlib.resources.path('animearena.resources', "Basic-Regular.ttf") as path:
        loaded_fonts[fontsize] = ImageFont.truetype(str(path), size = fontsize)

def get_character_width(fontsize, char):
    if not fontsize in loaded_fonts:
        load_fontsize(fontsize)
    font = loaded_fonts[fontsize]
    return font.getsize(char)[0]

def get_string_width(fontsize, string):
    width = 0
    for char in string:
        width += get_character_width(fontsize, char)
    return width

def get_font_height(fontsize):
    if not fontsize in loaded_fonts:
        load_fontsize(fontsize)
    font = loaded_fonts[fontsize]
    height = font.getsize("G")[1]
    height += int(height * 0.15)
    return height

def get_lines(input: str, max_width: int, fontsize: int) -> list[str]:
    

    words = input.split()
    word_data = []
    length = -4
    for word in words:
        length += 4
        width = get_string_width(fontsize, word)
        length += width
        word_data.append(WordData(length, word))
        length = 0
    
    lines = []
    line = []
    current_length = 0
    for word in word_data:
        if (current_length + word.length > max_width):
            lines.append(" ".join(word for word in line))
            line = []
            current_length = 0
        current_length += word.length
        line.append(word.word)
    
    lines.append(" ".join(word for word in line))

    return lines
    

