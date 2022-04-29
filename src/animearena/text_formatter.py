from dataclasses import dataclass
import importlib.resources
from PIL import ImageFont


with importlib.resources.path('animearena.resources', "Basic-Regular.ttf") as path:
    FONT = ImageFont.truetype(str(path), size = 16)



@dataclass
class WordData:
    length: int
    word: str

def get_lines(input: str, max_width: int) -> list[str]:
    

    words = input.split()
    word_data = []
    length = -4
    for word in words:
        length += 4
        width, _ = FONT.getsize(word)
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
    

