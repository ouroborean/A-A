"""Core game engine logic."""
import ctypes
import enum
import logging
import operator
import textwrap
import importlib.resources
from typing import Iterator
from typing import Literal
from typing import MutableMapping
from typing import Optional
from typing import Tuple
from typing import Union
from PIL import Image, ImageDraw
import sdl2
import sdl2.ext
import sdl2.sdlttf
import sdl2.surface
import itertools
from sdl2 import endian
from pathlib import Path
from animearena.animation import JoinAnimation, SplitAnimation
from animearena.text_formatter import get_lines, get_font_height
def get_image_from_path(file_name: str) -> Image:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return Image.open(path)

RESOURCES = Path(__file__).parent.parent.parent / "resources"
WHITE = sdl2.SDL_Color(255, 255, 255)


def sat_subtract(subtractor: int, subtractee: int) -> int:
    subtractee -= subtractor
    if subtractee < 0:
        subtractee = 0
    return subtractee


def get_mouse_position() -> Tuple[int, int]:
    x, y = ctypes.c_int(0), ctypes.c_int(0)
    sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
    return (x.value, y.value)

class Scene:
    """Scene assets, draw regions, and associated game state."""
    surfaces: MutableMapping[str, sdl2.SDL_Surface]
    region: "Region"
    sprite_factory: sdl2.ext.SpriteFactory
    ui_factory: sdl2.ext.UIFactory
    triggered_event: bool
    font: None
    animations: list
    animation_lock: list
    animation_locked: bool

    def __init__(self, sprite_type: Union[Literal[0], Literal[1]]):
        self.animations = []
        self.animation_lock = []
        self.animation_locked = False
        self.region = Region()
        self.animation_region = Region()
        self.sprite_factory = sdl2.ext.SpriteFactory(sprite_type, free=True)
        self.ui_factory = sdl2.ext.UIFactory(self.sprite_factory, free=True)
        self.surfaces = dict()
        self.window_closing = False
        self.window_up = False
        self.triggered_event = False

    def add_animation(self, animation):
        self.animations.append(animation)
        if animation.lock:
            logging.debug("Adding a locked animation of type %s", type(animation))
            self.animation_locked = True
            self.animation_lock.append(animation)

    def remove_animation(self, animation):
        self.animations.remove(animation)

    def check_animation_lock(self, animation):
        logging.debug("Checking animation lock for animation of type %s", type(animation))
        self.animation_lock.remove(animation)
    
    def end_animations(self):
        end_funcs = list()
        for animation in self.animations:
            for func in animation.end_funcs:
                end_funcs.append(func)
        self.animations.clear()
        self.animation_lock.clear()
        self.animation_locked = False
        self.animation_region.clear()
        for func in end_funcs:
            func[0](*func[1])

    def progress_animations(self):
        self.animation_region.clear()
        for animation in self.animations:
            if not type(animation) == JoinAnimation and not type(animation) == SplitAnimation:
                animation.progress_frame_timer()
                self.animation_region.add_sprite(animation.current_sprite, animation.display_x, animation.display_y)
    
    def check_animations(self):
        for animation in self.animations:
            if animation.has_ended:
                animation.end()
        
        if not self.animation_lock:
            self.animation_locked = False

    def load_assets(self, **kwargs: str):
        log = logging.getLogger(__name__)
        for (k, v) in kwargs.items():
            self.surfaces[k] = get_image_from_path(v)

    def renderables(self) -> Iterator[sdl2.ext.Sprite]:
        for it in [iter(self.region), iter(self.animation_region)]:
            for element in it:
                yield element
        

    def eventables(self) -> Iterator[sdl2.ext.Sprite]:
        return self.region.eventables()

    def render_text(self, font, text, color, target, x, y, flow = False, target_width = 0, fontsize = 0):
        if not flow:
            text_surface = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(text), color)
            sdl2.surface.SDL_BlitSurface(text_surface, None, target.surface, sdl2.SDL_Rect(x, y))
            sdl2.SDL_FreeSurface(text_surface)
        else:
            lines = get_lines(text, target_width, fontsize)
            line_height = get_font_height(fontsize)
            for i, line in enumerate(lines):
                text_surface = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), color)
                sdl2.surface.SDL_BlitSurface(text_surface, None, target.surface, sdl2.SDL_Rect(x, y + (i * line_height)))
                sdl2.SDL_FreeSurface(text_surface)
        return target
    
    def render_bordered_text(self, font, text, color, border_color, target, x, y, thickness, flow = False, target_width = 0, fontsize = 0):
        if not flow:
            text_surf = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(text), border_color)
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, y-thickness))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x,           y-thickness))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, y-thickness))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, y))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, y))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, y+thickness))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x,           y+thickness))
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, y+thickness))
            sdl2.SDL_FreeSurface(text_surf)
            
            text_surf = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(text), color)
            sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x, y))
            sdl2.SDL_FreeSurface(text_surf)
        else:
            lines = get_lines(text, target_width, fontsize)
            line_height = get_font_height(fontsize)
            for i, line in enumerate(lines):
                mod_y = y + (i * line_height)
                text_surf = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), border_color)
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, mod_y-thickness))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x,           mod_y-thickness))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, mod_y-thickness))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, mod_y))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, mod_y))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x-thickness, mod_y+thickness))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x,           mod_y+thickness))
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x+thickness, mod_y+thickness))
                sdl2.SDL_FreeSurface(text_surf)
                
                text_surf = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), color)
                sdl2.surface.SDL_BlitSurface(text_surf, None, target.surface, sdl2.SDL_Rect(x, mod_y))
                sdl2.SDL_FreeSurface(text_surf)
        
        return target
    
    def border_image(self, image, thickness):
        
        w, h = image.size
        
        brush = ImageDraw.Draw(image)
        brush.rectangle([(0, 0), (w, thickness)], fill="black", outline = "black")
        brush.rectangle([(0, 0), (thickness, h)], fill="black", outline = "black")
        brush.rectangle([(w - 2, 0), (w, h)], fill="black", outline = "black")
        brush.rectangle([(0, h - 2), (w, h)], fill="black", outline = "black")
        
        return image
        
    
    def border_sprite(self, sprite, color, thickness):
        
        target_surface = sprite.surface
        height = target_surface.h
        width = target_surface.w
        horizontal_border = self.sprite_factory.from_color(color, (width, thickness))
        vertical_border = self.sprite_factory.from_color(color, (thickness, height))
        
        sdl2.surface.SDL_BlitSurface(horizontal_border.surface, None, sprite.surface, sdl2.SDL_Rect(0, 0))
        sdl2.surface.SDL_BlitSurface(horizontal_border.surface, None, sprite.surface, sdl2.SDL_Rect(0, height - thickness))
        sdl2.surface.SDL_BlitSurface(vertical_border.surface, None, sprite.surface, sdl2.SDL_Rect(0, 0))
        sdl2.surface.SDL_BlitSurface(vertical_border.surface, None, sprite.surface, sdl2.SDL_Rect(width - thickness, 0))
        
        return sprite
    
    def blit_surface(self, target, surface, dest):
        
        sdl2.surface.SDL_BlitSurface(surface, None, target.surface, sdl2.SDL_Rect(*dest))
        
        return target
    
    def add_horizontal_line(self, sprite, color, thickness, length, destination):
        
        line = self.sprite_factory.from_color(color, (length, thickness))
        sdl2.surface.SDL_BlitSurface(line.surface, None, sprite.surface, sdl2.SDL_Rect(*destination))
        
        return sprite

    def get_scaled_surface(self, img, width: int = 0, height: int = 0, flipped=False) -> sdl2.SDL_Surface:
        image = img
        if width != 0 or height != 0:
            image = image.resize((width, height))
        else:
            width, height = (image.size)
        mode = image.mode
        if flipped:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        rmask = gmask = bmask = amask = 0
        if mode in ("1", "L", "P"):
            # 1 = B/W, 1 bit per byte
            # "L" = greyscale, 8-bit
            # "P" = palette-based, 8-bit
            pitch = width
            depth = 8
        elif mode == "RGB":
            # 3x8-bit, 24bpp
            
            if endian.SDL_BYTEORDER == endian.SDL_LIL_ENDIAN:
                rmask = 0x0000FF
                gmask = 0x00FF00
                bmask = 0xFF0000
            else:
                rmask = 0xFF0000
                gmask = 0x00FF00
                bmask = 0x0000FF
            depth = 24
            pitch = width * 3
        elif mode in ("RGBA", "RGBX"):
            # RGBX: 4x8-bit, no alpha
            # RGBA: 4x8-bit, alpha
            
            if endian.SDL_BYTEORDER == endian.SDL_LIL_ENDIAN:
                rmask = 0x000000FF
                gmask = 0x0000FF00
                bmask = 0x00FF0000
                if mode == "RGBA":
                    amask = 0xFF000000
            else:
                rmask = 0xFF000000
                gmask = 0x00FF0000
                bmask = 0x0000FF00
                if mode == "RGBA":
                    amask = 0x000000FF
            depth = 32
            pitch = width * 4
        else:
            # We do not support CMYK or YCbCr for now
            raise TypeError("unsupported image format")
        pxbuf = image.tobytes()
        
        imgsurface = sdl2.ext.surface.SDL_CreateRGBSurfaceFrom(pxbuf, width, height, depth, pitch, rmask, gmask, bmask, amask)
        imgsurface = imgsurface.contents
        imgsurface._pxbuf = pxbuf
        return imgsurface

    def create_selected_version(self, surface: sdl2.SDL_Surface,
                                filter_type: "FilterType") -> sdl2.ext.SoftwareSprite:
        new_sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, clone_surface(surface))

        filter_string = filter_type.name.lower()

        sdl2.surface.SDL_BlitSurface(self.get_scaled_surface(self.surfaces[filter_string]), None, new_sprite.surface,
                                     sdl2.SDL_Rect(0, 0, 0, 0))
        return new_sprite

    def add_sprite_with_border(self, region: "Region", sprite: sdl2.ext.Sprite, border_sprite, x:int, y:int, depth: int=0):
        region.add_sprite(border_sprite, x - 2, y - 2, depth=depth)
        region.add_sprite(sprite, x, y, depth)

    def add_bordered_sprite(self, region: "Region", sprite: sdl2.ext.Sprite, color: sdl2.SDL_Color, x:int, y:int, depth: int=0):
        width, height = sprite.size
        border_sprite = self.sprite_factory.from_color(color, (width+4, height+4))
        region.add_sprite(border_sprite, x - 2, y - 2, depth=depth)
        region.add_sprite(sprite, x, y, depth)

    def update_text_display(self, font, text, text_color, display, blotter, x, y):
        max_width = display.size[0] - (x * 2)
        char_width = 7.3
        chars_per_line = max_width // char_width

        lines = textwrap.wrap(text, chars_per_line)
        sdl2.surface.SDL_BlitSurface(self.get_scaled_surface(blotter), sdl2.SDL_Rect(0, 0, blotter.size[0], blotter.size[1]), display.surface, sdl2.SDL_Rect(0, 0, 0, 0))
        for row, line in enumerate(lines):
            sdl2.surface.SDL_BlitSurface(sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), text_color), None, display.surface,
                                         sdl2.SDL_Rect(x, y + (row * 15), 0, 0))
    
    

    def create_text_display(  # pylint: disable=too-many-arguments
            self,
            font: sdl2.sdlttf.TTF_Font,
            text: str,
            text_color: sdl2.ext.Color,
            background_color: sdl2.ext.Color,
            x: int,
            y: int,
            width: int,
            height: Optional[int] = None) -> sdl2.ext.Sprite:

        # create fake tiny lowercase constants to appease the overlord
        horizontal_margin = x
        max_width = width - (horizontal_margin * 2)
        y_offset = 15
        vertical_margin = 15
        char_width = 7.3
        chars_per_line = max_width // char_width

        # get list of lines from full string based on box width
        # lines = textwrap.wrap(text, chars_per_line)
        lines = get_lines(text, max_width, 16)

        # if height is on auto, then set it to a function of the margin plus
        # the space required for all lines
        if height is None:
            true_height = vertical_margin + (13 * len(lines))
        else:
            true_height = vertical_margin + height

        # create rectangular button using parameter-supplied color as background
        # and specified dimensions
        new_sprite = self.ui_factory.from_color(sdl2.ext.BUTTON,
                                                background_color,
                                                size=(width, true_height))
        # for each line in the list of lines, render that line on the sprite's surface
        for row, line in enumerate(lines):
            text_surface = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), text_color)
            sdl2.surface.SDL_BlitSurface(text_surface, None, new_sprite.surface,
                                         sdl2.SDL_Rect(x, y + (row * y_offset), 0, 0))
            sdl2.SDL_FreeSurface(text_surface)

        return new_sprite

    def create_bordered_font_text_display(  # pylint: disable=too-many-arguments
            self,
            font: sdl2.sdlttf.TTF_Font,
            text: str,
            text_color: sdl2.ext.Color,
            background_color: sdl2.ext.Color,
            x: int,
            y: int,
            width: int,
            height: Optional[int] = None) -> sdl2.ext.Sprite:

        # create fake tiny lowercase constants to appease the overlord
        horizontal_margin = x
        max_width = width - (horizontal_margin * 2)
        y_offset = 15
        vertical_margin = 15
        char_width = 7.3
        chars_per_line = max_width // char_width

        # get list of lines from full string based on box width
        # lines = textwrap.wrap(text, chars_per_line)
        lines = get_lines(text, max_width, 16)

        # if height is on auto, then set it to a function of the margin plus
        # the space required for all lines
        if height is None:
            true_height = vertical_margin + (13 * len(lines))
        else:
            true_height = vertical_margin + height

        # create rectangular button using parameter-supplied color as background
        # and specified dimensions
        new_sprite = self.ui_factory.from_color(sdl2.ext.BUTTON,
                                                background_color,
                                                size=(width, true_height))
        # for each line in the list of lines, render that line on the sprite's surface
        for row, line in enumerate(lines):
            border_text_surface = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), text_color)
            text_surface = sdl2.sdlttf.TTF_RenderText_Blended(font, str.encode(line), WHITE)
            sdl2.surface.SDL_BlitSurface(border_text_surface, None, new_sprite.surface,
                                        sdl2.SDL_Rect(x - 1, y + (row * y_offset) - 1, 0, 0))
            sdl2.surface.SDL_BlitSurface(border_text_surface, None, new_sprite.surface,
                                        sdl2.SDL_Rect(x - 1, y + (row * y_offset) + 1, 0, 0))
            sdl2.surface.SDL_BlitSurface(border_text_surface, None, new_sprite.surface,
                                        sdl2.SDL_Rect(x + 1, y + (row * y_offset) - 1, 0, 0))
            sdl2.surface.SDL_BlitSurface(border_text_surface, None, new_sprite.surface,
                                        sdl2.SDL_Rect(x + 1, y + (row * y_offset) + 1, 0, 0))
            
            sdl2.surface.SDL_BlitSurface(text_surface, None, new_sprite.surface,
                                         sdl2.SDL_Rect(x, y + (row * y_offset), 0, 0))
            sdl2.SDL_FreeSurface(text_surface)

        return new_sprite

class Region:
    """Spatial region on the screen with relative coordinate offsets & spinning rims."""
    x: int
    y: int
    width: int
    height: int
    _regions: list["Region"]
    _sprites: list[sdl2.ext.Sprite]

    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._regions = []
        self._sprites = []

    def __iter__(self) -> Iterator[sdl2.ext.Sprite]:
        yield from self._sprites
        for subregion in self._regions:
            yield from subregion

    def subregion(self, x: int, y: int, width: int, height: int) -> "Region":
        subreg = Region(self.x + x, self.y + y, width, height)
        self._regions.append(subreg)
        return subreg

    def add_sprite(self, sprite: sdl2.ext.Sprite, x: int, y: int, depth: int = 0):
        sprite.x = self.x + x
        sprite.y = self.y + y
        sprite.depth = depth
        self._sprites.append(sprite)
        self._sprites.sort(key=operator.attrgetter('depth'))

    def add_sprite_vertical_center(self, sprite: sdl2.ext.Sprite, x: int, depth: int = 0):
        sprite.x = self.x + x
        sprite.depth = depth

        region_center = self.height // 2
        sprite_center = sprite.size[1] // 2

        sprite.y = self.y + region_center - sprite_center

        self._sprites.append(sprite)
        self._sprites.sort(key=operator.attrgetter('depth'))

    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def clear(self):
        """Removes all sprites from this region and all sub-regions"""
        self._sprites.clear()
        
        for subregion in self._regions:
            subregion.clear()

    def from_bottom(self, y: int) -> int:
        return self.height - y

    def from_right(self, x: int) -> int:
        return self.width - x

    def eventables(self) -> Iterator[sdl2.ext.Sprite]:
        for subregion in reversed(self._regions):
            yield from subregion.eventables()
        yield from filter(is_eventable, reversed(self._sprites))


def is_eventable(sprite: sdl2.ext.Sprite) -> bool:
    """"Determines whether a sprite is configured to be an event handler or not."""
    return (isinstance(sprite, sdl2.ext.Sprite) and hasattr(sprite, "events")
            and hasattr(sprite, "uitype"))


def clone_surface(surface: sdl2.SDL_Surface) -> sdl2.SDL_Surface:
    return sdl2.SDL_DuplicateSurface(surface).contents


@enum.unique
class FilterType(enum.IntEnum):
    """A component for denoting which transparent color filter to apply to surfaces"""
    SELECTED = 0
    ALLY = 1
    ENEMY = 2
    LOCKED = 3
