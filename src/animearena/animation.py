from typing import Optional, Iterable, Callable, Tuple
import random

class Animation():

    rate: int
    active: bool
    iteration_max: Optional[int] = None
    iteration_count: int
    frame_count: int
    frames: list[Callable]
    magnitude: int

    def __init__(self, frames:Iterable, magnitude: int = 0, rate: int = 1, iteration_max: Optional[int]=None):
        self.rate = rate
        self.frame_count = 0
        self.iteration_count = 0
        self.magnitude = magnitude
        self.active = False
        self.iteration_max = iteration_max
        self.frames = []
        for frame in frames:
            self.frames.append(frame)

    def enable(self):
        self.active = True
    
    def disable(self):
        self.active = False
        self.frame_count = 0

    def pause(self):
        self.active = False

    def trigger(self):
        self.frames[self.frame_count](self.magnitude)
        self.frame_count += 1
        if self.frame_count >= len(self.frames):
            self.frame_count = 0
            if not self.iteration_max:
                self.disable()
            else:
                self.iteration_count += 1
                if self.iteration_count == self.iteration_max:
                    self.iteration_count = 0
                    self.disable()
        


def get_shake_animation(target, enemy: bool, shakes: int, shake_magnitude: int, rate: int) -> Animation:

    def get_shake_modification(shake_magnitude):
        x_orient = random.randint(-1, 1) * shake_magnitude
        y_orient = random.randint(-1, 1) * shake_magnitude
        if enemy:
            target.update_limited(x_orient, y_orient)
        else:
            target.update(x_orient, y_orient)
    
    def return_sprites_to_center(shake_magnitude):
        if enemy:
            target.update_limited()
        else:
            target.update()
        
    frames = [get_shake_modification for i in range(shakes)]
    frames.append(return_sprites_to_center)
    return Animation(frames, shake_magnitude, rate)

