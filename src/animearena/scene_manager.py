import sdl2
import sdl2.ext
import sdl2dll
from typing import Tuple
import typing




class SceneManager:
    """Manager for all game scenes"""
    window: sdl2.ext.Window
    spriterenderer: sdl2.ext.SpriteRenderSystem
    factory: sdl2.ext.SpriteFactory

    def __init__(self, window: sdl2.ext.Window = None):
        if window:
            self.window = window
            self.factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE, free=False)
            self.spriterenderer = self.factory.create_sprite_render_system(window)


    def set_scene_to_current(self, scene):
        self.current_scene = scene

    def bind_connection(self, connection):
        self.connection = connection

    def start_battle(self, player_team, enemy_team):
        self.change_window_size(900, 900)
        self.set_scene_to_current(self.battle_scene)
        self.battle_scene.setup_scene(player_team, enemy_team)

    def change_window_size(self, new_width: int, new_height: int):
        sdl2.SDL_SetWindowSize(self.window.window, new_width, new_height)
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)

    def create_new_window(self, size: Tuple[int, int], name: str):
        self.window.close()
        self.window = sdl2.ext.Window(name, size)
        self.window.show()
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)