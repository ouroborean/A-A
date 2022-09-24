import sdl2
import sdl2.ext
import logging
from animearena.color import *
from animearena.text_formatter import get_string_width, get_font_height

class Animation():
    
    current_x: int
    current_y: int
    display_x: int
    display_y: int
    i: int
    frequency: int
    frame_timer: int
    links: list
    sprites: list[sdl2.ext.SoftwareSprite]
    paused: bool
    pause_timer: int
    lock: bool
    
    def __init__(self, start_x, start_y, frequency, sprites, lock, scene):
        self.display_x = start_x
        self.display_y = start_y
        self.current_x = start_x
        self.current_y = start_y
        self.frame_timer = 0
        self.i = 0
        self.frequency = frequency
        self.sprites = sprites
        self.scene = scene
        self.lock = lock
        self.links = list()
        self.end_funcs = list()

    @property
    def current_sprite(self):
        return self.sprites[self.i]
    
    @property
    def has_ended(self):
        return True
    
    def link_animation(self, animation):
        self.links.append(animation)
    
    def add_end_func(self, func, args):
        self.end_funcs.append((func, args))
    
    def step(self):
        pass
    
    def add_pause(self, duration):
        self.pause_timer = duration * 30
        
    def progress_frame_timer(self):
        self.frame_timer += 1
        if self.frame_timer == self.frequency:
            self.frame_timer = 0
            self.step()
    
    def end(self):
        if self.links:
            for link in self.links:
                self.scene.add_animation(link)
        self.scene.animations.remove(self)
        if not self.scene.animations:
            self.scene.animation_region.clear()
        if self.lock:
            self.scene.check_animation_lock(self)
        if self.end_funcs:
            for func in self.end_funcs:
                func[0](*func[1])
    
    def progress_pause_timer(self):
        self.pause_timer -= 1
        

class MovementAnimation(Animation):
    
    def __init__(self, start_x, start_y, sprites, dest_x, dest_y, duration, scene, lock):
        
        self.dest_x = dest_x
        self.dest_y = dest_y
        x_diff = float(dest_x - start_x)
        y_diff = float(dest_y - start_y)
        if start_x < dest_x:
            self.x_orient = 1
        else:
            self.x_orient = -1
        
        if start_y < dest_y:
            self.y_orient = 1
        else:
            self.y_orient = -1
        
        frame_allotment = float(duration * 30)
        
        self.x_step = x_diff / frame_allotment
        self.y_step = y_diff / frame_allotment
        
        super().__init__(start_x, start_y, 1, sprites, lock, scene)
        
    def step(self):
        self.current_x = self.current_x + self.x_step
        self.current_y = self.y_step + self.current_y
        self.display_x = round(self.current_x)
        self.display_y = round(self.current_y)
        if self.display_x * self.x_orient > self.dest_x * self.x_orient:
            self.display_x = self.dest_x
        if self.display_y * self.y_orient > self.dest_y * self.y_orient:
            self.display_y = self.dest_y
            
    @property
    def has_ended(self):
        ended = (self.display_x == self.dest_x and self.display_y == self.dest_y)
        return ended
    
class SizeAnimation(Animation):
    
    def __init__(self, start_x, start_y, image, duration, scene, lock, shrink, dest_size = None, start_size = None):
        self.start_x = start_x
        self.start_y = start_y
        self.frame_timer = 0
        self.scene = scene
        self.lock = lock
        self.links = list()
        self.end_funcs = list()
        self.frequency = 1
        self.image = image.copy()
        frame_allotment = float(duration * 30)
        self.shrink = shrink
        x_offset = 0
        y_offset = 0
        if start_size:
            if start_size[0] > image.width and start_size[1] > image.height:
                x_offset = -(start_size[0] - image.width) // 2
                y_offset = -(start_size[1] - image.height) // 2
            elif start_size[0] < image.width and start_size[1] < image.height:
                x_offset = (image.width - start_size[0]) // 2
                y_offset = (image.height - start_size[1]) // 2
        
            
        if shrink:
            x_diff = image.width - 1
            y_diff = image.height - 1
            self.x_step = (x_diff / frame_allotment) * -1
            self.y_step = (y_diff / frame_allotment) * -1
            if dest_size:
                self.dest_width, self.dest_height = dest_size
            else:
                self.dest_width = 1
                self.dest_height = 1
            if start_size:
                self.current_width, self.current_height = start_size
                self.display_width, self.display_height = start_size
            else:
                self.current_width = image.width
                self.current_height = image.height
                self.display_width = image.width
                self.display_height = image.height
            self.orient = -1
            self.current_x = start_x + x_offset
            self.current_y = start_y + y_offset
            self.display_x = start_x + x_offset
            self.display_y = start_y + y_offset
        else:
            if dest_size:
                self.dest_width, self.dest_height = dest_size
            else:
                self.dest_width = image.width
                self.dest_height = image.height
            x_diff = self.dest_width - 1
            y_diff = self.dest_height - 1
            self.x_step = (x_diff / frame_allotment)
            self.y_step = (y_diff / frame_allotment)
            if start_size:
                self.current_width, self.current_height = start_size
                self.display_width, self.display_height = start_size
                self.current_x = start_x + x_offset
                self.current_y = start_y + y_offset
                self.display_x = start_x + x_offset
                self.display_y = start_y + y_offset
            else:
                self.current_width = max(round(self.x_step), 1)
                self.current_height = max(round(self.y_step), 1)
                self.display_width = max(round(self.x_step), 1)
                self.display_height = max(round(self.y_step), 1)
                self.current_x = start_x + (x_diff // 2) 
                self.current_y = start_y + (y_diff // 2)
                self.display_x = start_x + (x_diff // 2)
                self.display_y = start_y + (y_diff // 2)
            self.orient = 1
            
    
    @property
    def current_sprite(self):
        return self.scene.sprite_factory.from_surface(self.scene.get_scaled_surface(self.scene.border_image(self.image, 1), self.display_width, self.display_height), free=True)
    
    def step(self):
        self.current_width += self.x_step
        self.current_height += self.y_step
        self.display_height = round(self.current_height)
        self.display_width = round(self.current_width)
        
        if self.shrink:
            self.current_x += (self.x_step / 2) * self.orient
            self.current_y += (self.y_step / 2) * self.orient
            self.display_x = round(self.current_x)
            self.display_y = round(self.current_y)
        else:
            self.current_x -= (self.x_step / 2)
            self.current_y -= (self.y_step / 2)
            self.display_x = round(self.current_x)
            self.display_y = round(self.current_y)
        if self.display_height * self.orient > self.dest_height * self.orient:
            self.display_height = self.dest_height
            
        if self.display_width * self.orient > self.dest_width * self.orient:
            self.display_width = self.dest_width
        
    @property
    def has_ended(self):
        ended = (self.display_width == self.dest_width and self.display_height == self.dest_height)
        return ended

def create_pulse_animation(start_x, start_y, image, pulse_duration, pulse_amount, scene, lock, dest_size):
    image_start_size = image.size
    animations = []
    for i in range(pulse_amount):
        grow_animation = SizeAnimation(start_x, start_y, image, pulse_duration, scene, lock, False, dest_size=dest_size, start_size=image_start_size)
        if animations:
            animations[-1].link_animation(grow_animation)
        shrink_animation = SizeAnimation(start_x, start_y, image, pulse_duration, scene, lock, True, dest_size=image_start_size, start_size=dest_size)
        grow_animation.link_animation(shrink_animation)
        animations.append(grow_animation)
        animations.append(shrink_animation)
    
    return animations[0]


class DisplayAnimation(Animation):
    
    def __init__(self, start_x, start_y, sprites, duration, scene, lock):
        super().__init__(start_x, start_y, 1, sprites, lock, scene)
        self.duration = duration * 30
        
    def step(self):
        self.duration -= 1
        
    @property
    def has_ended(self):
        return self.duration <= 0

class FadeAnimation(Animation):
    
    def __init__(self, start_x, start_y, image, duration, scene, lock, fade_in=True):
        self.display_x = start_x
        self.display_y = start_y
        self.frequency = 1
        self.frame_timer = 0
        self.image = image.copy()
        self.scene = scene
        self.image = self.scene.border_image(self.image, 1)
        self.links = list()
        self.end_funcs = list()
        self.lock = lock
        self.duration = float(duration * 30)
        
        self.alpha_step = 255 / self.duration
        
        self.fade_in = fade_in
        
        if not self.fade_in:
            self.current_alpha = 255
            self.display_alpha = 255
            self.target_alpha = 0
            self.alpha_step *= -1
            self.orient = -1
        else:
            self.current_alpha = 0
            self.display_alpha = 0
            self.target_alpha = 255
            self.orient = 1
        
    @property
    def current_sprite(self):
        self.image.putalpha(self.display_alpha)
        return self.scene.sprite_factory.from_surface(self.scene.get_scaled_surface(self.image), free=True)
    
    def step(self):
        self.current_alpha += self.alpha_step
        self.display_alpha = round(self.current_alpha)
        
        if self.fade_in:
            if self.display_alpha < 0:
                self.display_alpha = 0
        else:
            if self.display_alpha > 255:
                self.display_alpha = 255
        
    @property
    def has_ended(self):
        return self.display_alpha == self.target_alpha
        

class TextAnimation(Animation):
    
    def __init__(self, text, color, border_color, font, dest_x, dest_y, scene, lock, typewriter):
        pass
