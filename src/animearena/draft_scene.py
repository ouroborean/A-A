from pathlib import Path
import importlib.resources
import os
import sys
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import logging
from playsound import playsound
from animearena import engine
from animearena import resource_manager
from animearena.character import get_character_db, Character
from animearena.color import *
import math
import enum

FONTSIZE = 16

@enum.unique
class Mode(enum.IntEnum):
    BAN = 0
    PICK = 1

class DraftScene(engine.Scene):
    
    
    
    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_manager = scene_manager
        self.font = resource_manager.init_font(FONTSIZE)
        self.player_bans = list()
        self.enemy_bans = list()
        self.mode = Mode.BAN
        self.player_bans = ["misaka", "mirio"]
        self.enemy_bans = ["ruler", "kuroko"]
        self.player_picks = ["snowwhite", "gajeel", "ripple"]
        self.enemy_picks = ["neji", "toga", "akame"]
        self.scrolling = False
        
        self.scroll_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["scroll_wheel"]), (20, 23))
        self.scroll_button.pressed += self.scroll_click
        self.scroll_button.click_offset = 0
        self.scroll_position = 0
        self.scroll_bar_y = 0
        self.character_sprites = {}
        for k, v in get_character_db().items():
            sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[k+"allyprof"], 75, 75), free=True)
            sprite.click += self.character_click
            sprite.character = v
            self.character_sprites[k] = sprite
        
        #region initialization
                
        self.player_region = self.region.subregion(5, 5, 0, 0)
        self.player_team_region = self.region.subregion(5, 135, 120, 320)
        self.enemy_region = self.region.subregion(895, 5, 0, 0)
        self.enemy_team_region = self.region.subregion(775, 135, 120, 320)
        self.character_select_region = self.region.subregion(135, 135, 630, 430)
        self.scroll_bar_region = self.character_select_region.subregion(608, 0, 22, 430)
        self.ban_region = self.region.subregion(200, 575, 500, 120)
        
        
    def full_render(self):
        self.background = self.sprite_factory.from_surface(
            self.get_scaled_surface(
                self.scene_manager.surfaces["in_game_background"]))
        self.region.add_sprite(self.background, 0, 0)
        self.render_char_select()
        self.render_player_region()
        self.render_enemy_region()
        self.render_ban_region()
    
    def render_char_select(self):
        self.character_select_region.clear()
        char_select_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.character_select_region.size()), AQUA, 2)
        self.character_select_region.add_sprite(char_select_panel, 0, 0)
        X_OFFSET = 25
        CHARS_PER_ROW = 6
        Y_OFFSET = 5
        PADDING = 5
        BUTTON_HEIGHT = 75
        BUTTON_SPACE = BUTTON_HEIGHT + PADDING
        characters = self.get_filtered_characters_list()
        CHARACTER_COUNT = len(characters)
        ROW_COUNT = math.ceil(CHARACTER_COUNT/CHARS_PER_ROW)
        VIEWPORT_HEIGHT = self.character_select_region.size()[1] - 10
        TOTAL_HEIGHT = (ROW_COUNT * BUTTON_SPACE) - VIEWPORT_HEIGHT
        if CHARACTER_COUNT <= 35:
            VERT_OFFSET = 0
        else:
            VERT_OFFSET = int(TOTAL_HEIGHT * self.scroll_position)
        
        scroll_bar = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU, self.scroll_bar_region.size())
        scroll_bar = self.border_sprite(scroll_bar, DULL_AQUA, 2)
        scroll_bar.click += self.scroll_bar_click
        
        self.scroll_bar_region.add_sprite(scroll_bar, 0, 0)
        
        if self.scrolling:
            self.scroll_bar_y = self.scene_manager.mouse_y - 402 - self.scroll_button.click_offset
            if self.scroll_bar_y > (280 - self.scroll_button.size[1]):
                self.scroll_bar_y = 280 - self.scroll_button.size[1]
            elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        
        for i, character in enumerate(characters):
            
            row = i // 7
            column = i % 7
            
            char_button = self.border_sprite(self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces[character.name + "allyprof"], 75, 75)), BLACK, 2)
            self.character_select_region.add_sprite(char_button, X_OFFSET + (column * 80), Y_OFFSET + (row * 80))
            
            
    
    def render_player_region(self):
        self.player_region.clear()
        player_region_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.player_region.size()), AQUA, 2)
        self.player_region.add_sprite(player_region_panel, 0, 0)
        self.render_player_team()
    
    def render_player_team(self):
        self.player_team_region.clear()
        player_team_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.player_team_region.size()), AQUA, 2)
        self.player_team_region.add_sprite(player_team_panel, 0, 0)
        for i, character in enumerate(self.player_picks):
            pick_sprite = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[character + "allyprof"])), BLACK, 2)
            self.player_team_region.add_sprite(pick_sprite, 10, 5 + (i * 105))
    
    def render_enemy_region(self):
        self.enemy_region.clear()
        enemy_region_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.enemy_region.size()), AQUA, 2)
        self.enemy_region.add_sprite(enemy_region_panel, 0, 0)
        self.render_enemy_team()
    
    def render_enemy_team(self):
        self.enemy_team_region.clear()
        enemy_team_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.enemy_team_region.size()), AQUA, 2)
        self.enemy_team_region.add_sprite(enemy_team_panel, 0, 0)
        for i, character in enumerate(self.enemy_picks):
            pick_sprite = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[character + "enemyprof"])), BLACK, 2)
            self.enemy_team_region.add_sprite(pick_sprite, 10, 5 + (i * 105))
    
    def render_ban_region(self):
        self.ban_region.clear()
        ban_placard = self.border_sprite(self.sprite_factory.from_color(MENU, (60, 25)), AQUA, 2)
        ban_placard = self.render_bordered_text(self.font, "BANS", RED, BLACK, ban_placard, 11, 1, 1)
        ban_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.ban_region.size()), AQUA, 2)
        self.ban_region.add_sprite(ban_panel, 0, 0)
        self.ban_region.add_sprite(ban_placard, 220, 0)
        for i in range(2):
            example_ban = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces["misakaallyprof"])), DARK_BLUE, thickness=2)
            self.ban_region.add_sprite(example_ban, 5 + (105 * i), 15)
        
        for i in range(2):
            example_ban = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces["misakaallyprof"])), DARK_RED, thickness=2)
            self.ban_region.add_sprite(example_ban, 500 - (105 * (i + 1)), 10)
    
    def scroll_click(self, _button, _sender):
        pass
    
    def scroll_bar_click(self, _button, _sender):
        pass
    
    def character_click(self, _button, _sender):
        pass
       
    def get_filtered_characters_list(self) -> list[Character]:
        # if not self.unlock_filtering:
        #     filtered_characters = list(get_character_db().values())
        # else:
        #     filtered_characters = [char for char in get_character_db().values() if self.player.missions[char.name][5]]
            

        # if not self.exclusive_filtering:
        #     for i, filter in enumerate(self.energy_filtering):
        #         if filter:
        #             filtered_characters = [char for char in filtered_characters if char.uses_energy(i)]
        # else:
        #     excluded_types = []
        #     for i, filter in enumerate(self.energy_filtering):
        #         if not filter:
        #             excluded_types.append(i)
        #     filtered_characters = [char for char in filtered_characters if not char.uses_energy_mult(excluded_types)]
        #     for i, filter in enumerate(self.energy_filtering):
        #         if filter:
        #             filtered_characters = [char for char in filtered_characters if char.uses_energy(i)]
        
        filtered_characters = list(get_character_db().values())
        
        return filtered_characters
        
        
def make_draft_scene(scene_manager) -> DraftScene:

    scene = DraftScene(scene_manager, sdl2.ext.SOFTWARE)
    
    return scene