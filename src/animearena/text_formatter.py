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
    


def get_length(input: str) -> int:
    if input == "a":
        return 9
    elif input == "b":
        return 8
    elif input == "c":
        return 8
    elif input == "d":
        return 9
    elif input == "e":
        return 9
    elif input == "f":
        return 5
    elif input == "g":
        return 9
    elif input == "h":
        return 8
    elif input == "i":
        return 3
    elif input == "j":
        return 4
    elif input == "k":
        return 7
    elif input == "l":
        return 3
    elif input == "m":
        return 14
    elif input == "n":
        return 9
    elif input == "o":
        return 9
    elif input == "p":
        return 8
    elif input == "q":
        return 9
    elif input == "r":
        return 7
    elif input == "s":
        return 7
    elif input == "t":
        return 6
    elif input == "u":
        return 8
    elif input == "v":
        return 8
    elif input == "w":
        return 13
    elif input == "x":
        return 9
    elif input == "y":
        return 9
    elif input == "z":
        return 8
    elif input == "A":
        return 9
    elif input == "B":
        return 8
    elif input == "C":
        return 9
    elif input == "D":
        return 9
    elif input == "E":
        return 7
    elif input == "F":
        return 7
    elif input == "G":
        return 9
    elif input == "H":
        return 9
    elif input == "I":
        return 3
    elif input == "J":
        return 5
    elif input == "K":
        return 8
    elif input == "L":
        return 7
    elif input == "M":
        return 11
    elif input == "N":
        return 10
    elif input == "O":
        return 10
    elif input == "P":
        return 8
    elif input == "Q":
        return 9
    elif input == "R":
        return 8
    elif input == "S":
        return 8
    elif input == "T":
        return 9
    elif input == "U":
        return 9
    elif input == "V":
        return 10
    elif input == "W":
        return 14
    elif input == "X":
        return 9
    elif input == "Y":
        return 8
    elif input == "Z":
        return 8
    elif input == ".":
        return 3
    elif input == ",":
        return 3
    elif input == "-":
        return 5
    elif input == ":":
        return 3
    elif input == "'":
        return 3
    elif input == "(":
        return 5
    elif input == ")":
        return 5
    elif input == " ":
        return 4
    elif input == ":":
        return 3
    elif input == "0":
        return 9
    elif input == "1":
        return 5
    elif input == "2":
        return 8
    elif input == "3":
        return 8
    elif input == "4":
        return 8
    elif input == "5":
        return 6
    elif input == "6":
        return 8
    elif input == "7":
        return 8
    elif input == "8":
        return 8
    elif input == "9":
        return 8
    elif input == "":
        return 0
    else:
        return 0
        

