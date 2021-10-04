from pathlib import Path
from typing import Union

import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import ctypes

from animearena import engine
from animearena import character
from animearena.character import Character, character_db
from animearena.ability import Ability
from animearena.engine import FilterType

FONT_FILENAME = "Basic-Regular.ttf"
FONTSIZE = 16
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

    character_info_region: engine.Region
    character_select_region: engine.Region
    team_region: engine.Region
    start_match_region: engine.Region
    player_profile_region: engine.Region
    detail_target: Union[Character, Ability] = None
    display_character: Character
    page_on_display: int
    selected_team: list[Character] = []
    clicked_search: bool = False


    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.page_on_display = 1
        self.display_character = None
        self.scene_manager = scene_manager
        fontpath = str.encode(f"{RESOURCES / FONT_FILENAME}")
        self.font = sdl2.sdlttf.TTF_OpenFont(fontpath, FONTSIZE)

        self.character_select_region = self.region.subregion(15, 400, 770, 285)

        self.team_region = self.region.subregion(240, 50, 320, 100)
        self.team_region.add_sprite(
            self.sprite_factory.from_color(RED, self.team_region.size()), 0, 0)

        self.character_info_region = self.region.subregion(15, 170, 770, 260)
        self.character_info_region.add_sprite(
            self.sprite_factory.from_color(GREEN,
                                           self.character_info_region.size()),
            0, 0)

        self.start_match_region = self.region.subregion(685, 50, 100, 100)
        self.start_match_region.add_sprite(
            self.sprite_factory.from_color(PURPLE,
                                           self.start_match_region.size()), 0,
            0)

        self.player_profile_region = self.region.subregion(15, 50, 200, 100)
        self.player_profile_region.add_sprite(
            self.sprite_factory.from_color(AQUA,
                                           self.player_profile_region.size()),
            0, 0)

    def left_click(self, _button, _sender):
        self.page_on_display -= 1
        if self.page_on_display < 1:
            self.page_on_display = 1
        self.full_render()

    def right_click(self, _button, _sender):
        self.page_on_display += 1
        max_pages = len(character_db) // 12
        if len(character_db) % 12 > 0:
            max_pages += 1
        if self.page_on_display > max_pages:
            self.page_on_display = max_pages
        self.full_render()

    def alt_arrow_click(self, _button, _sender):
        self.render_alt_character_info()

    def main_arrow_click(self, _button, _sender):
        self.render_main_character_info()

    def show_ability_details(self, ability: Ability):
        self.render_energy_cost(ability)
        self.render_cooldown(ability)

    def render_energy_cost(self, ability: Ability):
        total_energy = 0
        for k, v in ability.cost.items():
            for i in range(v):
                self.character_info_region.add_sprite(
                    self.sprite_factory.from_surface(
                        self.get_scaled_surface(self.surfaces[k.name])),
                    185 + (total_energy * 13), 240)
                total_energy += 1

    def render_cooldown(self, ability: Ability):
        cooldown_panel = self.create_text_display(self.font,
                                                  f"CD: {ability.cooldown}",
                                                  BLACK, WHITE, 0, 0, 40, 3)
        self.character_info_region.add_sprite(cooldown_panel, x=610, y=235)

    def ability_click(self, button, _sender):
        self.detail_target = button.ability
        self.render_main_character_info()
        self.show_ability_details(button.ability)

    def alt_ability_click(self, button, _sender):
        self.detail_target = button.ability
        self.render_alt_character_info()
        self.show_ability_details(button.ability)

    def render_main_character_info(self):
        self.character_info_region.clear()
        character_info_prof = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.display_character.profile_image))
        character_info_prof.character = self.display_character
        character_info_prof.click += self.character_main_click
        self.add_bordered_sprite(self.character_info_region, character_info_prof, BLACK, 5, 5)

        for i, ability in enumerate(self.display_character.main_abilities):
            ability_button = self.ui_factory.from_surface(
                sdl2.ext.BUTTON, self.get_scaled_surface(ability.image))
            ability_button.ability = ability
            ability_button.click += self.ability_click
            self.add_bordered_sprite(self.character_info_region, ability_button, BLACK, x=55 + ((i + 1) * 125),
                                                  y=5)

        if self.display_character.alt_abilities:
            alt_arrow = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.surfaces["right_arrow"]))
            alt_arrow.click += self.alt_arrow_click
            self.character_info_region.add_sprite(alt_arrow, 680, 17)

        if type(self.detail_target) == Ability:
            text = self.detail_target.name + ": " + self.detail_target.desc
        else:
            text = self.detail_target.desc

        info_text_panel = self.create_text_display(self.font, text, BLACK,
                                                   WHITE, 5, 0, 475, 130)
        self.add_bordered_sprite(self.character_info_region, info_text_panel, BLACK, 180, 110)

        if type(self.detail_target) == Ability:
            self.show_ability_details(self.detail_target)

    def render_alt_character_info(self):
        self.character_info_region.clear()
        character_info_prof = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.display_character.profile_image))
        character_info_prof.character = self.display_character
        character_info_prof.click += self.character_alt_click
        self.add_bordered_sprite(self.character_info_region, character_info_prof, BLACK, 5, 5)

        for i, ability in enumerate(self.display_character.alt_abilities):
            ability_button = self.ui_factory.from_surface(
                sdl2.ext.BUTTON, self.get_scaled_surface(ability.image))
            ability_button.ability = ability
            ability_button.click += self.alt_ability_click
            self.add_bordered_sprite(self.character_info_region, ability_button, BLACK, x=55 + ((i + 1) * 125),
                                                  y=5)

        main_arrow = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.surfaces["left_arrow"]))
        main_arrow.click += self.main_arrow_click
        self.character_info_region.add_sprite(main_arrow, 680, 17)

        if type(self.detail_target) == Ability:
            text = self.detail_target.name + ": " + self.detail_target.desc
        else:
            text = self.detail_target.desc

        info_text_panel = self.create_text_display(self.font, text, BLACK,
                                                   WHITE, 5, 0, 475, 130)
        self.character_info_region.add_sprite(info_text_panel, x=180, y=110)

        if type(self.detail_target) == Ability:
            self.show_ability_details(self.detail_target)

    def character_alt_click(self, button, _sender):
        self.detail_target = button.character
        self.display_character = button.character
        self.render_alt_character_info()

    def character_main_click(self, button, _sender):
        self.detail_target = button.character
        self.display_character = button.character
        self.render_main_character_info()

    def team_display_click(self, button, _sender):
        if self.detail_target == button.character:
            button.character.selected = False
            self.selected_team.remove(button.character)
            self.full_render()
        else:
            self.detail_target = button.character
            self.display_character = button.character
            self.render_main_character_info()

    def render_team_display(self):

        self.team_region.clear()

        for i, character in enumerate(self.selected_team):
            team_display = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(character.profile_image))
            team_display.character = character
            team_display.click += self.team_display_click
            self.add_bordered_sprite(self.team_region, team_display, BLACK, i * 110, 0)

    def character_click(self, button, _sender):
        if self.detail_target == button.character and not button.character.selected and len(self.selected_team) < 3:
            self.selected_team.append(button.character)
            button.character.selected = True
            self.full_render()
        else:
            self.detail_target = button.character
            self.display_character = button.character
            self.render_main_character_info()
        

    def render_start_button(self):
        if len(self.selected_team) == 3:
            start_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.surfaces["start"], 100, 40))
            start_button.click += self.start_click
            self.start_match_region.add_sprite(start_button, 0, 0)

    def start_click(self, _button, _sender):
        if not self.clicked_search:
            self.clicked_search = True
            names = [x.name for x in self.selected_team]
            self.scene_manager.connection.send_team_names(names)
    
    def start_battle(self, enemy_names):

        enemy_team = [Character(name) for name in enemy_names]

        self.scene_manager.start_battle(self.selected_team, enemy_team)

    def full_render(self):

        self.region.clear()
        self.region.add_sprite(
            self.sprite_factory.from_surface(
                self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        if self.display_character:
            self.render_main_character_info()
        self.render_character_selection()
        self.render_team_display()
        self.render_start_button()

    def render_character_selection(self):
        self.character_select_region.clear()

        left_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.surfaces["left_arrow"]))
        left_button.click += self.left_click
        self.character_select_region.add_sprite(left_button, -20, 105)

        right_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.surfaces["right_arrow"]))
        right_button.click += self.right_click
        self.character_select_region.add_sprite(right_button, 715, 105)

        column = 0
        row = 0
        characters = list(character_db.values())
        for i in range(12):
            current_slot = i + ((self.page_on_display - 1) * 12)
            try:
                if characters[current_slot].selected:
                    prof_button = self.create_selected_version(self.get_scaled_surface(characters[current_slot].profile_image), FilterType.LOCKED)
                else:
                    prof_button = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        characters[current_slot].profile_image))
                
                prof_button.character = characters[current_slot]
                prof_button.click += self.character_click
            except IndexError:
                break
            self.add_bordered_sprite(self.character_select_region, prof_button, BLACK, 60 + (column * 110), 35 + (row * 110))
            column += 1
            if column == 6:
                row += 1
                column = 0


def make_character_select_scene(scene_manager) -> CharacterSelectScene:

    scene = CharacterSelectScene(scene_manager, sdl2.ext.SOFTWARE, RESOURCES)

    assets = {
        "right_arrow": "arrowright.png",
        "left_arrow": "arrowleft.png",
        "background": "bright_background.png",
        "PHYSICAL": "physicalEnergy.png",
        "SPECIAL": "specialEnergy.png",
        "MENTAL": "mentalEnergy.png",
        "WEAPON": "weaponEnergy.png",
        "RANDOM": "randomEnergy.png",
        "selected": "selected_pane.png",
        "ally": "ally_pane.png",
        "locked": "null_pane.png",
        "enemy": "enemy_pane.png",
        "start": "start_button.png"
    }
    scene.load_assets(**assets)
    scene.full_render()
    return scene