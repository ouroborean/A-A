from pathlib import Path
from typing import Union
import os
import threading
import gc
import tkinter as tk
from tkinter import filedialog
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import importlib.resources
import easygui
from PIL import Image
import dill as pickle
from io import StringIO

from animearena import engine
from animearena import character
from animearena import player
from animearena.character import Character, character_db
from animearena.ability import Ability
from animearena.engine import FilterType
from animearena.player import Player
from animearena.mission import mission_db
from playsound import playsound

def get_path(file_name: str) -> Path:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return path

def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass
FONTSIZE = 16
FONT_FILENAME = "Basic-Regular.ttf"

def init_font():
    with importlib.resources.path('animearena.resources', FONT_FILENAME) as path:
        return sdl2.sdlttf.TTF_OpenFont(str.encode(os.fspath(path)), FONTSIZE)



RESOURCES = Path(__file__).parent.parent.parent / "resources"
BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)

TEST_ENEMY_TEAM = [character.get_character("jack"), character.get_character("jiro"), character.get_character("raba")]

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
    page_on_display: int
    selected_team: list[Character]
    clicked_search: bool
    player_profile: Image
    player_profile_lock: threading.Lock
    player_name: str
    player_wins: int
    player_losses: int
    player: Player
    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #region field initialization
        self.scene_manager = scene_manager
        self.player_profile = self.scene_manager.surfaces["default_prof"]
        self.page_on_display = 1
        self.display_character = None
        self.searching = False
        self.player_name = ""
        self.font = init_font()
        self.player_profile_lock = threading.Lock()
        self.selected_team = []
        self.clicked_search = False
        self.window_up = False
        #endregion
        #region region initialization
        self.character_select_region = self.region.subregion(15, 400, 770, 285)
        self.team_region = self.region.subregion(240, 20, 320, 100)
        self.character_info_region = self.region.subregion(72, 170, 770, 260)
        self.start_match_region = self.region.subregion(685, 50, 100, 100)
        self.player_profile_region = self.region.subregion(15, 20, 200, 100)
        self.search_panel_region = self.region.subregion(144, 158, 0, 0)
        self.mission_region = self.region.subregion(210, 158, 0, 0)
        #endregion
        #region sprite initialization
        self.banner_border = self.sprite_factory.from_color(BLACK, (179, 254))
        self.search_panel_border = self.sprite_factory.from_color(BLACK, (516, 388))
        self.player_region_border = self.sprite_factory.from_color(BLACK, (204, 104))
        self.info_display_border = self.sprite_factory.from_color(BLACK, (479, 149))
        self.avatar_upload_border = self.sprite_factory.from_color(WHITE, (94, 45))
        self.left_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["left_arrow"]))
        self.left_button.click += self.left_click
        self.right_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["right_arrow"]))
        self.right_button.click += self.right_click
        self.character_sprites = list([self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(self.scene_manager.surfaces[char.name+"allyprof"]), free=True) for char in list(character_db.values())])
        for sprite in self.character_sprites:
            sprite.click += self.character_click
            sprite.border_box = self.sprite_factory.from_color(BLACK, (104, 104))
        self.start_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["start"], 100, 40), free=True)
        self.start_button.click += self.start_click
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
        self.alt_arrow = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces["right_arrow"], width = 50, height = 50), free=True)
        self.alt_arrow.click += self.alt_arrow_click
        self.avatar = self.sprite_factory.from_surface(self.get_scaled_surface(self.player_profile, 100, 100), free=True)
        self.avatar.border_box = self.sprite_factory.from_color(BLACK, (104, 104))
        self.team_display = [self.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (100,100)) for i in range(3)]
        for sprite in self.team_display:
            sprite.click += self.team_display_click
            sprite.border_box = self.sprite_factory.from_color(BLACK, (104, 104))
        self.info_text_panel = self.create_text_display(self.font, "", BLACK,
                                                   WHITE, 5, 0, 475, 130)
        self.player_region_panel = self.sprite_factory.from_color(WHITE, self.player_profile_region.size())
        
        #endregion


    #region Render Functions

    def full_render(self):
        self.region.clear()
        self.region.add_sprite(
            self.sprite_factory.from_surface(
                self.get_scaled_surface(self.scene_manager.surfaces["background"]), free=True), 0, 0)
        if self.display_character:
            self.render_main_character_info()
        self.render_character_selection()
        self.render_team_display()
        self.render_start_button()
        self.render_player_profile()
        self.render_search_panel()
        gc.collect()

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


    def render_search_panel(self):
        self.search_panel_region.clear()
        if self.clicked_search:
            self.add_sprite_with_border(self.search_panel_region, self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces["search"])), self.search_panel_border, 0, 0)
            cancel_search_button = self.create_text_display(self.font, "Cancel", WHITE, BLACK, 5, 5, 80)
            print(f"Search Panel needs size of {cancel_search_button.size}")
            cancel_search_button.click += self.cancel_search_click
            

    def render_player_profile(self):
        self.player_profile_region.clear()

        
        self.add_sprite_with_border(self.player_profile_region, self.player_region_panel, self.player_region_border, 0, 0)
        
        

        self.player_profile_region.add_sprite(self.nametag, 105, 4)
        self.player_profile_region.add_sprite(self.wintag, 105, 38)
        self.player_profile_region.add_sprite(self.losstag, 105, 72)
        

        self.player_profile_lock.acquire()
        if self.player_profile == None:
            self.player_profile = self.scene_manager.surfaces["default_prof"]

        self.avatar.surface = self.get_scaled_surface(self.player_profile)
        
        self.add_sprite_with_border(self.player_profile_region, self.avatar, self.avatar.border_box, 0, 0)
        upload_button = self.create_text_display(self.font, "Upload Avatar", WHITE, BLACK, 20, 0, 90)
        upload_button.click += self.avatar_upload_click
        self.add_sprite_with_border(self.player_profile_region, upload_button, self.avatar_upload_border, 5, 104)
        self.player_profile_lock.release()

    def render_main_character_info(self):
        
        self.character_info_region.clear()
        self.character_info_prof.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.name + "banner"])
        self.character_info_prof.free = True
        self.character_info_prof.character = self.display_character
        self.add_sprite_with_border(self.character_info_region, self.character_info_prof, self.banner_border, 0, 5)
        mission_button = self.create_text_display(self.font, "Missions", WHITE, BLACK, 10, 3, 80)
        mission_button.click += self.mission_click
        self.add_bordered_sprite(self.character_info_region, mission_button, WHITE, 47, 225)
        for i, ability in enumerate(self.main_ability_sprites):
            ability.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.main_abilities[i].db_name])
            ability.ability = self.display_character.main_abilities[i]
            ability.free = True
            self.add_sprite_with_border(self.character_info_region, ability, ability.border_box, x=55 + ((i + 1) * 125),
                                                  y=5)

        if self.display_character.alt_abilities:
            self.character_info_region.add_sprite(self.alt_arrow, 670, 17)

        self.add_sprite_with_border(self.character_info_region, self.detail_target.char_select_desc, self.info_display_border, 180, 110)
        

        if type(self.detail_target) == Ability:
            self.show_ability_details(self.detail_target)

    def render_alt_character_info(self):
        self.character_info_region.clear()
        self.alt_character_info_prof.surface = self.get_scaled_surface(self.scene_manager.surfaces[self.display_character.name + "banner"])
        self.alt_character_info_prof.character = self.display_character
        self.alt_character_info_prof.free = True
        self.add_sprite_with_border(self.character_info_region, self.alt_character_info_prof, self.banner_border, 0, 5)
        mission_button = self.create_text_display(self.font, "Missions", WHITE, BLACK, 10, 3, 80)
        mission_button.click += self.mission_click
        self.add_bordered_sprite(self.character_info_region, mission_button, WHITE, 47, 225)
        for i, ability in enumerate(self.display_character.alt_abilities):
            self.alt_ability_sprites[i].surface = self.get_scaled_surface(self.scene_manager.surfaces[ability.db_name])
            self.alt_ability_sprites[i].free = True
            self.alt_ability_sprites[i].ability = ability
            self.add_sprite_with_border(self.character_info_region, self.alt_ability_sprites[i], self.alt_ability_sprites[i].border_box, x=55 + ((i + 1) * 125),
                                                  y=5)

        main_arrow = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["left_arrow"], width = 50, height = 50), free=True)
        main_arrow.click += self.main_arrow_click
        self.character_info_region.add_sprite(main_arrow, 670, 17)

        if type(self.detail_target) == Ability:
            text = self.detail_target.name + ": " + self.detail_target.desc
        else:
            text = self.detail_target.desc

        self.add_sprite_with_border(self.character_info_region, self.detail_target.char_select_desc, self.info_display_border, 180, 110)

        if type(self.detail_target) == Ability:
            self.show_ability_details(self.detail_target)

    def show_ability_details(self, ability: Ability):
        if not self.window_up:
            self.render_energy_cost(ability)
            self.render_cooldown(ability)

    def render_energy_cost(self, ability: Ability):
        total_energy = 0
        for k, v in ability.cost.items():
            for i in range(v):
                self.character_info_region.add_sprite(
                    self.sprite_factory.from_surface(
                        self.get_scaled_surface(self.scene_manager.surfaces[k.name])),
                    185 + (total_energy * 13), 240)
                total_energy += 1

    def render_cooldown(self, ability: Ability):
        cooldown_panel = self.create_text_display(self.font,
                                                  f"CD: {ability.cooldown}",
                                                  BLACK, WHITE, 0, 0, 40, 3)
        self.character_info_region.add_sprite(cooldown_panel, x=610, y=235)

    def render_team_display(self):

        self.team_region.clear()

        for i, character in enumerate(self.selected_team):
            self.team_display[i].surface = self.get_scaled_surface(self.scene_manager.surfaces[character.name + "allyprof"])
            self.team_display[i].free = True
            self.team_display[i].character = character
            self.add_sprite_with_border(self.team_region, self.team_display[i], self.team_display[i].border_box, i * 110, 0)

    def render_start_button(self):
        self.start_match_region.clear()
        if len(self.selected_team) == 3:
            self.start_match_region.add_sprite(self.start_button, 0, 0)

    def render_character_selection(self):
        self.character_select_region.clear()

        self.character_select_region.add_sprite(self.left_button, -20, 105)

        
        self.character_select_region.add_sprite(self.right_button, 715, 105)

        column = 0
        row = 0
        characters = list(character_db.values())
        for i in range(12):
            current_slot = i + ((self.page_on_display - 1) * 12)
            try:
                self.add_sprite_with_border(self.character_select_region, self.character_sprites[current_slot], self.character_sprites[current_slot].border_box, 60 + (column * 110), 35 + (row * 110))
                if characters[current_slot].selected:
                    selected_filter = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["locked"]), free=True)
                    selected_filter.character = characters[current_slot]
                    selected_filter.click += self.character_click
                    self.character_select_region.add_sprite(selected_filter, 60 + (column * 110), 35 + (row * 110))
                else:
                    self.character_sprites[current_slot].character = characters[current_slot]
                    
                
            except IndexError:
                break
            column += 1
            if column == 6:
                row += 1
                column = 0

    #endregion

    #region On-Click Event Handlers

    def mission_click(self, button, sender):
        self.window_up = not self.window_up
        if self.window_up:
            self.render_mission_panel()
        else:
            self.mission_region.clear()

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
            self.render_character_selection()

    def right_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.page_on_display += 1
            max_pages = len(character_db) // 12
            if len(character_db) % 12 > 0:
                max_pages += 1
            if self.page_on_display > max_pages:
                self.page_on_display = max_pages
            self.render_character_selection()

    def alt_arrow_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.render_alt_character_info()

    def main_arrow_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.render_main_character_info()


    def ability_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.ability
            self.render_main_character_info()
            self.show_ability_details(button.ability)

    def alt_ability_click(self, button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.detail_target = button.ability
            self.render_alt_character_info()
            self.show_ability_details(button.ability)

    

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
        if not self.window_up:
            if self.detail_target == button.character:
                play_sound(self.scene_manager.sounds["undo"])
                button.character.selected = False
                self.selected_team.remove(button.character)
                self.render_character_selection()
                self.render_start_button()
                self.render_team_display()
            else:
                play_sound(self.scene_manager.sounds["click"])
                self.detail_target = button.character
                self.display_character = button.character
                self.render_main_character_info()

    def character_click(self, button, _sender):
        if not self.window_up:
            if self.detail_target == button.character and not button.character.selected and len(self.selected_team) < 3:
                play_sound(self.scene_manager.sounds["select"])
                self.selected_team.append(button.character)
                button.character.selected = True
                self.render_team_display()
                self.render_character_selection()
            else:
                play_sound(self.scene_manager.sounds["click"])
                self.detail_target = button.character
                self.display_character = button.character
                if not button.character.char_select_desc:
                    button.character.char_select_desc = self.create_text_display(self.font, button.character.desc, BLACK, WHITE, 5, 0, 475, 130)
                    for ability in button.character.main_abilities:
                        ability.char_select_desc = self.create_text_display(self.font, ability.name + ": " + ability.desc, BLACK, WHITE, 5, 0, 475, 130)
                    for ability in button.character.alt_abilities:
                        ability.char_select_desc = self.create_text_display(self.font, ability.name + ": " + ability.desc, BLACK, WHITE, 5, 0, 475, 130)
                    
                self.render_character_selection()
                self.render_main_character_info()
            self.render_start_button()

    def start_click(self, _button, _sender):
        if not self.clicked_search and self.scene_manager.connected and not self.window_up:
            print("Detected a start click!")
            play_sound(self.scene_manager.sounds["page"])
            self.clicked_search = True
            names = [x.name for x in self.selected_team]
            image = {"mode": self.player_profile.mode, "size": self.player_profile.size, "pixels": self.player_profile.tobytes()}
            player_pouch = [self.player_name, self.player_wins, self.player_losses, image]
            pickled_player = pickle.dumps(player_pouch)
            self.scene_manager.connection.send_start_package(names, pickled_player)
            self.window_up = True
            self.render_search_panel()

    #endregion

    def settle_player(self, username: str, wins: int, losses: int, mission_data: str, ava_code = None):
        """Extracts and apportions player data into the character select scene.
        
           Called by Scene Manager to move from Login Scene or In-Game Scene to
           Character Select Scene"""
        self.clicked_search = False
        self.window_up = False
        self.player_name = username
        self.player_wins = wins
        self.player_losses = losses

        self.nametag = self.create_text_display(self.font, self.player_name, BLACK, WHITE, 0, 0, 95)
        self.wintag = self.create_text_display(self.font, f"Wins: {self.player_wins}", BLACK, WHITE, 0, 0, 95)
        self.losstag = self.create_text_display(self.font, f"Losses: {self.player_losses}", BLACK, WHITE, 0, 0, 95)

        if ava_code:
            new_image = pickle.loads(ava_code)

            self.player_profile = Image.frombytes(mode = new_image["mode"], size = new_image["size"], data=new_image["pixels"])
        
        self.player = Player(self.player_name, self.player_wins, self.player_losses, self.player_profile, mission_data)
        
        self.full_render()

    def start_battle(self, enemy_names, pickled_player, energy):
        """Function called by Scene Manager to move from Character Select Scene to
           In-Game Scene after receiving an enemy start package from the server"""
        enemy_team = [Character(name) for name in enemy_names]
        
        player_pouch = pickle.loads(pickled_player)

        enemy_ava = Image.frombytes(player_pouch[3]["mode"], player_pouch[3]["size"], player_pouch[3]["pixels"])

        enemy = Player(player_pouch[0], player_pouch[1], player_pouch[2], enemy_ava)

        

        for character in self.selected_team:
            character.dead = False
            character.hp = 100
            character.current_effects = []
            character.targeted = False
            character.acted = False

        self.scene_manager.start_battle(self.selected_team, enemy_team, self.player, enemy, energy)


    


def make_character_select_scene(scene_manager) -> CharacterSelectScene:

    scene = CharacterSelectScene(scene_manager, sdl2.ext.SOFTWARE, RESOURCES)

    

    return scene