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

    @property
    def current_sprite(self):
        return self.sprites[self.i]
    
    @property
    def has_ended(self):
        return True
    
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
        
        x_diff = dest_x - start_x
        y_diff = dest_y - start_y
        
        frame_allotment = duration * 30
        
        self.x_step = x_diff // frame_allotment
        self.y_step = y_diff // frame_allotment
        
        super().__init__(start_x, start_y, 1, sprites, lock, scene)
        
    def step(self):
        self.current_x += self.x_step
        self.current_y += self.y_step
        if self.current_x > self.dest_x:
            self.current_x = self.dest_x
        if self.current_y > self.dest_y:
            self.current_y = self.dest_y
            
    @property
    def has_ended(self):
        return self.current_x == self.dest_x and self.current_y == self.dest_y
    