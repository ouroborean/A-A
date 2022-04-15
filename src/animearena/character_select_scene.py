from pathlib import Path
from typing import Union
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
from animearena.character import Character, get_character_db
from animearena.ability import Ability
from animearena.mission import mission_db
from animearena.resource_manager import init_font
from playsound import playsound

def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass
FONTSIZE = 16

RESOURCES = Path(__file__).parent.parent.parent / "resources"
BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)

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

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #region field initialization
        self.scene_manager = scene_manager
        self.player_profile = self.scene_manager.surfaces["default_prof"]
        self.page_on_display = 1
        self.display_character = None
        self.searching = False
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
        #endregion
        #region region initialization
        self.character_select_region = self.region.subregion(15, 400, 770, 285)
        self.team_region = self.region.subregion(240, 20, 320, 100)
        self.character_info_region = self.region.subregion(72, 170, 770, 260)
        self.start_match_region = self.region.subregion(685, 50, 100, 40)
        self.how_to_region = self.region.subregion(685, 90, 100, 40)
        self.player_profile_region = self.region.subregion(15, 20, 200, 100)
        self.search_panel_region = self.region.subregion(144, 158, 0, 0)
        self.mission_region = self.region.subregion(210, 158, 0, 0)
        self.filter_region = self.region.subregion(70, 655, 210, 30)
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
        self.how_to_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["how_to"], 100, 40))
        self.how_to_button.click += self.tutorial_click
        self.character_sprites = {} 
        for k, v in get_character_db().items():
            self.character_sprites[k] = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[k+"allyprof"]), free=True)
        for sprite in self.character_sprites.values():
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
        self.render_character_selection()
        self.render_tutorial_button()
        self.render_team_display()
        self.render_start_button()
        self.render_player_profile()
        self.render_search_panel()
        self.render_filter_options()
        gc.collect()

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
        if self.unlock_filtering:
            self.filter_region.add_sprite(self.lock_border, -2, -2)
        self.filter_region.add_sprite(self.lock_icon, 0, 0)

        for i in range(5):
            if self.energy_filtering[i]:
                self.filter_region.add_sprite(self.energy_borders[i], -2 + (35 * (i + 1)), -2)
            self.filter_region.add_sprite(self.energy_icons[i], 35 * (i + 1), 0)
        
        if self.exclusive_filtering:
            self.filter_region.add_sprite(self.ex_border, 208, -2)
        self.filter_region.add_sprite(self.ex_icon, 210, 0)

    def render_search_panel(self):
        self.search_panel_region.clear()
        if self.clicked_search:
            self.add_sprite_with_border(self.search_panel_region, self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces["search"])), self.search_panel_border, 0, 0)
            cancel_search_button = self.create_text_display(self.font, "Cancel", WHITE, BLACK, 5, 5, 80)
            print(f"Search Panel needs size of {cancel_search_button.size}")
            cancel_search_button.click += self.cancel_search_click
            self.search_panel_region.add_sprite(cancel_search_button, 5, 5)
            

    def render_player_profile(self):
        self.player_profile_region.clear()

        
        self.add_sprite_with_border(self.player_profile_region, self.player_region_panel, self.player_region_border, 0, 0)
        
        

        self.player_profile_region.add_sprite(self.nametag, 105, 4)
        self.player_profile_region.add_sprite(self.wintag, 105, 38)
        self.player_profile_region.add_sprite(self.losstag, 105, 72)
        self.medaltag = self.create_text_display(self.font, f"Medals: {self.player.medals}", BLACK, WHITE, 12, 3, 95)
        self.medal_tag_border = self.sprite_factory.from_color(BLACK, (self.medaltag.size[0] + 4, self.medaltag.size[1] + 4))
        
        self.add_sprite_with_border(self.player_profile_region, self.medaltag, self.medal_tag_border, 103, 110)
        
        

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
        if self.player.missions[self.character_info_prof.character.name][5]:
            mission_button = self.create_text_display(self.font, "Missions", WHITE, BLACK, 10, 3, 80)
            mission_button.click += self.mission_click
            self.add_bordered_sprite(self.character_info_region, mission_button, WHITE, 47, 225)
        else:
            unlock_button = self.create_text_display(self.font, "Unlock", WHITE, BLACK, 16, 3, 80)
            unlock_button.click += self.unlock_click
            self.add_bordered_sprite(self.character_info_region, unlock_button, WHITE, 47, 225)
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
        if self.player.missions[self.character_info_prof.character.name][5]:
            mission_button = self.create_text_display(self.font, "Missions", WHITE, BLACK, 10, 3, 80)
            mission_button.click += self.mission_click
            self.add_bordered_sprite(self.character_info_region, mission_button, WHITE, 47, 225)
        else:
            unlock_button = self.create_text_display(self.font, "Unlock", WHITE, BLACK, 16, 3, 80)
            unlock_button.click += self.unlock_click
            self.add_bordered_sprite(self.character_info_region, unlock_button, WHITE, 47, 225)
        
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

        if self.page_on_display > 1:
            self.character_select_region.add_sprite(self.left_button, -20, 105)

        column = 0
        row = 0
        if not self.unlock_filtering:
            self.filtered_characters = list(get_character_db().values())
        else:
            self.filtered_characters = [char for char in get_character_db().values() if self.player.missions[char.name][5]]
            for character in self.filtered_characters:
                print(character.name)

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
                self.add_sprite_with_border(self.character_select_region, self.character_sprites[self.filtered_characters[current_slot].name], self.character_sprites[self.filtered_characters[current_slot].name].border_box, 60 + (column * 110), 35 + (row * 110))
                if self.filtered_characters[current_slot].selected or not self.player.missions[self.filtered_characters[current_slot].name][5]:
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

    #endregion

    #region On-Click Event Handlers

    def tutorial_click(self, button, sender):
        self.scene_manager.start_tutorial(self.player)

    def exclusive_filter_click(self, button, sender):
        self.exclusive_filtering = not self.exclusive_filtering
        
        self.energy_filtering[4] = self.exclusive_filtering
        self.page_on_display = 1
        self.render_filter_options()
        self.render_character_selection()

    def lock_filter_click(self, button, sender):
        self.unlock_filtering = not self.unlock_filtering
        self.page_on_display = 1
        self.render_filter_options()
        self.render_character_selection()

    def energy_filter_click(self, button, sender):
        self.energy_filtering[button.energy_id] = not self.energy_filtering[button.energy_id]
        if button.energy_id == 4:
            self.exclusive_filtering = self.energy_filtering[button.energy_id]
        self.page_on_display = 1
        self.render_filter_options()
        self.render_character_selection()

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
        self.render_character_selection()
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
            self.render_character_selection()

    def right_click(self, _button, _sender):
        if not self.window_up:
            play_sound(self.scene_manager.sounds["page"])
            self.page_on_display += 1
            max_pages = len(get_character_db()) // 12
            if len(get_character_db()) % 12 > 0:
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
                self.init_char_select_desc(button)
                self.render_main_character_info()

    def character_click(self, button, _sender):
        if not self.window_up:
            if self.detail_target == button.character and not button.character.selected and len(self.selected_team) < 3 and self.player.missions[button.character.name][5]:
                play_sound(self.scene_manager.sounds["select"])
                self.selected_team.append(button.character)
                button.character.selected = True
                self.render_team_display()
                self.render_character_selection()
            else:
                play_sound(self.scene_manager.sounds["click"])
                self.detail_target = button.character
                self.display_character = button.character
                self.init_char_select_desc(button)
                    
                self.render_character_selection()
                self.render_main_character_info()
            self.render_start_button()

    def init_char_select_desc(self, button):
        if not button.character.char_select_desc:
            button.character.char_select_desc = self.create_text_display(self.font, button.character.desc, BLACK, WHITE, 5, 0, 475, 130)
            for ability in button.character.main_abilities:
                ability.char_select_desc = self.create_text_display(self.font, ability.name + ": " + ability.desc, BLACK, WHITE, 5, 0, 475, 130)
            for ability in button.character.alt_abilities:
                ability.char_select_desc = self.create_text_display(self.font, ability.name + ": " + ability.desc, BLACK, WHITE, 5, 0, 475, 130)

    def start_click(self, _button, _sender):
        if not self.clicked_search and self.scene_manager.connected and not self.window_up:
            print("Detected a start click!")
            play_sound(self.scene_manager.sounds["page"])
            self.clicked_search = True
            names = [x.name for x in self.selected_team]
            image = {"mode": self.player_profile.mode, "size": self.player_profile.size, "pixels": self.player_profile.tobytes()}
            player_pouch = [self.player_name, self.player_wins, self.player_losses, image["mode"], image["size"], image["pixels"]]
            self.scene_manager.connection.send_start_package(names, player_pouch)
            self.window_up = True
            self.render_search_panel()

    #endregion

    

    def settle_player(self, username: str, wins: int, losses: int, medals: int, mission_data: str, ava_code = None, mission_complete: dict = {}):
        """Extracts and apportions player data into the character select scene.
        
           Called by Scene Manager to move from Login Scene or In-Game Scene to
           Character Select Scene"""
        self.clicked_search = False
        self.window_up = False
        self.player_name = username
        self.player_wins = wins
        self.player_losses = losses
        self.player_medals = medals

        self.nametag = self.create_text_display(self.font, self.player_name, BLACK, WHITE, 0, 0, 95)
        self.wintag = self.create_text_display(self.font, f"Wins: {self.player_wins}", BLACK, WHITE, 0, 0, 95)
        self.losstag = self.create_text_display(self.font, f"Losses: {self.player_losses}", BLACK, WHITE, 0, 0, 95)
        if ava_code:
            
            new_image = pickle.loads(ava_code)

            self.player_profile = Image.frombytes(mode = new_image["mode"], size = new_image["size"], data=new_image["pixels"])
        
        self.player = Player(self.player_name, self.player_wins, self.player_losses, self.player_profile, mission_data, self.player_medals, missions_complete=mission_complete)
        
        self.full_render()

    def start_battle(self, enemy_names, enemy_pouch, energy):
        """Function called by Scene Manager to move from Character Select Scene to
           In-Game Scene after receiving an enemy start package from the server"""
        enemy_team = [Character(name) for name in enemy_names]
        
        enemy_pouch[6] = bytes(enemy_pouch[6])

        enemy_ava = Image.frombytes(enemy_pouch[3], (enemy_pouch[4], enemy_pouch[5]), enemy_pouch[6])

        enemy = Player(enemy_pouch[0], enemy_pouch[1], enemy_pouch[2], enemy_ava)

        

        for character in self.selected_team:
            character.dead = False
            character.hp = 100
            character.current_effects = []
            character.targeted = False
            character.acted = False

        self.scene_manager.start_battle(self.selected_team, enemy_team, self.player, enemy, energy)


    


def make_character_select_scene(scene_manager) -> CharacterSelectScene:

    scene = CharacterSelectScene(scene_manager, sdl2.ext.SOFTWARE)

    

    return scene