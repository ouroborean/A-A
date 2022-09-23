import sdl2
import sdl2.ext
import logging


class Animation():
    
    current_x: int
    current_y: int
    i: int
    frequency: int
    frame_timer: int
    link: "Animation"
    sprites: list[sdl2.ext.SoftwareSprite]
    paused: bool
    pause_timer: int
    lock: bool
    
    def __init__(self, start_x, start_y, frequency, sprites, lock, scene):
        self.current_x = start_x
        self.current_y = start_y
        self.frame_timer = 0
        self.i = 0
        self.frequency = frequency
        self.sprites = sprites
        self.scene = scene
        self.lock = lock
        self.link = None

    @property
    def current_sprite(self):
        return self.sprites[self.i]
    
    @property
    def has_ended(self):
        return True
    
    def link_animation(self, animation):
        self.link = animation
    
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
        if self.link:
            self.scene.add_animation(self.link)
        self.scene.animations.remove(self)
        if not self.scene.animations:
            self.scene.animation_region.clear()
        if self.lock:
            self.scene.check_animation_lock(self)
    
    def progress_pause_timer(self):
        self.pause_timer -= 1
        

class MovementAnimation(Animation):
    
    def __init__(self, start_x, start_y, sprites, dest_x, dest_y, duration, scene, lock):
        
        self.dest_x = dest_x
        self.dest_y = dest_y
        x_diff = float(dest_x - start_x)
        y_diff = float(dest_y - start_y)
        logging.debug("X and Y diffs are %d and %d", x_diff, y_diff)
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
        
        logging.debug("During the allotted frame_count of %d, the sprite will move %d and %d each frame.", frame_allotment, self.x_step, self.y_step)
        
        super().__init__(start_x, start_y, 1, sprites, lock, scene)
        
    def step(self):
        self.current_x = round(self.current_x + self.x_step)
        self.current_y = round(self.y_step + self.current_y)
        if self.current_x * self.x_orient > self.dest_x * self.x_orient:
            self.current_x = self.dest_x
        if self.current_y * self.y_orient > self.dest_y * self.y_orient:
            self.current_y = self.dest_y
            
    @property
    def has_ended(self):
        ended = (self.current_x == self.dest_x and self.current_y == self.dest_y)
        return ended
    