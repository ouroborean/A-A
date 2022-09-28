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
STACK_FONTSIZE = 25

@enum.unique
class Mode(enum.IntEnum):
    BAN = 0
    PICK = 1

class DraftScene(engine.Scene):
    
    
    
    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_manager = scene_manager
        self.font = resource_manager.init_font(FONTSIZE)
        self.stack_font = resource_manager.init_font(STACK_FONTSIZE)
        self.player_bans = list()
        self.enemy_bans = list()
        self.player_picks = list()
        self.enemy_picks = list()
        self.mode = Mode.BAN
        
        self.waiting_for_turn = False
        self.going_first = False
        
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
                self.get_scaled_surface(self.border_image(self.scene_manager.surfaces[k+"allyprof"], 2), 75, 75), free=True)
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
    
    def scroll_character_select(self):
        self.character_select_region.clear()
        char_select_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.character_select_region.size()), AQUA, 2)
        self.character_select_region.add_sprite(char_select_panel, 0, 0)
        self.character_sprites.clear()
        for k, v in get_character_db().items():
            image = self.border_image(self.scene_manager.surfaces[k + "allyprof"].resize( ( 75, 75 )), 1)
            sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(image), free=True )
            sprite.click += self.character_click
            sprite.character = v
            self.character_sprites[k] = sprite
        
        if self.scrolling:
            self.scroll_bar_y = self.scene_manager.mouse_y - 137 - self.scroll_button.click_offset
            if self.scroll_bar_y > (430 - self.scroll_button.size[1]):
                self.scroll_bar_y = 430 - self.scroll_button.size[1]
            elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        
        self.scroll_position = self.scroll_bar_y / (430 - self.scroll_button.size[1])
        
        scroll_bar = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU, self.scroll_bar_region.size())
        scroll_bar = self.border_sprite(scroll_bar, DULL_AQUA, 2)
        scroll_bar.pressed += self.scroll_bar_click
        
        self.scroll_bar_region.add_sprite(scroll_bar, 0, 0)
        
        
                
        X_OFFSET = 25
        CHARS_PER_ROW = 7
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
        
        for i, character in enumerate(characters):
            if character.picked or character.banned:
                continue
            
            row = i // CHARS_PER_ROW
            column = i % CHARS_PER_ROW
            BASE_ROW_TOP = 5 + (row * BUTTON_SPACE)
            ROW_TOP = BASE_ROW_TOP - VERT_OFFSET
            ROW_BOTTOM = BASE_ROW_TOP + BUTTON_SPACE
            
            if (row + 1) * BUTTON_SPACE > VERT_OFFSET and ROW_TOP < VIEWPORT_HEIGHT:
                image = self.border_image(self.scene_manager.surfaces[character.name + "allyprof"].resize((75, 75)), 1)
                if ROW_TOP < 0:
                    image = image.crop( (0, abs(ROW_TOP), 75, 75))
                    ROW_TOP = 0
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.click += self.character_click
                    sprite.character = character
                    self.character_sprites[character.name] = sprite
                elif ROW_BOTTOM - VERT_OFFSET > VIEWPORT_HEIGHT:
                    image = image.crop( (0, 0, 75, min(75, VIEWPORT_HEIGHT - ROW_TOP)) )
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.click += self.character_click
                    sprite.character = character
                    self.character_sprites[character.name] = sprite
            
                self.character_select_region.add_sprite(self.character_sprites[character.name], X_OFFSET + (BUTTON_SPACE * column), Y_OFFSET + ROW_TOP)
        if CHARACTER_COUNT > 35:
            self.scroll_bar_region.add_sprite(self.scroll_button, 2, self.scroll_bar_y)
        
    
    def render_char_select(self):
        self.character_select_region.clear()
        char_select_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.character_select_region.size()), AQUA, 2)
        self.character_select_region.add_sprite(char_select_panel, 0, 0)
        
        if self.scrolling:
            self.scroll_bar_y = self.scene_manager.mouse_y - 137 - self.scroll_button.click_offset
            if self.scroll_bar_y > (430 - self.scroll_button.size[1]):
                self.scroll_bar_y = 430 - self.scroll_button.size[1]
            elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        
        self.scroll_position = self.scroll_bar_y / (430 - self.scroll_button.size[1])
        
        
        X_OFFSET = 25
        CHARS_PER_ROW = 7
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
        scroll_bar.pressed += self.scroll_bar_click
        
        self.scroll_bar_region.add_sprite(scroll_bar, 0, 0)
        
        
        for i, character in enumerate(characters):
            if character.picked or character.banned:
                continue
            
            row = i // CHARS_PER_ROW
            column = i % CHARS_PER_ROW
            BASE_ROW_TOP = 5 + (row * BUTTON_SPACE)
            ROW_TOP = BASE_ROW_TOP - VERT_OFFSET
            ROW_BOTTOM = BASE_ROW_TOP + BUTTON_SPACE
            
            if (row + 1) * BUTTON_SPACE > VERT_OFFSET and ROW_TOP < VIEWPORT_HEIGHT:
                image = self.border_image(self.scene_manager.surfaces[character.name + "allyprof"].resize((75, 75)), 1)
                if ROW_TOP < 0:
                    image = image.crop( (0, abs(ROW_TOP), 75, 75))
                    ROW_TOP = 0
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.click += self.character_click
                    sprite.character = character
                    self.character_sprites[character.name] = sprite
                elif ROW_BOTTOM - VERT_OFFSET > VIEWPORT_HEIGHT:
                    image = image.crop( (0, 0, 75, VIEWPORT_HEIGHT - ROW_TOP) )
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.click += self.character_click
                    sprite.character = character
                    self.character_sprites[character.name] = sprite
            
                self.character_select_region.add_sprite(self.character_sprites[character.name], X_OFFSET + (BUTTON_SPACE * column), Y_OFFSET + ROW_TOP)
        if CHARACTER_COUNT > 35:
            self.scroll_bar_region.add_sprite(self.scroll_button, 2, self.scroll_bar_y)
        
            
    
    def render_player_region(self):
        self.player_region.clear()
        player_ava = self.sprite_factory.from_surface(
                self.get_scaled_surface(self.player.avatar))
        self.add_bordered_sprite(self.player_region, player_ava, BLACK, 5,
                                    5)
        transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
        name_panel = self.render_bordered_text(self.stack_font, self.player.name, RED, BLACK, transparent_box, 0, 0, thickness=2)
        self.player_region.add_sprite(name_panel, 110, 0)
        if not self.player.clan:
            transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
            clan_panel = self.render_bordered_text(self.font, "Clanless", WHITE, BLACK, transparent_box, 0, 0, thickness=1)
            self.player_region.add_sprite(clan_panel, 110, 58)
        else:
            pass
        transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
        title_panel = self.render_bordered_text(self.font, self.player.title, WHITE, BLACK, transparent_box, 0, 0, thickness=1)
        self.player_region.add_sprite(title_panel, 110, 38)
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
        enemy_ava = self.sprite_factory.from_surface(
                self.get_scaled_surface(self.enemy.avatar))
        self.add_bordered_sprite(self.enemy_region, enemy_ava, BLACK, -100,
                                    5)
        name_width = int(len(self.enemy.name) * 11.5) + 5
        transparent_box = self.sprite_factory.from_color(TRANSPARENT, (name_width, 50))
        name_panel = self.render_bordered_text(self.stack_font, self.enemy.name, RED, BLACK, transparent_box, 0, 0, thickness=2)
        self.enemy_region.add_sprite(name_panel, -name_width - 100, 0)
        if not self.enemy.clan:
            transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
            clan_panel = self.render_bordered_text(self.font, "Clanless", WHITE, BLACK, transparent_box, 0, 0, thickness=1)
            clan_width = int(len("Clanless") * 7.3) + 5
            self.enemy_region.add_sprite(clan_panel, -clan_width - 100, 58)
        else:
            pass
        transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
        title_panel = self.render_bordered_text(self.font, self.enemy.title, WHITE, BLACK, transparent_box, 0, 0, thickness=1)
        title_width = int(len(self.enemy.title) * 7.3) + 5
        self.enemy_region.add_sprite(title_panel, -title_width - 100, 38)
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
        for i, character in enumerate(self.player_bans):
            ban_sprite = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[character + "allyprof"])), DARK_BLUE, thickness=2)
            
            self.ban_region.add_sprite(ban_sprite, 5 + (105 * i), 15)
        
        for i, character in enumerate(self.enemy_bans):
            ban_sprite = self.border_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[character + "allyprof"])), DARK_RED, thickness=2)
            self.ban_region.add_sprite(ban_sprite, 500 - (105 * (i + 1)), 10)
    
    def scroll_click(self, button, _sender):
        self.scrolling = True
        button.click_offset = self.get_click_coordinates(button)[1]

    def mouse_wheel_scroll(self, scroll_amount: int):
        self.scroll_bar_y += scroll_amount
        
        if self.scroll_bar_y > (430 - self.scroll_button.size[1]):
                self.scroll_bar_y = 430 - self.scroll_button.size[1]
        elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        self.scroll_character_select()
    
    def scroll_bar_click(self, button, sender):
        click_y = self.scene_manager.mouse_y - button.y
        if click_y < 11:
            click_y = 11
        elif click_y > 419:
            click_y = 419
        self.scroll_bar_y = click_y - 11
        self.scroll_character_select()
        self.scroll_click(self.scroll_button, sender)
    
    def character_click(self, _button, _sender):
        pass
    
    def get_click_coordinates(self, button):
        return (self.scene_manager.mouse_x - button.x, self.scene_manager.mouse_y - button.y)
  
    def start_draft(self, player, enemy):
        self.player = player
        self.enemy = enemy
        self.full_render()
        
    
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