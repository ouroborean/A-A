from pathlib import Path
from typing import Union, TYPE_CHECKING
import threading
import gc
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import easygui
from PIL import Image
import dill as pickle
from animearena import engine
from animearena.player import Player
from animearena.character import Character, get_character_db, reset_character_db
from animearena.ability import Ability
from animearena.mission import mission_db
from animearena.resource_manager import init_font
from animearena.color import *
from playsound import playsound
import logging
import math
import sys

if TYPE_CHECKING:
    from animearena.scene_manager import SceneManager


def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass
FONTSIZE = 16

RESOURCES = Path(__file__).parent.parent.parent / "resources"


class CharacterSelectScene(engine.Scene):

    font: sdl2.sdlttf.TTF_Font
    window_up: bool
    character_info_region: engine.Region
    character_select_region: engine.Region
    team_region: engine.Region
    start_match_region: engine.Region
    player_profile_region: engine.Region
    detail_target: Union[Character, Ability] = None
    display_character: Character
    filtered_characters: list[Character]
    page_on_display: int
    selected_team: list[Character]
    clicked_search: bool
    player_profile: Image
    player_profile_lock: threading.Lock
    player_name: str
    player_wins: int
    player_losses: int
    player: Player
    unlock_filtering: bool
    exclusive_filtering: bool
    energy_filtering: list[bool]
    dragging_picture: bool
    scene_manager: "SceneManager"
    drag_offset: tuple[int, int]
    dragging_character: str
    char_select_pressed: bool
    team_select_pressed: bool
    removing_from_team: bool

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #region field initialization
        self.scene_manager = scene_manager
        self.player_profile = self.scene_manager.surfaces["default_prof"]
        self.page_on_display = 1
        self.display_character = None
        self.searching = False
        self.dragging_picture = False
        self.player_name = ""
        self.font = init_font(FONTSIZE)
        self.player_profile_lock = threading.Lock()
        self.selected_team = []
        self.clicked_search = False
        self.window_up = False
        self.unlock_filtering = False
        self.exclusive_filtering = False
        self.energy_filtering = [False, False, False, False, False]
        self.filtered_characters = []
        self.drag_offset = (0, 0)
        self.player = None
        self.dragging_character = ""
        self.team_select_pressed = False
        self.char_select_pressed = False
        self.removing_from_team = False
        self.scrolling = False
        self.scroll_position = 0
        self.scroll_bar_y = 0
        #endregion
        #region region initialization
        
        
        self.character_info_region = self.region.subregion(15, 15, 770, 260)
        self.start_match_region = self.region.subregion(15, 355, 100, 40)
        self.how_to_region = self.region.subregion(120, 355, 100, 40)
        self.player_profile_region = self.region.subregion(15, 20, 200, 100)
        
        self.character_select_region = self.region.subregion(15, 400, 770, 285)
        self.character_scroll_selection_region = self.region.subregion(15, 400, 770, 285)
        self.scroll_bar_region = self.character_scroll_selection_region.subregion(485, 2, 20, 280)
        self.filter_region = self.character_scroll_selection_region.subregion(515, 240, 0, 0)
        self.player_profile_region = self.character_scroll_selection_region.subregion(515, 20, 0, 0)
        self.team_region = self.character_scroll_selection_region.subregion(515, 150, 245, 75)
        self.mission_region = self.region.subregion(210, 158, 0, 0)
        self.search_panel_region = self.region.subregion(144, 158, 0, 0)
        #endregion
        #region sprite initialization
        self.banner_border = self.sprite_factory.from_color(BLACK, (179, 254))
        self.search_panel_border = self.sprite_factory.from_color(BLACK, (516, 388))
        self.character_info_panel = self.sprite_factory.from_color(DARK_GRAY, (796, 286))
        self.character_info_panel_border = self.sprite_factory.from_color(BLACK, (800, 290))
        self.player_region_border = self.sprite_factory.from_color(BLACK, (249, 104))
        self.info_display_border = self.sprite_factory.from_color(BLACK, (479, 149))
        self.avatar_upload_border = self.sprite_factory.from_color(DARK_BLUE, (79, 44))
        self.character_select_border = self.sprite_factory.from_color(BLACK, (774, 289))
        self.scroll_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["scroll_wheel"]), (20, 23))
        self.scroll_button.pressed += self.click_scroll
        self.scroll_button.click_offset = 0
        self.left_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["left_arrow"]))
        self.left_button.click += self.left_click
        self.right_button = self.ui_factory.from_color(
            sdl2.ext.BUTTON,
            MENU_TRANSPARENT, (79, 79))
        sdl2.SDL_BlitSurface(self.get_scaled_surface(self.scene_manager.surfaces["right_arrow"]), None, self.right_button.surface, sdl2.SDL_Rect(7, 7))
        self.right_button = self.border_sprite(self.right_button, AQUA, 2)
        self.right_button.click += self.right_click
        self.how_to_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (100, 40))
        self.how_to_button = self.render_bordered_text(self.font, "Tutorial", WHITE, BLACK, self.how_to_button, 22, 9, 1)
        self.how_to_button = self.border_sprite(self.how_to_button, AQUA, 2)
        self.how_to_button.click += self.tutorial_click
        self.start_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (100, 40))
        self.start_button = self.render_bordered_text(self.font, "Quick Match", WHITE, BLACK, self.start_button, 9, 9, 1)
        self.start_button = self.border_sprite(self.start_button, AQUA, 2)
        self.start_button.click += self.start_click
        self.character_sprites = {}
        for k, v in get_character_db().items():
            sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[k+"allyprof"], 75, 75), free=True)
            sprite.click += self.character_click
            sprite.pressed += self.char_select_press
            sprite.border_box = self.sprite_factory.from_color(BLACK, (79, 79))
            sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, 75))
            sprite.filter_cover.click += self.character_click
            sprite.filter_cover.character = v
            sprite.character = v
            self.character_sprites[k] = sprite
        
        self.character_info_prof = self.ui_factory.from_color(
            sdl2.ext.BUTTON,
            BLACK, (175, 250))
        self.character_info_prof.click += self.character_main_click
        self.alt_character_info_prof = self.ui_factory.from_color(
            sdl2.ext.BUTTON,
            BLACK, (175, 250))
        self.alt_character_info_prof.click += self.character_alt_click
        self.main_ability_sprites = list([self.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (100, 100)) for i in range(4)])
        for sprite in self.main_ability_sprites:
            sprite.click += self.ability_click
            sprite.border_box = self.sprite_factory.from_color(BLACK, (104, 104))
        self.alt_ability_sprites = list([self.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (100, 100)) for i in range(4)])
        for sprite in self.alt_ability_sprites:
            sprite.click += self.alt_ability_click
            sprite.border_box = self.sprite_factory.from_color(BLACK, (104, 104))
        self.alt_arrow = self.ui_factory.from_color(
            sdl2.ext.BUTTON,
            MENU_TRANSPARENT, (79, 79))
        sdl2.SDL_BlitSurface(self.get_scaled_surface(self.scene_manager.surfaces["right_arrow"]), None, self.alt_arrow.surface, sdl2.SDL_Rect(-8, 7))
        self.alt_arrow = self.border_sprite(self.alt_arrow, AQUA, 2)
        self.alt_arrow.click += self.alt_arrow_click
        
        self.main_arrow = self.ui_factory.from_color(
            sdl2.ext.BUTTON,
            MENU_TRANSPARENT, (79, 79))
        sdl2.SDL_BlitSurface(self.get_scaled_surface(self.scene_manager.surfaces["left_arrow"]), None, self.main_arrow.surface, sdl2.SDL_Rect(20, 7))
        self.main_arrow = self.border_sprite(self.main_arrow, AQUA, 2)
        self.main_arrow.click += self.main_arrow_click
        
        self.avatar = self.sprite_factory.from_surface(self.get_scaled_surface(self.player_profile, 75, 75), free=True)
        self.avatar.border_box = self.sprite_factory.from_color(BLACK, (79, 79))
        self.team_display = [self.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (75,75)) for i in range(3)]
        for sprite in self.team_display:
            sprite.click += self.team_display_click
            sprite.pressed += self.team_select_press
            sprite.border_box = self.sprite_factory.from_color(BLACK, (79, 79))
        self.info_text_panel = self.create_text_display(self.font, "", BLACK,
                                                   WHITE, 5, 0, 475, 130)
        
        self.upload_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (79, 40))
        self.upload_button = self.render_bordered_text(self.font, "Upload Avatar", WHITE, BLACK, self.upload_button, 13, 0, 1, flow=True, target_width = 70, fontsize=16)
        self.upload_button = self.border_sprite(self.upload_button, ELECTRIC_BLUE, 2)
        self.upload_button.click += self.avatar_upload_click
        
        self.player_region_panel = self.sprite_factory.from_color(MENU_TRANSPARENT, (245, 123))
        self.player_region_panel = self.border_sprite(self.player_region_panel, AQUA, 2)
        
        self.lock_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["lock_icon"], width=30, height=30))
        self.lock_icon.click += self.lock_filter_click
        self.lock_border = self.sprite_factory.from_color(RED, (34, 34))

        self.phys_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["phys_icon"], width=30, height=30))
        self.phys_icon.click += self.energy_filter_click
        self.phys_icon.energy_id = 0
        self.phys_border = self.sprite_factory.from_color(RED, (34, 34))

        self.spec_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["spec_icon"], width=30, height=30))
        self.spec_icon.click += self.energy_filter_click
        self.spec_icon.energy_id = 1
        self.spec_border = self.sprite_factory.from_color(RED, (34, 34))

        self.ment_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["ment_icon"], width=30, height=30))
        self.ment_icon.click += self.energy_filter_click
        self.ment_icon.energy_id = 2
        self.ment_border = self.sprite_factory.from_color(RED, (34, 34))

        self.wep_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["wep_icon"], width=30, height=30))
        self.wep_icon.click += self.energy_filter_click
        self.wep_icon.energy_id = 3
        self.wep_border = self.sprite_factory.from_color(RED, (34, 34))

        self.rand_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["rand_icon"], width=30, height=30))
        self.rand_icon.click += self.energy_filter_click
        self.rand_icon.energy_id = 4
        self.rand_border = self.sprite_factory.from_color(RED, (34, 34))

        self.ex_icon = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["exclusive_icon"], width=30, height=30))
        self.ex_icon.click += self.exclusive_filter_click
        self.ex_border = self.sprite_factory.from_color(RED, (34, 34))

        self.energy_icons = [self.phys_icon, self.spec_icon, self.ment_icon, self.wep_icon, self.rand_icon]
        self.energy_borders = [self.phys_border, self.spec_border, self.ment_border, self.wep_border, self.rand_border]

        #endregion


    #region Render Functions

    def full_render(self):
        self.region.clear()
        self.region.add_sprite(
            self.sprite_factory.from_surface(
                self.get_scaled_surface(self.scene_manager.surfaces["background"]), free=True), 0, 0)
        if self.display_character:
            self.render_main_character_info()
        self.render_tutorial_button()
        self.render_start_button()
        self.render_character_scroll_selection()
        self.render_search_panel()

    def memory_test(self, _button, _sender):
        self.full_render()
    
    def render_tutorial_button(self):
        self.how_to_region.clear()
        self.how_to_region.add_sprite(self.how_to_button, 0, 0)

    def render_mission_panel(self):
        self.mission_region.clear()
        self.window_up = True
        self.add_bordered_sprite(self.mission_region, self.sprite_factory.from_color(BLACK, (512,384)), WHITE, 0, 0)
        MISSION_MAX_WIDTH = 492
        MISSION_Y_BUFFER = 10
        MISSION_MAX_HEIGHT = 72
        MISSION_X_BUFFER = 10
        
        for i in range(5):
            current = min(self.player.missions[self.display_character.name][i], mission_db[self.display_character.name][i].max)
            text_sprite = self.create_text_display(self.font, f"{mission_db[self.display_character.name][i].description} ({current}/{mission_db[self.display_character.name][i].max})", WHITE, BLACK, 0, 0, MISSION_MAX_WIDTH)
            self.mission_region.add_sprite(text_sprite, MISSION_X_BUFFER, (MISSION_MAX_HEIGHT * i) + MISSION_Y_BUFFER)

    def render_filter_options(self):
        self.filter_region.clear()
        background_border = self.sprite_factory.from_color(BLACK, (254, 44))
        background = self.sprite_factory.from_color(WHITE, (250, 40))
        self.filter_region.add_sprite(background_border, -4, -2)
        self.filter_region.add_sprite(background, -2, 0)
        if self.unlock_filtering:
            self.filter_region.add_sprite(self.lock_border, 1, 3)
        self.filter_region.add_sprite(self.lock_icon, 3, 5)

        for i in range(5):
            if self.energy_filtering[i]:
                self.filter_region.add_sprite(self.energy_borders[i], 1 + (35 * (i + 1)), 3)
            self.filter_region.add_sprite(self.energy_icons[i], 3 + 35 * (i + 1), 5)
        
        if self.exclusive_filtering:
            self.filter_region.add_sprite(self.ex_border, 211, 3)
        self.filter_region.add_sprite(self.ex_icon, 213, 5)

    def render_search_panel(self):
        self.search_panel_region.clear()
        if self.clicked_search:
            self.add_sprite_with_border(self.search_panel_region, self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces["search"])), self.search_panel_border, 0, 0)
            cancel_search_button = self.create_text_display(self.font, "Cancel", WHITE, BLACK, 5, 5, 80)
            cancel_search_button.click += self.cancel_search_click
            self.search_panel_region.add_sprite(cancel_search_button, 5, 5)
            
    def render_player_profile(self):
        self.player_profile_region.clear()

        self.player_profile_region.add_sprite(self.player_region_panel, -4, -4)
        

        self.player_profile_lock.acquire()
        if self.player_profile == None:
            self.player_profile = self.scene_manager.surfaces["default_prof"]

        self.avatar.surface = self.get_scaled_surface(self.player_profile, 75, 75)
        
        self.add_sprite_with_border(self.player_profile_region, self.avatar, self.avatar.border_box, 0, 0)
        
        self.player_profile_region.add_sprite(self.upload_button, -2, 77)
        self.player_profile_lock.release()

    def render_main_character_info(self):
        
        self.character_info_region.clear()
        
        info_panel = self.sprite_factory.from_color(MENU_TRANSPARENT, (770, 270))
        info_panel = self.border_sprite(info_panel, AQUA, 2)
        self.character_info_region.add_sprite(info_panel, 0, -5)
        
        self.character_info_prof.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.name + "banner"])
        self.character_info_prof.free = True
        self.character_info_prof.character = self.display_character
        self.add_sprite_with_border(self.character_info_region, self.character_info_prof, self.banner_border, 10, 5)
        if self.player.missions[self.character_info_prof.character.name][5]:
            mission_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (80, 40))
            mission_button = self.render_bordered_text(self.font, "Missions", WHITE, BLACK, mission_button, 10, 9, 1)
            mission_button = self.border_sprite(mission_button, AQUA, 2)
            mission_button.click += self.mission_click
            self.character_info_region.add_sprite(mission_button, 675, 215)
        else:
            unlock_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (80, 40))
            unlock_button = self.render_bordered_text(self.font, "Missions", WHITE, BLACK, unlock_button, 10, 9, 1)
            unlock_button = self.border_sprite(unlock_button, AQUA, 2)
            unlock_button.click += self.mission_click
            self.character_info_region.add_sprite(unlock_button, 675, 175)
        for i, ability in enumerate(self.main_ability_sprites):
            ability.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.main_abilities[i].db_name])
            ability.ability = self.display_character.main_abilities[i]
            ability.free = True
            if ability.ability == self.detail_target:
                self.add_bordered_sprite(self.character_info_region, ability, ELECTRIC_BLUE, x=65 + ((i + 1) * 125), y=5)
            else:
                self.add_bordered_sprite(self.character_info_region, ability, BLACK, x=65 + ((i + 1) * 125),
                                                  y=5)

        if self.display_character.alt_abilities:
            self.character_info_region.add_sprite(self.alt_arrow, 680, 27)
            

        detail_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, (479, 148)), AQUA, 2)

        if type(self.detail_target) == Ability:
            text = self.detail_target.name + ": " + self.detail_target.desc
            detail_panel = self.render_bordered_text(self.font, f"CD: {self.detail_target.cooldown}", WHITE, BLACK, detail_panel, 432, 121, 1)
            if self.detail_target.total_cost > 0:
                total_energy = 0
                for k, v in self.detail_target.cost.items():
                    for i in range(v):
                        sdl2.surface.SDL_BlitSurface(self.get_scaled_surface(self.scene_manager.surfaces[k.name], 18, 18), None, detail_panel.surface,
                            sdl2.SDL_Rect(7 + (total_energy * 21), 125))
                        total_energy += 1
            else:
                detail_panel = self.render_bordered_text(self.font, "No Cost", WHITE, BLACK, detail_panel, 7, 121, 1)
        else:
            text = self.detail_target.desc

        
        detail_panel = self.render_bordered_text(self.font, text, WHITE, BLACK, detail_panel, 5, 5, 1, flow=True, target_width = 465, fontsize=16)

        self.character_info_region.add_sprite(detail_panel, 188, 110)

    def render_alt_character_info(self):
        self.character_info_region.clear()
        
        info_panel = self.sprite_factory.from_color(MENU_TRANSPARENT, (770, 270))
        info_panel = self.border_sprite(info_panel, AQUA, 2)
        self.character_info_region.add_sprite(info_panel, 0, -5)
        
        self.alt_character_info_prof.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.name + "banner"])
        self.alt_character_info_prof.character = self.display_character
        self.alt_character_info_prof.free = True
        self.add_sprite_with_border(self.character_info_region, self.alt_character_info_prof, self.banner_border, 10, 5)
        if self.player.missions[self.character_info_prof.character.name][5]:
            mission_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (80, 40))
            mission_button = self.render_bordered_text(self.font, "Missions", WHITE, BLACK, mission_button, 10, 9, 1)
            mission_button = self.border_sprite(mission_button, AQUA, 2)
            mission_button.click += self.mission_click
            self.character_info_region.add_sprite(mission_button, 675, 215)
        else:
            unlock_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (80, 40))
            unlock_button = self.render_bordered_text(self.font, "Missions", WHITE, BLACK, unlock_button, 10, 9, 1)
            unlock_button = self.border_sprite(unlock_button, AQUA, 2)
            unlock_button.click += self.mission_click
            self.character_info_region.add_sprite(unlock_button, 675, 175)
        
        for i, ability in enumerate(self.display_character.alt_abilities):
            self.alt_ability_sprites[i].surface = self.get_scaled_surface(self.scene_manager.surfaces[ability.db_name])
            self.alt_ability_sprites[i].free = True
            self.alt_ability_sprites[i].ability = ability
            if self.alt_ability_sprites[i].ability == self.detail_target:
                self.add_bordered_sprite(self.character_info_region, self.alt_ability_sprites[i], ELECTRIC_BLUE, x=65 + ((i + 1) * 125), y=5)
            else:
                self.add_bordered_sprite(self.character_info_region, self.alt_ability_sprites[i], BLACK, x=65 + ((i + 1) * 125),
                                                  y=5)

        
        self.character_info_region.add_sprite(self.main_arrow, 680, 27)



        detail_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, (479, 148)), AQUA, 2)

        if type(self.detail_target) == Ability:
            text = self.detail_target.name + ": " + self.detail_target.desc
            detail_panel = self.render_bordered_text(self.font, f"CD: {self.detail_target.cooldown}", WHITE, BLACK, detail_panel, 432, 121, 1)
            if self.detail_target.total_cost > 0:
                total_energy = 0
                for k, v in self.detail_target.cost.items():
                    for i in range(v):
                        sdl2.surface.SDL_BlitSurface(self.get_scaled_surface(self.scene_manager.surfaces[k.name], 18, 18), None, detail_panel.surface,
                            sdl2.SDL_Rect(7 + (total_energy * 21), 125))
                        total_energy += 1
            else:
                detail_panel = self.render_bordered_text(self.font, "No Cost", WHITE, BLACK, detail_panel, 7, 121)
        else:
            text = self.detail_target.desc

        
        detail_panel = self.render_bordered_text(self.font, text, WHITE, BLACK, detail_panel, 5, 5, 1, flow=True, target_width = 465, fontsize=16)
        
            
        self.character_info_region.add_sprite(detail_panel, 188, 110)
        


        

    def render_cooldown(self, ability: Ability):
        cooldown_panel = self.create_text_display(self.font,
                                                  f"CD: {ability.cooldown}",
                                                  BLACK, WHITE, 0, 0, 40, 3)
        self.character_info_region.add_sprite(cooldown_panel, x=610, y=235)

    def render_team_display(self):

        self.team_region.clear()

        for i in range(3):
            if i < len(self.selected_team):
                self.team_display[i].surface = self.get_scaled_surface(self.scene_manager.surfaces[self.selected_team[i].name + "allyprof"], 75, 75)
                self.team_display[i].character = self.selected_team[i]
            else:
                self.team_display[i].surface = self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, 75)
            self.team_display[i].free = True
            self.add_sprite_with_border(self.team_region, self.team_display[i], self.team_display[i].border_box, i * 85, 0)

    def render_start_button(self):
        self.start_match_region.clear()
        if len(self.selected_team) == 3:
            self.start_match_region.add_sprite(self.start_button, 0, 0)

    def render_character_select(self):
        self.character_select_region.clear()
        if self.page_on_display > 1:
            self.character_select_region.add_sprite(self.left_button, -20, 105)

        column = 0
        row = 0
        if not self.unlock_filtering:
            self.filtered_characters = list(get_character_db().values())
        else:
            self.filtered_characters = [char for char in get_character_db().values() if self.player.missions[char.name][5]]
            

        if not self.exclusive_filtering:
            for i, filter in enumerate(self.energy_filtering):
                if filter:
                    self.filtered_characters = [char for char in self.filtered_characters if char.uses_energy(i)]
        else:
            excluded_types = []
            for i, filter in enumerate(self.energy_filtering):
                if not filter:
                    excluded_types.append(i)
            self.filtered_characters = [char for char in self.filtered_characters if not char.uses_energy_mult(excluded_types)]
            for i, filter in enumerate(self.energy_filtering):
                if filter:
                    self.filtered_characters = [char for char in self.filtered_characters if char.uses_energy(i)]

        if len(self.filtered_characters) > (self.page_on_display * 12):
            self.character_select_region.add_sprite(self.right_button, 715, 105)
        
        for i in range(12):
            current_slot = i + ((self.page_on_display - 1) * 12)
            try:
                if not self.filtered_characters[current_slot].selected:
                    self.add_sprite_with_border(self.character_select_region, self.character_sprites[self.filtered_characters[current_slot].name], self.character_sprites[self.filtered_characters[current_slot].name].border_box, 60 + (column * 110), 35 + (row * 110))
                if self.filtered_characters[current_slot].selected or not self.player.missions[self.filtered_characters[current_slot].name][5] or (self.dragging_picture and self.filtered_characters[current_slot].name == self.dragging_character):
                    selected_filter = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"]), free=True)
                    selected_filter.character = self.filtered_characters[current_slot]
                    selected_filter.click += self.character_click
                    self.character_sprites[self.filtered_characters[current_slot].name].character = self.filtered_characters[current_slot]
                    self.character_select_region.add_sprite(selected_filter, 60 + (column * 110), 35 + (row * 110))
                else:
                    self.character_sprites[self.filtered_characters[current_slot].name].character = self.filtered_characters[current_slot]
                    
                
            except IndexError:
                break
            column += 1
            if column == 6:
                row += 1
                column = 0
        if self.dragging_picture:
            self.add_sprite_with_border(self.character_select_region, self.character_sprites[self.dragging_character], self.character_sprites[self.dragging_character].border_box, self.scene_manager.mouse_x - self.drag_offset[0] - self.character_select_region.x, self.scene_manager.mouse_y - self.drag_offset[1] - self.character_select_region.y)
    
    
    def scroll_character_scroll_selection(self):
        self.character_scroll_selection_region.clear()
        background = self.sprite_factory.from_color(MENU_TRANSPARENT, (self.character_scroll_selection_region.size()[0], self.character_scroll_selection_region.size()[1] + 8))
        background = self.border_sprite(background, AQUA, 2)
        scroll_bar = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, self.scroll_bar_region.size())
        scroll_bar.pressed += self.click_scroll_bar
        self.character_scroll_selection_region.add_sprite(background, 0, -4)
        self.scroll_bar_region.add_sprite(scroll_bar, 0, 0)
        self.render_filter_options()
        self.render_team_display()
        self.render_player_profile()
        if self.scrolling:
            self.scroll_bar_y = self.scene_manager.mouse_y - 402 - self.scroll_button.click_offset
            if self.scroll_bar_y > (280 - self.scroll_button.size[1]):
                self.scroll_bar_y = 280 - self.scroll_button.size[1]
            elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        self.character_sprites.clear()
        for k, v in get_character_db().items():
            sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[k+"allyprof"], 75, 75), free=True)
            sprite.click += self.character_click
            sprite.pressed += self.char_select_press
            sprite.border_box = self.sprite_factory.from_color(BLACK, (79, 79))
            sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, 75))
            sprite.filter_cover.character = v
            sprite.filter_cover.click += self.character_click
            sprite.character = v
            self.character_sprites[k] = sprite
        
        self.scroll_position = self.scroll_bar_y / (280 - self.scroll_button.size[1])
        
        CHARS_PER_ROW = 6
        BUTTON_HEIGHT = 75
        BUTTON_WIDTH = 75
        PADDING = 5
        BUTTON_SPACE = BUTTON_HEIGHT + PADDING
        #TODO add filtering here
        characters = self.get_filtered_characters_list()
        CHARACTER_COUNT = len(characters)
        ROW_COUNT = math.ceil(CHARACTER_COUNT / CHARS_PER_ROW)
        VIEWPORT_HEIGHT = self.character_scroll_selection_region.size()[1]
        TOTAL_HEIGHT = (ROW_COUNT * BUTTON_SPACE) - VIEWPORT_HEIGHT - 5
        if CHARACTER_COUNT <= 18:
            VERT_OFFSET = 0
        else:
            VERT_OFFSET = int(TOTAL_HEIGHT * self.scroll_position)
        for i, character in enumerate(characters):
            row = i // CHARS_PER_ROW
            column = i % CHARS_PER_ROW
            ROW_TOP = PADDING + (row * BUTTON_SPACE) - VERT_OFFSET
            BASE_ROW_TOP = PADDING + (row * BUTTON_SPACE)
            ROW_BOTTOM = BASE_ROW_TOP + BUTTON_SPACE
            BORDER_TOP = ROW_TOP - 2
            if (row + 1) * BUTTON_SPACE > VERT_OFFSET and ROW_TOP < self.character_scroll_selection_region.size()[1]:
                image = self.scene_manager.surfaces[character.name + "allyprof"].resize((75, 75))
                BORDER_HEIGHT = 79
                if ROW_TOP < 0:
                    image = image.crop( (0, abs(ROW_TOP), 75, 75))
                    BORDER_HEIGHT = image.height + 2
                    ROW_TOP = 0
                    BORDER_TOP = 0
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, image.height))
                    sprite.click += self.character_click
                    sprite.pressed += self.char_select_press
                    sprite.filter_cover.click += self.character_click
                    sprite.character = character
                    sprite.filter_cover.character = character
                    sprite.border_box = self.sprite_factory.from_color(BLACK, (79, BORDER_HEIGHT))
                    self.character_sprites[character.name] = sprite
                elif ROW_BOTTOM - VERT_OFFSET > VIEWPORT_HEIGHT:
                    image = image.crop( (0, 0, 75, VIEWPORT_HEIGHT - ROW_TOP ))
                    BORDER_HEIGHT = image.height + 2
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.border_box = self.sprite_factory.from_color(BLACK, (79, BORDER_HEIGHT))
                    sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, image.height))
                    sprite.click += self.character_click
                    sprite.pressed += self.char_select_press
                    sprite.filter_cover.click += self.character_click
                    sprite.character = character
                    sprite.filter_cover.character = character
                    self.character_sprites[character.name] = sprite
                self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name].border_box, (PADDING - 2) + (BUTTON_SPACE * column), BORDER_TOP)
                self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name], PADDING + (BUTTON_SPACE * column), ROW_TOP)
                if character.selected or not self.player.missions[character.name][5] or (self.dragging_character == character.name):
                    self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name].filter_cover, PADDING + (BUTTON_SPACE * column), ROW_TOP)
                
        if CHARACTER_COUNT > 18:
            self.scroll_bar_region.add_sprite(self.scroll_button, 0, self.scroll_bar_y)
        
    
    def render_character_scroll_selection(self):
        self.character_scroll_selection_region.clear()
        background = self.sprite_factory.from_color(MENU_TRANSPARENT, (self.character_scroll_selection_region.size()[0], self.character_scroll_selection_region.size()[1] + 8))
        background = self.border_sprite(background, AQUA, 2)
        scroll_bar = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, self.scroll_bar_region.size())
        scroll_bar.pressed += self.click_scroll_bar
        self.character_scroll_selection_region.add_sprite(background, 0, -4)
        self.scroll_bar_region.add_sprite(scroll_bar, 0, 0)
        self.render_team_display()
        self.render_filter_options()
        self.render_player_profile()
        if self.scrolling:
            self.scroll_bar_y = self.scene_manager.mouse_y - 402 - self.scroll_button.click_offset
            if self.scroll_bar_y > (280 - self.scroll_button.size[1]):
                self.scroll_bar_y = 280 - self.scroll_button.size[1]
            elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0

        self.scroll_position = self.scroll_bar_y / (280 - self.scroll_button.size[1])
        
        CHARS_PER_ROW = 6
        BUTTON_HEIGHT = 75
        PADDING = 5
        BUTTON_SPACE = BUTTON_HEIGHT + PADDING
        #TODO add filtering here
        characters = self.get_filtered_characters_list()
        CHARACTER_COUNT = len(characters)
        ROW_COUNT = math.ceil(CHARACTER_COUNT / CHARS_PER_ROW)
        VIEWPORT_HEIGHT = self.character_scroll_selection_region.size()[1]
        TOTAL_HEIGHT = (ROW_COUNT * BUTTON_SPACE) - VIEWPORT_HEIGHT -5
        if CHARACTER_COUNT <= 18:
            VERT_OFFSET = 0
        else:
            VERT_OFFSET = int(TOTAL_HEIGHT * self.scroll_position)
        
        for i, character in enumerate(characters):
            row = i // CHARS_PER_ROW
            column = i % CHARS_PER_ROW
            ROW_TOP = PADDING + (row * BUTTON_SPACE) - VERT_OFFSET
            BASE_ROW_TOP = PADDING + (row * BUTTON_SPACE)
            ROW_BOTTOM = BASE_ROW_TOP + BUTTON_SPACE
            BORDER_TOP = ROW_TOP - 2
            if (row + 1) * BUTTON_SPACE > VERT_OFFSET and ROW_TOP < self.character_scroll_selection_region.size()[1]:
                image = self.scene_manager.surfaces[character.name + "allyprof"].resize((75, 75))
                BORDER_HEIGHT = 79
                if ROW_TOP < 0:
                    image = image.crop( (0, abs(ROW_TOP), 75, 75))
                    BORDER_HEIGHT = image.height + 2
                    ROW_TOP = 0
                    BORDER_TOP = 0
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, image.height))
                    sprite.click += self.character_click
                    sprite.pressed += self.char_select_press
                    sprite.filter_cover.click += self.character_click
                    sprite.character = character
                    sprite.filter_cover.character = character
                    sprite.border_box = self.sprite_factory.from_color(BLACK, (79, BORDER_HEIGHT))
                    self.character_sprites[character.name] = sprite
                elif ROW_BOTTOM - VERT_OFFSET > VIEWPORT_HEIGHT:
                    image = image.crop( (0, 0, 75, VIEWPORT_HEIGHT - ROW_TOP ))
                    BORDER_HEIGHT = image.height + 2
                    sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(image), free=True)
                    sprite.border_box = self.sprite_factory.from_color(BLACK, (79, BORDER_HEIGHT))
                    sprite.filter_cover = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"], 75, image.height))
                    sprite.click += self.character_click
                    sprite.pressed += self.char_select_press
                    sprite.filter_cover.click += self.character_click
                    sprite.character = character
                    sprite.filter_cover.character = character
                    self.character_sprites[character.name] = sprite
                self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name].border_box, (PADDING - 2) + (BUTTON_SPACE * column), BORDER_TOP)
                self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name], PADDING + (BUTTON_SPACE * column), ROW_TOP)
                if character.selected or not self.player.missions[character.name][5] or (self.dragging_character == character.name):
                    self.character_scroll_selection_region.add_sprite(self.character_sprites[character.name].filter_cover, PADDING + (BUTTON_SPACE * column), ROW_TOP)
        if CHARACTER_COUNT > 18:
            self.scroll_bar_region.add_sprite(self.scroll_button, 0, self.scroll_bar_y)
        if self.dragging_picture:
            sprite = self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[self.dragging_character + "allyprof"], 75, 75), free=True)
            self.add_sprite_with_border(self.team_region, sprite, self.sprite_factory.from_color(BLACK, (79, 79)), self.scene_manager.mouse_x - self.drag_offset[0] - self.team_region.x, self.scene_manager.mouse_y - self.drag_offset[1] - self.team_region.y)
    
    #endregion

    #region On-Click Event Handlers

    def mouse_wheel_scroll(self, scroll_amount: int):
        self.scroll_bar_y += scroll_amount
        
        if self.scroll_bar_y > (280 - self.scroll_button.size[1]):
                self.scroll_bar_y = 280 - self.scroll_button.size[1]
        elif self.scroll_bar_y < 0:
                self.scroll_bar_y = 0
        self.scroll_character_scroll_selection()
        

    def char_select_press(self, button, _sender):
        if hasattr(button, "character") and button.character and not self.window_up:
            if not get_character_db()[button.character.name].selected and self.player.missions[button.character.name][5]:
                self.char_select_pressed = True
                self.drag_offset = self.get_click_coordinates(button)
                self.dragging_character = button.character.name
    
    def team_select_press(self, button, _sender):
        if hasattr(button, "character") and button.character and not self.window_up:
            self.team_select_pressed = True
            self.removing_from_team = True
            self.drag_offset = self.get_click_coordinates(button)
            self.dragging_character = button.character.name

    def click_scroll_bar(self, button, sender):
        click_y = self.scene_manager.mouse_y - button.y
        if click_y < 11:
            click_y = 11
        elif click_y > 269:
            click_y = 269
        self.scroll_bar_y = click_y - 11
        self.scroll_character_scroll_selection()
        self.click_scroll(self.scroll_button, sender)

    def click_scroll(self, button, _sender):
        self.scrolling = True
        button.click_offset = self.get_click_coordinates(button)[1]

    def add_character(self, char):
        character = get_character_db()[char]
        character.selected = True
        self.selected_team.append(character)
        self.team_display[len(self.selected_team) - 1].character = character

    def resolve_drag_release(self):
        
        selected = self.is_dropping_to_selected()
        
        if selected and len(self.selected_team) < 3:
            self.add_character(self.dragging_character)
        
        self.drag_offset = (0, 0)
        self.dragging_picture = False
        self.dragging_character = ""
        self.render_start_button()
        self.render_team_display()
        self.render_character_scroll_selection()
        
    def is_dropping_to_selected(self) -> bool:
        return (self.scene_manager.mouse_x > 498 and self.scene_manager.mouse_x < 800 and self.scene_manager.mouse_y < 657 and self.scene_manager.mouse_y > 518)
    
    def tutorial_click(self, button, sender):
        self.scene_manager.start_tutorial(self.player)

    def exclusive_filter_click(self, button, sender):
        self.exclusive_filtering = not self.exclusive_filtering
        
        self.energy_filtering[4] = self.exclusive_filtering
        self.page_on_display = 1
        self.render_filter_options()
        self.scroll_character_scroll_selection()

    def lock_filter_click(self, button, sender):
        self.unlock_filtering = not self.unlock_filtering
        self.page_on_display = 1
        self.render_filter_options()
        self.scroll_character_scroll_selection()

    def energy_filter_click(self, button, sender):
        self.energy_filtering[button.energy_id] = not self.energy_filtering[button.energy_id]
        if button.energy_id == 4:
            self.exclusive_filtering = self.energy_filtering[button.energy_id]
        self.page_on_display = 1
        self.render_filter_options()
        self.scroll_character_scroll_selection()

    def mission_click(self, button, sender):
        self.window_up = not self.window_up
        if self.window_up:
            self.render_mission_panel()
        else:
            self.mission_region.clear()

    def unlock_click(self, button, sender):
        if self.player.medals >= 3:
            self.player.medals -= 3
            self.player.missions[self.display_character.name][5] = 1
            self.scene_manager.connection.send_player_update(self.player)
        self.scroll_character_scroll_selection()
        self.render_player_profile()

    def cancel_search_click(self, button, sender):
        play_sound(self.scene_manager.sounds["undo"])
        self.window_up = False
        self.clicked_search = False
        self.scene_manager.connection.send_search_cancellation()
        self.render_search_panel()

    def avatar_upload_click(self, button, sender):
        def callback():
            file = easygui.fileopenbox()
            self.player_profile_lock.acquire()
            try:
                self.player_profile = Image.open(file)
                self.player_profile = self.player_profile.resize((100, 100))
                self.player.avatar = self.player_profile
                image = {"mode": self.player_profile.mode, "size": self.player_profile.size, "pixels": self.player_profile.tobytes()}
                msg = pickle.dumps(image)
                self.scene_manager.connection.update_avatar(msg)
            except:
                pass
            self.player_profile_lock.release()
            self.render_player_profile()
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            t = threading.Thread(target=callback)
            t.start()

    def left_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.page_on_display -= 1
            if self.page_on_display < 1:
                self.page_on_display = 1
            self.render_character_scroll_selection()

    def right_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.page_on_display += 1
            max_pages = len(get_character_db()) // 12
            if len(get_character_db()) % 12 > 0:
                max_pages += 1
            if self.page_on_display > max_pages:
                self.page_on_display = max_pages
            self.render_character_scroll_selection()

    def alt_arrow_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.detail_target = self.display_character.alt_abilities[0]
            self.render_alt_character_info()

    def main_arrow_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.detail_target = self.display_character.main_abilities[0]
            self.render_main_character_info()

    def ability_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.ability
            self.render_main_character_info()

    def alt_ability_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.ability
            self.render_alt_character_info()

    def character_alt_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.character
            self.display_character = button.character
            self.render_alt_character_info()

    def character_main_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.character
            self.display_character = button.character
            self.render_main_character_info()

    def team_display_click(self, button, _sender):
        if not self.window_up and hasattr(button, "character") and button.character != None:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.character
            self.display_character = button.character
            self.init_char_select_desc(button)
            self.render_main_character_info()

    def character_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.character
            self.display_character = button.character
            self.init_char_select_desc(button)
            # self.render_character_scroll_selection()
            self.render_character_scroll_selection()
            self.render_main_character_info()

    def start_dragging(self):
        self.dragging_picture = True
        self.render_character_scroll_selection()
    
    def start_dragging_from_selected(self):
        self.dragging_picture = True
        if self.removing_from_team:
            self.removing_from_team = False    
            for character in self.selected_team:
                if character.name == self.dragging_character:
                    get_character_db()[character.name].selected = False
                    self.selected_team.remove(character)
                    
        self.render_team_display()
        self.render_character_scroll_selection()

    def get_click_coordinates(self, button):
        return (self.scene_manager.mouse_x - button.x, self.scene_manager.mouse_y - button.y)
  

    def init_char_select_desc(self, button):
        pass
    
    def start_click(self, _button, _sender):
        if not self.clicked_search and self.scene_manager.connected and not self.window_up:
            self.start_searching()

    #endregion

    def start_searching(self):
        play_sound(self.scene_manager.sounds["page"])
        self.clicked_search = True
        names = [x.name for x in self.selected_team]
        image = {"mode": self.player_profile.mode, "size": self.player_profile.size, "pixels": self.player_profile.tobytes()}
        player_pouch = [self.player_name, self.player_wins, self.player_losses, image["mode"], image["size"], image["pixels"]]
        self.scene_manager.connection.send_start_package(names, player_pouch)
        self.window_up = True
        self.render_search_panel()
    
    def get_filtered_characters_list(self) -> list[Character]:
        if not self.unlock_filtering:
            filtered_characters = list(get_character_db().values())
        else:
            filtered_characters = [char for char in get_character_db().values() if self.player.missions[char.name][5]]
            

        if not self.exclusive_filtering:
            for i, filter in enumerate(self.energy_filtering):
                if filter:
                    filtered_characters = [char for char in filtered_characters if char.uses_energy(i)]
        else:
            excluded_types = []
            for i, filter in enumerate(self.energy_filtering):
                if not filter:
                    excluded_types.append(i)
            filtered_characters = [char for char in filtered_characters if not char.uses_energy_mult(excluded_types)]
            for i, filter in enumerate(self.energy_filtering):
                if filter:
                    filtered_characters = [char for char in filtered_characters if char.uses_energy(i)]
        return filtered_characters
    
    def auto_queue(self):
        self.add_character(sys.argv[3])
        self.add_character(sys.argv[4])
        self.add_character(sys.argv[5])
        self.start_searching()
        self.full_render()

    def settle_player(self, username: str, wins: int, losses: int, medals: int, mission_data: str, ava_code = None, mission_complete: dict = {}):
        """Extracts and apportions player data into the character select scene.
        
           Called by Scene Manager to move from Login Scene or In-Game Scene to
           Character Select Scene"""
        logging.debug("Settling in Character Select!")
        self.clicked_search = False
        self.window_up = False
        self.player_name = username
        self.player_wins = wins
        self.player_losses = losses
        self.player_medals = medals
        reset_character_db()
        
        if ava_code:
            
            new_image = pickle.loads(ava_code)

            self.player_profile = Image.frombytes(mode = new_image["mode"], size = new_image["size"], data=new_image["pixels"])
        
        self.player = Player(self.player_name, self.player_wins, self.player_losses, self.player_profile, mission_data, self.player_medals, missions_complete=mission_complete)
        
        self.render_bordered_text(self.font, self.player.name, RED, BLACK, self.player_region_panel, 84, 2, 1)
        self.render_bordered_text(self.font, self.player.title, WHITE, BLACK, self.player_region_panel, 84, 21, 1)
        self.render_bordered_text(self.font, "Wins: ", WHITE, BLACK, self.player_region_panel, 84, 51, 1)
        self.render_bordered_text(self.font, "Losses: ", WHITE, BLACK, self.player_region_panel, 84, 67, 1)
        self.render_bordered_text(self.font, "Medals: ", WHITE, BLACK, self.player_region_panel, 84, 83, 1)
        self.render_bordered_text(self.font, "Clan: ", WHITE, BLACK, self.player_region_panel, 84, 99, 1)
        
        self.render_bordered_text(self.font, str(self.player.wins), WHITE, BLACK, self.player_region_panel, 149, 51, 1)
        self.render_bordered_text(self.font, str(self.player.losses), WHITE, BLACK, self.player_region_panel, 149, 67, 1)
        self.render_bordered_text(self.font, str(self.player.medals), WHITE, BLACK, self.player_region_panel, 149, 83, 1)
        self.render_bordered_text(self.font, "None", WHITE, BLACK, self.player_region_panel, 149, 99, 1)
        
        
        
        
        self.full_render()

    def start_battle(self, enemy_names, enemy_pouch, energy, seed):
        """Function called by Scene Manager to move from Character Select Scene to
           In-Game Scene after receiving an enemy start package from the server"""
        enemy_team = [Character(name) for name in enemy_names]
        
        enemy_pouch[6] = bytes(enemy_pouch[6])

        enemy_ava = Image.frombytes(enemy_pouch[3], (enemy_pouch[4], enemy_pouch[5]), enemy_pouch[6])

        enemy = Player(enemy_pouch[0], enemy_pouch[1], enemy_pouch[2], enemy_ava)

        

        for character in self.selected_team:
            character.dead = False
            character.hp = 200
            character.current_effects = []
            character.targeted = False
            character.acted = False

        self.scene_manager.start_battle(self.selected_team, enemy_team, self.player, enemy, energy, seed)


    


def make_character_select_scene(scene_manager) -> CharacterSelectScene:

    scene = CharacterSelectScene(scene_manager, sdl2.ext.SOFTWARE)

    

    return scene