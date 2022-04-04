import logging
import math
from msilib.schema import ProgId
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import dill as pickle
import itertools
import textwrap
import os
import json
import importlib.resources
from PIL import Image
from animearena import engine
from animearena import character
from animearena.character import Character, get_character_db
from animearena.ability import Ability, Target, one, two, three
from animearena.energy import Energy
from animearena.effects import Effect, EffectType
from animearena.player import Player
from random import randint
from playsound import playsound
from pathlib import Path
from typing import Optional, Union
import typing

if typing.TYPE_CHECKING:
    from animearena.scene_manager import SceneManager

FONT_FILENAME = "Basic-Regular.ttf"
FONTSIZE = 16
COOLDOWN_FONTSIZE = 100
STACK_FONTSIZE = 28
INNER_STACK_FONTSIZE = 22


def init_font(size: int):
    with importlib.resources.path('animearena.resources',
                                  FONT_FILENAME) as path:
        return sdl2.sdlttf.TTF_OpenFont(str.encode(os.fspath(path)), size)


def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass


RESOURCES = Path(__file__).parent.parent.parent / "resources"
BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)
TRANSPARENT = sdl2.SDL_Color(255, 255, 255, 255)


class MatchPouch():
    team1_pouch: list
    team2_pouch: list

    def __init__(self, team1pouch, team2pouch):
        self.team1_pouch = team1pouch
        self.team2_pouch = team2pouch


class Team():

    character_managers: list["CharacterManager"]
    energy_pool: dict[Energy, int]

    def __init__(self, characters: list["CharacterManager"]):
        self.character_managers = characters
        self.energy_pool = {
            Energy.PHYSICAL: 0,
            Energy.SPECIAL: 0,
            Energy.MENTAL: 0,
            Energy.WEAPON: 0,
            Energy.RANDOM: 0
        }


class ActiveTeamDisplay():

    scene: engine.Scene
    team: Team
    team_region: engine.Region
    energy_region: engine.Region
    character_regions: list[engine.Region]
    effect_regions: list[engine.Region]
    targeting_regions: list[engine.Region]
    text_regions: list[engine.Region]
    hp_bar_regions: list[engine.Region]

    def __init__(self, scene: engine.Scene):
        self.scene = scene
        self.team_region = self.scene.region.subregion(x=5,
                                                       y=108,
                                                       width=670,
                                                       height=750)
        self.character_regions = [
            self.team_region.subregion(x=0, y=i * 250, width=670, height=230)
            for i in range(3)
        ]
        for region in self.character_regions:
            region.add_sprite(
                self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces["banner"]), 0, 0)
        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.text_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.character_regions:
            self.effect_regions.append(region.subregion(-3, 124, 106, 103))
            self.targeting_regions.append(
                region.subregion(x=105, y=0, width=25, height=100))
            self.text_regions.append(
                region.subregion(x=150, y=110, width=520, height=110))
            self.hp_bar_regions.append(region.subregion(0, 100, 100, 20))

    def assign_team(self, team: Team):
        self.team = team
        for i, manager in enumerate(team.character_managers):
            manager.targeting_region = self.targeting_regions[i]
            manager.text_region = self.text_regions[i]
            manager.effect_region = self.effect_regions[i]
            manager.hp_bar_region = self.hp_bar_regions[i]
            manager.character_region = self.character_regions[i]

    def update_display(self):
        for manager in self.team.character_managers:
            manager.update()


class EnemyTeamDisplay():

    scene: engine.Scene
    team: Team
    enemy_region: engine.Region
    effect_regions: list[engine.Region]
    targeting_regions: list[engine.Region]
    hp_bar_regions: list[engine.Region]

    def __init__(self, scene: engine.Scene):
        self.scene = scene
        self.enemy_region = self.scene.region.subregion(x=795,
                                                        y=108,
                                                        width=130,
                                                        height=750)
        self.enemy_regions = [
            self.enemy_region.subregion(x=0, y=i * 250, width=130, height=230)
            for i in range(3)
        ]

        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.enemy_regions:
            self.effect_regions.append(region.subregion(-3, 124, 106, 103))
            self.targeting_regions.append(
                region.subregion(x=-30, y=0, width=25, height=100))
            self.hp_bar_regions.append(region.subregion(0, 100, 100, 20))

    def assign_team(self, team: Team):
        self.team = team
        for i, manager in enumerate(team.character_managers):
            manager.targeting_region = self.targeting_regions[i]
            manager.effect_region = self.effect_regions[i]
            manager.hp_bar_region = self.hp_bar_regions[i]
            manager.character_region = self.enemy_regions[i]

    def update_display(self):
        for manager in self.team.character_managers:
            manager.update_limited()

class ExecutionListFrame:
        source: Union[Ability, Effect]

        def __init__(self, source: Union[Ability, Effect]):
            
            self.source = source

        @property
        def image(self) -> Image:
            if type(self.source) == Ability:
                return self.source.image
            elif type(self.source) == Effect:
                return self.source.source.image

        @property
        def name(self) -> str:
            if type(self.source) == Ability:
                return self.source.name + ": Ability"
            elif type(self.source) == Effect:
                return self.source.source.name + ": Effect Activation"

class BattleScene(engine.Scene):
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-branches

    player_display: ActiveTeamDisplay
    enemy_display: EnemyTeamDisplay
    ally_managers: list["CharacterManager"]
    enemy_managers: list["CharacterManager"]
    team_region: engine.Region
    enemy_region: engine.Region
    energy_region: engine.Region
    enemy_regions: list[engine.Region]
    character_regions: list[engine.Region]
    turn_end_region: engine.Region
    turn_expend_region: engine.Region
    hover_effect_region: engine.Region
    ally_energy_pool: dict[Energy, int]
    enemy_energy_pool: dict[Energy, int]
    offered_pool: dict[Energy, int]
    current_button: Optional[sdl2.ext.SoftwareSprite]
    round_any_cost: int
    waiting_for_turn: bool
    window_up: bool
    moving_first: bool
    exchanging_energy: bool
    has_exchanged: bool
    traded_away_energy: int
    traded_for_energy: int
    player: Player
    enemy: Player
    dying_to_doping: bool
    sharingan_reflecting: bool
    sharingan_reflector: Optional["CharacterManager"]
    sharingan_reflected_effects: list[Effect]
    sharingan_reflected_effect_ticking: bool
    target_clicked: bool
    missions_to_check: list[str]
    active_effect_buttons: list
    triggering_stack_print: bool
    stacks_to_print: int
    acting_order: list["CharacterManager"]

    @property
    def pteam(self):
        return self.player_display.team.character_managers

    @property
    def eteam(self):
        return self.enemy_display.team.character_managers

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window_closing = True
        self.window_closing = False
        self.waiting_for_turn = False
        self.first_turn = True
        self.acting_order = list()
        self.target_clicked = False
        self.sharingan_reflecting = False
        self.sharingan_reflector = None
        self.sharingan_reflected_effects = []
        self.sharingan_reflected_effect_ticking = False
        self.triggering_stack_print = False
        self.stacks_to_print = 0
        self.scene_manager = scene_manager
        self.ally_managers = []
        self.enemy_managers = []
        self.missions_to_check = []
        self.round_any_cost = 0
        self.current_button = None
        self.player_display = ActiveTeamDisplay(self)
        self.enemy_display = EnemyTeamDisplay(self)
        self.moving_first = False
        self.font = init_font(FONTSIZE)
        self.cooldown_font = init_font(COOLDOWN_FONTSIZE)
        self.stack_font = init_font(STACK_FONTSIZE)
        self.inner_stack_font = init_font(INNER_STACK_FONTSIZE)
        self.selected_ability = None
        self.acting_character = None
        self.exchanging_energy = False
        self.has_exchanged = False
        self.clicked_surrender = False
        self.traded_away_energy = 5
        self.traded_for_energy = 5
        self.enemy_detail_character = None
        self.enemy_detail_ability = None
        self.active_effect_buttons = list()
        self.ally_energy_pool = {
            Energy.PHYSICAL: 0,
            Energy.SPECIAL: 0,
            Energy.MENTAL: 0,
            Energy.WEAPON: 0,
            Energy.RANDOM: 0
        }
        self.enemy_energy_pool = {
            Energy.PHYSICAL: 0,
            Energy.SPECIAL: 0,
            Energy.MENTAL: 0,
            Energy.WEAPON: 0,
            Energy.RANDOM: 0
        }
        self.offered_pool = {
            Energy.PHYSICAL: 0,
            Energy.SPECIAL: 0,
            Energy.MENTAL: 0,
            Energy.WEAPON: 0,
            Energy.RANDOM: 0
        }
        self.turn_end_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["end"],
                                    width=150,
                                    height=50),
            free=True)
        self.turn_end_button.click += self.turn_end_button_click
        self.surrender_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["quit"],
                                    width=150,
                                    height=50))
        self.surrender_button.click += self.click_surrender_button
        self.player_panel = self.sprite_factory.from_color(WHITE, (200, 100))
        self.player_panel_border = self.sprite_factory.from_color(
            BLACK, (204, 104))
        self.enemy_panel = self.sprite_factory.from_color(WHITE, (200, 100))
        self.enemy_panel_border = self.sprite_factory.from_color(
            BLACK, (204, 104))
        self.waiting_label = self.create_text_display(self.font,
                                                      "Waiting for opponent",
                                                      WHITE, BLACK, 4, 4, 160)
        self.turn_label = self.create_text_display(self.font,
                                                   "It's your turn!", WHITE,
                                                   BLACK, 22, 4, 150)
        self.energy_region = self.region.subregion(x=206,
                                                   y=5,
                                                   width=150,
                                                   height=53)
        self.turn_end_region = self.region.subregion(x=375,
                                                     y=5,
                                                     width=150,
                                                     height=200)
        self.turn_expend_region = self.region.subregion(x=335,
                                                        y=5,
                                                        width=220,
                                                        height=140)
        self.hover_effect_region = self.region.subregion(0, 0, 0, 0)
        self.player_region = self.region.subregion(2, 2, 200, 100)
        self.enemy_region = self.region.subregion(698, 2, 200, 100)
        self.game_end_region = self.region.subregion(60, 207, 781, 484)
        self.surrender_button_region = self.region.subregion(725, 925, 0, 0)
        self.enemy_info_region = self.region.subregion(5, 860, 670, 135)

    #region On-Click event handlers

    def enemy_info_profile_click(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.enemy_detail_ability = None
        self.draw_enemy_info_region()

    def enemy_info_ability_click(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.enemy_detail_ability = button.ability
        self.draw_enemy_info_region()

    def click_surrender_button(self, button, sender):
        if not self.clicked_surrender and (
            (not self.window_up) or
            (self.window_up and self.exchanging_energy)):
            play_sound(self.scene_manager.sounds["click"])
            self.clicked_surrender = True
            self.scene_manager.connection.send_surrender(self.get_enemy_mission_progress_packages())
            self.lose_game()

    def ingest_mission_packages(self, packages):
        
        for i, package in enumerate(packages):
                self.player_display.team.character_managers[i].source.mission1progress = package[0]
                self.player_display.team.character_managers[i].source.mission2progress = package[1]
                self.player_display.team.character_managers[i].source.mission3progress = package[2]
                self.player_display.team.character_managers[i].source.mission4progress = package[3]
                self.player_display.team.character_managers[i].source.mission5progress = package[4]
                

    def get_enemy_mission_progress_packages(self) -> list[list[int]]:
        output = []
        for manager in self.enemy_display.team.character_managers:
            mission_progress_package = [manager.source.mission1progress,
                                        manager.source.mission2progress,
                                        manager.source.mission3progress,
                                        manager.source.mission4progress,
                                        manager.source.mission5progress]
            output.append(mission_progress_package)
        return output
            

    def confirm_button_click(self, _button, _sender):
        self.execution_loop()
        for attr, _ in self.offered_pool.items():
            self.offered_pool[attr] = 0
        self.turn_expend_region.clear()
        self.draw_turn_end_region()
        self.window_closing = True
        play_sound(self.scene_manager.sounds["turnend"])
        self.turn_end()

    def plus_button_click(self, button, _sender):
        attr = button.energy
        play_sound(self.scene_manager.sounds["click"])
        if self.player_display.team.energy_pool[
                attr] > 0 and self.round_any_cost > 0:
            self.player_display.team.energy_pool[attr] -= 1
            self.offered_pool[attr] += 1
            self.round_any_cost -= 1
        self.draw_any_cost_expenditure_window()

    def any_expenditure_cancel_click(self, _button, _sender):
        for attr, energy in self.offered_pool.items():
            if energy > 0 and attr != Energy.RANDOM:
                self.round_any_cost += energy
                self.player_display.team.energy_pool[attr] += energy
                self.offered_pool[attr] = 0
        self.turn_expend_region.clear()
        self.window_closing = True
        play_sound(self.scene_manager.sounds["undo"])
        self.draw_turn_end_region()

    def minus_button_click(self, button, _sender):
        attr = button.energy
        play_sound(self.scene_manager.sounds["click"])
        if self.offered_pool[attr] > 0:
            self.player_display.team.energy_pool[attr] += 1
            self.offered_pool[attr] -= 1
            self.round_any_cost += 1
        self.draw_any_cost_expenditure_window()

    def turn_end_button_click(self, _button, _sender):
        if not self.waiting_for_turn and not self.window_up:
            self.reset_targeting()
            self.return_targeting_to_default()
            self.full_update()

            if self.round_any_cost == 0:
                play_sound(self.scene_manager.sounds["turnend"])
                self.execution_loop()
                self.turn_end()
            else:
                self.window_up = True
                self.turn_end_region.clear()
                self.draw_any_cost_expenditure_window()

    def exchange_accept_click(self, button, sender):
        self.has_exchanged = True
        play_sound(self.scene_manager.sounds["click"])
        self.player_display.team.energy_pool[Energy(
            self.traded_away_energy)] -= 2
        self.player_display.team.energy_pool[Energy(
            self.traded_for_energy)] += 1
        self.player_display.team.energy_pool[4] -= 1
        self.window_closing = True
        self.exchanging_energy = not self.exchanging_energy
        self.traded_away_energy = 5
        self.traded_for_energy = 5
        self.window_up = False
        self.full_update()

    def exchange_cancel_click(self, button, sender):
        self.window_closing = True
        self.window_up = False
        play_sound(self.scene_manager.sounds["undo"])
        self.exchanging_energy = not self.exchanging_energy
        self.traded_away_energy = 5
        self.traded_for_energy = 5
        self.full_update()

    def received_click(self, button, sender):
        play_sound(self.scene_manager.sounds["select"])
        self.traded_for_energy = button.energy_type
        self.update_energy_region()

    def offered_click(self, button, sender):
        play_sound(self.scene_manager.sounds["select"])
        self.traded_away_energy = button.energy_type
        self.update_energy_region()

    def exchange_button_click(self, button, sender):
        if not self.waiting_for_turn and not self.window_up:
            play_sound(self.scene_manager.sounds["click"])
            self.exchanging_energy = not self.exchanging_energy
            self.update_energy_region()

    def show_hover_text(self):
        self.hover_effect_region.clear()
        if self.current_button is not None:
            
            max_line_width = 270
            base_height = 50
            additional_height = 0
            for effect in self.current_button.effects:
                additional_height += len(textwrap.wrap(effect.get_desc(), 35))
            hover_panel_sprite = self.sprite_factory.from_color(
                WHITE,
                size=(max_line_width, base_height + (additional_height * 18) +
                      (len(self.current_button.effects) * 20)))
            mouse_x, mouse_y = engine.get_mouse_position()
            self.hover_effect_region.x = mouse_x - hover_panel_sprite.size[
                0] if self.current_button.is_enemy else mouse_x
            if self.current_button.y > 600:
                self.hover_effect_region.y = mouse_y - (
                    base_height + (additional_height * 18) +
                    (len(self.current_button.effects) * 20))
            else:
                self.hover_effect_region.y = mouse_y
            self.add_bordered_sprite(self.hover_effect_region,
                                           hover_panel_sprite, BLACK, 0, 0)
            effect_lines = self.get_effect_lines(
                self.current_button.effects)
            self.hover_effect_region.add_sprite(effect_lines[0], 5, 5)
            effect_lines.remove(effect_lines[0])
            effect_y = 26
            is_duration = False

            for effect in effect_lines:
                is_duration = not is_duration
                if is_duration:
                    effect_x = 265 - effect.size[0]
                else:
                    effect_x = 0
                self.hover_effect_region.add_sprite(
                    effect, effect_x, effect_y)
                effect_y += effect.size[1] - 5

    def get_effect_lines(
            self, effect_list: list[Effect]) -> list[sdl2.ext.SoftwareSprite]:
        output: list[sdl2.ext.SoftwareSprite] = []

        output.append(
            self.create_text_display(self.font,
                                           effect_list[0].name, BLUE, WHITE, 0,
                                           0, 260))

        for i, effect in enumerate(effect_list):
            output.append(
                self.create_text_display(
                    self.font, self.get_duration_string(effect.duration),
                    RED, WHITE, 0, 0,
                    len(self.get_duration_string(effect.duration) * 8)))
            output.append(
                self.create_text_display(self.font,
                                               effect.get_desc(), BLACK, WHITE,
                                               5, 0, 270))

        return output

    def get_duration_string(self, duration: int) -> str:
        if (duration // 2) > 10000:
            return "Infinite"
        elif (duration // 2) > 0:
            return f"{duration // 2} turns remaining"
        else:
            return "Ends this turn"

    def get_hovered_button(self):
        for button in self.active_effect_buttons:
            if button.state == sdl2.ext.HOVERED:
                self.effect_hovering = True
                self.current_button = button
                return button
        self.effect_hovering = False
        self.current_button = None
        return None



    #endregion

    #region Rendering functions

    def full_update(self):
        self.region.clear()
        self.region.add_sprite(self.background, 0, 0)

        self.active_effect_buttons.clear()

        self.player_display.update_display()
        self.enemy_display.update_display()
        self.update_energy_region()
        self.draw_turn_end_region()
        self.draw_effect_hover()
        self.draw_player_region()
        self.draw_enemy_region()
        self.draw_surrender_region()
        self.draw_enemy_info_region()

    def draw_enemy_info_region(self):
        self.enemy_info_region.clear()
        if self.enemy_detail_character and not self.enemy_detail_ability:
            ability_count = len(
                self.enemy_detail_character.main_abilities) + len(
                    self.enemy_detail_character.alt_abilities)
            width = 10 + 90 + (65 * ability_count)
            enemy_info_panel = self.sprite_factory.from_color(
                WHITE, (width, 135))
            self.add_bordered_sprite(self.enemy_info_region, enemy_info_panel,
                                     BLACK, 0, 0)
        elif self.enemy_detail_character and self.enemy_detail_ability:
            enemy_info_panel = self.sprite_factory.from_color(
                WHITE, (670, 135))
            self.add_bordered_sprite(self.enemy_info_region, enemy_info_panel,
                                     BLACK, 0, 0)

        if self.enemy_detail_character and not self.enemy_detail_ability:
            profile_sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[
                    self.enemy_detail_character.name + "allyprof"],
                                        width=90,
                                        height=90),
                free=True)
            self.add_bordered_sprite(self.enemy_info_region, profile_sprite,
                                     BLACK, 5, 20)
            ability_count = 0
            for ability in self.enemy_detail_character.main_abilities:
                ability_sprite = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[ability.db_name],
                        width=60,
                        height=60),
                    free=True)
                ability_sprite.ability = ability
                ability_sprite.click += self.enemy_info_ability_click
                self.add_bordered_sprite(self.enemy_info_region,
                                         ability_sprite, BLACK,
                                         100 + (ability_count * 65), 35)
                ability_count += 1
            for ability in self.enemy_detail_character.alt_abilities:
                ability_sprite = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[ability.db_name],
                        width=60,
                        height=60),
                    free=True)
                ability_sprite.ability = ability
                ability_sprite.click += self.enemy_info_ability_click
                self.add_bordered_sprite(self.enemy_info_region,
                                         ability_sprite, BLACK,
                                         100 + (ability_count * 65), 35)
                ability_count += 1

        elif self.enemy_detail_character and self.enemy_detail_ability:
            profile_sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[
                    self.enemy_detail_character.name + "allyprof"],
                                        width=90,
                                        height=90),
                free=True)
            profile_sprite.click += self.enemy_info_profile_click
            self.add_bordered_sprite(self.enemy_info_region, profile_sprite,
                                     BLACK, 5, 20)
            ability_sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[
                    self.enemy_detail_ability.db_name],
                                        width=60,
                                        height=60),
                free=True)
            self.add_bordered_sprite(self.enemy_info_region, ability_sprite,
                                     BLACK, 100, 35)
            self.add_ability_details_to_enemy_info(self.enemy_detail_ability)
            ability_description = self.create_text_display(
                self.font, self.enemy_detail_ability.name + ": " +
                self.enemy_detail_ability.desc, BLACK, WHITE, 0, 0, 500)

            self.enemy_info_region.add_sprite(
                ability_description, 165,
                (135 - ability_description.size[1]) // 2)

    def add_ability_details_to_enemy_info(self, ability):
        energy_display_region = self.enemy_info_region.subregion(
            x=105, y=15, width=(4 + 10) * ability.total_cost, height=10)
        cost_to_display: list[Energy] = sorted(ability.cost_iter())
        energy_squares = [
            energy_display_region.subregion(x, y=0, width=10, height=10)
            for x in itertools.islice(range(0, 1000, 10 +
                                            4), ability.total_cost)
        ]
        for cost, energy_square in zip(cost_to_display, energy_squares):
            energy_surface = self.scene_manager.surfaces[cost.name]
            energy_sprite = self.sprite_factory.from_surface(
                self.get_scaled_surface(energy_surface), free=True)
            energy_square.add_sprite(energy_sprite, x=0, y=0)
        cooldown_text_sprite = self.create_text_display(self.font,
                                                        "CD: " +
                                                        str(ability.cooldown),
                                                        BLACK,
                                                        WHITE,
                                                        x=0,
                                                        y=0,
                                                        width=48,
                                                        height=6)
        self.enemy_info_region.add_sprite(cooldown_text_sprite, 105, 105)

    def draw_surrender_region(self):
        self.surrender_button_region.clear()
        self.surrender_button_region.add_sprite(self.surrender_button, 0, 0)

    def draw_player_region(self):
        self.player_region.clear()
        if self.player:
            self.add_sprite_with_border(self.player_region, self.player_panel,
                                        self.player_panel_border, 0, 0)
            player_ava = self.sprite_factory.from_surface(
                self.get_scaled_surface(self.player.avatar))
            self.add_bordered_sprite(self.player_region, player_ava, BLACK, 0,
                                     0)
            username_label = self.create_text_display(self.font,
                                                      self.player.name, BLACK,
                                                      WHITE, 0, 0, 90)
            win_label = self.create_text_display(self.font,
                                                 f"Wins: {self.player.wins}",
                                                 BLACK, WHITE, 0, 0, 90)
            loss_label = self.create_text_display(
                self.font, f"Losses: {self.player.losses}", BLACK, WHITE, 0, 0,
                90)

            self.player_region.add_sprite(username_label, x=104, y=5)
            self.player_region.add_sprite(win_label, x=104, y=30)
            self.player_region.add_sprite(loss_label, x=104, y=55)

    def draw_enemy_region(self):
        self.enemy_region.clear()
        if self.enemy:
            self.add_sprite_with_border(self.enemy_region, self.enemy_panel,
                                        self.enemy_panel_border, 0, 0)
            enemy_ava = self.sprite_factory.from_surface(
                self.get_scaled_surface(self.enemy.avatar))
            self.add_bordered_sprite(self.enemy_region, enemy_ava, BLACK, 100,
                                     0)

            username_label = self.create_text_display(self.font,
                                                      self.enemy.name, BLACK,
                                                      WHITE, 0, 0, 90)
            win_label = self.create_text_display(self.font,
                                                 f"Wins: {self.enemy.wins}",
                                                 BLACK, WHITE, 0, 0, 90)
            loss_label = self.create_text_display(
                self.font, f"Losses: {self.enemy.losses}", BLACK, WHITE, 0, 0,
                90)

            self.enemy_region.add_sprite(username_label, x=4, y=5)
            self.enemy_region.add_sprite(win_label, x=4, y=30)
            self.enemy_region.add_sprite(loss_label, x=4, y=55)

    def draw_turn_end_region(self):
        self.turn_end_region.clear()
        self.turn_end_region.add_sprite(self.turn_end_button, 0, 0)
        if self.waiting_for_turn:
            self.add_bordered_sprite(self.turn_end_region, self.waiting_label,
                                     WHITE, -5, 55)
        else:
            self.add_bordered_sprite(self.turn_end_region, self.turn_label,
                                     WHITE, 0, 55)

    def draw_any_cost_expenditure_window(self):
        self.turn_expend_region.clear()
        any_cost_panel = self.sprite_factory.from_color(WHITE, size=(220, 140))
        self.add_bordered_sprite(self.turn_expend_region, any_cost_panel,
                                 BLACK, 0, 0)
        left_buffer = 20
        top_buffer = 40
        vertical_spacing = 25
        cost_display = self.create_text_display(
            self.font,
            f"Assign {self.round_any_cost} colorless energy",
            BLACK,
            WHITE,
            x=0,
            y=0,
            width=210,
            height=10)
        self.turn_expend_region.add_sprite(cost_display, x=5, y=6)

        if self.round_any_cost == 0:
            confirm_button = self.create_text_display(self.font,
                                                      "OK",
                                                      WHITE,
                                                      BLACK,
                                                      x=20,
                                                      y=10,
                                                      width=60,
                                                      height=30)
            confirm_button.click += self.confirm_button_click
            self.turn_expend_region.add_sprite(confirm_button, x=150, y=40)

        cancel_button = self.create_text_display(self.font,
                                                 "Cancel",
                                                 WHITE,
                                                 BLACK,
                                                 x=6,
                                                 y=10,
                                                 width=60,
                                                 height=30)
        cancel_button.click += self.any_expenditure_cancel_click
        self.turn_expend_region.add_sprite(cancel_button, x=150, y=90)

        energy_rows = [
            self.turn_expend_region.subregion(left_buffer,
                                              y,
                                              width=150,
                                              height=20)
            for y in itertools.islice(
                range(top_buffer, 10000, vertical_spacing), 4)
        ]

        for idx, row in enumerate(energy_rows):
            self.draw_energy_row(row, idx)

    def draw_energy_row(self, region: engine.Region, idx: int):

        plus_button_x = 80
        minus_button_x = 50
        current_pool_x = 20
        offered_pool_x = 110

        region.add_sprite_vertical_center(self.sprite_factory.from_surface(
            self.get_scaled_surface(
                self.scene_manager.surfaces[Energy(idx).name])),
                                          x=0)
        plus_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["add"]))
        plus_button.energy = Energy(idx)
        plus_button.click += self.plus_button_click
        minus_button = self.ui_factory.from_surface(
            sdl2.ext.BUTTON,
            self.get_scaled_surface(self.scene_manager.surfaces["remove"]))
        minus_button.energy = Energy(idx)
        minus_button.click += self.minus_button_click

        current_pool = self.create_text_display(
            self.font,
            f"{self.player_display.team.energy_pool[Energy(idx)]}",
            BLACK,
            WHITE,
            x=0,
            y=1,
            width=16,
            height=10)
        offered_pool = self.create_text_display(
            self.font,
            f"{self.offered_pool[Energy(idx)]}",
            BLACK,
            WHITE,
            x=0,
            y=2,
            width=16,
            height=10)
        region.add_sprite_vertical_center(current_pool, current_pool_x)
        region.add_sprite_vertical_center(offered_pool, offered_pool_x)

        region.add_sprite_vertical_center(plus_button, x=plus_button_x)
        region.add_sprite_vertical_center(minus_button, x=minus_button_x)

    def draw_effect_hover(self):
        self.hover_effect_region.clear()
        if self.current_button is not None:
            self.show_hover_text()

    #endregion

    
    
    def get_execution_list(self):
        execution_list = list[ExecutionListFrame]
        continuous_types = [EffectType.CONT_DMG, EffectType.CONT_PIERCE_DMG, EffectType.CONT_AFF_DMG, EffectType.CONT_HEAL, EffectType.CONT_DEST_DEF, EffectType.CONT_UNIQUE]

        for manager in self.pteam:
            if manager.acted:
                execution_list.append(ExecutionListFrame(manager.used_ability))
        
        for manager in self.pteam:
            eff_list = [eff for eff in manager.source.current_effects if eff.eff_type in continuous_types and eff.check_waiting() and self.is_allied_effect(eff)]
            for eff in eff_list:
                execution_list.append(ExecutionListFrame(eff))

        for manager in self.eteam:
            eff_list = [eff for eff in manager.source.current_effects if eff.eff_type in continuous_types and eff.check_waiting() and self.is_allied_effect(eff)]
            for eff in eff_list:
                execution_list.append(ExecutionListFrame(eff))
        


    def execution_loop(self):
        for manager in self.acting_order:
            if manager.acted:
                manager.execute_ability()
        self.acting_order.clear()
        self.resolve_ticking_ability()

    def reset_id(self):
        for i, manager in enumerate(self.player_display.team.character_managers):
            manager.id = i
        for i, manager in enumerate(self.enemy_display.team.character_managers):
            manager.id = i + 3

    def is_allied_effect(self, effect: Effect) -> bool:
        for manager in self.player_display.team.character_managers:
            if effect.user == manager:
                return True
        return False

    def return_character(self, char_name) -> Character:
        return Character(get_character_db()[char_name].name, get_character_db()[char_name].desc)

    def is_allied_character(self, character: "CharacterManager"):
        return character in self.player_display.team.character_managers

    def resolve_ticking_ability(self):
        """Checks all Character Managers for continuous effects.
        
        All continuous effects that belong to the player whose turn
        is currently ending are triggered and resolved."""
        for manager in self.player_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_PIERCE_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_pierce_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    if eff.name == "Doping Rampage":
                        self.dying_to_doping = True
                    eff.user.deal_eff_aff_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_HEAL)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    eff.user.give_eff_healing(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DEST_DEF)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    if manager.has_effect(EffectType.DEST_DEF, eff.name):
                        manager.get_effect(EffectType.DEST_DEF,
                                           eff.name).alter_dest_def(eff.mag)
                    else:
                        manager.add_effect(
                            Effect(
                                eff.source, EffectType.DEST_DEF, eff.user,
                                280000, lambda eff:
                                f"This character has {eff.mag} destructible defense.",
                                eff.mag))
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_UNIQUE)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    manager.check_unique_cont(eff)

        for manager in self.enemy_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_PIERCE_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_pierce_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff) and (
                        eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_aff_damage(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_HEAL)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    eff.user.give_eff_healing(eff.mag, manager, eff)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DEST_DEF)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    if manager.has_effect(EffectType.DEST_DEF, eff.name):
                        manager.get_effect(EffectType.DEST_DEF,
                                           eff.name).alter_dest_def(eff.mag)
                    else:
                        manager.add_effect(
                            Effect(
                                eff.source, EffectType.DEST_DEF, eff.user,
                                280000, lambda eff:
                                f"This character has {eff.mag} destructible defense.",
                                eff.mag))
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_UNIQUE)
            for eff in gen:
                if eff.check_waiting() and self.is_allied_effect(eff):
                    manager.check_unique_cont(eff)
    
    def tick_ability_cooldown(self):
        for manager in self.player_display.team.character_managers:
            for ability in manager.source.main_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)
            for ability in manager.source.alt_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)


    def turn_end(self):
        self.sharingan_reflecting = False
        self.sharingan_reflector = None

        # Kuroko invulnerability check #
        for manager in self.player_display.team.character_managers:
            if manager.source.name == "kuroko" and manager.check_invuln():
                manager.progress_mission(1, 1)
            if manager.source.name == "cmary" and manager.check_invuln() and manager.has_effect(EffectType.ALL_INVULN, "Quickdraw - Sniper"):
                manager.progress_mission(4, 1)

        self.tick_effect_duration()
        self.tick_ability_cooldown()
        self.has_exchanged = False
        self.waiting_for_turn = True
        self.traded_away_energy = 5
        self.traded_for_energy = 5
        self.exchanging_energy = False

        game_lost = True
        for manager in self.player_display.team.character_managers:
            manager.refresh_character()
            manager.received_ability.clear()
            if not manager.source.dead:
                game_lost = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)
        game_won = True
        for manager in self.enemy_display.team.character_managers:
            manager.refresh_character(True)
            manager.received_ability.clear()
            if not manager.source.dead:
                game_won = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)

        #region Yatsufusa Resurrection handling
        for manager in self.enemy_display.team.character_managers:
            if manager.source.dead and manager.has_effect(
                    EffectType.MARK, "Yatsufusa"):
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa")
                manager.source.dead = False
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa").user.progress_mission(1, 1)
                manager.source.hp = 40
                manager.remove_effect(
                    manager.get_effect(EffectType.MARK, "Yatsufusa"))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.UNIQUE, yatsu.user, 280000,
                        lambda eff:
                        "This character has been animated by Kurome."))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.DEF_NEGATE, yatsu.user,
                        280000, lambda eff:
                        "This character cannot reduce damage or become invulnerable."
                    ))
                manager.add_effect(
                    Effect(
                        yatsu.source,
                        EffectType.COST_ADJUST,
                        yatsu.user,
                        280000,
                        lambda eff:
                        "This character's abilities costs have been increased by one random energy.",
                        mag=51))

        #endregion

        self.full_update()
        if game_lost:
            self.lose_game()
        if game_won and not game_lost:
            self.win_game()
        pouch1, pouch2 = self.pickle_match(self.player_display.team,
                                           self.enemy_display.team)
        match = MatchPouch(pouch1, pouch2)
        msg = pickle.dumps(match)
        self.scene_manager.connection.send_match_communication(
            self.get_energy_pool(), self.get_enemy_energy_cont(), msg)

    def get_energy_pool(self) -> list:
        output = []
        for i in range(4):
            output.append(self.player_display.team.energy_pool[i])
        return output

    def get_enemy_energy_cont(self) -> list:
        total_pool = [0, 0, 0, 0, 0]
        for manager in self.enemy_display.team.character_managers:
            pool = manager.check_energy_contribution()
            for i, v in enumerate(pool):
                total_pool[i] += v
        return total_pool

    def pickle_match(self, team1: Team, team2: Team):
        team1_pouch = []
        for manager in team1.character_managers:
            effects_pouch = []
            character_pouch = []
            character_pouch.append(manager.source.hp)
            character_pouch.append(manager.source.energy_contribution)
            character_pouch.append(manager.source.mission1progress)
            character_pouch.append(manager.source.mission1complete)
            character_pouch.append(manager.source.mission2progress)
            character_pouch.append(manager.source.mission2complete)
            character_pouch.append(manager.source.mission3progress)
            character_pouch.append(manager.source.mission3complete)
            character_pouch.append(manager.source.mission4progress)
            character_pouch.append(manager.source.mission4complete)
            character_pouch.append(manager.source.mission5progress)
            character_pouch.append(manager.source.mission5complete)
            character_pouch.append(manager.is_toga)
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
                effect_pouch.append(effect.system)
                effect_pouch.append(effect.waiting)
                effects_pouch.append(effect_pouch)
            character_pouch.append(effects_pouch)
            team1_pouch.append(character_pouch)
        team2_pouch = []
        for manager in team2.character_managers:
            effects_pouch = []
            character_pouch = []
            character_pouch.append(manager.source.hp)
            character_pouch.append(manager.source.energy_contribution)
            character_pouch.append(manager.source.mission1progress)
            character_pouch.append(manager.source.mission1complete)
            character_pouch.append(manager.source.mission2progress)
            character_pouch.append(manager.source.mission2complete)
            character_pouch.append(manager.source.mission3progress)
            character_pouch.append(manager.source.mission3complete)
            character_pouch.append(manager.source.mission4progress)
            character_pouch.append(manager.source.mission4complete)
            character_pouch.append(manager.source.mission5progress)
            character_pouch.append(manager.source.mission5complete)
            character_pouch.append(manager.is_toga)
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
                effect_pouch.append(effect.system)
                effect_pouch.append(effect.waiting)
                effects_pouch.append(effect_pouch)
            character_pouch.append(effects_pouch)
            team2_pouch.append(character_pouch)
        return (team1_pouch, team2_pouch)

    def unpickle_match(self, data: bytes, rejoin=False, my_pickle=False):
        match = pickle.loads(data)
        if not my_pickle:
            team1pouch = match.team2_pouch
            team2pouch = match.team1_pouch
        else:
            team1pouch = match.team1_pouch
            team2pouch = match.team2_pouch
        for i, character_pouch in enumerate(team1pouch):
            self.player_display.team.character_managers[
                i].source.hp = character_pouch[0]
            self.player_display.team.character_managers[
                i].source.energy_contribution = character_pouch[1]
            self.player_display.team.character_managers[
                i].source.mission1progress=character_pouch[2]
            self.player_display.team.character_managers[i].source.mission1complete = character_pouch[3]
            self.player_display.team.character_managers[
                i].source.mission2progress=character_pouch[4]
            self.player_display.team.character_managers[i].source.mission1complete = character_pouch[5]
            self.player_display.team.character_managers[
                i].source.mission3progress=character_pouch[6]
            self.player_display.team.character_managers[i].source.mission1complete = character_pouch[7]
            self.player_display.team.character_managers[
                i].source.mission4progress=character_pouch[8]
            self.player_display.team.character_managers[i].source.mission1complete = character_pouch[9]
            self.player_display.team.character_managers[
                i].source.mission5progress=character_pouch[10]
            self.player_display.team.character_managers[i].source.mission1complete = character_pouch[11]
            self.player_display.team.character_managers[i].is_toga = character_pouch[12]
            self.player_display.team.character_managers[
                i].source.current_effects.clear()
            
            for j, effect_pouch in enumerate(character_pouch[13]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[
                        effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[
                        effect_pouch[5]]
                if effect_pouch[7] == True:
                    source = effect_pouch[4]
                else:
                    source = Ability(effect_pouch[4])
                effect = Effect(source,
                                EffectType(effect_pouch[0]), user,
                                effect_pouch[2], effect_pouch[3],
                                effect_pouch[1], effect_pouch[6], effect_pouch[7])
                effect.waiting = effect_pouch[8]
                self.player_display.team.character_managers[
                    i].source.current_effects.append(effect)
            if self.player_display.team.character_managers[
                    i].has_effect(EffectType.UNIQUE, "Quirk - Transform") and self.player_display.team.character_managers[
                    i].source.name != self.player_display.team.character_managers[
                    i].get_effect(EffectType.SYSTEM, "TogaTransformTarget").get_desc():

                    self.player_display.team.character_managers[
                    i].toga_transform(self.player_display.team.character_managers[
                    i].get_effect(EffectType.SYSTEM, "TogaTransformTarget").get_desc())
        for i, character_pouch in enumerate(team2pouch):
            self.enemy_display.team.character_managers[
                i].source.hp = character_pouch[0]
            self.enemy_display.team.character_managers[
                i].source.energy_contribution = character_pouch[1]
            self.enemy_display.team.character_managers[
                i].source.mission1progress=character_pouch[2]
            self.enemy_display.team.character_managers[
                i].source.mission1complete = character_pouch[3]
            self.enemy_display.team.character_managers[
                i].source.mission2progress=character_pouch[4]
            self.enemy_display.team.character_managers[
                i].source.mission2complete = character_pouch[5]
            self.enemy_display.team.character_managers[
                i].source.mission3progress=character_pouch[6]
            self.enemy_display.team.character_managers[
                i].source.mission3complete = character_pouch[7]
            self.enemy_display.team.character_managers[
                i].source.mission4progress=character_pouch[8]
            self.enemy_display.team.character_managers[
                i].source.mission4complete = character_pouch[9]
            self.enemy_display.team.character_managers[
                i].source.mission5progress=character_pouch[10]
            self.enemy_display.team.character_managers[
                i].source.mission5complete = character_pouch[11]
            self.enemy_display.team.character_managers[i].is_toga = character_pouch[12]
            self.enemy_display.team.character_managers[
                i].source.current_effects.clear()
                
            for j, effect_pouch in enumerate(character_pouch[13]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[
                        effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[
                        effect_pouch[5]]
                if effect_pouch[7] == True:
                    source = effect_pouch[4]
                else:
                    source = Ability(effect_pouch[4])
                effect = Effect(source,
                                EffectType(effect_pouch[0]), user,
                                effect_pouch[2], effect_pouch[3],
                                effect_pouch[1], effect_pouch[6], effect_pouch[7])
                effect.waiting = effect_pouch[8]
                self.enemy_display.team.character_managers[
                    i].source.current_effects.append(effect)
            if self.enemy_display.team.character_managers[
                    i].has_effect(EffectType.UNIQUE, "Quirk - Transform") and self.enemy_display.team.character_managers[
                    i].source.name != self.enemy_display.team.character_managers[
                    i].get_effect(EffectType.SYSTEM, "TogaTransformTarget").get_desc():
                    self.enemy_display.team.character_managers[
                    i].toga_transform(self.enemy_display.team.character_managers[
                    i].get_effect(EffectType.SYSTEM, "TogaTransformTarget").get_desc())
            elif self.enemy_display.team.character_managers[
                    i].has_effect(EffectType.SYSTEM, "TogaReturnSignal"):
                    self.enemy_display.team.character_managers[
                    i].toga_transform("toga")
        if not rejoin:
            self.turn_start()

    def tick_effect_duration(self):
        player_team = self.player_display.team.character_managers
        enemy_team = self.enemy_display.team.character_managers

        for manager in player_team:
            for eff in manager.source.current_effects:
                
                
                #region Spend Turn Under Effect Mission Check
                if not eff.eff_type == EffectType.SYSTEM:
                    #region Spend Enemy Turn Under Effect
                    if eff.name == "Uzumaki Barrage" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(2, 1)
                    if eff.name == "Tsukuyomi" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(2, 1)
                    if eff.name == "Alaudi's Handcuffs" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(4, 1)
                    #endregion
                    if eff.name == "Active Combat Mode" and eff.eff_type == EffectType.CONT_DEST_DEF:
                        eff.user.progress_mission(2, 1)
                    if eff.name == "Dive":
                        eff.user.progress_mission(4, 1)
                    if eff.name == "Ally Mobilization":
                        eff.user.progress_mission(2, 1)
                    if eff.name == "Loyal Guard" and manager.check_invuln():
                        manager.progress_mission(3, 1)
                    if eff.name == "Fog of London" and eff.eff_type == EffectType.MARK and not eff.user.has_effect(EffectType.SYSTEM, "JackMission5Success"):
                        if not eff.user.has_effect(EffectType.SYSTEM, "JackMission5Tracker"):
                            eff.user.add_effect(Effect("JackMission5Tracker", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", mag=0, system=True))
                        else:
                            eff.user.get_effect(EffectType.SYSTEM, "JackMission5Tracker").alter_mag(1)
                            if eff.user.get_effect(EffectType.SYSTEM, "JackMission5Tracker").mag >= 10:
                                eff.user.add_effect(Effect("JackMission5Success", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", system=True))
                                eff.user.remove_effect(EffectType.SYSTEM, "JackMission5Tracker")
                    if eff.name == "Shadow Clones" and eff.eff_type == EffectType.ALL_DR:
                        eff.user.progress_mission(1, 30)
                    if eff.name == "Asari Ugetsu" and eff.eff_type == EffectType.ALL_DR:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Flying Raijin" and eff.eff_type == EffectType.ALL_INVULN:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Kamui" and eff.eff_type == EffectType.IGNORE:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Ice, Make Unlimited":
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Summon Gyudon" and eff.eff_type == EffectType.MARK:
                        eff.user.progress_mission(5, 1)
                    
                #endregion
                if eff.eff_type == EffectType.CONSECUTIVE_TRACKER:
                        if not manager.has_effect(EffectType.CONSECUTIVE_BUFFER, eff.name):
                            eff.removing = True
                eff.tick_duration()


                if eff.duration == 0:
                    
                    if eff.name == "Lightning Palm" or eff.name == "Narukami" or eff.name == "Whirlwind Rush":
                        if not eff.user.has_effect(EffectType.SYSTEM, "KilluaMission5Tracker"):
                            eff.user.add_effect(Effect("KilluaMission5Failure", EffectType.SYSTEM, eff.user, 280000, lambda eff: "", system=True))

                    if eff.name == "Quirk - Transform":
                        for effect in manager.source.current_effects:
                            if effect.user == manager:
                                manager.remove_effect(effect)
                        manager.toga_transform("toga")
                        manager.add_effect(Effect("TogaReturnSignal", EffectType.SYSTEM, manager, 280000, lambda eff: "", system = True))

                    if eff.name == "Bunny Assault" and eff.eff_type == EffectType.CONT_USE:
                        if manager.has_effect(EffectType.DEST_DEF,
                                              "Perfect Paper - Rampage Suit"):
                            manager.get_effect(
                                EffectType.DEST_DEF,
                                "Perfect Paper - Rampage Suit").alter_dest_def(
                                    20)
                            manager.progress_mission(3, 20)
                    if eff.name == "Thunder Palace":
                        for enemy in self.enemy_display.team.character_managers:
                            if enemy.final_can_effect(
                                    manager.check_bypass_effects()):
                                eff.user.deal_eff_damage(40, enemy, eff)
                    if eff.name == "Lightning Dragon's Roar":
                        manager.add_effect(
                            Effect(Ability("laxus2"),
                                   EffectType.ALL_DR,
                                   eff.user,
                                   2,
                                   lambda eff:
                                   "This character will take 10 more damage.",
                                   mag=-10))
                    if eff.name == "Mahapadma" and eff.eff_type == EffectType.MARK:
                        manager.add_effect(
                            Effect(Ability("esdeathalt1"), EffectType.ALL_STUN,
                                   manager, 5,
                                   lambda eff: "Esdeath is stunned."))
                    if eff.name == "Quickdraw - Rifle" and eff.eff_type == EffectType.CONT_USE:
                        manager.full_remove_effect("Quickdraw - Rifle",
                                                   manager)
                        manager.add_effect(
                            Effect(
                                Ability("cmaryalt2"),
                                EffectType.ABILITY_SWAP,
                                manager,
                                280000,
                                lambda eff:
                                "Quickdraw - Rifle has been replaced by Quickdraw - Sniper",
                                mag=12))
                    if eff.name == "Illusory Breakdown" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Illusory Breakdown"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Illusory Breakdown").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(25, emanager, eff)
                                    emanager.add_effect(
                                        Effect(
                                            Ability("chrome2"),
                                            EffectType.ALL_STUN, manager, 2,
                                            lambda eff:
                                            "This character is stunned."))
                                    if emanager.meets_stun_check():
                                        manager.check_on_stun(emanager)
                    if eff.name == "Mental Immolation" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Mental Immolation"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Mental Immolation").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(20, emanager, eff)
                                    eff.user.progress_mission(3, 1)
                                    emanager.source.energy_contribution -= 1
                                    manager.check_on_drain(emanager)
                    if eff.name == "Mental Annihilation" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Mental Annihilation"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Mental Annihilation").user == manager:
                                if emanager.final_can_effect("BYPASS"):
                                    manager.deal_eff_damage(35, emanager, eff)
                    if eff.name == "Illusory World Destruction" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.final_can_effect(
                                    manager.check_bypass_effects()):
                                manager.deal_eff_damage(25, emanager, eff)
                                emanager.add_effect(
                                    Effect(
                                        Ability("chromealt2"),
                                        EffectType.ALL_STUN, manager, 2, lambda
                                        eff: "This character is stunned."))
                                if emanager.meets_stun_check():
                                    manager.check_on_stun(emanager)
                    if not manager.has_effect(
                            EffectType.INVIS_END,
                            eff.name) and eff.invisible == True:
                        manager.add_effect(
                            Effect(eff.source, EffectType.INVIS_END, eff.user,
                                   2, lambda eff: f"{eff.name} has ended."))
            new_list = [
                eff for eff in manager.source.current_effects
                if eff.duration > 0 and not eff.removing
            ]
            
            manager.source.current_effects = new_list

        for manager in enemy_team:
            for eff in manager.source.current_effects:
                eff.tick_duration()

                if eff.name == "Consecutive Normal Punches":
                    if manager.has_effect(EffectType.SYSTEM, "SaitamaMission2Tracker") and not eff.user.source.mission2complete:
                        manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").alter_mag(1)
                        if manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").mag >= 7:
                            eff.user.source.mission2complete = True
                            eff.user.progress_mission(2, 1)
                        else:
                            manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").duration += 2
                if eff.duration == 0:
                    if eff.invisible and not manager.has_effect(
                            EffectType.INVIS_END, eff.name):
                        manager.add_effect(
                            Effect(eff.source, EffectType.INVIS_END, eff.user,
                                   2, lambda eff: f"{eff.name} has ended."))
                    if eff.name == "In The Name Of Ruler!" and eff.eff_type == EffectType.ALL_STUN:
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Hidden Mine" and eff.eff_Type == EffectType.UNIQUE:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Illusory Disorientation":
                        eff.user.progress_mission(5, 1)
            new_list = [
                eff for eff in manager.source.current_effects
                if eff.duration > 0 and not eff.removing
            ]
            manager.source.current_effects = new_list
        new_reflected_list = [eff for eff in self.sharingan_reflected_effects if eff.duration > 0 and not eff.removing]
        self.sharingan_reflected_effects = new_reflected_list

    def test_enemy_tick_effect_duration(self):
        player_team = self.enemy_display.team.character_managers
        enemy_team = self.player_display.team.character_managers

        for manager in player_team:
            for eff in manager.source.current_effects:
                
                
                #region Spend Turn Under Effect Mission Check
                if not eff.eff_type == EffectType.SYSTEM:
                    #region Spend Enemy Turn Under Effect
                    
                    if eff.name == "Uzumaki Barrage" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(2, 1)
                    if eff.name == "Tsukuyomi" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(2, 1)
                    if eff.name == "Alaudi's Handcuffs" and eff.eff_type == EffectType.ALL_STUN:
                        if manager.is_stunned():
                            eff.user.progress_mission(4, 1)
                    #endregion
                    if eff.name == "Active Combat Mode" and eff.eff_type == EffectType.CONT_DEST_DEF:
                        eff.user.progress_mission(2, 1)
                    if eff.name == "Dive":
                        eff.user.progress_mission(4, 1)
                    if eff.name == "Ally Mobilization":
                        eff.user.progress_mission(2, 1)
                    if eff.name == "Loyal Guard" and manager.check_invuln():
                        manager.progress_mission(3, 1)
                    if eff.name == "Fog of London" and eff.eff_type == EffectType.MARK and not eff.user.has_effect(EffectType.SYSTEM, "JackMission5Success"):
                        if not eff.user.has_effect(EffectType.SYSTEM, "JackMission5Tracker"):
                            eff.user.add_effect(Effect("JackMission5Tracker", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", mag=0, system=True))
                        else:
                            eff.user.get_effect(EffectType.SYSTEM, "JackMission5Tracker").alter_mag(1)
                            if eff.user.get_effect(EffectType.SYSTEM, "JackMission5Tracker").mag >= 10:
                                eff.user.add_effect(Effect("JackMission5Success", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", system=True))
                                eff.user.remove_effect(EffectType.SYSTEM, "JackMission5Tracker")
                    if eff.name == "Shadow Clones" and eff.eff_type == EffectType.ALL_DR:
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Asari Ugetsu" and eff.eff_type == EffectType.ALL_DR:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Flying Raijin" and eff.eff_type == EffectType.ALL_INVULN:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Kamui" and eff.eff_type == EffectType.IGNORE:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Ice, Make Unlimited":
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Summon Gyudon" and eff.eff_type == EffectType.MARK:
                        eff.user.progress_mission(5, 1)
                    
                #endregion
                if eff.eff_type == EffectType.CONSECUTIVE_TRACKER:
                        if not manager.has_effect(EffectType.CONSECUTIVE_BUFFER, eff.name):
                            eff.removing = True

                eff.tick_duration()

                if eff.duration == 0:
                    
                    if eff.name == "Lightning Palm" or eff.name == "Narukami" or eff.name == "Whirlwind Rush":
                        if not eff.user.has_effect(EffectType.SYSTEM, "KilluaMission5Tracker"):
                            eff.user.add_effect(Effect("KilluaMission5Failure", EffectType.SYSTEM, eff.user, 280000, lambda eff: "", system=True))

                    if eff.name == "Quirk - Transform":
                        for effect in manager.source.current_effects:
                            if effect.user == manager:
                                manager.remove_effect(effect)
                        manager.toga_transform("toga")
                        manager.add_effect(Effect("TogaReturnSignal", EffectType.SYSTEM, manager, 280000, lambda eff: "", system = True))

                    if eff.name == "Bunny Assault" and eff.eff_type == EffectType.CONT_USE:
                        if manager.has_effect(EffectType.DEST_DEF,
                                              "Perfect Paper - Rampage Suit"):
                            manager.get_effect(
                                EffectType.DEST_DEF,
                                "Perfect Paper - Rampage Suit").alter_dest_def(
                                    20)
                            manager.progress_mission(3, 20)
                    if eff.name == "Thunder Palace":
                        for enemy in self.enemy_display.team.character_managers:
                            if enemy.final_can_effect(
                                    manager.check_bypass_effects()):
                                eff.user.deal_eff_damage(40, enemy, eff)
                    if eff.name == "Lightning Dragon's Roar":
                        manager.add_effect(
                            Effect(Ability("laxus2"),
                                   EffectType.ALL_DR,
                                   eff.user,
                                   2,
                                   lambda eff:
                                   "This character will take 10 more damage.",
                                   mag=-10))
                    if eff.name == "Mahapadma" and eff.eff_type == EffectType.MARK:
                        manager.add_effect(
                            Effect(Ability("esdeathalt1"), EffectType.ALL_STUN,
                                   manager, 5,
                                   lambda eff: "Esdeath is stunned."))
                    if eff.name == "Quickdraw - Rifle" and eff.eff_type == EffectType.CONT_USE:
                        manager.full_remove_effect("Quickdraw - Rifle",
                                                   manager)
                        manager.add_effect(
                            Effect(
                                Ability("cmaryalt2"),
                                EffectType.ABILITY_SWAP,
                                manager,
                                280000,
                                lambda eff:
                                "Quickdraw - Rifle has been replaced by Quickdraw - Sniper",
                                mag=12))
                    if eff.name == "Illusory Breakdown" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Illusory Breakdown"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Illusory Breakdown").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(25, emanager, eff)
                                    emanager.add_effect(
                                        Effect(
                                            Ability("chrome2"),
                                            EffectType.ALL_STUN, manager, 2,
                                            lambda eff:
                                            "This character is stunned."))
                                    if emanager.meets_stun_check():
                                        manager.check_on_stun(emanager)
                    if eff.name == "Mental Immolation" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Mental Immolation"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Mental Immolation").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(20, emanager, eff)
                                    eff.user.progress_mission(3, 1)
                                    emanager.source.energy_contribution -= 1
                                    manager.check_on_drain(emanager)
                    if eff.name == "Mental Annihilation" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.has_effect(
                                    EffectType.MARK, "Mental Annihilation"
                            ) and emanager.get_effect(
                                    EffectType.MARK,
                                    "Mental Annihilation").user == manager:
                                if emanager.final_can_effect("BYPASS"):
                                    manager.deal_eff_damage(35, emanager, eff)
                    if eff.name == "Illusory World Destruction" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.final_can_effect(
                                    manager.check_bypass_effects()):
                                manager.deal_eff_damage(25, emanager, eff)
                                emanager.add_effect(
                                    Effect(
                                        Ability("chromealt2"),
                                        EffectType.ALL_STUN, manager, 2, lambda
                                        eff: "This character is stunned."))
                                if emanager.meets_stun_check(emanager):
                                    manager.check_on_stun(emanager)
                    if not manager.has_effect(
                            EffectType.INVIS_END,
                            eff.name) and eff.invisible == True:
                        manager.add_effect(
                            Effect(eff.source, EffectType.INVIS_END, eff.user,
                                   2, lambda eff: f"{eff.name} has ended."))
            new_list = [
                eff for eff in manager.source.current_effects
                if eff.duration > 0 and not eff.removing
            ]
            
            manager.source.current_effects = new_list

        for manager in enemy_team:
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.name == "Consecutive Normal Punches":
                    if manager.has_effect(EffectType.SYSTEM, "SaitamaMission2Tracker") and not eff.user.source.mission2complete:
                        manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").alter_mag(1)
                        if manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").mag >= 7:
                            eff.user.source.mission2complete = True
                            eff.user.progress_mission(2, 1)
                        else:
                            manager.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").duration += 2
                if eff.duration == 0:
                    if eff.invisible and not manager.has_effect(
                            EffectType.INVIS_END, eff.name):
                        manager.add_effect(
                            Effect(eff.source, EffectType.INVIS_END, eff.user,
                                   2, lambda eff: f"{eff.name} has ended."))
                    if eff.name == "In The Name Of Ruler!" and eff.eff_type == EffectType.ALL_STUN:
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Hidden Mine" and eff.eff_Type == EffectType.UNIQUE:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Illusory Disorientation":
                        eff.user.progress_mission(5, 1)
            new_list = [
                eff for eff in manager.source.current_effects
                if eff.duration > 0 and not eff.removing
            ]
            manager.source.current_effects = new_list
        new_reflected_list = [eff for eff in self.sharingan_reflected_effects if eff.duration > 0 and not eff.removing]
        self.sharingan_reflected_effects = new_reflected_list

    def turn_start(self):
        self.sharingan_reflecting = False
        self.sharingan_reflector = None
        self.waiting_for_turn = False
        self.round_any_cost = 0
        self.acting_character = None
        play_sound(self.scene_manager.sounds["turnstart"])
        game_lost = True
        for manager in self.player_display.team.character_managers:

            if manager.source.name == "nemurin":
                if manager.has_effect(EffectType.CONT_UNIQUE, "Nemurin Nap") and manager.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").mag <= 0:
                    if not (manager.has_effect(EffectType.SYSTEM, "NemurinMission5Tracker") or manager.has_effect(EffectType.SYSTEM, "NemurinMission5Failure")):
                        manager.add_effect(Effect("NemurinMission5Tracker", EffectType.SYSTEM, manager, 280000, lambda eff:"", mag=1, system=True))
                    else:
                        manager.add_effect(Effect("NemurinMission5Failure", EffectType.SYSTEM, manager, 280000, lambda eff:"", system=True))
            manager.source.energy_contribution = 1
            if manager.source.hp <= 0:
                manager.source.dead = True
            manager.refresh_character()
            if not manager.source.dead:
                game_lost = False

        game_won = True
        for manager in self.enemy_display.team.character_managers:
            if manager.source.hp <= 0:
                manager.source.dead = True
            manager.refresh_character(True)
            if not manager.source.dead:
                game_won = False



        #region Yatsufusa resurrection handling
        for manager in self.player_display.team.character_managers:
            if manager.source.dead and manager.has_effect(
                    EffectType.MARK, "Yatsufusa"):
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa")
                manager.source.dead = False
                manager.source.hp = 40
                manager.remove_effect(
                    manager.get_effect(EffectType.MARK, "Yatsufusa"))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.UNIQUE, yatsu.user, 280000,
                        lambda eff:
                        "This character has been animated by Kurome."))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.DEF_NEGATE, yatsu.user,
                        280000, lambda eff:
                        "This character cannot reduce damage or become invulnerable."
                    ))
                manager.add_effect(
                    Effect(
                        yatsu.source,
                        EffectType.COST_ADJUST,
                        yatsu.user,
                        280000,
                        lambda eff:
                        "This character's abilities costs have been increased by one random energy.",
                        mag=51))
        #endregion
        self.full_update()
        if game_lost:
            self.lose_game()
        if game_won and not game_lost:
            self.win_game()

    def lose_game(self):
        self.player.losses += 1

        self.lose_game_mission_check()

        for i in range(3):
            self.player.missions[self.player_display.team.character_managers[i].source.name][0] += self.player_display.team.character_managers[i].source.mission1progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][1] += self.player_display.team.character_managers[i].source.mission2progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][2] += self.player_display.team.character_managers[i].source.mission3progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][3] += self.player_display.team.character_managers[i].source.mission4progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][4] += self.player_display.team.character_managers[i].source.mission5progress
            
        self.scene_manager.connection.send_player_update(self.player)
        self.scene_manager.connection.send_match_statistics([
            manager.source.name
            for manager in self.player_display.team.character_managers
        ], False)
        self.window_up = True
        loss_panel = self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["lost"]))
        self.add_bordered_sprite(self.game_end_region, loss_panel, BLACK, 0, 0)
        return_button = self.create_text_display(self.font,
                                                 "Return To Character Select",
                                                 WHITE, BLACK, 14, 5, 220)
        return_button.click += self.return_to_char_select
        self.add_bordered_sprite(self.game_end_region, return_button, WHITE,
                                 550, 400)

    def return_to_char_select(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.scene_manager.return_to_select(self.player)
        self.window_up = False

    def saber_is_the_strongest_servant(self, saber: "CharacterManager") -> bool:
        saber_damage = 0
        manager_damage = 0
        if saber.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
            saber_damage = saber.get_effect(EffectType.SYSTEM, "SaberDamageTracker").mag
            for manager in self.player_display.team.character_managers:
                if manager != saber:
                    if manager.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                        manager_damage = manager.get_effect(EffectType.SYSTEM, "SaberDamageTracker").mag
                    else:
                        manager_damage = 0
                    if manager_damage > saber_damage:
                        return False
            for manager in self.enemy_display.team.character_managers:
                if manager != saber:
                    if manager.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                        manager_damage = manager.get_effect(EffectType.SYSTEM, "SaberDamageTracker").mag
                    else:
                        manager_damage = 0
                    if manager_damage > saber_damage:
                        return False
            return True

    def win_game_mission_check(self):
        for character in self.player_display.team.character_managers:
            if "itachi" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "ItachiMission4Tracker"):
                    character.progress_mission(4, 1)
            if "aizen" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "AizenMission5Tracker"):
                    character.progress_mission(5, 1)
            if "toga" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "TogaMission3Ready"):
                    character.progress_mission(3, 1)
                if not character.has_effect(EffectType.UNIQUE, "Quirk - Transform") and character.source.name == "toga":
                    character.progress_mission(5, 1)
                if character.has_effect(EffectType.UNIQUE, "Quirk - Transform"):
                    character.progress_mission(4, 1)
            if "mirio" in self.missions_to_check:
                if self.get_character_from_team("mirio", self.player_display.team.character_managers):
                    mission4check = False
                    for character in self.player_display.team.character_managers:
                        if character.source.hp == 100:
                            mission4check = True
                    if mission4check:
                        self.get_character_from_team("mirio", self.player_display.team.character_managers).progress_mission(4, 1)
            if "shigaraki" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "ShigarakiMission3Tracker"):
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker") and character.get_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker").mag >= 3:
                    character.progress_mission(4, 1)
            if "uraraka" in self.missions_to_check:
                if not character.has_effect(EffectType.SYSTEM, "UrarakaMission5Tracker") and character.source.name == "uraraka":
                    character.progress_mission(5, 1)
            if "todoroki" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "TodorokiMission1Tracker") and character.get_effect(EffectType.SYSTEM, "TodorokiMission1Tracker").mag >= 3:
                    character.progress_mission(1, 1)
            if "jiro" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "JiroMission5Tracker"):
                    character.progress_mission(5, 1)
            if "natsu" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "NatsuMission3TrackerSuccess"):
                    character.progress_mission(3, 1)
            if "gray" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "GrayMission3Tracker") and character.get_effect(EffectType.SYSTEM, "GrayMission3Tracker").mag >= 4:
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.SYSTEM, "GrayMission4TrackerSuccess"):
                    character.progress_mission(4, 1)
            if "erza" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "ErzaMission5Tracker"):
                    character.progress_mission(5, 1)
            if "lucy" in self.missions_to_check:
                if self.get_character_from_team("lucy", self.player_display.team.character_managers) and not character.has_effect(EffectType.SYSTEM, "LucyMission5Failure"):
                    character.progress_mission(5, 1)
            if "saber" in self.missions_to_check:
                if self.get_character_from_team("saber", self.player_display.team.character_managers) and self.saber_is_the_strongest_servant(character):
                    character.progress_mission(3, 1)
            if "jack" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "JackMission5Success"):
                    character.progress_mission(5, 1)
            if "gunha" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "GunhaMission3Tracker"):
                    character.progress_mission(3, 1)
            if "misaki" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "MisakiMission4Success"):
                    character.progress_mission(4, 1)
                if character.has_effect(EffectType.SYSTEM, "MisakiMission5Success"):
                    character.progress_mission(5, 1)
            if "frenda" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "FrendaMission2Tracker") and character.get_effect(EffectType.SYSTEM, "FrendaMission2Tracker").mag >= 3:
                    character.progress_mission(2, 1)
                if character.source.name == "frenda":
                    mission_complete = True
                    for ally in self.player_display.team.character_managers:
                        if ally.source.name != "frenda" and not ally.source.dead:
                            mission_complete = False
                        if ally.source.name == "frenda" and not ally.source.hp < 25:
                            mission_complete = False
                    if mission_complete:
                        character.progress_mission(5, 1)
            if "naruha" in self.missions_to_check:
                if not character.has_effect(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"):
                    character.progress_mission(1, 1)
                if character.has_effect(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"):
                    character.progress_mission(2, 1)
            if "frenda" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "FrendaMission4Tracker") and character.get_effect(EffectType.SYSTEM, "FrendaMission4Tracker").mag >= 3:
                    character.progress_mission(4, 1)
            if "lambo" in self.missions_to_check:
                if self.get_character_from_team("lambo", self.player_display.team.character_managers) and not character.has_effect(EffectType.SYSTEM, "LamboMission1Failure"):
                    character.progress_mission(1, 1)
                if self.has_effect(EffectType.PROF_SWAP, "Ten-Year Bazooka"):
                    if self.get_effect(EffectType.PROF_SWAP, "Ten-YearBazooka").mag == 1:
                        character.progress_mission(2, 1)
                    else:
                        character.progress_mission(3, 1)
            if "chrome" in self.missions_to_check:
                if self.get_character_from_team("chrome", self.player_display.team.character_managers):
                    if character.has_effect(EffectType.PROF_SWAP, "You Are Needed"):
                        character.progress_mission(2, 1)
                    else:
                        character.progress_mission(1, 1)
                    if character.has_effect(EffectType.SYSTEM, "ChromeMission5Tracker") and character.get_effect(EffectType.SYSTEM, "ChromeMission5Tracker").mag >= 3:
                        character.progress_mission(5, 1)
            if "tatsumi" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "TatsumiMission5Tracker") and character.get_effect(EffectType.SYSTEM, "TatsumiMission5Tracker").mag >= 3:
                    character.progress_mission(4, 1)
            if "mine" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "MineMission4Tracker") and character.get_effect(EffectType.SYSTEM, "MineMission4Tracker").mag >= 3:
                    character.progress_mission(4, 1)
                if character.has_effect(EffectType.SYSTEM, "SaberDamageTracker") and character.get_effect(EffectType.SYSTEM, "SaberDamageTracker").mag >= 225:
                    character.progress_mission(5, 1)
            if "tsuna" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "TsunaMission4Tracker") and character.get_effect(EffectType.SYSTEM, "TsunaMission4Tracker").mag >= 3:
                    character.progress_mission(4, 1)
            if "akame" in self.missions_to_check:
                if character.has_effect(EffectType.SYSTEM, "AkameMission3Tracker"):
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.SYSTEM, "AkameMission5Tracker") and character.get_effect(EffectType.SYSTEM, "AkameMission5Tracker").mag >= 3:
                    character.progress_mission(5, 1)
            if character.source.name == "leone":
                if character.has_effect(EffectType.SYSTEM, "LeoneMission5Tracker") and character.get_effect(EffectType.SYSTEM, "LeoneMission5Tracker").mag >= 200:
                    character.progress_mission(5, 1)
            if character.source.name == "lubbock":
                if not character.has_effect(EffectType.SYSTEM, "LubbockMission4Failure"):
                    character.progress_mission(4, 1)
                if not character.has_effect(EffectType.SYSTEM, "LubbockMission5Failure"):
                    character.progress_mission(5, 1)
            if character.source.name == "esdeath":
                character.progress_mission(2, 1)
                if not character.has_effect(EffectType.SYSTEM, "EsdeathMission3Failure"):
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.SYSTEM, "EsdeathMission5Tracker"):
                    character.progress_mission(5, 1)
            if character.source.name == "snowwhite":
                if not character.has_effect(EffectType.SYSTEM, "SnowWhiteMission4Failure"):
                    character.progress_mission(4, 1)
            if character.source.name == "ripple":
                if character.has_effect(EffectType.SYSTEM, "RippleMission5Tracker") and character.get_effect(EffectType.SYSTEM, "RippleMission5Tracker").mag >= 3:
                    character.progress_mission(5, 1)
            if character.source.name == "nemurin":
                if not character.has_effect(EffectType.SYSTEM, "NemurinMission5Failure"):
                    character.progress_mission(5, 1)
            if character.source.name == "swimswim":
                if character.last_man_standing():
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.SYSTEM, "SwimSwimMission5Tracker") and character.get_effect(EffectType.SYSTEM, "SwimSwimMission5Tracker").mag >= 5:
                    character.progress_mission(5, 1)
            if character.source.name == "pucelle":
                if character.has_effect(EffectType.SYSTEM, "PucelleMission5Tracker"):
                    character.progress_mission(5, 1)
            if character.source.name == "chachamaru":
                if character.has_effect(EffectType.SYSTEM, "ChachamaruMission4Tracker") and character.get_effect(EffectType.SYSTEM, "ChachamaruMission4Tracker").mag >= 3:
                    character.progress_mission(4, 1)
            if character.source.name == "saitama":
                if character.has_effect(EffectType.SYSTEM, "SaitamaMission4Tracker") and not character.has_effect(EffectType.SYSTEM, "SaitamaMission4Failure"):
                    character.progress_mission(4, 1)
            if character.source.name == "saitama":
                if character.has_effect(EffectType.SYSTEM, "SaitamaMission5Tracker") and character.get_effect(EffectType.SYSTEM, "SaitamaMission5Tracker").mag >= 3:
                    character.progress_mission(5, 1)
            if character.source.name == "touka":
                if not character.has_effect(EffectType.SYSTEM, "ToukaMission5Failure"):
                    character.progress_mission(5, 1)
            if character.source.name == "killua":
                if not character.has_effect(EffectType.SYSTEM, "KilluaMission5Failure"):
                    character.progress_mission(5, 1)
                
                
    def lose_game_mission_check(self):
        for character in self.player_display.team.character_managers:   
            if "saber" in self.missions_to_check:
                if self.get_character_from_team("saber", self.player_display.team.character_managers) and self.saber_is_the_strongest_servant(character):
                    character.progress_mission(4, 1)
            if "mine" in self.missions_to_check:
                if self.get_character_from_team("mine", self.player_display.team.character_managers) and character.has_effect(EffectType.SYSTEM, "SaberDamageTracker") and character.get_effect(EffectType.SYSTEM, "SaberDamageTracker").mag >= 225:
                    character.progress_mission(5, 1)
            if character.source.name == "leone":
                if character.has_effect(EffectType.SYSTEM, "LeoneMission5Tracker") and character.get_effect(EffectType.SYSTEM, "LeoneMission5Tracker").mag >= 200:
                    character.progress_mission(5, 1)

    def get_character_from_team(self, name: str, team: list["CharacterManager"]):
        for character in team:
            if character.source.name == name:
                return character
        return None

    def win_game(self, surrendered=False):
        self.player.wins += 1

        self.win_game_mission_check()

        for i in range(3):
            self.player.missions[self.player_display.team.character_managers[i].source.name][0] += self.player_display.team.character_managers[i].source.mission1progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][1] += self.player_display.team.character_managers[i].source.mission2progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][2] += self.player_display.team.character_managers[i].source.mission3progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][3] += self.player_display.team.character_managers[i].source.mission4progress
            self.player.missions[self.player_display.team.character_managers[i].source.name][4] += self.player_display.team.character_managers[i].source.mission5progress
        self.scene_manager.connection.send_player_update(self.player)
        self.scene_manager.connection.send_match_statistics([
            manager.source.name
            for manager in self.player_display.team.character_managers
        ], True)
        self.window_up = True
        win_panel = self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["won"]))
        self.add_bordered_sprite(self.game_end_region, win_panel, BLACK, 0, 0)
        return_button = self.create_text_display(self.font,
                                                 "Return To Character Select",
                                                 WHITE, BLACK, 14, 5, 220)
        return_button.click += self.return_to_char_select
        self.add_bordered_sprite(self.game_end_region, return_button, WHITE,
                                 20, 25)
        if not surrendered:
            self.scene_manager.connection.send_match_ending()

    def generate_energy(self):
        total_energy = 0
        for manager in self.player_display.team.character_managers:
            pool = manager.check_energy_contribution()
            total_energy += pool[Energy.RANDOM.value]
            for i in range(4):
                self.player_display.team.energy_pool[i] += pool[i]
                self.player_display.team.energy_pool[4] += pool[i]
            manager.source.energy_contribution = 1
        for _ in range(total_energy):
            self.player_display.team.energy_pool[randint(0, 3)] += 1
            self.player_display.team.energy_pool[4] += 1

        self.update_energy_region()

    def update_energy_region(self):
        if self.exchanging_energy:
            self.show_energy_exchange()
        else:
            self.show_energy_display()

    def show_energy_display(self):
        self.energy_region.clear()
        self.add_bordered_sprite(
            self.energy_region,
            self.sprite_factory.from_color(BLACK, self.energy_region.size()),
            WHITE, 0, 0)
        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["PHYSICAL"])),
                                      x=5,
                                      y=8)

        PHYSICAL_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.PHYSICAL]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(PHYSICAL_counter, x=17, y=0)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["SPECIAL"])),
                                      x=60,
                                      y=8)

        SPECIAL_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.SPECIAL]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(SPECIAL_counter, x=72, y=0)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["MENTAL"])),
                                      x=5,
                                      y=32)

        MENTAL_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.MENTAL]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(MENTAL_counter, x=17, y=25)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["WEAPON"])),
                                      x=60,
                                      y=32)

        WEAPON_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.WEAPON]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(WEAPON_counter, x=72, y=25)

        total_counter = self.create_text_display(
            self.font,
            "T x " + f"{self.player_display.team.energy_pool[Energy.RANDOM]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=47,
            height=4)
        self.energy_region.add_sprite(total_counter, x=102, y=12)

        can_exchange = False
        for i in range(4):
            if self.player_display.team.energy_pool[Energy(i)] >= 2:
                can_exchange = True

        if can_exchange and not self.has_exchanged and not self.waiting_for_turn:
            exchange_button = self.create_text_display(self.font,
                                                       "EXCHANGE",
                                                       WHITE,
                                                       BLACK,
                                                       x=10,
                                                       y=6,
                                                       width=92,
                                                       height=20)
            exchange_button.click += self.exchange_button_click
            self.add_bordered_sprite(self.energy_region, exchange_button,
                                     WHITE, 29, 55)

    def show_energy_exchange(self):
        self.window_up = True
        self.energy_region.clear()
        self.add_bordered_sprite(
            self.energy_region,
            self.sprite_factory.from_color(BLACK, (150, 120)), WHITE, 0, 0)
        trade_label = self.create_text_display(self.font,
                                               "Trade 2",
                                               WHITE,
                                               BLACK,
                                               x=0,
                                               y=0,
                                               width=60,
                                               height=10)
        self.energy_region.add_sprite(trade_label, 5, 2)
        receive_label = self.create_text_display(self.font,
                                                 "Receive",
                                                 WHITE,
                                                 BLACK,
                                                 x=0,
                                                 y=0,
                                                 width=57,
                                                 height=10)
        self.energy_region.add_sprite(receive_label, 92, 2)
        rows = 0
        for i in range(4):
            if self.player_display.team.energy_pool[Energy(i)] >= 2:
                if i == self.traded_away_energy:
                    offered_energy_symbol = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces[Energy(i).name]))
                    offered_energy_symbol.energy_type = i
                    offered_energy_symbol.click += self.offered_click
                    self.add_bordered_sprite(self.energy_region,
                                             offered_energy_symbol, AQUA, 26,
                                             25 + (rows * 15))
                else:
                    offered_energy_symbol = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces[Energy(i).name]))
                    offered_energy_symbol.energy_type = i
                    offered_energy_symbol.click += self.offered_click
                    self.energy_region.add_sprite(offered_energy_symbol, 26,
                                                  25 + (rows * 15))

            if i == self.traded_for_energy:
                received_energy_symbol = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[Energy(i).name]))
                received_energy_symbol.energy_type = i
                received_energy_symbol.click += self.received_click
                self.add_bordered_sprite(self.energy_region,
                                         received_energy_symbol, AQUA, 114,
                                         25 + (rows * 15))
            else:
                received_energy_symbol = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[Energy(i).name]))
                received_energy_symbol.energy_type = i
                received_energy_symbol.click += self.received_click
                self.energy_region.add_sprite(received_energy_symbol, 114,
                                              25 + (rows * 15))

            rows += 1

        cancel_button = self.create_text_display(self.font,
                                                 "Cancel",
                                                 WHITE,
                                                 BLACK,
                                                 x=6,
                                                 y=0,
                                                 width=60,
                                                 height=10)
        cancel_button.click += self.exchange_cancel_click
        self.add_bordered_sprite(self.energy_region, cancel_button, RED, 85,
                                 90)

        if self.traded_for_energy != 5 and self.traded_away_energy != 5 and self.traded_for_energy != self.traded_away_energy:
            accept_button = self.create_text_display(self.font, "Accept",
                                                     WHITE, BLACK, 6, 0, 60,
                                                     10)
            accept_button.click += self.exchange_accept_click
            self.add_bordered_sprite(self.energy_region, accept_button, GREEN,
                                     4, 90)

    def handle_unique_startup(self, character: "CharacterManager"):
        if character.source.name == "gokudera":
            character.add_effect(
                Effect(
                    Ability("gokudera1"),
                    EffectType.STACK,
                    character,
                    280000,
                    lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.",
                    mag=1))
        if character.source.name == "aizen":
            character.add_effect(Effect("AizenMission5Tracker", EffectType.SYSTEM, character, 280000, lambda eff: "", mag = 0, system = True))
        if character.source.name == "jiro":
            character.add_effect(Effect("JiroMission5Tracker", EffectType.SYSTEM, character, 2, lambda eff:"", system=True))
        if character.source.name == "toga":
            character.is_toga = True

    def setup_scene(self,
                    ally_team: list[Character],
                    enemy_team: list[Character],
                    player: Player = None,
                    enemy: Player = None,
                    energy=[0, 0, 0, 0]):
        self.window_closing = True
        self.sharingan_reflecting = False
        self.sharingan_reflector = None
        self.clicked_surrender = False
        self.round_any_cost = 0
        self.has_exchanged = False
        self.region.clear()
        self.enemy_detail_ability = None
        self.enemy_detail_character = None
        self.background = self.sprite_factory.from_surface(
            self.get_scaled_surface(
                self.scene_manager.surfaces["in_game_background"]))
        self.region.add_sprite(self.background, 0, 0)
        self.draw_turn_end_region()
        self.enemy = enemy
        self.player = player
        ally_roster: list[CharacterManager] = []
        enemy_roster: list[CharacterManager] = []
        for i, ally in enumerate(ally_team):
            char_manager = CharacterManager(ally, self)
            if not ally.name in self.missions_to_check:
                self.missions_to_check.append(ally.name)
            if player:
                char_manager.profile_sprite = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[char_manager.source.name +
                                                    "allyprof"]),
                    free=True)
                char_manager.profile_border = self.ui_factory.from_color(
                    sdl2.ext.BUTTON, BLACK, (104, 104))
                char_manager.profile_sprite.click += char_manager.detail_click
                char_manager.selected_filter = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces["selected"]),
                    free=True)
                char_manager.selected_filter.click += char_manager.profile_click
                char_manager.main_ability_sprites = [
                    self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(self.scene_manager.surfaces[
                            char_manager.source.main_abilities[j].db_name]))
                    for j in range(4)
                ]
                for j, sprite in enumerate(char_manager.main_ability_sprites):
                    sprite.selected_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["selected"]),
                        free=True)
                    sprite.ability = char_manager.source.main_abilities[j]
                    char_manager.source.main_abilities[j].cooldown_remaining = 0
                    sprite.null_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["locked"]),
                        free=True)
                    sprite.null_pane.ability = char_manager.source.main_abilities[
                        j]
                    sprite.null_pane.in_battle_desc = self.create_text_display(
                        self.font, sprite.null_pane.ability.name + ": " +
                        sprite.null_pane.ability.desc, BLACK, WHITE, 5, 0, 520,
                        110)
                    sprite.null_pane.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))
                    sprite.border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (104, 104))
                    sprite.click += char_manager.set_selected_ability

                char_manager.alt_ability_sprites = [
                    self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(self.scene_manager.surfaces[
                            char_manager.source.alt_abilities[j].db_name]))
                    for j in range(len(char_manager.source.alt_abilities))
                ]
                for j, sprite in enumerate(char_manager.alt_ability_sprites):
                    sprite.selected_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["selected"]),
                        free=True)
                    sprite.ability = char_manager.source.alt_abilities[j]
                    char_manager.source.alt_abilities[j].cooldown_remaining = 0
                    sprite.null_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["locked"]),
                        free=True)
                    sprite.null_pane.ability = char_manager.source.main_abilities[
                        j]
                    sprite.null_pane.in_battle_desc = self.create_text_display(
                        self.font, sprite.null_pane.ability.name + ": " +
                        sprite.null_pane.ability.desc, BLACK, WHITE, 5, 0, 520,
                        110)
                    sprite.null_pane.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))
                    sprite.border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (104, 104))
                    sprite.click += char_manager.set_selected_ability

                char_manager.current_ability_sprites = [
                    ability for ability in char_manager.main_ability_sprites
                ]
                for j, sprite in enumerate(char_manager.current_ability_sprites):
                    sprite.ability = char_manager.source.current_abilities[j]

                char_manager.in_battle_desc = self.create_text_display(
                    self.font, char_manager.source.desc, BLACK, WHITE, 5, 0, 520,
                    110)
                char_manager.text_border = self.ui_factory.from_color(
                    sdl2.ext.BUTTON, BLACK, (524, 129))
                for sprite in char_manager.main_ability_sprites:
                    sprite.in_battle_desc = self.create_text_display(
                        self.font,
                        sprite.ability.name + ": " + sprite.ability.desc, BLACK,
                        WHITE, 5, 0, 520, 110)
                    sprite.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))
                for sprite in char_manager.alt_ability_sprites:
                    sprite.in_battle_desc = self.create_text_display(
                        self.font,
                        sprite.ability.name + ": " + sprite.ability.desc, BLACK,
                        WHITE, 5, 0, 520, 110)
                    sprite.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))

            char_manager.id = i
            self.handle_unique_startup(char_manager)
            ally_roster.append(char_manager)
        for i, enemy in enumerate(enemy_team):
            e_char_manager = CharacterManager(enemy, self)
            if not enemy.name in self.missions_to_check:
                self.missions_to_check.append(enemy.name)
            if enemy:
                e_char_manager.profile_sprite = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[e_char_manager.source.name +
                                                    "enemyprof"]),
                    free=True)
                e_char_manager.profile_border = self.ui_factory.from_color(
                    sdl2.ext.BUTTON, BLACK, (104, 104))
                e_char_manager.profile_sprite.click += e_char_manager.detail_click
                e_char_manager.selected_filter = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces["selected"]),
                    free=True)
                e_char_manager.selected_filter.click += e_char_manager.profile_click
            e_char_manager.id = i + 3
            self.handle_unique_startup(e_char_manager)
            enemy_roster.append(e_char_manager)

        scene_ally_team = Team(ally_roster)
        scene_enemy_team = Team(enemy_roster)

        self.player_display.assign_team(scene_ally_team)
        self.enemy_display.assign_team(scene_enemy_team)

        for i, v in enumerate(energy):
            self.player_display.team.energy_pool[i] += v
            self.player_display.team.energy_pool[4] += v

        if self.moving_first:
            self.first_turn = False

        if player:
            self.update_energy_region()

            for manager in self.player_display.team.character_managers:
                manager.source.current_hp = 100
                manager.update()

            for manager in self.enemy_display.team.character_managers:
                manager.source.current_hp = 100
                manager.update_limited()
            self.draw_player_region()
            self.draw_enemy_region()
            self.draw_surrender_region()

    def apply_targeting(self, primary_target: "CharacterManager"):
        if self.selected_ability.target_type == Target.SINGLE:
            self.acting_character.add_current_target(primary_target)
            primary_target.add_received_ability(self.selected_ability)
        elif self.selected_ability.target_type == Target.MULTI_ALLY:
            self.selected_ability.primary_target = primary_target
            for manager in self.player_display.team.character_managers:
                if manager.targeted:
                    self.acting_character.add_current_target(manager)
                    manager.add_received_ability(self.selected_ability)
        elif self.selected_ability.target_type == Target.MULTI_ENEMY:
            self.selected_ability.primary_target = primary_target
            for manager in self.enemy_display.team.character_managers:
                if manager.targeted:
                    self.acting_character.add_current_target(manager)
                    manager.add_received_ability(self.selected_ability)
        elif self.selected_ability.target_type == Target.ALL_TARGET:
            self.selected_ability.primary_target = primary_target
            for manager in self.enemy_display.team.character_managers:
                if manager.targeted:
                    self.acting_character.add_current_target(manager)
                    manager.add_received_ability(self.selected_ability)
            for manager in self.player_display.team.character_managers:
                if manager.targeted:
                    self.acting_character.add_current_target(manager)
                    manager.add_received_ability(self.selected_ability)
        elif self.selected_ability.target_type == Target.MULTI_EITHER:
            self.selected_ability.primary_target = primary_target
            if primary_target in self.player_display.team.character_managers:
                for manager in self.player_display.team.character_managers:
                    if manager.targeted:
                        self.acting_character.add_current_target(manager)
                        manager.add_received_ability(self.selected_ability)
            elif primary_target in self.enemy_display.team.character_managers:
                for manager in self.enemy_display.team.character_managers:
                    if manager.targeted:
                        self.acting_character.add_current_target(manager)
                        manager.add_received_ability(self.selected_ability)
        self.reset_targeting()
        self.acting_character.primary_target = primary_target
        self.selected_ability.user = self.acting_character
        self.acting_character.used_ability = self.selected_ability
        self.acting_order.append(self.acting_character)
        self.selected_ability = None
        self.acting_character.acted = True

    def expend_energy(self, ability: Ability):
        for idx, cost in enumerate(ability.all_costs):
            if cost > 0:
                self.player_display.team.energy_pool[Energy(idx)] -= cost
                if idx != Energy.RANDOM.value:
                    self.player_display.team.energy_pool[Energy.RANDOM] -= cost
                else:
                    self.round_any_cost += cost

    def get_ally_characters(self) -> list[character.Character]:
        output = []
        for manager in self.player_display.team.character_managers:
            output.append(manager.source)
        return output

    def get_enemy_characters(self) -> list[character.Character]:
        output = []
        for manager in self.enemy_display.team.character_managers:
            output.append(manager.source)
        return output

    def return_targeting_to_default(self):
        self.selected_ability = None

    def reset_targeting(self):
        for manager in self.player_display.team.character_managers:
            manager.set_untargeted()

        for manager in self.enemy_display.team.character_managers:
            manager.set_untargeted()

    def refund_energy_costs(self, ability: Ability):
        for idx, cost in enumerate(ability.all_costs):
            if cost > 0:
                self.player_display.team.energy_pool[Energy(idx)] += cost
                if idx != Energy.RANDOM.value:
                    self.player_display.team.energy_pool[Energy.RANDOM] += cost
                else:
                    self.round_any_cost -= cost

    def remove_targets(self, ability: Ability):
        for manager in self.player_display.team.character_managers:
            if ability == manager.used_ability:
                manager.current_targets.clear()
            if manager.received_ability.count(ability):
                manager.received_ability.remove(ability)
        for manager in self.enemy_display.team.character_managers:
            if manager.received_ability.count(ability):
                manager.received_ability.remove(ability)
        if ability.user is not None:
            ability.user.acted = False
            ability.user.used_ability = None
            self.acting_order = [char for char in self.acting_order if char.id != targeter.id]
        self.refund_energy_costs(ability)
        self.full_update()

        

class CharacterManager():
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-branches
    # pylint: disable=no-self-use
    character_region: engine.Region
    source: character.Character
    text_region: engine.Region
    scene: BattleScene
    current_targets: list["CharacterManager"]
    primary_target: "CharacterManager"
    targeted: bool
    targeting: bool
    acted: bool
    received_ability: list[Ability]
    used_ability: Optional[Ability]
    targeting_region: engine.Region
    hp_bar_region: engine.Region
    effect_region: engine.Region
    hover_effect_region: engine.Region
    is_toga: bool
    id: int

    def __init__(self, source: character.Character, scene: BattleScene):
        self.source = source
        self.scene = scene
        self.selected_ability = None
        self.selected_button = None
        self.used_ability = None
        self.targeted = False
        self.acted = False
        self.is_toga = False
        self.received_ability = []
        self.current_targets = []

    @property
    def player_team(self):
        return self.scene.player_display.team.character_managers
    
    @property
    def enemy_team(self):
        return self.scene.enemy_display.team.character_managers

    def get_ability_by_name(self, name: str) -> Optional[Ability]:
        for ability in self.source.current_abilities:
            if ability.name == name:
                return ability
        return None

    def update_text(self):

        self.text_region.clear()
        if self.selected_ability is not None and self.selected_button is not None:
            self.scene.add_sprite_with_border(
                self.text_region, self.selected_button.in_battle_desc,
                self.selected_button.text_border, 0, 0)
            self.text_region.add_sprite(self.selected_button.in_battle_desc, 0,
                                        0)
            energy_display_region = self.text_region.subregion(
                x=10,
                y=self.text_region.from_bottom(2),
                width=(4 + 10) * self.selected_ability.total_cost,
                height=10)
            cost_to_display: list[Energy] = sorted(
                self.selected_ability.cost_iter())
            energy_squares = [
                energy_display_region.subregion(x, y=0, width=10, height=10)
                for x in itertools.islice(range(0, 1000, 10 + 4),
                                          self.selected_ability.total_cost)
            ]
            for cost, energy_square in zip(cost_to_display, energy_squares):
                energy_surface = self.scene.scene_manager.surfaces[cost.name]
                energy_sprite = self.scene.sprite_factory.from_surface(
                    self.scene.get_scaled_surface(energy_surface), free=True)
                energy_square.add_sprite(energy_sprite, x=0, y=0)
            cooldown_text_sprite = self.scene.create_text_display(
                self.scene.font,
                "CD: " + str(self.selected_ability.cooldown),
                BLACK,
                WHITE,
                x=0,
                y=0,
                width=48,
                height=6)
            self.text_region.add_sprite(cooldown_text_sprite,
                                        x=self.text_region.from_right(53),
                                        y=self.text_region.from_bottom(8))
        else:
            self.scene.add_sprite_with_border(self.text_region,
                                              self.in_battle_desc,
                                              self.text_border, 0, 0)

    def adjust_targeting_types(self):
        for i, abi in enumerate(self.source.current_abilities):
            abi.target_type = Target(abi._base_target_type.value)
            gen = (eff for eff in self.source.current_effects
                   if eff.eff_type == EffectType.TARGET_SWAP)
            for eff in gen:
                ability_target = eff.mag // 10
                target_type = eff.mag - (ability_target * 10)
                if ability_target - 1 == i:
                    abi.target_type = Target(target_type)
            if abi.name == "Hyper Eccentric Ultra Great Giga Extreme Hyper Again Awesome Punch" and self.has_effect(
                    EffectType.STACK, "Guts") and self.get_effect(
                        EffectType.STACK, "Guts").mag >= 3:
                abi.target_type = Target.MULTI_ENEMY
            if abi.name == "I Reject!" and one(self) and two(self) and three(
                    self):
                abi.target_type = Target.ALL_TARGET
            if abi.name == "I Reject!" and two(self) and three(self):
                abi.target_type = Target.MULTI_ALLY

    def adjust_ability_costs(self):
        for i, ability in enumerate(self.source.current_abilities):
            ability.reset_costs()
            if self.has_effect(EffectType.STACK, "Quirk - Half-Cold"):
                ability.modify_ability_cost(
                    Energy(4),
                    self.get_effect(EffectType.STACK, "Quirk - Half-Cold").mag)
            if ability.name == "Knight's Sword" and self.has_effect(
                    EffectType.STACK, "Magic Sword"):
                ability.modify_ability_cost(
                    Energy(4),
                    self.get_effect(EffectType.STACK, "Magic Sword").mag)
            if ability.name == "Roman Artillery - Pumpkin" and self.source.hp < 30:
                ability.modify_ability_cost(Energy(3), -1)
            if ability.name == "Kangaryu" and self.has_effect(
                    EffectType.STACK, "Kangaryu"):
                if not self.has_effect(EffectType.MARK, "Vongola Headgear"):
                    ability.modify_ability_cost(
                        Energy(4),
                        self.get_effect(EffectType.STACK, "Kangaryu").mag)
            if ability.name == "Maximum Cannon" and self.has_effect(
                    EffectType.STACK, "Maximum Cannon"):
                if not self.has_effect(EffectType.MARK, "Vongola Headgear"):
                    ability.modify_ability_cost(
                        Energy(4),
                        self.get_effect(EffectType.STACK,
                                        "Maximum Cannon").mag)
            gen = (eff for eff in self.source.current_effects
                   if eff.eff_type == EffectType.COST_ADJUST)
            for eff in gen:
                negative_cost = False
                if eff.mag < 0:
                    negative_cost = True
                ability_to_modify = math.trunc(eff.mag / 100)
                cost_type = math.trunc(
                    (eff.mag - (ability_to_modify * 100)) / 10)
                magnitude = eff.mag - (ability_to_modify * 100) - (cost_type *
                                                                   10)
                if negative_cost:
                    ability_to_modify = ability_to_modify * -1
                    cost_type = cost_type * -1
                if ability_to_modify - 1 == i or ability_to_modify == 0:
                    ability.modify_ability_cost(Energy(cost_type - 1),
                                                magnitude)

    def check_on_harm(self):
        for character in self.current_targets:
            if character.id > 2:
                
                if character.source.name == "gajeel":
                    if not character.has_effect(EffectType.SYSTEM, "GajeelMission5Tracker"):
                        character.add_effect(Effect("GajeelMission5Tracker", EffectType.SYSTEM, character, 280000, lambda eff:"", mag=1, system=True))
                    else:
                        character.get_effect(EffectType.SYSTEM, "GajeelMission5Tracker").alter_mag(1)
                    if character.get_effect(EffectType.SYSTEM, "GajeelMission5Tracker").mag >= 15 and not character.source.mission5complete:
                        character.progress_mission(5, 1)
                        character.source.mission5complete = True
                if character.has_effect(EffectType.IGNORE, "Serious Series - Serious Punch"):
                    character.progress_mission(3, 1)
                if character.has_effect(EffectType.UNIQUE, "Vector Reflection"):
                    target_holder = character.current_targets
                    character.current_targets.clear()
                    character.current_targets.append(self)
                    character.used_ability = character.source.main_abilities[0]
                    character.free_execute_ability()
                    character.current_targets = target_holder
                if character.has_effect(EffectType.UNIQUE, "Hear Distress"):
                    character.source.energy_contribution += 1
                    character.get_effect(EffectType.UNIQUE, "Hear Distress").user.progress_mission(1, 1)
                if character.has_effect(
                        EffectType.UNIQUE,
                        "Iron Shadow Dragon") and not character.is_ignoring():
                    character.add_effect(
                        Effect(Ability("gajeel3"), EffectType.IGNORE,
                               character, 1, lambda eff: ""))
                if character.has_effect(EffectType.MARK, "Quirk - Permeation"):
                    character.get_effect(EffectType.MARK, "Quirk - Permeation").user.progress_mission(1, 1)

                    self.add_effect(
                        Effect(
                            Ability("mirio2"), EffectType.MARK, character, 2,
                            lambda eff:
                            "This character will take 15 more piercing damage from Phantom Menace, and it will automatically target them."
                        ))
                if character.has_effect(EffectType.MARK, "Protect Ally"):
                    character.get_effect(EffectType.MARK, "Protect Ally").user.progress_mission(2, 1)

                    self.add_effect(
                        Effect(
                            Ability("mirio2"), EffectType.MARK, character, 2,
                            lambda eff:
                            "This character will take 15 more piercing damage from Phantom Menace, and it will automatically target them."
                        ))
                if character.has_effect(EffectType.DEST_DEF,
                                        "Four-God Resisting Shield"):
                    self.receive_eff_damage(
                        15,
                        character.get_effect(EffectType.DEST_DEF,
                                             "Four-God Resisting Shield"))
        if self.has_effect(EffectType.UNIQUE, "Porcospino Nuvola"):
            self.receive_eff_damage(
                10, self.get_effect(EffectType.UNIQUE,
                                         "Porcospino Nuvola"))

    def check_on_help(self):
        for target in self.current_targets:
            if target.source.name == "swimswim":
                if not target.has_effect(EffectType.SYSTEM, "SwimSwimMission5Tracker"):
                    target.add_effect(Effect("SwimSwimMission5Tracker", EffectType.SYSTEM, target, 280000, lambda eff:"", mag=1, system=True))
                else:
                    target.get_effect(EffectType.SYSTEM, "SwimSwimMission5Tracker").alter_mag(1)
            if target.has_effect(EffectType.UNIQUE, "Tsukuyomi"):
                target.full_remove_effect(
                    "Tsukuyomi",
                    target.get_effect(EffectType.UNIQUE, "Tsukuyomi").user)

    def check_on_use(self):
        for target in self.current_targets:

            #region Receive Ability Mission Tracking
            if target.has_effect(EffectType.ALL_DR, "Eight Trigrams - 64 Palms") and self.used_ability.name != "Eight Trigrams - 64 Palms":
                target.get_effect(EffectType.ALL_DR, "Eight Trigrams - 64 Palms").user.progress_mission(4, 1)
            if self.mission_active("lucy", self):
                if self.has_effect(EffectType.MARK, "Gemini"):
                    self.progress_mission(2, 1)
                else:
                    self.add_effect(Effect("LucyMission5Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
            #endregion

            if target.has_effect(EffectType.MARK,
                                 "Shredding Wedding") and not self.has_effect(
                                     EffectType.MARK, "Shredding Wedding"):
                if self.final_can_effect():
                    self.receive_eff_pierce_damage(
                        20,
                        target.get_effect(EffectType.MARK,
                                          "Shredding Wedding").user)
            if self.has_effect(EffectType.MARK,
                               "Shredding Wedding") and not target.has_effect(
                                   EffectType.MARK, "Shredding Wedding"):
                if self.final_can_effect():
                    self.receive_eff_pierce_damage(
                        20,
                        self.get_effect(EffectType.MARK,
                                        "Shredding Wedding").user)
        if self.has_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame"):
            self.get_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame").alter_mag(1)
            self.get_effect(
                EffectType.CONT_UNIQUE, "Utsuhi Ame"
            ).desc = lambda eff: "This character will take 40 damage and Yamamoto will gain 3 stacks of Asari Ugetsu."
        if self.has_effect(EffectType.MARK, "Hidden Mine"):
            if self.final_can_effect():
                self.receive_eff_pierce_damage(
                    20,
                    self.get_effect(EffectType.MARK, "Hidden Mine"))
            self.full_remove_effect(
                "Hidden Mine",
                self.get_effect(EffectType.MARK, "Hidden Mine").user)
        if self.has_effect(EffectType.MARK, "Illusory Disorientation"):
            self.full_remove_effect(
                "Illusory Disorientation",
                self.get_effect(EffectType.MARK,
                                "Illusory Disorientation").user)
        if self.has_effect(EffectType.MARK, "Solid Script - Fire"):
            self.get_effect(EffectType.MARK, "Solid Script - Fire").user.progress_mission(1, 1)
            self.receive_eff_aff_damage(
                10,
                self.get_effect(EffectType.MARK, "Solid Script - Fire"))

    def check_bypass_effects(self) -> str:
        if self.has_effect(EffectType.UNIQUE, "Dive"):
            return "BYPASS"
        if self.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
            return "BYPASS"
        return "NORMAL"

    def receive_stun(self):
        #TODO Stun receipt checks
        pass

    def check_on_stun(self, target: "CharacterManager"):
        #TODO stun checks

        if target.has_effect(EffectType.MARK, "Counter-Balance"):
            self.source.energy_contribution -= 1
            self.add_effect(Effect("JiroMission4Tracker", EffectType.SYSTEM, target.get_effect(EffectType.MARK, "Counter-Balance").user, 2, lambda eff:"", system=True))
            target.get_effect(EffectType.MARK, "Counter-Balance").user.progress_mission(1, 1)

        if target.is_stunned():
            target.cancel_control_effects()

    def cancel_control_effects(self):
        for eff in self.source.current_effects:
            if eff.eff_type == EffectType.CONT_USE and eff.name == "Quickdraw - Rifle":
                self.remove_effect(
                    self.get_effect(EffectType.CONT_USE, "Quickdraw - Rifle"))
                for manager in self.scene.player_display.team.character_managers:
                    manager.remove_effect(
                        manager.get_effect(EffectType.CONT_DMG,
                                           "Quickdraw - Rifle"))
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.remove_effect(
                        manager.get_effect(EffectType.CONT_DMG,
                                           "Quickdraw - Rifle"))
            elif eff.eff_type == EffectType.CONT_USE:
                self.full_remove_effect(eff.name, self)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect(eff.name, self)
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.full_remove_effect(eff.name, self)

    def check_on_drain(self, target: "CharacterManager"):

        if target.has_effect(EffectType.MARK, "Counter-Balance"):
            self.add_effect(
                Effect(
                    Ability("jiro1"), EffectType.ALL_STUN,
                    target.get_effect(EffectType.MARK, "Counter-Balance").user,
                    3, lambda eff: "This character is stunned."))
            self.add_effect(Effect("JiroMission4Tracker", EffectType.SYSTEM, target.get_effect(EffectType.MARK, "Counter-Balance").user, 2, lambda eff:"", system=True))
            target.get_effect(EffectType.MARK, "Counter-Balance").user.progress_mission(1, 1)

    def check_damage_drain(self) -> int:
        gen = [
            eff for eff in self.source.current_effects
            if eff.eff_type == EffectType.ALL_BOOST and eff.mag < 0
        ]

        total_drain = 0
        for eff in gen:
            total_drain += eff.mag

        return total_drain

    def check_unique_cont(self, eff: Effect):
        if eff.name == "Utsuhi Ame":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                self.receive_eff_damage(eff.mag * 20, eff)
                if eff.mag == 1:
                    eff.user.apply_stack_effect(
                        Effect(
                            Ability("yamamoto3"),
                            EffectType.STACK,
                            eff.user,
                            280000,
                            lambda eff:
                            f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.",
                            mag=1), eff.user)
                else:
                    eff.user.progress_mission(1, 1)
                    eff.user.apply_stack_effect(
                        Effect(
                            Ability("yamamoto3"),
                            EffectType.STACK,
                            eff.user,
                            280000,
                            lambda eff:
                            f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.",
                            mag=3), eff.user)
                if eff.user.get_effect(EffectType.STACK, "Asari Ugetsu").mag >= 10:
                    eff.user.progress_mission(3, 1)
        if eff.name == "Vacuum Syringe":
            if self.final_can_effect("BYPASS"):
                self.receive_eff_aff_damage(10, eff.user)
                self.apply_stack_effect(
                    Effect(
                        Ability("toga3"),
                        EffectType.STACK,
                        eff.user,
                        280000,
                        lambda eff:
                        f"Toga has drawn blood from this character {eff.mag} time(s).",
                        mag=1), eff.user)
                eff.user.progress_mission(2, 1)
        if eff.name == "Decaying Touch":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                self.receive_eff_aff_damage((5 * (2**eff.mag)), eff.user)
        if eff.name == "Nemurin Nap":
            eff.alter_mag(1)
            if eff.mag == 2:
                self.add_effect(
                    Effect(Ability("nemu2"),
                           EffectType.COST_ADJUST,
                           eff.user,
                           280000,
                           lambda eff:
                           "Nemurin Beam will cost one less random energy.",
                           mag=-251))
                self.add_effect(
                    Effect(
                        Ability("nemu3"),
                        EffectType.COST_ADJUST,
                        eff.user,
                        280000,
                        lambda eff:
                        "Dream Manipulation will cost one less random energy.",
                        mag=-351))
            if eff.mag == 3:
                self.add_effect(
                    Effect(Ability("nemu2"),
                           EffectType.TARGET_SWAP,
                           eff.user,
                           280000,
                           lambda eff: "Nemurin Beam will target all enemies.",
                           mag=21))
                self.add_effect(
                    Effect(Ability("nemu3"),
                           EffectType.TARGET_SWAP,
                           eff.user,
                           280000,
                           lambda eff:
                           "Dream Manipulation will target all allies.",
                           mag=32))
        if eff.name == "Eight Trigrams - 128 Palms":
            if self.final_can_effect(eff.user.check_bypass_effects()) and (
                    not self.deflecting() or (2 * (2 ** eff.mag) > 15)):
                base_damage = (2 * (2**eff.mag))
                eff.user.deal_eff_damage(base_damage, self, eff)
                
                eff.alter_mag(1)
                if self.has_effect(
                        EffectType.MARK, "Chakra Point Strike"
                ) and base_damage > self.check_for_dmg_reduction():
                    self.source.energy_contribution -= 1
                    eff.user.check_on_drain(self)
                    eff.user.source.mission2progress += 1
        if eff.name == "Relentless Assault":
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                if self.check_for_dmg_reduction() < 15:
                    eff.user.deal_eff_pierce_damage(15, self, eff)
                else:
                    eff.user.deal_eff_damage(15, self, eff)
        if eff.name == "Bridal Chest":
            valid_targets: list["CharacterManager"] = []
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()
                                          ) and not enemy.deflecting():
                    valid_targets.append(enemy)
            if valid_targets:
                damage = eff.mag
                if eff.user.has_effect(EffectType.STACK, "Galvanism"):
                    damage = damage + (eff.user.get_effect(EffectType.STACK, "Galvanism").mag * 10)
                target = randint(0, len(valid_targets) - 1)
                
                self.deal_eff_damage(damage, valid_targets[target], eff)
        if eff.name == "Titania's Rampage":
            valid_targets: list["CharacterManager"] = []
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()
                                          ) and not enemy.deflecting():
                    valid_targets.append(enemy)
            if valid_targets:
                damage = 15 + (eff.mag * 5)
                target = randint(0, len(valid_targets) - 1)
                
                self.deal_eff_pierce_damage(damage, valid_targets[target], eff)
                eff.alter_mag(1)
        if eff.name == "Circle Blade":
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()
                                          ) and not enemy.deflecting():
                    self.deal_eff_damage(15, enemy, eff)
        if eff.name == "Butou Renjin":
            
            eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").duration = 3
            eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").alter_mag(1)
            if eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").mag >= 8:
                eff.user.remove_effect(eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker"))
                eff.user.progress_mission(4, 1)
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                eff.user.deal_eff_damage(15, self, eff)
                self.apply_stack_effect(
                    Effect(
                        Ability("ichimaru3"),
                        EffectType.STACK,
                        eff.user,
                        280000,
                        lambda eff:
                        f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.",
                        mag=1), eff.user)
        if eff.name == "Rubble Barrage":
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                base_damage = 10
                if eff.user.has_effect(EffectType.STACK, "Gather Power"):
                    base_damage += (5 * eff.user.get_effect(
                        EffectType.STACK, "Gather Power").mag)
                eff.user.deal_eff_damage(base_damage, self, eff)
        if eff.name == "Railgun":
            base_damage = 10
            if self.final_can_effect(eff.user.check_bypass_effects()):
                if eff.user.has_effect(EffectType.STACK, "Overcharge"):
                    base_damage += (5 * eff.user.get_effect(EffectType.STACK, "Overcharge").mag)
                eff.user.deal_eff_damage(base_damage, self, eff)
        if eff.name == "Iron Sand":
            base_defense = 10
            if self.helpful_target(eff.user, eff.user.check_bypass_effects()):
                if eff.user.has_effect(EffectType.STACK, "Overcharge"):
                    base_defense += (5 * eff.user.get_effect(EffectType.STACK, "Overcharge").mag)
                self.apply_dest_def_effect(Effect(eff.source, EffectType.DEST_DEF, eff.user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = base_defense))
        if eff.name == "Overcharge":
            self.apply_stack_effect(Effect(eff.source, EffectType.STACK, eff.user, 280000, lambda eff: "", mag = 1), eff.user)
        if eff.name == "Level-6 Shift":
            if not eff.user.is_stunned():
                ability = randint(1, 3)
                print(ability)
                if ability == 1:
                    valid_targets = [manager for manager in self.scene.pteam if manager.helpful_target(eff.user, eff.user.check_bypass_effects())]
                    print(valid_targets)
                    if valid_targets:
                        chosen_target = valid_targets[randint(0, len(valid_targets) - 1)]
                        eff.user.current_targets.append(chosen_target)
                        eff.user.acted = True
                        eff.user.used_ability = eff.user.source.main_abilities[0]
                        eff.user.execute_ability()
                elif ability == 2:
                    valid_targets = [manager for manager in self.scene.eteam if manager.hostile_target(eff.user, "BYPASS")]
                    print(valid_targets)
                    if valid_targets:
                        chosen_target = valid_targets[randint(0, len(valid_targets) - 1)]
                        eff.user.current_targets.append(chosen_target)
                        eff.user.acted = True
                        eff.user.used_ability = eff.user.source.main_abilities[1]
                        eff.user.execute_ability()
                elif ability == 3:
                    chosen_target = eff.user
                    eff.user.current_targets.append(chosen_target)
                    eff.user.acted = True
                    eff.user.used_ability = eff.user.source.main_abilities[2]
                    eff.user.execute_ability()

    def is_controllable(self) -> bool:
        if self.has_effect(EffectType.MARK, "Level-6 Shift"):
            return False
        return True

    def is_counter_immune(self):
        gen = [
            eff for eff in self.source.current_effects
            if eff.eff_type == EffectType.COUNTER_IMMUNE
        ]
        for eff in gen:
            return True
        return False

    def shirafune_check(self, counter: Effect):
        if self.has_effect(EffectType.MARK,
                                           "Third Dance - Shirafune"):
                            counter.user.progress_mission(4, 1)
                            if not self.has_effect(EffectType.SYSTEM, "RukiaMission5Tracker"):
                                self.add_effect(Effect("RukiaMission5Tracker", EffectType.SYSTEM, counter.user, 280000, lambda eff: "", system = True))
                            else:
                                counter.user.progress_mission(5, 1)
                                counter.user.mission5complete = True
                            if counter.user.final_can_effect():
                                counter.user.receive_eff_damage(30, self.get_effect(EffectType.MARK, "Third Dance - Shirafune"))
                                counter.user.add_effect(
                                    Effect(
                                        Ability("rukia3"), EffectType.ALL_STUN,
                                        self.get_effect(EffectType.MARK, "Third Dance - Shirafune").user, 2, lambda eff:
                                        "This character is stunned."))
                                if self.meets_stun_check():
                                    counter.user.check_on_stun(self)
                            self.full_remove_effect("Third Dance - Shirafune",
                                                    self)

    def check_for_cost_increase_missions(self):
        gen = [eff for eff in self.source.current_effects if eff.eff_type == EffectType.COST_ADJUST and eff.mag > 0]
        for eff in gen:
            if eff.name == "Shatter, Kyoka Suigetsu":
                eff.user.progress_mission(2, 1)
            if eff.name == "Quirk - Half-Cold":
                eff.user.progress_mission(3, 1)
            if eff.name == "Illusory Disorientation":
                eff.user.progress_mission(1, 1)
        gen = [eff for eff in self.source.current_effects if eff.eff_type == EffectType.COOLDOWN_MOD]
        for eff in gen:
            if eff.name == "Raiou":
                eff.user.progress_mission(2, 1)

    def check_countered(self, pteam: list["CharacterManager"],
                        eteam: list["CharacterManager"]) -> bool:
        def is_harmful(self: "CharacterManager",
                       eteam: list["CharacterManager"]) -> bool:
            for enemy in eteam:
                if enemy.id > 2:
                    return True
            return False
        if is_harmful(self, eteam):
            if not self.is_counter_immune():
                #self reflect effects:
                gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.REFLECT
                       and not self.scene.is_allied_effect(eff))
                for eff in gen:
                    pass

                #self counter check
                gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.COUNTER
                       and not self.scene.is_allied_effect(eff))
                for eff in gen:
                    if eff.name == "Hear Distress":
                        src = Ability("snowwhite2")
                        self.full_remove_effect("Hear Distress", eff.user)
                        self.add_effect(
                            Effect(
                                src, EffectType.UNIQUE, eff.user, 2,
                                lambda eff:
                                "This character was countered by Hear Distress."
                            ))
                        eff.user.progress_mission(2, 1)
                        self.source.energy_contribution -= 1
                        eff.user.check_on_drain(self)
                        self.shirafune_check(eff)
                        return True
                for eff in gen:
                    if eff.name == "Enkidu, Chains of Heaven":
                        src = Ability("gilgamesh2")
                        self.full_remove_effect("Enkidu, Chains of Heaven", eff.user)
                        self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Enkidu, Chains of Heaven."))
                        self.add_effect(Effect(src, EffectType.ALL_STUN, eff.user, 3, lambda eff: "This character is stunned."))
                        self.add_effect(Effect(src, EffectType.MARK, eff.user, 3, lambda eff: "This character's continuous abilities will not activate."))
                        self.shirafune_check(eff)
                #target counter check
                for target in self.current_targets:

                    gen = (eff for eff in target.source.current_effects
                           if eff.eff_type == EffectType.COUNTER
                           and not self.scene.is_allied_effect(eff))
                    for eff in gen:
                        if eff.name == "Draw Stance":
                            src = Ability("touka1")
                            self.add_effect(
                                Effect(
                                    src, EffectType.UNIQUE, eff.user, 2,
                                    lambda eff:
                                    "This character was countered by Draw Stance."
                                ))
                            eff.user.progress_mission(1, 1)
                            if not eff.user.has_effect(EffectType.SYSTEM, "ToukaMission5Failure"):
                                eff.user.add_effect(Effect("ToukaMission5Failure", EffectType.SYSTEM, eff.user, 280000, lambda eff: "", system=True))
                        
                            if self.final_can_effect(
                            ) and not self.deflecting():
                                self.receive_eff_damage(15, eff)
                            target.full_remove_effect("Draw Stance", eff.user)
                            self.shirafune_check(eff)
                            return True
                        if eff.name == "Zero Point Breakthrough":
                            eff.user.progress_mission(2, 1)
                            if not self.has_effect(EffectType.SYSTEM, "TsunaMission5Tracker"):
                                self.add_effect(Effect("TsunaMission5Tracker", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", system=True))
                            else:
                                eff.user.progress_mission(5, 1)
                                eff.user.source.mission5complete = True
                            src = Ability("tsunayoshi3")
                            target.full_remove_effect(
                                "Zero Point Breakthrough", eff.user)
                            self.add_effect(
                                Effect(
                                    src, EffectType.UNIQUE, eff.user, 2,
                                    lambda eff:
                                    "This character was countered by Zero Point Breakthrough."
                                ))
                            self.add_effect(
                                Effect(
                                    src, EffectType.ALL_STUN, eff.user, 5,
                                    lambda eff: "This character is stunned."))
                            eff.user.add_effect(
                                Effect(src,
                                       EffectType.ALL_BOOST,
                                       eff.user,
                                       4,
                                       lambda eff:
                                       "X-Burner will deal 10 more damage.",
                                       mag=110))
                            self.shirafune_check(eff)
                            return True
                        if eff.name == "One For All - Shoot Style":
                            eff.user.progress_mission(3, 1)
                            src = Ability("midoriya3")
                            target.full_remove_effect(
                                "One For All - Shoot Style", eff.user)
                            self.add_effect(
                                Effect(
                                    src, EffectType.UNIQUE, eff.user, 2,
                                    lambda eff:
                                    "This character was countered by One For All - Shoot Style."
                                ))
                            self.shirafune_check(eff)
                            return True
                        if eff.name == "Minion - Tama":
                            src = Ability("ruler3")
                            target.full_remove_effect("Minion - Tama",
                                                      eff.user)
                            eff.user.full_remove_effect(
                                "Minion - Tama", eff.user)
                            self.add_effect(
                                Effect(
                                    src, EffectType.UNIQUE, eff.user, 2,
                                    lambda eff:
                                    "This character was countered by Minion - Tama."
                                ))
                            eff.user.progress_mission(3, 1)
                            eff.user.source.main_abilities[
                                2].cooldown_remaining = 2
                            if self.final_can_effect():
                                self.receive_eff_pierce_damage(20, eff)
                            self.shirafune_check(eff)
                            return True
                        if eff.name == "Casseur de Logistille":
                            src = Ability("astolfo1")
                            if self.used_ability._base_cost[
                                    Energy.
                                    SPECIAL] > 0 or self.used_ability._base_cost[
                                        Energy.MENTAL] > 0:
                                self.add_effect(
                                    Effect(
                                        src, EffectType.UNIQUE, eff.user, 2,
                                        lambda eff:
                                        "This character was countered by Casseur de Logistille."
                                    ))
                                eff.user.progress_mission(1, 1)
                                target.full_remove_effect(
                                    "Casseur de Logistille", eff.user)
                                if self.final_can_effect():
                                    self.add_effect(
                                        Effect(
                                            src, EffectType.ALL_STUN, eff.user,
                                            3, lambda eff:
                                            "This character is stunned."))
                                    self.add_effect(
                                        Effect(
                                            src, EffectType.ISOLATE, eff.user,
                                            3, lambda eff:
                                            "This character is isolated."))
                                    if self.meets_stun_check():
                                        eff.user.check_on_stun(self)
                                self.shirafune_check(eff)
                                return True

                    gen = (eff for eff in target.source.current_effects
                           if eff.eff_type == EffectType.REFLECT
                           and not self.scene.is_allied_effect(eff))
                    for eff in gen:
                        if eff.name == "Copy Ninja Kakashi":
                            logging.debug("Kakashi is reflecting!")
                            self.scene.sharingan_reflecting = True
                            self.scene.sharingan_reflector = target.get_effect(EffectType.REFLECT, "Copy Ninja Kakashi").user
                            target.full_remove_effect("Copy Ninja Kakashi",
                                                      eff.user)
                            alt_targets = [
                                char for char in self.current_targets
                                if char != target
                            ]
                            self.id = self.id + 3
                            alt_targets.append(self)
                            for target in alt_targets:
                                logging.debug(f"Reflected ability targeting {target.source.name}")
                            self.current_targets = alt_targets
                            self.used_ability.execute(self, pteam, eteam)
                            return True
            else:
                if self.has_effect(EffectType.COUNTER_IMMUNE, "Mental Radar"):
                    self.get_effect(EffectType.COUNTER_IMMUNE, "Mental Radar").user.progress_mission(3, 1)
        return False

    def meets_stun_check(self) -> bool:
        output = False
        if self.is_stunned():
            output = True
        gen = [eff for eff in self.source.current_effects if eff.eff_type == EffectType.SPECIFIC_STUN]
        for eff in gen:
            if self.source.uses_energy(eff.mag - 1):
                output = True
        return output

    def check_on_damage_dealt(self, target: "CharacterManager", damage: int):
        #TODO check user effects

        #TODO check target effects
        if target.has_effect(EffectType.MARK, "Lightning Palm"):
            src = target.get_effect(EffectType.MARK, "Lightning Palm")
            src.user.progress_mission(1, 1)
            src.user.add_effect(Effect("KilluaMission5Tracker", EffectType.MARK, src.user, 2, lambda eff: "", system=True))
            if not self.has_effect(EffectType.STUN_IMMUNE, "Lightning Palm"):
                self.add_effect(
                    Effect(
                        src.source, EffectType.STUN_IMMUNE, src.user, 3, lambda
                        eff: "This character will ignore stun effects."))
        if target.has_effect(EffectType.MARK, "Narukami"):
            src = target.get_effect(EffectType.MARK, "Narukami")
            src.user.progress_mission(2, 1)
            src.user.add_effect(Effect("KilluaMission5Tracker", EffectType.MARK, src.user, 2, lambda eff: "", system=True))
            if not self.has_effect(EffectType.COUNTER_IMMUNE, "Narukami"):
                self.add_effect(
                    Effect(
                        src.source, EffectType.COUNTER_IMMUNE, src.user, 3,
                        lambda eff:
                        "This character will ignore counter effects."))
        if target.has_effect(EffectType.MARK, "Whirlwind Rush"):
            src = target.get_effect(EffectType.MARK, "Whirlwind Rush")
            src.user.progress_mission(3, 1)
            src.user.add_effect(Effect("KilluaMission5Tracker", EffectType.MARK, src.user, 2, lambda eff: "", system=True))
            self.add_effect(
                Effect(src.source, EffectType.ALL_INVULN, src.user, 2,
                       lambda eff: "This character is invulnerable."))

        if target.has_effect(EffectType.ALL_DR, "Arrest Assault"):
            target.get_effect(EffectType.ALL_DR,
                              "Arrest Assault").user.progress_mission(2, 1)
            target.get_effect(EffectType.ALL_DR,
                              "Arrest Assault").user.get_effect(
                                  EffectType.UNIQUE,
                                  "Arrest Assault").alter_mag(1)
        if target.has_effect(EffectType.MARK, "Doll Trap"):
            target_dolls = [
                eff for eff in target.source.current_effects
                if eff.eff_type == EffectType.STACK and eff.name == "Doll Trap"
            ]
            for eff in target_dolls:
                if not self.has_effect_with_user(EffectType.MARK, "Doll Trap",
                                                 eff.user):
                    self.add_effect(
                        Effect(
                            Ability("frenda2"),
                            EffectType.MARK,
                            eff.user,
                            280000,
                            lambda leff:
                            f"If an enemy damages this character, all stacks of Doll Trap will be transferred to them.",
                            invisible=True))
                self.apply_stack_effect(
                    Effect(
                        Ability("frenda1"),
                        EffectType.STACK,
                        eff.user,
                        280000,
                        lambda leff:
                        f"Detonate will deal {20 * leff.mag} damage to this character.",
                        mag=eff.mag,
                        invisible=True), eff.user)
                eff.user.progress_mission(1, eff.mag)
                target.full_remove_effect("Doll Trap", eff.user)
        if target.has_effect(EffectType.ALL_DR, "Conductivity"):
            target.get_effect(EffectType.ALL_DR,
                              "Conductivity").user.receive_eff_damage(
                                  10,
                                  target.get_effect(EffectType.ALL_DR,
                                                    "Conductivity"))

        if target.source.hp <= 0:
            if self.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct"):
                self.get_effect(EffectType.STUN_IMMUNE,
                                "Beast Instinct").duration = 5
                self.get_effect(EffectType.COUNTER_IMMUNE,
                                "Beast Instinct").duration = 5
            if self.used_ability != None and self.used_ability.name == "Yatsufusa":
                if target in self.scene.player_display.team.character_managers:
                    target.add_effect(
                        Effect(
                            self.used_ability, EffectType.MARK, self, 3,
                            lambda eff:
                            "At the beginning of her next turn, Kurome will animate this character."
                        ))
                else:
                    self.apply_stack_effect(
                        Effect(
                            self.used_ability,
                            EffectType.STACK,
                            self,
                            280000,
                            lambda eff:
                            f"Mass Animation will deal {eff.mag * 10} more damage.",
                            mag=1), self)

    def apply_stack_effect(self, effect: Effect, user: "CharacterManager"):
        gen = [
            eff for eff in self.source.current_effects
            if (eff.eff_type == effect.eff_type and eff.name == effect.name
                and eff.user == user)
        ]
        if gen:
            for eff in gen:
                eff.alter_mag(effect.mag)
        else:
            self.add_effect(effect)

    def apply_dest_def_effect(self, effect: Effect):
        gen = [eff for eff in self.source.current_effects if (eff.eff_type == EffectType.DEST_DEF and eff.name == effect.name and eff.user == effect.user)]
        if gen:
            for eff in gen:
                eff.alter_dest_def(effect.mag)
        else:
            self.add_effect(effect)


    def get_dest_def_total(self) -> int:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEST_DEF)
        dest_def = 0
        for eff in gen:
            dest_def += eff.mag
        return dest_def

    def will_die(self, damage: int) -> bool:
        total_life = self.get_dest_def_total() + self.source.hp
        return damage >= total_life

    def deal_damage(self, damage: int, target: "CharacterManager"):
        mod_damage = self.get_boosts(damage)
        if self.used_ability.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
            target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
            target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
        else:
            if self.mission_active("ryohei", self):
                if mod_damage >= 100 and self.used_ability.name == "Maximum Cannon":
                    self.progress_mission(5, 1)


            if mod_damage > target.check_for_dmg_reduction():
                if self.has_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"):
                    self.receive_eff_healing(10, self.get_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"))

            target.receive_damage(mod_damage, self)

            if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
                self.receive_eff_damage(mod_damage, target.get_effect(EffectType.UNIQUE, "Thunder Palace"))
                target.full_remove_effect("Thunder Palace", target)
            if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
                user = target.get_effect(EffectType.UNIQUE, "Burning Axle").user
                target.full_remove_effect("Burning Axle", user)
                target.add_effect(
                    Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user, 2,
                        lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
                    user.progress_mission(3, 1)


    def receive_damage(self, damage: int, dealer: "CharacterManager"):
        mod_damage = damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        #region Damage Dealt Mission Check

        if "hinata" in self.scene.missions_to_check:
            if dealer.source.name == "hinata" and dealer.used_ability.name == "Eight Trigrams - 64 Palms":
                dealer.progress_mission(5, mod_damage)
        if "neji" in self.scene.missions_to_check:
            if dealer.used_ability.name == "Eight Trigrams - 128 Palms":
                dealer.progress_mission(3, mod_damage)
        if "rukia" in self.scene.missions_to_check:
            if dealer.used_ability.name == "Second Dance - Hakuren":
                dealer.progress_mission(2, mod_damage)
        if "midoriya" in self.scene.missions_to_check:
            if dealer.used_ability.name == "SMASH!":
                dealer.progress_mission(1, mod_damage)
            if dealer.used_ability.name == "One For All - Shoot Style":
                dealer.progress_mission(2, mod_damage)
        if "uraraka" in self.scene.missions_to_check:
            if dealer.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                dealer.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if "todoroki" in self.scene.missions_to_check:
            if dealer.used_ability.name == "Quirk - Half-Cold":
                dealer.progress_mission(2, mod_damage)
            if dealer.used_ability.name == "Quirk - Half-Hot" and self.scene.is_allied_character(dealer):
                dealer.progress_mission(4, mod_damage)
        if "natsu" in self.scene.missions_to_check:
            if dealer.source.name == "natsu":
                if not self.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                    self.add_effect(Effect("NatsuMission5Tracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", system=True))
                mission5_complete = True
                for manager in self.enemy_team:
                    if not manager.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                        mission5_complete = False
                if mission5_complete:
                    dealer.progress_mission(5, 1)
        if "gray" in self.scene.missions_to_check:
            if dealer.source.name == "gray" and dealer.used_ability.name == "Ice, Make Freeze Lancer":
                if not self.has_effect(EffectType.SYSTEM, "GrayMission4Tracker"):
                    self.add_effect(Effect("GrayMission4Tracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", mag = mod_damage, system=True))
                else:
                    self.get_effect(EffectType.SYSTEM, "GrayMission4Tracker").alter_mag(mod_damage)
                mission4_complete = True
                for character in self.enemy_team:
                    if not character.has_effect(EffectType.SYSTEM, "GrayMission4Tracker"):
                        mission4_complete = False
                    else:
                        if character.get_effect(EffectType.SYSTEM, "GrayMission4Tracker").mag < 50:
                            mission4_complete = False
                if mission4_complete:
                    dealer.add_effect(Effect("GrayMission4TrackerSuccess", EffectType.SYSTEM, dealer, 280000, lambda eff:"", system=True))
        if self.mission_active("gajeel", dealer):
            if dealer.has_effect(EffectType.ALL_DR, "Blacksteel Gajeel"):
                dealer.progress_mission(2, mod_damage)
        if "lucy" in self.scene.missions_to_check:
            if self.can_defend() and self.has_effect(EffectType.ALL_DR, "Aquarius"):
                self.get_effect(EffectType.ALL_DR, "Aquarius").user.progress_mission(1, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not dealer.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                dealer.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                dealer.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if "jack" in self.scene.missions_to_check and not dealer.source.name == "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if "chu" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Flashing Deflection"):
                self.progress_mission(2, 1)
        if self.mission_active("misaka", dealer):
            if dealer.used_ability.name == "Iron Sand":
                dealer.progress_mission(3, mod_damage)
            if dealer.used_ability.name == "Railgun":
                dealer.progress_mission(5, mod_damage)
        if self.mission_active("tsunayoshi", dealer):
            if dealer.used_ability.name == "X-Burner":
                dealer.progress_mission(1, mod_damage)
        if self.mission_active("hibari", dealer):
            if dealer.used_ability.name == "Bite You To Death":
                dealer.progress_mission(1, mod_damage)
            if self.has_effect(EffectType.ALL_STUN, "Alaudi's Handcuffs"):
                dealer.progress_mission(2, 1)
            if self.has_effect(EffectType.UNIQUE, "Porcospino Nuvola"):
                dealer.progress_mission(3, 1)
        if self.mission_active("gokudera", dealer):
            if dealer.used_ability.name == "Sistema C.A.I.":
                dealer.progress_mission(2, mod_damage)
        if self.mission_active("seryu", dealer):
            if dealer.used_ability.name == "Raging Koro":
                dealer.progress_mission(1, mod_damage)
                if not self.has_effect(EffectType.SYSTEM, "SeryuKoroTracker"):
                    self.add_effect(Effect("SeryuKoroTracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", system=True))
            if dealer.used_ability.name == "Body Modification - Arm Gun":
                if not self.has_effect(EffectType.SYSTEM, "SeryuArmGunTracker"):
                    self.add_effect(Effect("SeryuArmGunTracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", system=True))
        if self.mission_active("ruler", dealer):
            if dealer.used_ability.name == "Minion - Minael and Yunael":
                dealer.progress_mission(2, mod_damage)
        if self.mission_active("cranberry", dealer):
            if dealer.used_ability.name == "Fortissimo" and (self.check_invuln() or self.is_ignoring()):
                dealer.progress_mission(4, mod_damage)
        if self.mission_active("pucelle", dealer):
            if dealer.used_ability.name == "Knight's Sword" and mod_damage >= 100:
                dealer.progress_mission(4, 1)
        if "mirai" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Blood Shield"):
                dealer.progress_mission(5, 1)
        if self.mission_active("byakuya", dealer):
            if dealer.used_ability.name == "Scatter, Senbonzakura":
                dealer.progress_mission(2, mod_damage)
        #endregion

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                    temp_yatsufusa_storage.user.progress_mission(1, 1)
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)

        mod_damage = self.pass_through_dest_def(mod_damage)

        if self.has_effect(EffectType.SYSTEM, "SheelePunctureCounter"):
            if dealer.source.name == "sheele" and dealer.used_ability.name == "Extase - Bisector of Creation":
                dealer.progress_mission(4, self.get_effect(EffectType.SYSTEM, "SheelePunctureCounter").mag)

        self.apply_active_damage_taken(mod_damage, dealer)
        self.death_check(dealer)

    def deal_eff_damage(self, damage: int, target: "CharacterManager", source: Effect):
        damage = self.get_boosts(damage)
        if source.source.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
            target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
            target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
        else:
            target.receive_eff_damage(damage, source)

    def progress_mission(self, mission_number: int, progress: int):
        if not self.has_effect(EffectType.UNIQUE, "Quirk - Transform"):
            if mission_number == 1 and not self.source.mission1complete:
                self.source.mission1progress += progress
            elif mission_number == 2 and not self.source.mission2complete:
                self.source.mission2progress += progress
            elif mission_number == 3 and not self.source.mission3complete:
                self.source.mission3progress += progress
            elif mission_number == 4 and not self.source.mission4complete:
                self.source.mission4progress += progress
            elif mission_number == 5 and not self.source.mission5complete:
                self.source.mission5progress += progress
        else:
            self.source.mission1progress += 1


    def receive_eff_damage(self, damage: int, source: Effect):
        mod_damage = damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        if "neji" in self.scene.missions_to_check:
            if source.name == "Eight Trigrams - 128 Palms":
                source.user.progress_mission(3, mod_damage)
        if "uraraka" in self.scene.missions_to_check:
            if source.user.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                source.user.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if "gray" in self.scene.missions_to_check:
            if source.user.source.name == "gray" and source.user.used_ability.name == "Ice, Make Freeze Lancer":
                if not self.has_effect(EffectType.SYSTEM, "GrayMission4Tracker"):
                    self.add_effect(Effect("GrayMission4Tracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", mag = mod_damage, system=True))
                else:
                    self.get_effect(EffectType.SYSTEM, "GrayMission4Tracker").alter_mag(mod_damage)
        if "lucy" in self.scene.missions_to_check:
            if self.can_defend() and self.has_effect(EffectType.ALL_DR, "Aquarius"):
                self.get_effect(EffectType.ALL_DR, "Aquarius").user.progress_mission(1, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not source.user.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                source.user.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                source.user.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if "jack" in self.scene.missions_to_check and source.user.source.name != "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if self.mission_active("hibari", source.user):
            if source.name == "Porcospino Nuvola":
                source.user.progress_mission(5, mod_damage)
        if "lambo" in self.scene.missions_to_check:
            if source.name == "Conductivity":
                source.user.progress_mission(4, mod_damage)
        if self.mission_active("seryu", source.user):
            if source.user.used_ability.name == "Raging Koro":
                source.user.progress_mission(1, mod_damage)
                if not self.has_effect(EffectType.SYSTEM, "SeryuKoroTracker"):
                    self.add_effect(Effect("SeryuKoroTracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", system=True))
                

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)

        mod_damage = self.pass_through_dest_def(mod_damage)
        self.apply_eff_damage_taken(mod_damage, source)
        self.eff_death_check(source)

    def deal_pierce_damage(self, damage: int, target: "CharacterManager"):
        mod_damage = self.get_boosts(damage)
        if self.used_ability.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
            target.receive_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
            target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
        else:
            if mod_damage > target.check_for_dmg_reduction():
                if self.has_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"):
                    self.receive_eff_healing(10, self.get_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"))

            target.receive_pierce_damage(mod_damage, self)

            if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
                self.receive_eff_damage(mod_damage, target.get_effect(EffectType.UNIQUE, "Thunder Palace"))
                target.full_remove_effect("Thunder Palace", target)
            if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
                user = target.get_effect(EffectType.UNIQUE, "Burning Axle").user
                target.full_remove_effect("Burning Axle", user)
                target.add_effect(
                    Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user, 2,
                        lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
                    user.progress_mission(3, 1)


    def receive_pierce_damage(self, damage: int, dealer: "CharacterManager"):
        mod_damage = damage
        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        if "uraraka" in self.scene.missions_to_check:
            if dealer.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                dealer.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if self.mission_active("gajeel", dealer):
            if dealer.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon"):
                dealer.progress_mission(3, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not dealer.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                dealer.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                dealer.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if "jack" in self.scene.missions_to_check and not dealer.source.name == "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if self.mission_active("chu", dealer):
            if dealer.used_ability.name == "Relentless Assault":
                dealer.progress_mission(1, mod_damage)
        if "chu" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Flashing Deflection"):
                self.progress_mission(2, 1)
        if "mirai" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Blood Shield"):
                dealer.progress_mission(5, 1)

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                    temp_yatsufusa_storage.user.progress_mission(1, 1)
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)

        mod_damage = self.pass_through_dest_def(mod_damage)

        self.apply_active_damage_taken(mod_damage, dealer)
        self.death_check(dealer)

    def deal_eff_pierce_damage(self, damage: int, target: "CharacterManager", source: Effect):
        damage = self.get_boosts(damage)
        if source.source.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
            target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
            target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
        else:
            target.receive_eff_pierce_damage(damage, source)

    def receive_eff_pierce_damage(self, damage: int, source: Effect):
        mod_damage = damage

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        if "uraraka" in self.scene.missions_to_check:
            if source.user.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                source.user.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if self.mission_active("wendy", source.user):
            if source.name == "Shredding Wedding":
                source.user.progress_mission(3, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not source.user.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                source.user.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                source.user.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if "jack" in self.scene.missions_to_check and source.user.source.name != "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if self.mission_active("chu", source.user):
            if source.name == "Relentless Assault":
                source.user.progress_mission(1, mod_damage)
        if self.mission_active("cmary", source.user):
            if source.name == "Hidden Mine":
                source.user.progress_mission(1, mod_damage)

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                    temp_yatsufusa_storage.user.progress_mission(1, 1)
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)
        mod_damage = self.pass_through_dest_def(mod_damage)
        self.apply_eff_damage_taken(mod_damage, source)
        self.eff_death_check(source)

    def deal_aff_damage(self, damage: int, target: "CharacterManager"):
        #TODO check for affliction boosts

        if not target.is_aff_immune():


            if self.used_ability.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
                target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
                target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
            else:
                if self.has_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"):
                    self.receive_eff_healing(10, self.get_effect(EffectType.UNIQUE,
                                "Three-God Empowering Shield"))

                target.receive_aff_dmg(damage, self)

                if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
                    self.receive_eff_damage(damage, target.get_effect(EffectType.UNIQUE, "Thunder Palace"))
                    target.full_remove_effect("Thunder Palace", target)
                if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
                    user = target.get_effect(EffectType.UNIQUE,
                                            "Burning Axle").user
                    target.full_remove_effect("Burning Axle", user)
                    target.add_effect(
                        Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user,
                            2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        user.check_on_stun(target)
                        user.progress_mission(3, 1)
        else:
            #Check for affliction negation missions
            #TODO add affliction damage received boosts
            mod_damage = damage

            if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
                mod_damage = mod_damage * 2
            if target.has_effect(EffectType.AFF_IMMUNE, "Heaven's Wheel Armor"):
                target.progress_mission(2, mod_damage)



    def receive_aff_dmg(self, damage: int, dealer: "CharacterManager"):
        #TODO add affliction damage received boosts
        mod_damage = damage

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        #region Affliction Damage Mission Progress

        if self.mission_active("shikamaru", dealer):
            if dealer.used_ability.name == "Shadow Neck Bind":
                dealer.progress_mission(1, mod_damage)
        if self.mission_active("shigaraki", dealer):
            dealer.progress_mission(1, mod_damage)
        if "uraraka" in self.scene.missions_to_check:
            if dealer.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                dealer.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if self.mission_active("natsu", dealer):
            dealer.progress_mission(1, mod_damage)
            if not self.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                self.add_effect(Effect("NatsuMission5Tracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", system=True))
            mission5_complete = True
            for manager in self.enemy_team:
                if not manager.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                    mission5_complete = False
            if mission5_complete:
                dealer.progress_mission(5, 1)
        if self.mission_active("levy", dealer):
            if dealer == "Solid Script - Fire":
                dealer.progress_mission(4, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not dealer.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                dealer.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, dealer, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                dealer.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if self.mission_active("jack", dealer):
            dealer.progress_mission(3, mod_damage)
        if "jack" in self.scene.missions_to_check and not dealer.source.name == "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if "chu" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Flashing Deflection"):
                self.progress_mission(2, 1)
        if self.mission_active("mirai", dealer):
            dealer.progress_mission(1, mod_damage)
        if "mirai" in self.scene.missions_to_check:
            if self.has_effect(EffectType.ALL_DR, "Blood Shield"):
                dealer.progress_mission(5, 1)
        #endregion


        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                    temp_yatsufusa_storage.user.progress_mission(1, 1)
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)

        self.apply_active_damage_taken(mod_damage, dealer)
        self.death_check(dealer)

    def deal_eff_aff_damage(self, damage: int, target: "CharacterManager", source: Effect):
        #TODO add affliction damage boosts
        if not target.is_aff_immune():
            if source.source.all_costs[1] and target.has_effect(EffectType.UNIQUE, "Galvanism"):
                target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
                target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1), target)
            else:
                target.receive_eff_aff_damage(damage, source)
        else:
            #Check for affliction negation missions
            #TODO add affliction damage received boosts
            mod_damage = damage

            if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
                mod_damage = mod_damage * 2
            if target.has_effect(EffectType.AFF_IMMUNE, "Heaven's Wheel Armor"):
                target.progress_mission(2, mod_damage)

    def receive_eff_aff_damage(self, damage: int, source: Effect):
        #TODO add affliction damage received boosts
        mod_damage = damage

        if mod_damage < 0:
            mod_damage = 0

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        #region Effect Affliction Damage Mission Check:

        if self.mission_active("shikamaru", source.user):
            if source.name == "Shadow Neck Bind":
                source.user.progress_mission(1, mod_damage)
        if self.mission_active("shigaraki", source.user):
            source.user.progress_mission(1, mod_damage)
        if "uraraka" in self.scene.missions_to_check:
            if source.user.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                source.user.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if self.mission_active("natsu", source.user):
            source.user.progress_mission(1, mod_damage)
            if not self.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                self.add_effect(Effect("NatsuMission5Tracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", system=True))
            mission5_complete = True
            for manager in self.enemy_team:
                if not manager.has_effect(EffectType.SYSTEM, "NatsuMission5Tracker"):
                    mission5_complete = False
            if mission5_complete:
                source.user.progress_mission(5, 1)
        if self.mission_active("levy", source.user):
            if source.name == "Solid Script - Fire":
                source.user.progress_mission(4, mod_damage)
        if "saber" in self.scene.missions_to_check or "mine" in self.scene.missions_to_check:
            if not source.user.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
                source.user.add_effect(Effect("SaberDamageTracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", mag=mod_damage, system=True))
            else:
                source.user.get_effect(EffectType.SYSTEM, "SaberDamageTracker").alter_mag(mod_damage)
        if self.mission_active("jack", source.user):
            source.user.progress_mission(3, mod_damage)
        if "jack" in self.scene.missions_to_check and source.user.source.name != "jack":
            if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                self.add_effect(Effect("JackMission1Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
        if self.mission_active("mirai", source.user):
            source.user.progress_mission(1, mod_damage)
            if source.name == "Blood Suppression Removal":
                source.user.progress_mission(3, mod_damage)
        #endregion

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(
                    Effect(
                        Ability("neji3"),
                        EffectType.ALL_BOOST,
                        self.get_effect(EffectType.MARK,
                                        "Selfless Genius").user,
                        2,
                        lambda eff:
                        "This character will deal 10 more damage with non-affliction abilities.",
                        mag=10))
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.mission4progress += 1
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK,
                                "Selfless Genius").user.source.dead = True
                temp_yatsufusa_storage = None
                if self.get_effect(EffectType.MARK,
                                   "Selfless Genius").user.has_effect(
                                       EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                    temp_yatsufusa_storage.user.progress_mission(1, 1)
                self.get_effect(
                    EffectType.MARK,
                    "Selfless Genius").user.source.clear_effects()
                if temp_yatsufusa_storage:
                    self.get_effect(
                        EffectType.MARK,
                        "Selfless Genius").user.source.current_effects.append(
                            temp_yatsufusa_storage)

        self.apply_eff_damage_taken(mod_damage, source)

        self.eff_death_check(source)

    def receive_system_aff_damage(self, damage: int):
        if not self.is_aff_immune():
            mod_damage = damage
        else:
            mod_damage = 0    
        self.source.hp -= mod_damage
        self.death_check(self)

    def receive_system_healing(self, healing: int):
        #TODO check heal immune/heal boosts
        self.source.hp += healing
        if self.source.hp > 100:
            self.source.hp = 100

    def apply_eff_damage_taken(self, damage: int, source: "Effect"):
        if damage < 0:
            damage = 0

        self.source.hp -= damage

        if damage > 0:
            self.eff_damage_taken_check(damage, source)
            #region Effect damage-based mission checks

            #endregion

    def toga_transform(self, target_name: str):
        swap_hp = self.source.hp
        swap_effects = self.source.current_effects
        self.source = self.scene.return_character(target_name)
        try:
            for i, sprite in enumerate(self.main_ability_sprites):
                sprite.surface = self.scene.get_scaled_surface(self.scene.scene_manager.surfaces[self.source.main_abilities[i].db_name])
                sprite.ability = self.source.main_abilities[i]
                sprite.null_pane.ability = self.source.main_abilities[i]
                sprite.null_pane.in_battle_desc = self.scene.create_text_display(self.scene.font, sprite.null_pane.ability.name + ": " + sprite.null_pane.ability.desc, BLACK, WHITE, 5, 0, 520, 110)
                sprite.in_battle_desc = self.scene.create_text_display(self.scene.font, sprite.ability.name + ": " + sprite.ability.desc, BLACK, WHITE, 5, 0, 520, 110)
            
            self.alt_ability_sprites.clear()
            for ability in self.source.alt_abilities:
                self.alt_ability_sprites.append(self.scene.ui_factory.from_surface(sdl2.ext.BUTTON, self.scene.get_scaled_surface(self.scene.scene_manager.surfaces[ability.db_name]), free=True))
            for j, sprite in enumerate(self.alt_ability_sprites):
                    sprite.selected_pane = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON, self.scene.get_scaled_surface(self.scene.scene_manager.surfaces["selected"]), free=True)
                    sprite.ability = self.source.alt_abilities[j]
                    sprite.null_pane = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON, self.scene.get_scaled_surface(self.scene.scene_manager.surfaces["locked"]), free=True)
                    sprite.null_pane.ability = self.source.main_abilities[j]
                    sprite.null_pane.in_battle_desc = self.scene.create_text_display(self.scene.font, sprite.null_pane.ability.name + ": " + sprite.null_pane.ability.desc, BLACK, WHITE, 5, 0, 520, 110)
                    sprite.null_pane.text_border = self.scene.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (524, 129))
                    sprite.null_pane.click += self.set_selected_ability
                    sprite.in_battle_desc = self.scene.create_text_display(self.scene.font, sprite.ability.name + ": " + sprite.ability.desc, BLACK, WHITE, 5, 0, 520, 110)
                    sprite.border = self.scene.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (104, 104))
                    sprite.text_border = self.scene.ui_factory.from_color(sdl2.ext.BUTTON, BLACK, (524, 129))
                    sprite.click += self.set_selected_ability
        except AttributeError:
            pass

        self.source.hp = swap_hp
        self.source.current_effects = swap_effects

    def apply_active_damage_taken(self, damage: int, dealer: "CharacterManager"):
        if damage < 0:
            damage = 0


        
        self.source.hp -= damage

        if dealer.has_effect(EffectType.ALL_BOOST, "Nemurin Beam"):
            dealer.progress_mission(2, 1)

        if damage > 0:
            self.damage_taken_check(damage, dealer)
            dealer.check_on_damage_dealt(self, damage)
            #region Damage-based mission checks

            #endregion

    def get_boosts(self, damage: int) -> int:
        mod_damage = damage
        no_boost = False
        which = 0
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.BOOST_NEGATE)
        for eff in gen:
            no_boost = True
            break
        for i, ability in enumerate(self.source.current_abilities):
            if self.used_ability == ability and not no_boost:
                which = i + 1
                if ability.name == "Knight's Sword" and self.has_effect(
                        EffectType.STACK, "Magic Sword"):
                    mod_damage += (
                        20 *
                        self.get_effect(EffectType.STACK, "Magic Sword").mag)
                if ability.name == "Maximum Cannon" and self.has_effect(
                        EffectType.STACK, "Maximum Cannon"):
                    guts = self.get_effect(
                        EffectType.STACK, "Maximum Cannon")
                    if guts.mag >= 5:
                        self.progress_mission(4, 1)
                    mod_damage += (15 * guts.mag)

        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_BOOST)
        for eff in gen:
            negative = False
            if eff.mag > 0 and no_boost:
                continue
            if eff.mag < 0:
                negative = True
            ability_target = math.trunc(eff.mag / 100)

            boost_value = eff.mag - (ability_target * 100)
            if negative:
                ability_target = ability_target * -1
            if ability_target == which or ability_target == 0:
                mod_damage = mod_damage + boost_value

        if self.used_ability != None and self.used_ability.name == "Trap of Argalia - Down With A Touch!":
            if self.has_effect(
                    EffectType.STACK,
                    "Trap of Argalia - Down With A Touch!") and not no_boost:
                mod_damage += (self.get_effect(
                    EffectType.STACK,
                    "Trap of Argalia - Down With A Touch!").mag * 5)

        return mod_damage

    def can_boost(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.BOOST_NEGATE)
        for eff in gen:
            return False
        return True

    def has_boosts(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_BOOST)
        for eff in gen:
            if eff.mag > 0:
                return True

        if self.has_effect(EffectType.STACK,
                           "Trap of Argalia - Down With A Touch!"):
            return True
        if self.has_effect(EffectType.STACK, "Zangetsu Strike"):
            return True
        if self.has_effect(EffectType.MARK, "Teleporting Strike"):
            return True
        if self.has_effect(EffectType.STACK, "Magic Sword"):
            return True
        if self.has_effect(EffectType.STACK, "Yatsufusa"):
            return True
        if self.has_effect(EffectType.STACK, "Maximum Cannon"):
            return True
        return False

    def can_defend(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEF_NEGATE)
        for _ in gen:
            return True
        return False

    def check_for_dmg_reduction(self) -> int:
        dr = 0
        no_boost = False

        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEF_NEGATE)
        for eff in gen:
            no_boost = True
            break

        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_DR)
        for eff in gen:
            if no_boost:
                if eff.mag < 0:
                    dr += eff.mag
            else:
                dr += eff.mag

        return dr

    def check_for_cooldown_mod(self, ability: Ability) -> int:
        cd_mod = 0
        which = 0

        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.COOLDOWN_MOD)
        for i, abi in enumerate(self.source.current_abilities):
            if ability == abi:
                if ability.name == "Knight's Sword" and self.has_effect(
                        EffectType.STACK, "Magic Sword"):
                    cd_mod += self.get_effect(EffectType.STACK,
                                              "Magic Sword").mag
                which = i + 1
        for eff in gen:
            negative = False
            if eff.mag < 0:
                negative = True
            ability_target = math.trunc(eff.mag / 10)

            boost_value = eff.mag - (ability_target * 10)
            if negative:
                ability_target = ability_target * -1
            if ability_target == which or ability_target == 0:
                cd_mod = cd_mod + boost_value
        return cd_mod

    def check_stun_duration_mod(self, base_dur: int) -> int:
        if self.has_effect(EffectType.UNIQUE, "Defensive Stance"):
            base_dur -= 2
        if base_dur < 0:
            base_dur = 0
        return base_dur

    def get_effect(self, eff_type: EffectType, eff_name: str):
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == eff_type)
        for eff in gen:
            if eff.name == eff_name:
                return eff

    def get_effect_with_user(self, eff_type: EffectType, eff_name: str,
                             user: "CharacterManager"):
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == eff_type and eff.user == user)
        for eff in gen:
            if eff.name == eff_name:
                return eff

    def has_effect_with_user(self, eff_type: EffectType, eff_name: str,
                             user: "CharacterManager") -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == eff_type and eff.user == user)
        for eff in gen:
            if eff.name == eff_name:
                return True
        return False

    def get_ability(self, name: str):
        for ability in self.source.current_abilities:
            if ability.name == name:
                return ability

    def has_effect(self, eff_type: EffectType, eff_name: str) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == eff_type)
        for eff in gen:
            if eff.name == eff_name:
                return True
        return False

    def check_for_collapsing_dest_def(self, eff: Effect):
        if eff.mag == 0:
            if eff.name == "Five-God Inviolate Shield":
                self.full_remove_effect("Five-God Inviolate Shield", eff.user)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect("Five-God Inviolate Shield",
                                               eff.user)
            if eff.name == "Four-God Resisting Shield":
                self.full_remove_effect("Four-God Resisting Shield", eff.user)
            if eff.name == "Three-God Linking Shield":
                self.full_remove_effect("Three-God Linking Shield", eff.user)
            if eff.name == "Perfect Paper - Rampage Suit":
                self.full_remove_effect("Perfect Paper - Rampage Suit",
                                        eff.user)
                self.add_effect(
                    Effect(
                        eff.source, EffectType.UNIQUE, self, 280000,
                        lambda eff:
                        "Naruha cannot use Perfect Paper - Rampage Suit."))
                
            if eff.name == "Illusory Breakdown":
                self.full_remove_effect("Illusory Breakdown", self)
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.full_remove_effect("Illusory Breakdown", self)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect("Illusory Breakdown", self)

            if eff.name == "Illusory World Destruction":
                self.full_remove_effect("Illusory World Destruction", self)
            if eff.name == "Mental Immolation":
                self.full_remove_effect("Mental Immolation", self)
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.full_remove_effect("Mental Immolation", self)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect("Mental Immolation", self)
            if eff.name == "Mental Annihilation":
                self.full_remove_effect("Mental Annihilation", self)
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.full_remove_effect("Mental Annihilation", self)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect("Mental Annihilation", self)

    def pass_through_dest_def(self, dmg: int) -> int:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEST_DEF)
        for eff in gen:
            current_def = eff.mag
            self.check_for_absorb_missions(eff, dmg)
            eff.alter_dest_def(-dmg)
            if eff.mag <= 0:
                if not self.has_effect(EffectType.SYSTEM, "SheelePunctureCounter"):
                    self.add_effect(Effect("SheelePunctureCounter", EffectType.SYSTEM, self, 1, lambda eff:"", mag=1, system=True))
                else:
                    self.get_effect(EffectType.SYSTEM, "SheelePunctureCounter").alter_mag(1)
            self.check_for_collapsing_dest_def(eff)
            dmg = engine.sat_subtract(current_def, dmg)
            if dmg == 0:
                return dmg
        return dmg

    def check_for_absorb_missions(self, eff: Effect, damage: int):
        if eff.mag > damage:
            progress = damage
        else:
            progress = eff.mag
        
        if "itachi" in self.scene.missions_to_check:
            if self.source.name == "itachi" and eff.name == "Susano'o":
                eff.user.progress_mission(5, progress)
        if "orihime" in self.scene.missions_to_check:
            if eff.user.source.name == "orihime":
                eff.user.progress_mission(4, progress)
        if "misaka" in self.scene.missions_to_check:
            if eff.user.source.name == "misaka" and eff.name == "Iron Sand":
                eff.user.progress_mission(3, progress)
        if "tatsumi" in self.scene.missions_to_check:
            if eff.user.source.name == "tatsumi" and eff.name == "Incursio":
                eff.user.progress_mission(3, progress)
        if "ruler" in self.scene.missions_to_check:
            if eff.user.source.name == "ruler" and eff.name == "Minion - Minael and Yunael":
                eff.user.progress_mission(2, progress)
        if "chachamaru" in self.scene.missions_to_check:
            if eff.user.source.name == "chachamaru" and eff.name == "Active Combat Mode":
                eff.user.progress_mission(5, progress)
        if "byakuya" in self.scene.missions_to_check:
            if eff.user.source.name == "byakuya" and eff.name == "Scatter, Senbonzakura":
                eff.user.progress_mission(2, progress)

    def can_act(self) -> bool:
        if self.is_stunned():
            return False
        return True

    def is_aff_immune(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.AFF_IMMUNE)
        for eff in gen:
            return True
        return False

    def has_specific_stun(self) -> bool:
        gen = (eff for eff in self.source.current_effects if eff.eff_type == EffectType.SPECIFIC_STUN)
        output = False
        for eff in gen:
            output = True
            break
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.STUN_IMMUNE)
        for eff in gen:
            output = False
            break
        return output

    def get_specific_stun_types(self) -> list[int]:
        output = []
        gen = (eff for eff in self.source.current_effects if eff.eff_type == EffectType.SPECIFIC_STUN)
        for eff in gen:
            if not eff.mag in output:
                output.append(eff.mag)
        return output



    def is_stunned(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_STUN)
        output = False
        for eff in gen:
            output = True
            break
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.STUN_IMMUNE)
        for eff in gen:
            output = False
            break
        return output

    def eff_damage_taken_check(self, damage: int, source: "Effect"):

        if "naruto" in self.scene.missions_to_check:
            if not self.has_effect(EffectType.SYSTEM, "NarutoMission5Tracker") and source.name != "Rasengan":
                self.add_effect(Effect("NarutoMission5Tracker", EffectType.SYSTEM, source.user, 280000, lambda eff: "", system = True))
        if "kakashi" in self.scene.missions_to_check:
            if not self.has_effect(EffectType.SYSTEM, "KakashiMission4Tracker"):
                self.add_effect(Effect("KakashiMission4Tracker", EffectType.SYSTEM, source.user, 280000, lambda eff: "", system = True))
        
        if self.source.name == "seryu" and self.source.hp < 30:
            self.add_effect(
                Effect(
                    Ability("seryualt1"),
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Body Modification - Arm Gun has been replaced by Body Modification - Self Destruct.",
                    mag=11))
        if self.has_effect(EffectType.MARK, "To The Extreme!"):
            extreme = self.get_effect(EffectType.MARK, "To The Extreme!")
            extreme.alter_mag(damage)
            if extreme.mag >= 20:
                stacks = extreme.mag // 20
                extreme.user.progress_mission(3, stacks)
                extreme.alter_mag(-(stacks * 20))
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei1"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Maximum Cannon will deal {eff.mag * 15} more damage and cost {eff.mag} more random energy.",
                        mag=stacks), self)
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei2"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Kangaryu will heal {eff.mag * 20} more health and cost {eff.mag} more random energy.",
                        mag=stacks), self)
        if self.has_effect(EffectType.MARK,
                    "You Are Needed") and self.source.hp < 30:
            self.full_remove_effect("You Are Needed", self)
            src = Ability("chrome1")
            self.add_effect(
                Effect(
                    src,
                    EffectType.PROF_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Rokudou Mukuro has intervened, replacing Chrome for the rest of the match.",
                    mag=1))
            self.add_effect(
                Effect(src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "You Are Needed has been replaced by Trident Combat.",
                    mag=11))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Illusory Breakdown has been replaced by Illusory World Destruction.",
                    mag=22))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Mental Immolation has been replaced by Mental Annihilation.",
                    mag=33))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Mental Substitution has been replaced by Trident Deflection.",
                    mag=44))
            if self.has_effect(EffectType.DEST_DEF, "Illusory Breakdown"):
                self.remove_effect(
                    self.get_effect(EffectType.DEST_DEF, "Illusory Breakdown"))
            if self.has_effect(EffectType.DEST_DEF, "Mental Immolation"):
                self.remove_effect(
                    self.get_effect(EffectType.DEST_DEF, "Mental Immolation"))
            for manager in self.scene.enemy_display.team.character_managers:
                if manager.has_effect(
                        EffectType.MARK,
                        "Illusory Breakdown") and manager.get_effect(
                            EffectType.MARK,
                            "Illusory Breakdown").user == self:
                    manager.remove_effect(
                        manager.get_effect(EffectType.MARK,
                                        "Illusory Breakdown"))
                if manager.has_effect(
                        EffectType.MARK,
                        "Mental Immolation") and manager.get_effect(
                            EffectType.MARK, "Mental Immolation").user == self:
                    manager.remove_effect(
                        manager.get_effect(EffectType.MARK,
                                        "Mental Immolation"))
        if self.has_effect(EffectType.CONT_AFF_DMG, "Susano'o"):
            if self.source.hp < 20 or self.get_effect(EffectType.DEST_DEF,
                                                      "Susano'o").mag <= 0:
                self.full_remove_effect("itachi3", self)
                self.full_remove_effect("Susano'o", self)
                if not self.has_effect(EffectType.SYSTEM, "ItachiMission4Tracker"):
                    self.add_effect(Effect("ItachiMission4Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system = True))


        

    def damage_taken_check(self, damage: int, damager: "CharacterManager"):

        if "naruto" in self.scene.missions_to_check:
            if not self.has_effect(EffectType.SYSTEM, "NarutoMission5Tracker") and damager.used_ability.name != "Rasengan":
                self.add_effect(Effect("NarutoMission5Tracker", EffectType.SYSTEM, damager, 280000, lambda eff: "", system = True))
        if "kakashi" in self.scene.missions_to_check:
            if not self.has_effect(EffectType.SYSTEM, "KakashiMission4Tracker") and damager.source.name != "kakashi":
                self.add_effect(Effect("KakashiMission4Tracker", EffectType.SYSTEM, damager, 280000, lambda eff:"", system = True))
        if "leone" in self.scene.missions_to_check:
            if self.source.name == "leone":
                if not self.has_effect(EffectType.SYSTEM, "LeoneMission5Tracker"):
                    self.add_effect(Effect("LeoneMission5Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", mag=damage, system=True))
                else:
                    self.get_effect(EffectType.SYSTEM, "LeoneMission5Tracker").alter_mag(damage)

        if self.has_effect(EffectType.UNIQUE, "In The Name Of Ruler!"):
            for manager in self.scene.player_display.team.character_managers:
                if manager.has_effect_with_user(EffectType.ALL_STUN,
                                                "In The Name Of Ruler!", self):
                    manager.full_remove_effect("In The Name Of Ruler!", self)
            self.full_remove_effect("In The Name Of Ruler!", self)
        if self.has_effect(EffectType.MARK, "Electric Rage"):
            self.add_effect(
                Effect(Ability("misaka3"),
                       EffectType.ENERGY_GAIN,
                       self,
                       2,
                       lambda eff: "Misaka will gain 1 special energy.",
                       mag=21,
                       system=True))
        if self.source.name == "seiryu" and self.source.hp < 30:
            self.add_effect(
                Effect(
                    Ability("seiryualt1"),
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Body Modification - Arm Gun has been replaced by Body Modification - Self Destruct.",
                    mag=11))
        if self.has_effect(EffectType.MARK, "To The Extreme!"):
            extreme = self.get_effect(EffectType.MARK, "To The Extreme!")
            extreme.alter_mag(damage)
            if extreme.mag >= 20:
                stacks = extreme.mag // 20
                extreme.user.progress_mission(3, stacks)
                extreme.alter_mag(-(stacks * 20))
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei1"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Maximum Cannon will deal {eff.mag * 15} more damage and cost {eff.mag} more random energy.",
                        mag=stacks), self)
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei2"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Kangaryu will heal {eff.mag * 20} more health and cost {eff.mag} more random energy.",
                        mag=stacks), self)
        if self.has_effect(EffectType.CONT_UNIQUE, "Nemurin Nap"):
            self.get_effect(EffectType.CONT_UNIQUE,
                            "Nemurin Nap").alter_mag(-1)
            if self.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").mag == 2:
                self.remove_effect(
                    self.get_effect(EffectType.TARGET_SWAP, "Nemurin Beam"))
                self.remove_effect(
                    self.get_effect(EffectType.TARGET_SWAP,
                                    "Dream Manipulation"))
            if self.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").mag == 1:
                self.remove_effect(
                    self.get_effect(EffectType.COST_ADJUST, "Nemurin Beam"))
                self.remove_effect(
                    self.get_effect(EffectType.COST_ADJUST,
                                    "Dream Manipulation"))
        if self.has_effect(EffectType.MARK,
                           "You Are Needed") and self.source.hp < 30:
            self.full_remove_effect("You Are Needed", self)
            src = Ability("chrome1")
            self.add_effect(
                Effect(
                    src,
                    EffectType.PROF_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Rokudou Mukuro has intervened, replacing Chrome for the rest of the match.",
                    mag=1))
            self.add_effect(
                Effect(src,
                       EffectType.ABILITY_SWAP,
                       self,
                       280000,
                       lambda eff:
                       "You Are Needed has been replaced by Trident Combat.",
                       mag=11))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Illusory Breakdown has been replaced by Illusory World Destruction.",
                    mag=22))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Mental Immolation has been replaced by Mental Annihilation.",
                    mag=33))
            self.add_effect(
                Effect(
                    src,
                    EffectType.ABILITY_SWAP,
                    self,
                    280000,
                    lambda eff:
                    "Mental Substitution has been replaced by Trident Deflection.",
                    mag=44))
            if self.has_effect(EffectType.DEST_DEF, "Illusory Breakdown"):
                self.remove_effect(
                    self.get_effect(EffectType.DEST_DEF, "Illusory Breakdown"))
            if self.has_effect(EffectType.DEST_DEF, "Mental Immolation"):
                self.remove_effect(
                    self.get_effect(EffectType.DEST_DEF, "Mental Immolation"))
            for manager in self.scene.enemy_display.team.character_managers:
                if manager.has_effect(
                        EffectType.MARK,
                        "Illusory Breakdown") and manager.get_effect(
                            EffectType.MARK,
                            "Illusory Breakdown").user == self:
                    manager.remove_effect(
                        manager.get_effect(EffectType.MARK,
                                           "Illusory Breakdown"))
                if manager.has_effect(
                        EffectType.MARK,
                        "Mental Immolation") and manager.get_effect(
                            EffectType.MARK, "Mental Immolation").user == self:
                    manager.remove_effect(
                        manager.get_effect(EffectType.MARK,
                                           "Mental Immolation"))
        if self.has_effect(EffectType.CONT_AFF_DMG, "Susano'o"):
            if self.source.hp < 20 or self.get_effect(EffectType.DEST_DEF,
                                                      "Susano'o").mag <= 0:
                self.full_remove_effect("itachi3", self)
                self.full_remove_effect("Susano'o", self)
                self.update_profile()
                if not self.has_effect(EffectType.SYSTEM, "ItachiMission4Tracker"):
                    self.add_effect(Effect("ItachiMission4Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system = True))


    def deflecting(self) -> bool:
        return self.has_effect(EffectType.MARK, "Flashing Deflection")

    def mission_active(self, name: str, character: "CharacterManager") -> bool:
        return name in self.scene.missions_to_check and character.source.name == name

    def check_for_all_kill_status(self, mission_name: str) -> bool:
        for manager in self.enemy_team:
            if not manager.has_effect(EffectType.SYSTEM, mission_name):
                return False
        return True

    def is_countering(self):
        gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.COUNTER
                       and not self.scene.is_allied_effect(eff))
        for eff in gen:
            return True
        return False

    def apply_all_kill_mission_tracker(self, targeter: "CharacterManager", mission_name: str):
        if not self.has_effect(EffectType.SYSTEM, mission_name):
            self.add_effect(Effect(mission_name, EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
        if self.killing_blow_mission_check(mission_name):
            self.add_effect(Effect(mission_name + "Success", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=False))

    def killing_blow_mission_check(self, targeter: Union["CharacterManager", Effect], active_killing_blow = True):
        if active_killing_blow:
            if self.mission_active("naruto", targeter):
                if targeter.has_effect(EffectType.ALL_INVULN, "Sage Mode"):
                    targeter.progress_mission(3, 1)
                if targeter.used_ability.name == "Rasengan" and not self.has_effect(EffectType.SYSTEM, "NarutoMission5Tracker"):
                    targeter.progress_mission(5, 1)
            if self.mission_active("itachi", targeter):
                if targeter.has_effect(EffectType.DEST_DEF, "Susano'o"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("minato", targeter):
                if targeter.used_ability.name == "Flying Raijin":
                    targeter.progress_mission(2, 1)
            if self.mission_active("neji", targeter):
                if targeter.used_ability.name == "Eight Trigrams - Mountain Crusher" and self.check_invuln():
                    targeter.progress_mission(1, 1)
            if self.mission_active("hinata", targeter):
                if targeter.used_ability.name == "Gentle Step - Twin Lion Fists" and targeter.source.second_swing:
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Gentle Step - Twin Lion Fists" and targeter.source.second_swing and targeter.source.first_countered:
                    targeter.progress_mission(3, 1)
            if self.mission_active("shikamaru", targeter):
                if targeter.used_ability.name == "Shadow Neck Bind":
                    if targeter.has_effect(EffectType.SYSTEM, "ShikamaruMission2Tracker"):
                        targeter.progress_mission(2, 1)
                    else:
                        targeter.add_effect(Effect("ShikamaruMissionTracker2", EffectType.SYSTEM, targeter, 1, lambda eff:"", system = True))
            if "shikamaru" in self.scene.missions_to_check:
                if self.has_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind") and targeter != self.get_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind").user: 
                    self.get_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind").user.progress_mission(3, 1)
            if "kakashi" in self.scene.missions_to_check:
                if self.scene.sharingan_reflecting:
                    self.scene.sharingan_reflector.progress_mission(1, 1)
            if self.mission_active("kakashi", targeter):
                if targeter.used_ability.name == "Raikiri" and self.has_effect(EffectType.ALL_STUN, "Summon - Nin-dogs"):
                    targeter.progress_mission(2, 1)
                if not self.has_effect(EffectType.SYSTEM, "KakashiMission4Tracker"):
                    targeter.progress_mission(4, 1)
            if self.mission_active("ichigo", targeter):
                if targeter.has_effect(EffectType.ALL_INVULN, "Tensa Zangetsu"):
                    targeter.progress_mission(2, 1)
                if targeter.source.hp < 30:
                    targeter.progress_mission(5, 1)
            if self.mission_active("ichimaru", targeter):
                if targeter.used_ability.name == "Kill, Kamishini no Yari":
                    targeter.progress_mission(1, 1)
                if targeter.last_man_standing():
                    if not targeter.has_effect(EffectType.SYSTEM, "IchimaruMission5Tracker"):
                        targeter.add_effect(Effect("IchimaruMission5Tracker", EffectType.SYSTEM, targeter, 280000, lambda eff: "", mag = 1, system=True))
                    else:
                        targeter.get_effect(EffectType.SYSTEM, "IchimaruMission5Tracker").alter_mag(1)
            if self.mission_active("aizen", targeter):
                if targeter.used_ability.name == "Overwhelming Power":
                    targeter.progress_mission(3, 1)
            if self.mission_active("midoriya", targeter):
                if targeter.used_ability.name == "One For All - Shoot Style":
                    targeter.progress_mission(4, 1)
            if self.mission_active("mirio", targeter):
                if targeter.used_ability.name == "Phantom Menace":
                    targeter.progress_mission(5, 1)
            if "toga" in self.scene.missions_to_check:
                if targeter.is_toga:
                    if not targeter.user.has_effect(EffectType.UNIQUE, "Quirk - Transform"):
                        targeter.source.mission5progress += 1
                    else:
                        targeter.source.mission4progress += 1
            if self.mission_active("shigaraki", targeter):
                targeter.progress_mission(2, 1)
            if "shigaraki" in self.scene.missions_to_check:
                if self.has_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"):
                    shigaraki: "CharacterManager" = self.get_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love").user
                    if shigaraki.has_effect(EffectType.SYSTEM, "ShigarakiMission3Tracker"):
                        shigaraki.get_effect(EffectType.SYSTEM, "ShigarakiMission3Tracker").alter_mag(1)
                    else:
                        shigaraki.add_effect(Effect("ShigarakiMission3Tracker", EffectType.SYSTEM, shigaraki, 280000, lambda eff:"", mag=1, system=True))
                if targeter.has_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"):
                    shigaraki = targeter.get_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love").user
                    if shigaraki.has_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker"):
                        shigaraki.get_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker").alter_mag(1)
                    else:
                        shigaraki.add_effect(Effect("ShigarakiMission4Tracker", EffectType.SYSTEM, shigaraki, 280000, lambda eff:"", mag=1, system=True))
            if "uraraka" in self.scene.missions_to_check:
                if targeter.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                    targeter.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(1, 1)
                if self.has_effect(EffectType.ALL_DR, "Quirk - Zero Gravity"):
                    self.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(2, 1)
            if self.mission_active("uraraka", targeter):
                if not self.has_effect(EffectType.SYSTEM, "UrarakaMission5Tracker"):
                    self.add_effect(Effect("UrarakaMission5Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system = True))
            if self.mission_active("todoroki", targeter):
                if targeter.used_ability.name == "Flashfreeze Heatwave":
                    targeter.get_effect(EffectType.SYSTEM, "TodorokiMission1Tracker").alter_mag(1)
            if self.mission_active("jiro", targeter):
                if self.has_effect(EffectType.SYSTEM, "JiroMission4Tracker"):
                    targeter.progress_mission(4, 1)
                if self.has_effect(EffectType.UNIQUE, "Heartbeat Surround") or self.has_effect(EffectType.UNIQUE, "Heartbeat Distortion"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("natsu", targeter):
                targeter.progress_mission(3, 1)
                self.apply_all_kill_mission_tracker(targeter, "NatsuMission3Tracker")
            if self.mission_active("gajeel", targeter):
                if targeter.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon"):
                    if not targeter.has_effect(EffectType.UNIQUE, "GajeelMission1ShadowTracker"):
                        targeter.add_effect(Effect("GajeelMission1ShadowTracker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
                    if targeter.has_effect(EffectType.SYSTEM, "GajeelMission1IronTracker") and not targeter.source.mission1complete:
                        targeter.progress_mission(1, 1)
                        targeter.source.mission1complete = True
                if targeter.has_effect(EffectType.ALL_DR, "Blacksteel Gajeel"):
                    if not targeter.has_effect(EffectType.UNIQUE, "GajeelMission1IronTracker"):
                        targeter.add_effect(Effect("GajeelMission1IronTracker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
                    if targeter.has_effect(EffectType.SYSTEM, "GajeelMission1ShadowTracker") and not targeter.source.mission1complete:
                        targeter.progress_mission(1, 1)
                        targeter.source.mission1complete = True
            if self.mission_active("wendy", targeter):
                if self.has_effect(EffectType.MARK, "Shredding Wedding"):
                    targeter.progress_mission(2, 1)
            if self.mission_active("erza", targeter):
                if targeter.used_ability.name == "Titania's Rampage":
                    targeter.progress_mission(1, 1)
            if "erza" in self.scene.missions_to_check:
                if targeter.has_effect(EffectType.ALL_INVULN, "Adamantine Barrier"):
                    targeter.get_effect(EffectType.ALL_INVULN, "Adamantine Barrier").user.progress_mission(4, 1)
            if "levy" in self.scene.missions_to_check:
                if self.has_effect(EffectType.ISOLATE, "Solid Script - Silent"):
                    if self in self.enemy_team:
                        self.get_effect(EffectType.ISOLATE, "Solid Script - Silent").user.progress_mission(2, 1)
                if targeter.has_effect(EffectType.AFF_IMMUNE, "Solid Script - Mask"):
                    targeter.get_effect(EffectType.AFF_IMMUNE, "Solid Script - Mask").user.progress_mission(3, 1)
            if self.mission_active("jack", targeter):
                if self.has_effect(EffectType.MARK, "Streets of the Lost"):
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Maria the Ripper":
                    targeter.progress_mission(4, 1)
                if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                    targeter.progress_mission(1, 1)
            if self.mission_active("chu", targeter):
                if targeter.used_ability.name == "Gae Bolg" and self.has_effect(EffectType.SYSTEM, "GaeBolgPierceMarker"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("astolfo", targeter):
                if targeter.used_ability.name == "Trap of Argalia - Down With A Touch!":
                    targeter.progress_mission(3, 1)
                if self.has_effect(EffectType.BOOST_NEGATE, "La Black Luna"):
                    targeter.progress_mission(5, 1)
            if self.mission_active("misaka", targeter):
                if targeter.has_effect(EffectType.MARK, "Electric Rage") and targeter.used_ability.name == "Railgun":
                    targeter.progress_mission(1, 1)
            if self.mission_active("kuroko", targeter):
                if targeter.used_ability.name == "Teleporting Strike":
                    targeter.progress_mission(4, 1)
            if self.mission_active("gunha", targeter):
                if targeter.used_ability.name == "Super Awesome Punch":
                    targeter.progress_mission(2, 1)
            if "gunha" in self.scene.missions_to_check:
                if self.has_effect(EffectType.DEF_NEGATE, "Overwhelming Suppression"):
                    self.get_effect(EffectType.DEF_NEGATE, "Overwhelming Suppression").user.progress_mission(4, 1)
            if "misaki" in self.scene.missions_to_check:
                if targeter.has_effect(EffectType.ALL_STUN, "Mental Out"):
                    targeter.get_effect(EffectType.ALL_STUN, "Mental Out").user.progress_mission(1, 1)
            if self.mission_active("frenda", targeter):
                if targeter.used_ability.name == "Detonate":
                    targeter.get_effect(EffectType.SYSTEM, "FrendaMission2Tracker").alter_mag(1)
                    targeter.progress_mission(3, 1)
            if self.mission_active("naruha", targeter):
                if targeter.has_effect(EffectType.MARK, "Perfect Paper - Rampage Suit"):
                    targeter.progress_mission(4, 1)
                if targeter.used_ability.name == "Enraged Blow":
                    targeter.progress_mission(5, 1)
            if self.mission_active("tsunayoshi", targeter):
                if targeter.used_ability.name == "X-Burner":
                    targeter.get_effect(EffectType.SYSTEM, "TsunaMission4Tracker").alter_mag(1)
            if self.mission_active("yamamoto", targeter):
                if targeter.used_ability.name == "Shinotsuku Ame":
                    targeter.progress_mission(2, 1)
            if self.mission_active("gokudera", targeter):
                if targeter.used_ability.name == "Sistema C.A.I." and targeter.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("ryohei", targeter):
                if targeter.used_ability.name == "Maximum Cannon":
                    targeter.progress_mission(1, 1)
            if self.mission_active("chrome", targeter):
                targeter.progress_mission(4, 1)
                if not self.has_effect(EffectType.SYSTEM, "ChromeMission5Marker"):
                    if targeter.has_effect(EffectType.SYSTEM, "ChromeMission5Tracker"):
                        targeter.get_effect(EffectType.SYSTEM, "ChromeMission5Tracker").alter_mag(1)
                    else:
                        targeter.add_effect(Effect("ChromeMission5Tracker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", mag=1, system=True))
                    self.add_effect(Effect("ChromeMission5Marker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
            if self.mission_active("tatsumi", targeter):
                targeter.progress_mission(5, 1)
                if not self.has_effect(EffectType.SYSTEM, "TatsumiMission5Marker"):
                    if targeter.has_effect(EffectType.SYSTEM, "TatsumiMission5Tracker"):
                        targeter.get_effect(EffectType.SYSTEM, "TatsumiMission5Tracker").alter_mag(1)
                    else:
                        targeter.add_effect(Effect("TatsumiMission5Tracker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", mag=1, system=True))
                    self.add_effect(Effect("TatsumiMission5Marker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
            if self.mission_active("mine", targeter):
                if self.check_invuln() and targeter.has_effect(EffectType.MARK, "Pumpkin Scouter"):
                    targeter.progress_mission(1, 1)
                if targeter.used_ability.name == "Roman Artillery - Pumpkin" and targeter.source.hp < 30:
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Cut-Down Shot" and targeter.source.hp < 25:
                    targeter.progress_mission(3, 1)
                if targeter.has_effect(EffectType.SYSTEM, "MineMission4Tracker"):
                    targeter.get_effect(EffectType.SYSTEM, "MineMission4Tracker").alter_mag(1)
            if self.mission_active("akame", targeter):
                targeter.progress_mission(2, 1)
                if targeter.has_effect(EffectType.MARK, "Little War Horn"):
                    targeter.progress_mission(1, 1)
                if not self.has_effect(EffectType.SYSTEM, "AkameMission5Marker"):
                    if targeter.has_effect(EffectType.SYSTEM, "AkameMission5Tracker"):
                        targeter.get_effect(EffectType.SYSTEM, "AkameMission5Tracker").alter_mag(1)
                    else:
                        targeter.add_effect(Effect("AkameMission5Tracker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", mag=1, system=True))
                    self.add_effect(Effect("AkameMission5Marker", EffectType.SYSTEM, targeter, 280000, lambda eff:"", system=True))
            if self.mission_active("leone", targeter):
                targeter.progress_mission(2, 1)
                if self.has_effect(EffectType.MARK, "Beast Instinct"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("lubbock", targeter):
                if targeter.used_ability.name == "Heartseeker Thrust":
                    targeter.progress_mission(3, 1)
            if self.mission_active("sheele", targeter):
                targeter.progress_mission(1, 1)
                if self.is_ignoring() or self.is_countering():
                    targeter.progress_mission(2, 1)
                if self.has_effect(EffectType.ALL_STUN, "Trump Card - Blinding Light"):
                    targeter.progress_mission(5, 1)
            if self.mission_active("seryu", targeter):
                if targeter.used_ability.name == "Insatiable Justice":
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Body Modification - Arm Gun" and self.has_effect(EffectType.ALL_BOOST, "Berserker Howl"):
                    targeter.progress_mission(3, 1)
                if targeter.used_ability.name == "Body Modification - Self Destruct":
                    targeter.progress_mission(5, 1)
                if self.has_effect(EffectType.SYSTEM, "SeryuKoroTracker") and self.has_effect(EffectType.SYSTEM, "SeryuArmGunTracker"):
                    targeter.progress_mission(4, 1)
            if self.mission_active("kurome", targeter):
                if targeter.used_ability.name == "Mass Animation" and targeter.has_effect(EffectType.STACK, "Yatsufusa"):
                    targeter.progress_mission(2, 1)
                if targeter.has_effect(EffectType.UNIQUE, "Yatsufusa"):
                    targeter.get_effect(EffectType.UNIQUE, "Yatsufusa").user.progress_mission(3, 1)
                if targeter.has_effect(EffectType.MARK, "Doping Rampage"):
                    targeter.progress_mission(5, 1)
            if self.mission_active("esdeath", targeter):
                if self.has_effect(EffectType.MARK, "Frozen Castle"):
                    targeter.progress_mission(1, 1)
                if self.has_effect(EffectType.ALL_STUN, "Mahapadma"):
                    targeter.progress_mission(4, 1)
            if "ruler" in self.scene.missions_to_check:
                if self.has_effect(EffectType.ALL_STUN, "In The Name Of Ruler!"):
                    self.get_effect(EffectType.ALL_STUN, "In The Name Of Ruler!").user.progress_mission(5, 1)
            if self.mission_active("ripple", targeter):
                if self.has_effect(EffectType.CONT_PIERCE_DMG, "Night of Countless Stars"):
                    targeter.progress_mission(3, 1)
                if self.check_invuln():
                    targeter.progress_mission(4, 1)
                if not targeter.has_effect(EffectType.SYSTEM, "RippleMission5Tracker"):
                    targeter.add_effect(Effect("RippleMission5Tracker", EffectType.SYSTEM, targeter, 1, lambda eff:"", mag = 1, system=True))
                else:
                    targeter.get_effect(EffectType.SYSTEM, "RippleMission5Tracker").alter_mag(1)
            if "nemurin" in self.scene.missions_to_check:
                if targeter.has_effect(EffectType.ALL_BOOST, "Dream Manipulation"):
                    targeter.progress_mission(3, 1)
            if self.mission_active("cmary", targeter):
                if targeter.used_ability.name == "Grenade Toss" and self.has_effect(EffectType.UNIQUE, "Hidden Mine"):
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Quickdraw - Pistol" or targeter.used_ability.name == "Quickdraw - Rifle" or targeter.used_ability.name == "Quickdraw - Sniper":
                    targeter.progress_mission(3, 1)
            if self.mission_active("cranberry", targeter):
                if targeter.used_ability.name == "Merciless Finish":
                    targeter.progress_mission(2, 1)
            if self.mission_active("swimswim", targeter):
                if targeter.has_effect(EffectType.UNIQUE, "Dive"):
                    targeter.progress_mission(1, 1)
                if targeter.has_effect(EffectType.ALL_BOOST, "Vitality Pill"):
                    targeter.progress_mission(2, 1)
            if self.mission_active("pucelle", targeter):
                if targeter.used_ability.name == "Ideal Strike":
                    targeter.progress_mission(1, 1)
                    if targeter.last_man_standing():
                        targeter.add_effect(Effect("PucelleMission5Tracker", EffectType.SYSTEM, targeter, 1, lambda eff:"", system=True))
                if targeter.used_ability.name == "Knight's Sword":
                    targeter.progress_mission(3, 1)
            if self.mission_active("chachamaru", targeter):
                if targeter.used_ability.name == "Orbital Satellite Cannon":
                    targeter.progress_mission(3, 1)
                    if not targeter.has_effect(EffectType.SYSTEM, "ChachamaruMission4Tracker"):
                        targeter.add_effect(Effect("ChachamaruMission4Tracker", EffectType.SYSTEM, targeter, 1, lambda eff:"", mag = 1, system=True))
                    else:
                        targeter.get_effect(EffectType.SYSTEM, "ChachamaruMission4Tracker").alter_mag(1)
            if self.mission_active("saitama", targeter):
                if targeter.used_ability.name == "One Punch":
                    targeter.progress_mission(1, 1)
                if not self.has_effect(EffectType.SYSTEM, "SaitamaMission5Marker"):
                    if targeter.has_effect(EffectType.SYSTEM, "SaitamaMission5Tracker"):
                        targeter.get_effect(EffectType.SYSTEM, "SaitamaMission5Tracker").alter_mag(1)
                    else:
                        targeter.add_effect(Effect("SaitamaMission5Tracker", EffectType.SYSTEM, targeter.user, 280000, lambda eff:"", mag=1, system=True))
                    self.add_effect(Effect("SaitamaMission5Marker", EffectType.SYSTEM, targeter.user, 280000, lambda eff:"", system=True))
            if self.mission_active("tatsumaki", targeter):
                if targeter.used_ability.name == "Return Assault":
                    targeter.progress_mission(3, 1)
                if targeter.used_ability.name == "Rubble Barrage":
                    targeter.progress_mission(5, 1)
            if self.mission_active("mirai", targeter):
                if targeter.has_effect(EffectType.MARK, "Blood Suppression Removal"):
                    targeter.progress_mission(2, 1)
                if targeter.used_ability.name == "Blood Sword Combat":
                    targeter.progress_mission(4, 1)
            if self.mission_active("touka", targeter):
                if targeter.used_ability.name == "Raikiri":
                    targeter.progress_mission(3, 1)
                if targeter.has_effect(EffectType.MARK, "Nukiashi"):
                    targeter.progress_mission(4, 1)
            if self.mission_active("killua", targeter):
                if targeter.has_effect(EffectType.MARK, "Godspeed"):
                    targeter.progress_mission(4, 1)
            if self.mission_active("byakuya", targeter):
                if targeter.source.hp == 100:
                    targeter.progress_mission(4, 1)
                if targeter.source.hp <= 20 and targeter.used_ability.name == "White Imperial Sword":
                    targeter.progress_mission(5, 1)
        else:
            if "shikamaru" in self.scene.missions_to_check:
                if targeter.name == "Shadow Neck Bind":
                    if targeter.user.has_effect(EffectType.SYSTEM, "ShikamaruMission2Tracker"):
                        targeter.user.progress_mission(2, 1)
                    else:
                        targeter.user.add_effect(Effect("ShikamaruMissionTracker2", EffectType.SYSTEM, targeter.user, 1, lambda eff:"", system = True))
                if self.has_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind") and targeter.user != self.get_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind").user: 
                    self.get_effect(EffectType.CONT_AFF_DMG, "Shadow Neck Bind").user.source.mission3progress += 1
                if targeter in self.scene.sharingan_reflected_effects:
                    targeter.user.source.mission1progress += 1
            if "ichimaru" in self.scene.missions_to_check:
                if targeter.name == "Kill, Kamishini no Yari":
                    
                    if targeter.name == "Kill, Kamishini no Yari":
                        targeter.user.progress_mission(2, 1)
                if targeter.user.last_man_standing():
                    if not targeter.user.has_effect(EffectType.SYSTEM, "IchimaruMission5Tracker"):
                        targeter.user.add_effect(Effect("IchimaruMission5Tracker", EffectType.SYSTEM, targeter.user, 280000, lambda eff: "", mag = 1, system=True))
                    else:
                        targeter.user.get_effect(EffectType.SYSTEM, "IchimaruMission5Tracker").alter_mag(1)
            if "toga" in self.scene.missions_to_check:
                if targeter.user.is_toga:
                    if not targeter.user.has_effect(EffectType.UNIQUE, "Quirk - Transform"):
                        targeter.user.source.mission5progress += 1
                    else:
                        targeter.user.source.mission4progress += 1
            if self.mission_active("shigaraki", targeter.user):
                targeter.user.progress_mission(2, 1)
            if "shigaraki" in self.scene.missions_to_check:
                if self.has_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"):
                    shigaraki = self.get_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love").user
                    if shigaraki.has_effect(EffectType.SYSTEM, "ShigarakiMission3Tracker"):
                        shigaraki.get_effect(EffectType.SYSTEM, "ShigarakiMission3Tracker").alter_mag(1)
                    else:
                        shigaraki.add_effect(Effect("ShigarakiMission3Tracker", EffectType.SYSTEM, shigaraki, 280000, lambda eff:"", mag=1, system=True))
                if targeter.user.has_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"):
                    shigaraki = targeter.user.get_effect(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love").user
                    if shigaraki.has_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker"):
                        shigaraki.get_effect(EffectType.SYSTEM, "ShigarakiMission4Tracker").alter_mag(1)
                    else:
                        shigaraki.add_effect(Effect("ShigarakiMission4Tracker", EffectType.SYSTEM, shigaraki, 280000, lambda eff:"", mag=1, system=True))
            if "uraraka" in self.scene.missions_to_check:
                if targeter.user.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                    targeter.user.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(1, 1)
                if self.has_effect(EffectType.ALL_DR, "Quirk - Zero Gravity"):
                    self.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(2, 1)
            if "jiro" in self.scene.missions_to_check:
                if self.has_effect(EffectType.SYSTEM, "JiroMission4Tracker"):
                    targeter.user.progress_mission(4, 1)
                if targeter.name == "Heartbeat Distortion" or targeter.name == "Heartbeat Surround":
                    targeter.user.progress_mission(2, 1)
            if self.mission_active("natsu", targeter.user):
                targeter.user.progress_mission(3, 1)
                self.add_effect(Effect("NatsuMission4Tracker", EffectType.SYSTEM, targeter.user, 280000, lambda eff:"", system=True))
            if self.mission_active("wendy", targeter.user):
                if self.has_effect(EffectType.MARK, "Shredding Wedding"):
                    targeter.user.progress_mission(2, 1)
            if self.mission_active("erza", targeter.user):
                if targeter.name == "Titania's Rampage":
                    targeter.user.progress_mission(1, 1)
            if targeter.user.has_effect(EffectType.AFF_IMMUNE, "Solid Script - Mask"):
                    targeter.user.get_effect(EffectType.AFF_IMMUNE, "Solid Script - Mask").user.progress_mission(3, 1)
            if self.mission_active("lucy", targeter.user):
                if targeter.eff_type == EffectType.CONT_DMG:
                    targeter.user.progress_mission(3, 1)
            if self.mission_active("jack", targeter.user):
                if self.has_effect(EffectType.MARK, "Streets of the Lost"):
                    targeter.user.progress_mission(2, 1)
                if not self.has_effect(EffectType.SYSTEM, "JackMission1Failure"):
                    targeter.user.progress_mission(1, 1)
            if self.mission_active("chu", targeter.user):
                if targeter.name == "Relentless Assault" and targeter.duration <= 1:
                    targeter.user.progress_mission(5, 1)
            if "misaki" in self.scene.missions_to_check:
                if targeter.user.has_effect(EffectType.ALL_STUN, "Mental Out"):
                    targeter.user.get_effect(EffectType.ALL_STUN, "Mental Out").user.progress_mission(1, 1)
            if self.mission_active("naruha", targeter.user):
                if targeter.user.has_effect(EffectType.MARK, "Perfect Paper - Rampage Suit"):
                    targeter.user.progress_mission(4, 1)
            if self.mission_active("chrome", targeter.user):
                targeter.user.progress_mission(4, 1)
                if not self.has_effect(EffectType.SYSTEM, "ChromeMission5Marker"):
                    if targeter.user.has_effect(EffectType.SYSTEM, "ChromeMission5Tracker"):
                        targeter.user.get_effect(EffectType.SYSTEM, "ChromeMission5Tracker").alter_mag(1)
                    else:
                        targeter.user.add_effect(Effect("ChromeMission5Tracker", EffectType.SYSTEM, targeter.user, 280000, lambda eff:"", mag=1, system=True))
                    self.add_effect(Effect("ChromeMission5Marker", EffectType.SYSTEM, targeter.user, 280000, lambda eff:"", system=True))
            if "ruler" in self.scene.missions_to_check:
                if self.has_effect(EffectType.ALL_STUN, "In The Name Of Ruler!"):
                    self.get_effect(EffectType.ALL_STUN, "In The Name Of Ruler!").user.progress_mission(5, 1)
            if self.mission_active("ripple", targeter.user):
                if self.has_effect(EffectType.CONT_PIERCE_DMG, "Night of Countless Stars"):
                    targeter.user.progress_mission(3, 1)
                if self.check_invuln():
                    targeter.user.progress_mission(4, 1)
                if not targeter.user.has_effect(EffectType.SYSTEM, "RippleMission5Tracker"):
                    targeter.user.add_effect(Effect("RippleMission5Tracker", EffectType.SYSTEM, targeter.user, 1, lambda eff:"", mag = 1, system=True))
                else:
                    targeter.user.get_effect(EffectType.SYSTEM, "RippleMission5Tracker").alter_mag(1)
            if self.mission_active("cranberry", targeter.user):
                if targeter.name == "Merciless Finish":
                    targeter.progress_mission(2, 1)
            if self.mission_active("tatsumaki", targeter.user):
                if targeter.name == "Rubble Barrage":
                    targeter.progress_mission(5, 1)
            

    def death_check(self, targeter: "CharacterManager"):
        if self.source.hp <= 0:
            if self.has_effect(
                    EffectType.MARK,
                    "Doping Rampage") and not self.scene.dying_to_doping:
                self.source.hp = 1
                self.progress_mission(4, 1)
            elif self.has_effect(EffectType.MARK, "Electric Rage"):
                self.progress_mission(2, 1)
                self.source.hp = 1
            elif self.has_effect(EffectType.MARK, "Lucky Rabbit's Foot"):
                self.source.hp = 35
                self.get_effect(EffectType.MARK, "Lucky Rabbit's Foot").user.progress_mission(3, 1)
                self.add_effect(Effect("SnowWhiteMission5Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
            else:

                if self.source.name == "esdeath":
                    if not self.has_effect(EffectType.SYSTEM, "EsdeathMission3Failure"):
                        self.add_effect(Effect("EsdeathMission3Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
                if self.has_effect(EffectType.ALL_INVULN, "Crimson Holy Maiden"):
                    for enemy in self.scene.enemy_display.team.character_managers:
                        enemy.full_remove_effect("Crimson Holy Maiden", self)
                    for player in self.scene.player_display.team.character_managers:
                        player.full_remove_effect("Crimson Holy Maiden", self)

                #region Active Killing Blow Mission Check
                self.killing_blow_mission_check(targeter)
                #endregion
                if self.has_effect(EffectType.MARK, "Beast Instinct"):
                    if targeter == self.get_effect(EffectType.MARK,
                                                   "Beast Instinct").user:
                        targeter.receive_eff_healing(20, self.get_effect(EffectType.MARK,
                                                   "Beast Instinct"))
                self.source.hp = 0
                self.source.dead = True
                temp_yatsufusa_storage = None
                if self.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                self.source.clear_effects()
                self.update_effect_region()
                if temp_yatsufusa_storage:
                    self.source.current_effects.append(temp_yatsufusa_storage)
                
                #region Checking for winning killing blow mission progress
                winning_kb = True
                for manager in self.scene.enemy_display.team.character_managers:
                    if not manager.source.dead and manager != self:
                        winning_kb = False
                if winning_kb:
                    if "neji" in self.scene.missions_to_check:
                        if targeter.has_effect(EffectType.ALL_BOOST, "Selfless Genius"):
                            targeter.get_effect(EffectType.ALL_BOOST, "Selfless Genius").user.progress_mission(5, 1)
                    if self.mission_active("ichimaru", targeter):
                        if targeter.has_effect(EffectType.SYSTEM, "IchimaruMission5Tracker"):
                            if targeter.get_effect(EffectType.SYSTEM, "IchimaruMission5Tracker").mag == 3:
                                targeter.progress_mission(5, 1)
                    if "snowwhite" in self.scene.missions_to_check:
                        if targeter.has_effect(EffectType.SYSTEM, "SnowWhiteMission5Tracker"):
                            targeter.get_effect(EffectType.SYSTEM, "SnowWhiteMission5Tracker").user.progress_mission(5, 1)
                    if "nemurin" in self.scene.missions_to_check:
                        if targeter.has_effect(EffectType.ALL_BOOST, "Dream Manipulation"):
                            if targeter.get_effect(EffectType.ALL_BOOST, "Dream Manipulation").user.source.dead:
                                targeter.get_effect(EffectType.ALL_BOOST, "Dream Manipulation").user.progress_mission(4, 1)
                #endregion

        self.scene.dying_to_doping = False

    def last_man_standing(self) -> bool:
        for manager in self.scene.player_display.team.character_managers:
            if manager != self and not manager.source.dead:
                return False
        return True

    def eff_death_check(self, source: Effect):
        if self.source.hp <= 0:
            if self.has_effect(
                    EffectType.MARK,
                    "Doping Rampage") and not self.scene.dying_to_doping:
                self.source.hp = 1
                self.progress_mission(4, 1)
            elif self.has_effect(EffectType.MARK, "Electric Rage"):
                self.source.hp = 1
            elif self.has_effect(EffectType.MARK, "Lucky Rabbit's Foot"):
                self.source.hp = 35
            else:

                if self.source.name == "esdeath":
                    if not self.has_effect(EffectType.SYSTEM, "EsdeathMission3Failure"):
                        self.add_effect(Effect("EsdeathMission3Failure", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))

                #region Effect Killing Blow Mission Check
                
                self.killing_blow_mission_check(source, active_killing_blow=False)

                #endregion
                if self.has_effect(EffectType.MARK, "Beast Instinct"):
                    if source.user == self.get_effect(EffectType.MARK,
                                                   "Beast Instinct").user:
                        source.user.receive_eff_healing(20, self.get_effect(EffectType.MARK,
                                                   "Beast Instinct"))
                self.source.hp = 0
                self.source.dead = True
                temp_yatsufusa_storage = None
                if self.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = self.get_effect(
                        EffectType.MARK, "Yatsufusa")
                self.source.clear_effects()
                self.update_effect_region()
                if temp_yatsufusa_storage:
                    self.source.current_effects.append(temp_yatsufusa_storage)
                
                #region Checking for winning killing blow mission progress

                winning_kb = True
                for manager in self.scene.enemy_display.team.character_managers:
                    if not manager.source.dead and manager != self:
                        winning_kb = False
                if winning_kb:
                    if "neji" in self.scene.missions_to_check:
                        if source.user.has_effect(EffectType.ALL_BOOST, "Selfless Genius"):
                            source.user.get_effect(EffectType.ALL_BOOST, "Selfless Genius").user.progress_mission(5, 1)
                        if source.user.has_effect(EffectType.SYSTEM, "IchimaruMission5Tracker"):
                            if source.user.get_effect(EffectType.SYSTEM, "IchimaruMission5Tracker").mag == 3:
                                source.user.progress_mission(5, 1)
                        if "snowwhite" in self.scene.missions_to_check:
                            if source.user.has_effect(EffectType.SYSTEM, "SnowWhiteMission5Tracker"):
                                source.user.get_effect(EffectType.SYSTEM, "SnowWhiteMission5Tracker").user.progress_mission(5, 1)
                #endregion

        self.scene.dying_to_doping = False



    def check_energy_contribution(self) -> list[int]:
        output = [0, 0, 0, 0, 0]
        output[4] += self.source.energy_contribution
        gen = [
            eff for eff in self.source.current_effects
            if eff.eff_type == EffectType.ENERGY_GAIN
        ]
        for eff in gen:
            negative = False
            if eff.mag < 0:
                negative = True
            energy_type = math.trunc(eff.mag / 10)
            if negative:
                energy_type = energy_type * -1
            mod_value = eff.mag - (energy_type * 10)
            output[energy_type - 1] += mod_value
        return output

    def give_healing(self, healing: int, target: "CharacterManager"):
        #TODO add healing boosts
        mod_healing = healing

        if self.used_ability.name == "Kangaryu":
            if self.has_effect(EffectType.STACK, "Kangaryu"):
                guts = self.get_effect(EffectType.STACK, "Kangaryu")
                if guts.mag >= 5:
                    self.progress_mission(4, 1)
                mod_healing += (
                    20 * guts.mag)

        target.receive_healing(mod_healing, self)

    def receive_healing(self, healing: int, healer: "CharacterManager"):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation

        if self.source.name == "seiryu" and self.source.hp >= 30:
            self.full_remove_effect("Body Modification - Self Destruct", self)

        #region Healing Mission Check
        if self.mission_active("orihime", healer):
            healer.progress_mission(3, mod_healing)
        if self.mission_active("wendy", healer):
            healer.progress_mission(1, mod_healing)
            if healer.used_ability.name == "Sky Dragon's Roar":
                healer.progress_mission(4, mod_healing)
        if self.mission_active("gunha", healer):
            if healer.used_ability.name == "Guts":
                healer.progress_mission(5, mod_healing)
        if self.mission_active("gokudera", healer):
            if healer.used_ability.name == "Sistema C.A.I.":
                healer.progress_mission(2, mod_healing)
        if self.mission_active("ryohei", healer):
            if healer.used_ability.name == "Kangaryu":
                healer.progress_mission(2, mod_healing)
        if self.mission_active("leone", healer):
            healer.progress_mission(1, mod_healing)
        if self.mission_active("nemurin", healer):
            healer.progress_mission(1, mod_healing)

        #endregion

        self.source.hp += mod_healing
        if self.source.hp > 100:
            self.source.hp = 100

    def give_eff_healing(self, healing: int, target: "CharacterManager", source: Effect):
        #TODO add healing boosts
        target.receive_eff_healing(healing, source)

    def receive_eff_healing(self, healing: int, source: Effect):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation

        if self.source.name == "seiryu" and self.source.hp >= 30:
            self.full_remove_effect("Body Modification - Self Destruct", self)

        #region Healing Mission Check
        if self.mission_active("orihime", source.user):
            source.user.progress_mission(3, mod_healing)
        if self.mission_active("leone", source.user):
            source.user.progress_mission(1, mod_healing)
        if self.mission_active("nemurin", source.user):
            source.user.progress_mission(1, mod_healing)
        #endregion

        self.source.hp += mod_healing
        if self.source.hp > 100:
            self.source.hp = 100

    def check_isolated(self) -> bool:
        return any(eff.eff_type == EffectType.ISOLATE
                   for eff in self.source.current_effects)

    def check_invuln(self) -> bool:
        output = False
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_INVULN)
        for eff in gen:
            output = True
            break

        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEF_NEGATE)
        for eff in gen:
            output = False
            break
        return output

    def drain_energy(self, drain: int, targeter: "CharacterManager"):
        #TODO check for immunities
        self.source.energy_contribution -= drain

        #region Drain Mission Check

        if targeter.source.name == "hinata":
            targeter.source.mission1progress += 1

        #endregion

        targeter.check_on_drain(self)


    def special_targeting_exemptions(self,
                                     targeter: "CharacterManager") -> bool:
        target = self
        if targeter.has_effect(EffectType.MARK,
                               "Frozen Castle") and not target.has_effect(
                                   EffectType.UNIQUE, "Frozen Castle"):
            return True
        if not targeter.has_effect(EffectType.MARK,
                                   "Frozen Castle") and target.has_effect(
                                       EffectType.UNIQUE, "Frozen Castle"):
            return True
        if not targeter.has_effect(EffectType.UNIQUE,
                                   "Frozen Castle") and target.has_effect(
                                       EffectType.MARK, "Frozen Castle"):
            return True
        if targeter.has_effect(
                EffectType.UNIQUE,
                "Streets of the Lost") and self != targeter.get_effect(
                    EffectType.UNIQUE, "Streets of the Lost").user:
            return True
        return False

    def hostile_target(self,
                       targeter: "CharacterManager",
                       def_type="NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_invuln()
                        or targeter.has_effect(EffectType.UNIQUE, "Shadow Pin")
                        or self.source.dead or self.source.untargetable
                        or self.special_targeting_exemptions(targeter))
        elif def_type == "BYPASS":
            return not (self.source.dead or targeter.has_effect(
                EffectType.UNIQUE, "Shadow Pin") or self.source.untargetable
                        or self.special_targeting_exemptions(targeter))

    def final_can_effect(self, def_type="NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_invuln() or self.source.dead
                        or self.is_ignoring())
        elif def_type == "REGBYPASS":
            if self.check_bypass_effects():
                return not (self.source.dead)
            else:
                return not (self.source.dead or self.check_invuln())
        elif def_type == "BYPASS":
            return not (self.source.dead or self.is_ignoring())
        elif def_type == "FULLBYPASS":
            return not (self.source.dead)

    def execute_ability(self):
        self.used_ability.execute(self, self.scene.pteam, self.scene.eteam)
        self.check_for_cost_increase_missions()
        self.scene.reset_id()
        self.scene.sharingan_reflector = None
        self.scene.sharingan_reflecting = False
        expected_cd = self.used_ability.cooldown + self.check_for_cooldown_mod(self.used_ability)
        if expected_cd < 0:
            expected_cd = 0
        for ability in self.source.main_abilities:
                    if ability.name == self.used_ability.name:
                        ability.cooldown_remaining = expected_cd + 1
                        break
        for ability in self.source.alt_abilities:
            if ability.name == self.used_ability.name:
                ability.cooldown_remaining = expected_cd + 1
                break
        
    def free_execute_ability(self):
        self.used_ability.execute(self, self.scene.pteam, self.scene.eteam)
        self.check_for_cost_increase_missions()
        self.scene.reset_id()
        self.scene.sharingan_reflector = None
        self.scene.sharingan_reflecting = False
        

    def is_ignoring(self) -> bool:
        for effect in self.source.current_effects:
            if effect.eff_type == EffectType.IGNORE:
                return True
        return False

    def helpful_target(self,
                       targeter: "CharacterManager",
                       def_type="NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_isolated() or self.source.dead
                        or self.special_targeting_exemptions(targeter))
        elif def_type == "BYPASS":
            return not (self.source.dead
                        or self.special_targeting_exemptions(targeter))

    def add_effect(self, effect: Effect):
        stun_types = [EffectType.ALL_STUN, EffectType.SPECIFIC_STUN]

        if not self.has_effect(EffectType.UNIQUE, "Plasma Bomb") or effect.eff_type in stun_types or effect.eff_type == EffectType.SYSTEM or effect.system:
            self.source.current_effects.append(effect)

    def remove_effect(self, effect: Effect):
        new_current_effects: list[Effect] = []
        for eff in self.source.current_effects:
            if not (eff == effect):
                new_current_effects.append(eff)
        self.source.current_effects = new_current_effects

    def full_remove_effect(self, eff_name: str, user: "CharacterManager"):
        new_current_effects: list[Effect] = []
        for eff in self.source.current_effects:
            if not (eff.name == eff_name and eff.user == user):
                new_current_effects.append(eff)
        self.source.current_effects = new_current_effects

    def is_enemy(self) -> bool:
        return self.character_region.x > 400



    def update_effect_region(self):
        self.effect_region.clear()

        x_offset = 27
        y_offset = 27
        max_columns = 4

        for idx, effect_set in enumerate(self.make_effect_clusters().values()):
            (column, row) = (idx // max_columns, idx % max_columns)
            effect_sprite = self.scene.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.scene.get_scaled_surface(effect_set[0].eff_img, 25, 25),
                free=True)
            effect_sprite.effects = effect_set
            effect_sprite.ID = f"{idx}/{self.id}"
            effect_sprite.is_enemy = self.is_enemy()
            self.scene.active_effect_buttons.append(effect_sprite)
            self.scene.add_bordered_sprite(self.effect_region, effect_sprite,
                                           BLACK, row * x_offset,
                                           column * y_offset)


    def is_in_bounds(self) -> bool:
        mouse_x, mouse_y = engine.get_mouse_position()

        bound_x_left = self.scene.current_button.x
        bound_y_up = self.scene.current_button.y
        width, height = self.scene.current_button.size
        bound_x_right = bound_x_left + width
        bound_y_down = bound_y_up + height

        if mouse_x < bound_x_left or mouse_x > bound_x_right or mouse_y < bound_y_up or mouse_y > bound_y_down:
            self.scene.current_button = None
            return False

        return True


    def make_effect_clusters(self) -> dict[str, list[Effect]]:
        output: dict[str, list[Effect]] = {}
        for effect in self.source.current_effects:
            if effect.eff_type == EffectType.DEST_DEF and effect.mag == 0:
                continue
            if effect.invisible == True and effect.user.is_enemy():
                continue
            if effect.system or effect.eff_type == EffectType.SYSTEM:
                continue
            if effect.name in output.keys() and effect.user == output[
                    effect.name][0].user:
                output[effect.name].append(effect)
            else:
                output[effect.name] = []
                output[effect.name].append(effect)
        return output

    def add_current_target(self, target: "CharacterManager"):
        self.current_targets.append(target)

    def set_targeted(self):
        if self.targeted is not True:
            self.targeted = True

    def set_untargeted(self):
        if self.targeted is True:
            self.targeted = False

    def draw_hp_bar(self):
        increment = -1
        if self.source.current_hp != self.source.hp:
            if self.source.current_hp - self.source.hp < 0:
                increment = 1
        else:
            increment = 0
        self.source.current_hp += increment
        if self.source.current_hp == 100:
            hp_bar = self.scene.sprite_factory.from_color(GREEN,
                                                          size=(100, 20))
        elif self.source.current_hp == 0:
            hp_bar = self.scene.sprite_factory.from_color(RED, size=(100, 20))
        else:
            hp_bar = self.scene.sprite_factory.from_color(BLACK,
                                                          size=(100, 20))
            green_bar = self.scene.sprite_factory.from_color(
                GREEN, size=(self.source.current_hp, 20))
            sdl2.surface.SDL_BlitSurface(green_bar.surface, None,
                                         hp_bar.surface,
                                         sdl2.SDL_Rect(0, 0, 0, 0))
            if self.source.current_hp <= 100:
                red_bar = self.scene.sprite_factory.from_color(
                    RED, size=(100 - self.source.current_hp, 20))
                sdl2.surface.SDL_BlitSurface(
                    red_bar.surface, None, hp_bar.surface,
                    sdl2.SDL_Rect(self.source.current_hp + 1, 0, 0, 0))
        hp_text = sdl2.sdlttf.TTF_RenderText_Blended(
            self.scene.font, str.encode(f"{self.source.current_hp}"), BLACK)

        if self.source.current_hp == 100:
            hp_text_x = 38
        elif self.source.current_hp > 9:
            hp_text_x = 42
        else:
            hp_text_x = 46

        sdl2.surface.SDL_BlitSurface(hp_text, None, hp_bar.surface,
                                     sdl2.SDL_Rect(hp_text_x, 0, 0, 0))
        self.scene.add_bordered_sprite(self.hp_bar_region, hp_bar, BLACK, 0, 0)

    def refresh_character(self, enemy=False):
        if self.source.hp <= 0:
            self.source.dead = True
        self.acted = False
        self.current_targets.clear()
        self.received_ability.clear()
        self.used_ability = None
        self.set_untargeted()
        self.targeting = False
        for ability in self.source.current_abilities:
            ability.reset_cooldown()
        if self.scene.player:
            if enemy:
                self.update_limited()
            else:
                self.update()

    def add_received_ability(self, ability: Ability):
        self.received_ability.append(ability)

    def update(self, x: int = 0, y: int = 0):
        self.character_region.clear()
        self.update_profile(x, y)
        self.adjust_ability_costs()
        self.update_ability()
        self.update_targeted_sprites()
        self.update_text()
        self.update_effect_region()
        self.draw_hp_bar()

    def update_limited(self, x: int = 0, y: int = 0):
        self.character_region.clear()
        self.adjust_ability_costs()
        self.update_enemy_profile(x, y)
        self.update_targeted_sprites()
        self.update_effect_region()
        self.draw_hp_bar()

    def erza_requip(self):
        if self.has_effect(EffectType.MARK, "Clear Heart Clothing"):
            self.full_remove_effect("Clear Heart Clothing", self)
            self.full_remove_effect("Titania's Rampage", self)
            for manager in self.scene.player_display.team.character_managers:
                manager.full_remove_effect("Clear Heart Clothing", self)
                manager.full_remove_effect("Titania's Rampage", self)
            for manager in self.scene.enemy_display.team.character_managers:
                manager.full_remove_effect("Clear Heart Clothing", self)
                manager.full_remove_effect("Titania's Rampage", self)
        if self.has_effect(EffectType.MARK, "Heaven's Wheel Armor"):
            self.full_remove_effect("Heaven's Wheel Armor", self)
            self.full_remove_effect("Circle Blade", self)
        if self.has_effect(EffectType.MARK, "Nakagami's Armor"):
            self.full_remove_effect("Nakagami's Armor", self)
        if self.has_effect(EffectType.MARK, "Adamantine Armor"):
            self.full_remove_effect("Adamantine Armor", self)
        self.check_ability_swaps()

    def check_profile_swaps(self):
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.PROF_SWAP)
        for eff in gen:
            if eff.mag == 1:
                
                self.profile_sprite.surface = self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces[self.source.name +
                                                    "altprof1"])
            elif eff.mag == 2:
                self.profile_sprite.surface = self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces[self.source.name +
                                                      "altprof2"])
        

    def check_enemy_profile_swaps(self):
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.PROF_SWAP)
        for eff in gen:
            if eff.mag == 1:
                self.profile_sprite.surface = self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces[self.source.name +
                                                    "altprof1"])
            elif eff.mag == 2:
                self.profile_sprite.surface = self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces[self.source.name +
                                                      "enemyaltprof2"])

    def update_profile(self, x: int = 0, y: int = 0):
        self.character_region.add_sprite(
            self.scene.sprite_factory.from_surface(
                self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces["banner"],
                    width=640,
                    height=150),
                free=True), 100, -27)
        self.profile_sprite.surface = self.scene.get_scaled_surface(
            self.scene.scene_manager.surfaces[self.source.name + "allyprof"])
        self.check_profile_swaps()
        
        
        self.scene.add_sprite_with_border(self.character_region,
                                          self.profile_sprite,
                                          self.profile_border, x, y)
        if self.targeted:
            self.character_region.add_sprite(self.selected_filter, 0, 0)

    def update_enemy_profile(self, x: int = 0, y: int = 0):

        self.profile_sprite.surface = self.scene.get_scaled_surface(
            self.scene.scene_manager.surfaces[self.source.name + "enemyprof"])
        self.check_enemy_profile_swaps()

        self.scene.add_bordered_sprite(self.character_region,
                                       self.profile_sprite, BLACK, x, y)
        if self.targeted:
            self.character_region.add_sprite(self.selected_filter, 0, 0)

    def update_targeted_sprites(self):
        vertical_offset = 12
        for idx, ability in enumerate(self.received_ability):
            target_sprite = self.scene.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.scene.get_scaled_surface(ability.image, 25, 25))
            target_sprite.idx = idx
            target_sprite.click += self.target_sprite_click
            self.scene.add_bordered_sprite(
                self.targeting_region, target_sprite, BLACK, 0,
                (vertical_offset * idx) + (idx * 25))

    def target_sprite_click(self, button, _sender):
        play_sound(self.scene.scene_manager.sounds["undo"])
        self.scene.remove_targets(self.received_ability[button.idx])

    def profile_click(self, _button, _sender):
        if self.scene.selected_ability is not None and self.targeted:
            play_sound(self.scene.scene_manager.sounds["select"])
            self.scene.target_clicked = True
            self.scene.expend_energy(self.scene.selected_ability)
            self.scene.apply_targeting(self)
            self.scene.return_targeting_to_default()
        self.scene.full_update()

    def detail_click(self, _button, _sender):
        if self.character_region.x > 400 and not self.scene.target_clicked:
            play_sound(self.scene.scene_manager.sounds["select"])
            self.scene.enemy_detail_character = self.source
            self.scene.enemy_detail_ability = None
            self.scene.full_update()

    def set_selected_ability(self, button, _sender):
        if not self.scene.window_up:
            play_sound(self.scene.scene_manager.sounds["click"])
            self.selected_ability = button.ability
            self.selected_button = button
            self.scene.reset_targeting()
            if button.ability.can_use(self.scene, self) and not self.acted:
                self.scene.selected_ability = button.ability
                self.scene.acting_character = self
                button.ability.target(
                    self, self.scene.player_display.team.character_managers,
                    self.scene.enemy_display.team.character_managers)
            else:
                self.scene.selected_ability = None
                self.scene.acting_character = None
            self.scene.full_update()

    def check_ability_swaps(self):
        self.source.current_abilities = [
            ability for ability in self.source.main_abilities
        ]
        if self.scene.player:
            self.current_ability_sprites = [
                sprite for sprite in self.main_ability_sprites
            ]
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ABILITY_SWAP)
        for eff in gen:
            swap_from = eff.mag // 10
            swap_to = eff.mag - (swap_from * 10)
            if self.scene.player:
                self.current_ability_sprites[swap_from -
                                         1] = self.alt_ability_sprites[swap_to
                                                                       - 1]
            self.source.current_abilities[
                swap_from - 1] = self.source.alt_abilities[swap_to - 1]
        if self.scene.player:
            for i, sprite in enumerate(self.current_ability_sprites):
                sprite.ability = self.source.current_abilities[i]

    def update_ability(self):

        self.check_ability_swaps()
        self.adjust_targeting_types()

        for i, button in enumerate(self.current_ability_sprites):
            self.scene.add_sprite_with_border(self.character_region, button,
                                              button.border, 150 + (i * 140),
                                              0)

            if self.scene.selected_ability and button.ability.name == self.scene.selected_ability.name:
                self.character_region.add_sprite(button.selected_pane,
                                                 150 + (i * 140), 0)
            else:
                if not button.ability.can_use(self.scene, self) or self.acted or not self.is_controllable():
                    if button.ability.cooldown_remaining > 0:
                        button.null_pane.surface = self.scene.get_scaled_surface(
                            self.scene.scene_manager.surfaces["locked"])
                        button.null_pane.surface = self.stamp_cooldown(
                            button.ability.cooldown_remaining,
                            button.null_pane.surface)
                        self.character_region.add_sprite(
                            button.null_pane, 150 + (i * 140), 0)
                    else:
                        button.null_pane.surface = self.scene.get_scaled_surface(
                            self.scene.scene_manager.surfaces["locked"])
                        self.character_region.add_sprite(
                            button.null_pane, 150 + (i * 140), 0)

    def stamp_cooldown(self, cooldown: int,
                       surface: sdl2.SDL_Surface) -> sdl2.SDL_Surface:
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.scene.cooldown_font, str.encode(f"{cooldown}"), BLACK)
        sdl2.surface.SDL_BlitSurface(text_surface, None, surface,
                                     sdl2.SDL_Rect(25, -20, 0, 0))
        return surface


def make_battle_scene(scene_manager) -> BattleScene:

    scene = BattleScene(scene_manager, sdl2.ext.SOFTWARE)

    return scene