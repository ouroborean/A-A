
import importlib.resources
from pathlib import Path
import sdl2.sdlttf
import os

FONT_FILENAME = "Basic-Regular.ttf"

def init_font(size: int):
    with importlib.resources.path('animearena.resources',
                                  FONT_FILENAME) as path:
        return sdl2.sdlttf.TTF_OpenFont(str.encode(os.fspath(path)), size)

def get_path(file_name: str) -> Path:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return path