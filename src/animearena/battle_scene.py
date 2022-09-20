from os import rename
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import itertools
import textwrap
from animearena import engine
from animearena.character import Character, get_character_db
from animearena.ability import Ability, Target, DamageType, rename_i_reject
from animearena.color import TRANSPARENT
from animearena.energy import Energy
from animearena.effects import Effect, EffectType
from animearena.player import Player
from animearena.character_manager import CharacterManager
from random import randint
from playsound import playsound
from pathlib import Path
from typing import Optional
import typing
import logging
from animearena.mission_handler import MissionHandler
from animearena.turn_timer import TurnTimer
from animearena.resource_manager import init_font
from animearena.color import *
from animearena.text_formatter import get_font_height, get_lines, get_string_width
import random
if typing.TYPE_CHECKING:
    from animearena.scene_manager import SceneManager

FONTSIZE = 16
COOLDOWN_FONTSIZE = 80
STACK_FONTSIZE = 25
LARGE_STACK_FONTSIZE = 20
HUGE_STACK_FONTSIZE = 16
TIMER_FONTSIZE = 100

def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass



class AbilityMessage:

    user_id: int
    ability_id: int
    ally_targets: list[int]
    enemy_targets: list[int]
    primary_id: int

    def __init__(self, manager: Optional["CharacterManager"] = None):
        self.ally_targets = list()
        self.enemy_targets = list()
        if manager:
            self.user_id = manager.char_id
            for i, ability in enumerate(manager.source.current_abilities):
                if ability.name == manager.used_ability.name:
                    self.ability_id = i
            if manager.primary_target:
                if manager.primary_target.id == "ally":
                    self.primary_id = manager.primary_target.char_id
                elif manager.primary_target.id == "enemy":
                    self.primary_id = manager.primary_target.char_id + 3
            else:
                self.primary_id = 69
            for target in manager.current_targets:
                if target.id == "ally":
                    self.ally_targets.append(target.char_id)
                if target.id == "enemy":
                    self.enemy_targets.append(target.char_id)

    def assign_user_id(self, user_id: int):
        self.user_id = user_id

    def assign_ability_id(self, ability_id: int):
        self.ability_id = ability_id

    def add_to_ally_targets(self, target_id: int):
        self.ally_targets.append(target_id)

    def add_to_enemy_targets(self, target_id: int):
        self.enemy_targets.append(target_id)
    
    def set_primary_target(self, target_id: int):
        self.primary_id = target_id


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
                                                       y=115,
                                                       width=670,
                                                       height=390)
        self.character_regions = [
            self.team_region.subregion(x=0, y=i * 155, width=670, height=130)
            for i in range(3)
        ]
        for region in self.character_regions:
            region.add_sprite(
                self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces["banner"]), 5, 5)
        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.text_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.character_regions:
            self.effect_regions.append(region.subregion(135, 95, 0, 25))
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
                                                        y=140,
                                                        width=130,
                                                        height=750)
        self.enemy_regions = [
            self.enemy_region.subregion(x=0, y=i * 155, width=130, height=230)
            for i in range(3)
        ]

        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.enemy_regions:
            self.effect_regions.append(region.subregion(-32, 100, 0, 25))
            self.targeting_regions.append(
                region.subregion(x=-32, y=0, width=25, height=100))
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
    timer_region: engine.Region
    timer: TurnTimer
    ally_energy_pool: dict[Energy, int]
    enemy_energy_pool: dict[Energy, int]
    offered_pool: dict[Energy, int]
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
    execution_order: list[int]
    sharingan_reflector: Optional["CharacterManager"]
    sharingan_reflected_effects: list[Effect]
    sharingan_reflected_effect_ticking: bool
    target_clicked: bool
    missions_to_check: list[str]
    active_effect_buttons: list
    acting_order: list["CharacterManager"]
    ability_messages: list["AbilityMessage"]
    scene_manager: "SceneManager"
    random_spent: list
    catching_up: bool
    d20: random.Random
    collapsing_ally_inviolate_shield: bool
    collapsing_enemy_inviolate_shield: bool
    
    @property
    def pteam(self):
        return self.player_display.team.character_managers

    @property
    def eteam(self):
        return self.enemy_display.team.character_managers

    @property
    def ally_energy_pool(self):
        return self.player_display.team.energy_pool

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dying_to_doping = False
        self.catching_up = False
        self.collapsing_ally_inviolate_shield = False
        self.collapsing_enemy_inviolate_shield = False
        self.d20 = random.Random()
        self.ability_messages = list()
        self.timer = TurnTimer(1, self.empty_placeholder)
        self.random_spent = [0, 0, 0, 0]
        self.window_closing = False
        self.waiting_for_turn = True
        self.first_turn = True
        self.execution_order = list()
        self.dragging_order_button = False
        self.dragging_button = False
        self.cont_list = list()
        self.acting_order = list()
        self.cont_storage = dict()
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
        self.large_stack_font = init_font(LARGE_STACK_FONTSIZE)
        self.huge_stack_font = init_font(HUGE_STACK_FONTSIZE)
        self.timer_font = init_font(TIMER_FONTSIZE)
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
        self.surrender_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (150, 50))
        self.surrender_button = self.render_bordered_text(self.font, "SURRENDER", WHITE, BLACK, self.surrender_button, 34, 13, 1)
        self.surrender_button = self.border_sprite(self.surrender_button, AQUA, 2)
        self.surrender_button.click += self.click_surrender_button
        self.player_panel = self.sprite_factory.from_color(WHITE, (200, 100))
        self.player_panel_border = self.sprite_factory.from_color(
            BLACK, (204, 104))
        self.enemy_panel = self.sprite_factory.from_color(WHITE, (200, 100))
        self.enemy_panel_border = self.sprite_factory.from_color(
            BLACK, (204, 104))
        
        label_background = self.sprite_factory.from_color(MENU_TRANSPARENT, (150, 50))
        self.waiting_label = self.render_bordered_text(self.font, "OPPONENT'S TURN", WHITE, BLACK, label_background, 10, 14, 1)
        self.waiting_label = self.border_sprite(self.waiting_label, AQUA, 2)
        label_background = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (150, 50))
        self.turn_label = self.render_bordered_text(self.font, "PRESS WHEN READY", WHITE, BLACK, label_background, 6, 14, 1)
        self.turn_label = self.border_sprite(self.turn_label, AQUA, 2)
        self.turn_label.click += self.turn_end_button_click
        
        
        self.turn_end_region = self.region.subregion(x=375,
                                                     y=5,
                                                     width=150,
                                                     height=200)
        self.turn_expend_region = self.region.subregion(x=250,
                                                        y=225,
                                                        width=400,
                                                        height=250)
        
        self.player_region = self.region.subregion(2, 2, 100, 100)
        self.enemy_region = self.region.subregion(793, 2, 100, 100)
        self.surrender_button_region = self.region.subregion(725, 625, 0, 0)
        self.enemy_info_region = self.region.subregion(5, 578, 670, 120)
        self.hover_effect_region = self.region.subregion(0, 0, 0, 0)
        self.game_end_region = self.region.subregion(60, 207, 781, 484)
        self.timer_region = self.region.subregion(x=269, y=95, width=362, height=12)
        self.energy_region = self.region.subregion(x=300,
                                                   y=60,
                                                   width=300,
                                                   height=30)

    #region On-Click event handlers

    def enemy_info_profile_click(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.enemy_detail_ability = None
        self.draw_enemy_info_region()

    def draw_ability_info(self, ability):
        self.enemy_detail_ability = ability
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
            self.scene_manager.connection.send_surrender(
                self.get_enemy_mission_progress_packages())
            self.lose_game()

    def ingest_mission_packages(self, packages):

        for i, package in enumerate(packages):
            self.player_display.team.character_managers[
                i].source.mission1progress = package[0]
            self.player_display.team.character_managers[
                i].source.mission2progress = package[1]
            self.player_display.team.character_managers[
                i].source.mission3progress = package[2]
            self.player_display.team.character_managers[
                i].source.mission4progress = package[3]
            self.player_display.team.character_managers[
                i].source.mission5progress = package[4]

    def get_enemy_mission_progress_packages(self) -> list[list[int]]:
        output = []
        for manager in self.enemy_display.team.character_managers:
            mission_progress_package = [
                manager.source.mission1progress,
                manager.source.mission2progress,
                manager.source.mission3progress,
                manager.source.mission4progress,
                manager.source.mission5progress
            ]
            output.append(mission_progress_package)
        return output

    def confirm_button_click(self, _button, _sender):
        
        self.execution_loop()

        for attr, i in self.offered_pool.items():
            if attr < 4:
                self.random_spent[attr] = i
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
        self.execution_order.clear()
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

            # if self.round_any_cost == 0:
            #     play_sound(self.scene_manager.sounds["turnend"])
            #     self.execution_loop()
            #     self.turn_end()
            # else:
            self.window_up = True
            self.get_execution_order_base("ally")
            self.draw_any_cost_expenditure_window()

    def exchange_accept_click(self, button, sender):
        self.has_exchanged = True
        play_sound(self.scene_manager.sounds["click"])
        self.player_display.team.energy_pool[Energy(
            self.traded_away_energy)] -= 2
        self.player_display.team.energy_pool[Energy(
            self.traded_for_energy)] += 1
        self.random_spent[Energy(self.traded_away_energy)] += 2
        self.random_spent[Energy(self.traded_for_energy)] -= 1
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

            panel_width = 270
            if 10 + get_string_width(16, self.current_button.effects[0].name) > panel_width:
                panel_width += (10 + get_string_width(16, self.current_button.effects[0].name) - panel_width)
            effect_spacing = 6
            line_height = get_font_height(16)
            base_height = 15 + line_height
            height = base_height
            for effect in self.current_button.effects:
                height += effect_spacing
                height += line_height
                height += (line_height * len(get_lines(effect.get_desc(), 260, 16)))
                
            line_height = get_font_height(16)
            hover_panel_sprite = self.sprite_factory.from_color(
                MENU,
                size=(panel_width, height))
            mouse_x, mouse_y = engine.get_mouse_position()
            self.hover_effect_region.x = mouse_x - hover_panel_sprite.size[
                0] if self.current_button.is_enemy else mouse_x
            if self.current_button.y > 600:
                self.hover_effect_region.y = mouse_y - base_height
            else:
                self.hover_effect_region.y = mouse_y
            hover_panel_sprite = self.border_sprite(hover_panel_sprite, AQUA, 2)
            
            
            hover_panel_sprite = self.draw_effect_lines(self.current_button.effects, hover_panel_sprite)
            self.hover_effect_region.add_sprite(hover_panel_sprite, 0, 0)

    def draw_effect_lines(self, effect_list: list[Effect], panel):

        panel = self.render_bordered_text(self.font, effect_list[0].name, AQUA, BLACK, panel, 5, 5, 1, flow=True, target_width=panel.size[0] - 10, fontsize=16)
        
        y_offset = 5
        line_height = get_font_height(16)
        lines = 1
        effect_spacing = 6
        current_y = y_offset + effect_spacing
        
        
        
        for i, effect in enumerate(effect_list):
            
            panel = self.add_horizontal_line(panel, AQUA, 2, panel.size[0], (0, current_y + (effect_spacing * i) + (line_height * lines) - 2))
            
            duration_width = get_string_width(16, self.get_duration_string(effect.duration))
            panel = self.render_bordered_text(self.font, self.get_duration_string(effect.duration), RED, BLACK, panel, 260 - duration_width, current_y + (effect_spacing * i) + (line_height * lines), 1)
            lines += 1
            for line in get_lines(effect.get_desc(), panel.size[0] - 10, 16):
                panel = self.render_bordered_text(self.font, line, WHITE, BLACK, panel, 5, current_y + (effect_spacing * i) + (lines * line_height), 1)
                lines += 1
            

        return panel

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

    def draw_timer_region(self):
        self.timer_region.clear()
        bar_height = self.timer_region.size()[1] - 2
        bar_width = self.timer_region.size()[0] - 2
        self.timer_region.add_sprite(self.sprite_factory.from_color(AQUA, size=(self.timer_region.size())), 0, 0)
        self.timer_region.add_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, size=(bar_width, bar_height)), 1, 1)
        if self.timer and self.timer.time_left > 0:
            self.timer_region.add_sprite(self.sprite_factory.from_color(DULL_AQUA, size=(self.timer.time_left * 4, bar_height)), 1, 1)

    def draw_enemy_info_region(self):
        self.enemy_info_region.clear()
        if self.enemy_detail_character and not self.enemy_detail_ability:
            ability_count = len(
                self.enemy_detail_character.main_abilities) + len(
                    self.enemy_detail_character.alt_abilities)
            width = 10 + 90 + (65 * ability_count)
            enemy_info_panel = self.sprite_factory.from_color(
                MENU_TRANSPARENT, (width, 120))
            enemy_info_panel = self.border_sprite(enemy_info_panel, AQUA, 2)
            self.enemy_info_region.add_sprite(enemy_info_panel, 0, 0)
        elif self.enemy_detail_character and self.enemy_detail_ability:
            enemy_info_panel = self.sprite_factory.from_color(
                MENU_TRANSPARENT, (670, 120))
            enemy_info_panel = self.border_sprite(enemy_info_panel, AQUA, 2)
            
            ability_description = self.enemy_detail_ability.name + ": " + self.enemy_detail_ability.desc
            #width 500
            height = get_font_height(16) * len(get_lines(ability_description, 500, 16))
            enemy_info_panel = self.render_bordered_text(self.font, ability_description, WHITE, BLACK, enemy_info_panel, 165, (120 - height) // 2, 1, flow=True, target_width=500, fontsize=16)
            enemy_info_panel = self.add_ability_details_to_enemy_info(self.enemy_detail_ability, enemy_info_panel)
            self.enemy_info_region.add_sprite(enemy_info_panel, 0, 0)

            
        if self.enemy_detail_character and not self.enemy_detail_ability:
            profile_sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[
                    self.enemy_detail_character.name + "allyprof"],
                                        width=90,
                                        height=90),
                free=True)
            self.add_bordered_sprite(self.enemy_info_region, profile_sprite,
                                     BLACK, 5, 15)
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
                                         100 + (ability_count * 65), 30)
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
                                         100 + (ability_count * 65), 30)
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
                                     BLACK, 5, 15)
            ability_sprite = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces[
                    self.enemy_detail_ability.db_name],
                                        width=60,
                                        height=60),
                free=True)
            self.add_bordered_sprite(self.enemy_info_region, ability_sprite,
                                     BLACK, 100, 30)
            

    def add_ability_details_to_enemy_info(self, ability: Ability, panel):
        if ability.total_base_cost > 0:
            cost_to_display: list[Energy] = sorted(ability.cost_iter())
            for i, energy in enumerate(cost_to_display):
                energy_image = self.get_scaled_surface(self.scene_manager.surfaces[energy.name], 13, 13)
                sdl2.SDL_BlitSurface(energy_image, None, panel.surface, sdl2.SDL_Rect(105 + (i * 17), 12))
                sdl2.SDL_FreeSurface(energy_image)

        else:
            panel = self.render_bordered_text(self.font, "No Cost", WHITE, BLACK, panel, 105, 12, 1)
        
        panel = self.render_bordered_text(self.font, "CD: " + str(ability.cooldown), WHITE, BLACK, panel, 105, 95, 1)
        
        return panel

    def draw_surrender_region(self):
        self.surrender_button_region.clear()
        self.surrender_button_region.add_sprite(self.surrender_button, 0, 0)

    def draw_player_region(self):
        self.player_region.clear()
        if self.player:
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

    def draw_enemy_region(self):
        self.enemy_region.clear()
        if self.enemy:
            enemy_ava = self.sprite_factory.from_surface(
                self.get_scaled_surface(self.enemy.avatar))
            self.add_bordered_sprite(self.enemy_region, enemy_ava, BLACK, 0,
                                     5)
            name_width = int(len(self.enemy.name) * 11.2) + 5
            transparent_box = self.sprite_factory.from_color(TRANSPARENT, (name_width, 50))
            name_panel = self.render_bordered_text(self.stack_font, self.enemy.name, RED, BLACK, transparent_box, 0, 0, thickness=2)
            self.enemy_region.add_sprite(name_panel, -name_width, 0)
            if not self.enemy.clan:
                transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
                clan_panel = self.render_bordered_text(self.font, "Clanless", WHITE, BLACK, transparent_box, 0, 0, thickness=1)
                clan_width = int(len("Clanless") * 7.3) + 5
                self.enemy_region.add_sprite(clan_panel, -clan_width, 58)
            else:
                pass
            transparent_box = self.sprite_factory.from_color(TRANSPARENT, (200, 50))
            title_panel = self.render_bordered_text(self.font, self.enemy.title, WHITE, BLACK, transparent_box, 0, 0, thickness=1)
            title_width = int(len(self.enemy.title) * 7.3) + 5
            self.enemy_region.add_sprite(title_panel, -title_width, 38)
            

    def draw_turn_end_region(self):
        self.turn_end_region.clear()
        
        if self.waiting_for_turn:
            self.turn_end_region.add_sprite(self.waiting_label, 0, 0)
        else:
            self.turn_end_region.add_sprite(self.turn_label, 0, 0)
        self.draw_timer_region()



    def draw_any_cost_expenditure_window(self):
        self.turn_expend_region.clear()
        any_cost_panel = self.sprite_factory.from_color(MENU, size=(400, 250))
        any_cost_panel = self.border_sprite(any_cost_panel, AQUA, 2)
        self.turn_expend_region.add_sprite(any_cost_panel, 0, 0)
        
        self.render_bordered_text(self.font, f"Assign {self.round_any_cost} colorless energy", WHITE, BLACK, any_cost_panel, 115, 5, 1)
        self.render_bordered_text(self.font, f"Energy Pool", WHITE, BLACK, any_cost_panel, 20, 30, 1)
        self.render_bordered_text(self.font, f"Physical", WHITE, BLACK, any_cost_panel, 20, 60, 1)
        self.render_bordered_text(self.font, f"Special", WHITE, BLACK, any_cost_panel, 20, 85, 1)
        self.render_bordered_text(self.font, f"Mental", WHITE, BLACK, any_cost_panel, 20, 110, 1)
        self.render_bordered_text(self.font, f"Weapon", WHITE, BLACK, any_cost_panel, 20, 135, 1)
        self.render_bordered_text(self.font, f"Physical", WHITE, BLACK, any_cost_panel, 275, 60, 1)
        self.render_bordered_text(self.font, f"Special", WHITE, BLACK, any_cost_panel, 275, 85, 1)
        self.render_bordered_text(self.font, f"Mental", WHITE, BLACK, any_cost_panel, 275, 110, 1)
        self.render_bordered_text(self.font, f"Weapon", WHITE, BLACK, any_cost_panel, 275, 135, 1)
        self.render_bordered_text(self.font, f"Colorless Offered", WHITE, BLACK, any_cost_panel, 275, 30, 1)
        if self.round_any_cost == 0:
            confirm_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (60, 30))
            confirm_button = self.border_sprite(confirm_button, AQUA, 2)
            confirm_button = self.render_bordered_text(self.font, "OK", WHITE, BLACK, confirm_button, 20, 4, 1)
            confirm_button.click += self.confirm_button_click
            self.turn_expend_region.add_sprite(confirm_button, x=135, y=165)
        
        cancel_button = self.ui_factory.from_color(sdl2.ext.BUTTON, DULL_AQUA, (60, 30))
        cancel_button = self.border_sprite(cancel_button, AQUA, 2)
        cancel_button = self.render_bordered_text(self.font, "Cancel", WHITE, BLACK, cancel_button, 8, 3, 1)
        cancel_button.click += self.any_expenditure_cancel_click
        self.turn_expend_region.add_sprite(cancel_button, x=205, y=165)
        
        any_cost_panel = self.draw_energy_rows(any_cost_panel)
        
        self.draw_execution_order_region()
        
    def draw_execution_order_region(self):
        
        for i, eff in enumerate(self.execution_order):
            if self.dragging_order_button and self.dragging_button.index == i:
                continue
            if eff < 3:
                img = self.pteam[eff].used_ability.image
                source = self.pteam[eff].used_ability
            else:
                img = self.cont_list[eff - 3].source.image
                source = self.cont_list[eff - 3]

            order_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(img, 25, 25), free=True)
            
            order_button.pressed += self.order_button_press
            order_button.index = i
            order_button.source = source
            self.add_bordered_sprite(self.turn_expend_region, order_button, BLACK, 5 + (i * 33), 215)
        if self.dragging_order_button:
            eff = self.execution_order[self.dragging_button.index]
            if eff < 3:
                img = self.pteam[eff].used_ability.image
            else:
                img = self.cont_list[eff - 3].source.image
            dragging_button = self.sprite_factory.from_surface(self.get_scaled_surface(img, 25, 25), free=True)
            self.add_bordered_sprite(self.turn_expend_region, dragging_button, BLACK, self.scene_manager.mouse_x - 12 - self.turn_expend_region.x - 5, 215)
        
    def check_swapped_order(self):
        SWAP_POINT = 13
        MOUSE_X = self.scene_manager.mouse_x - self.turn_expend_region.x - 5
        #origin point for dragged button is halfway through its original spot
        ORIGIN_X = self.dragging_button.index * 33 + 5 + 12
        LEFT_NEIGHBOR_X = ORIGIN_X - SWAP_POINT - 8
        RIGHT_NEIGHBOR_X = ORIGIN_X + SWAP_POINT
        # if our current mouse x enters the halfway point of another button, swap them!
        # things to check for: are we before or after the origin X?
        #                      is there actually something to swap with in that direction?
        
        if MOUSE_X > ORIGIN_X and len(self.execution_order) - 1 > self.dragging_button.index:
            if MOUSE_X > RIGHT_NEIGHBOR_X:
                swap = self.execution_order[self.dragging_button.index]
                logging.debug("Swap is %d", swap)
                self.execution_order[self.dragging_button.index] = self.execution_order[self.dragging_button.index + 1]
                logging.debug("Current index is %d", self.execution_order[self.dragging_button.index])
                self.execution_order[self.dragging_button.index + 1] = swap
                logging.debug("Right index is %d", self.execution_order[self.dragging_button.index + 1])
                self.dragging_button.index += 1
        elif MOUSE_X < ORIGIN_X and self.dragging_button.index != 0:
            if MOUSE_X < LEFT_NEIGHBOR_X:
                swap = self.execution_order[self.dragging_button.index]
                self.execution_order[self.dragging_button.index] = self.execution_order[self.dragging_button.index - 1]
                self.execution_order[self.dragging_button.index - 1] = swap
                self.dragging_button.index -= 1
        logging.debug(self.execution_order)
        

    def order_button_press(self, button, _sender):
        self.dragging_order_button = True
        self.dragging_button = button
        self.draw_any_cost_expenditure_window()
        
    def get_execution_order_base(self, team: str):
        self.cont_list.clear()
        self.cont_storage.clear()
        self.execution_order.clear()
        for i, manager in enumerate(self.pteam):
            for eff in manager.source.current_effects:
                if eff.continuous() and eff.user_id == team:
                    if not self.cont_storage.setdefault(eff.signature, False):
                        self.cont_list.append(eff)
                        self.cont_storage[eff.signature] = [i]
                    else:
                        self.cont_storage[eff.signature].append(i)
        for i, manager in enumerate(self.eteam):
            for eff in manager.source.current_effects:
                if eff.continuous() and eff.user_id == team:
                    if not self.cont_storage.setdefault(eff.signature, False):
                        self.cont_list.append(eff)
                        self.cont_storage[eff.signature] = [i + 3]
                    else:
                        self.cont_storage[eff.signature].append(i + 3)
        for i, eff in enumerate(self.cont_list):
            self.execution_order.append(i + 3)
        for manager in self.acting_order:
            self.execution_order.append(manager.char_id)
        logging.debug(self.cont_storage)

    def draw_energy_rows(self, panel):

        plus_button_x = 180
        minus_button_x = 150
        current_pool_x = 130
        offered_pool_x = 210
        left_buffer = 20
        top_buffer = 60
        vertical_spacing = 25
        
        for i in range(4):
            self.turn_expend_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[Energy(i).name])), 110, top_buffer + (i * vertical_spacing) + 7)
            
            plus_button = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces["add"]))
            plus_button.energy = Energy(i)
            plus_button.click += self.plus_button_click
            minus_button = self.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.get_scaled_surface(self.scene_manager.surfaces["remove"]))
            minus_button.energy = Energy(i)
            minus_button.click += self.minus_button_click

            self.turn_expend_region.add_sprite(plus_button, plus_button_x, top_buffer + (i * vertical_spacing) + 3)
            self.turn_expend_region.add_sprite(minus_button, minus_button_x, top_buffer + (i * vertical_spacing) + 3)
            
            
            panel = self.render_bordered_text(self.font, f"{self.player_display.team.energy_pool[Energy(i)]}", WHITE, BLACK, panel, current_pool_x, top_buffer + (i * vertical_spacing), 1)
            panel = self.render_bordered_text(self.font, f"{self.offered_pool[Energy(i)]}", WHITE, BLACK, panel, offered_pool_x, top_buffer + (i * vertical_spacing), 1)
            
            self.turn_expend_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.scene_manager.surfaces[Energy(i).name])), 230, top_buffer + (i * vertical_spacing) + 7)


    def draw_effect_hover(self):
        self.hover_effect_region.clear()
        if self.current_button is not None:
            self.show_hover_text()

    #endregion

    def check_for_hp_bar_changes(self):
        for manager in self.pteam:
            if manager.source.hp != manager.source.current_hp:
                manager.draw_hp_bar()
        for manager in self.eteam:
            if manager.source.hp != manager.source.current_hp:
                manager.draw_hp_bar()

    def start_timer(self, time: int = 90) -> TurnTimer:
        if self.timer:
            self.timer.cancel()
        return TurnTimer(time, self.empty_placeholder)

    def empty_placeholder(self):
        pass

    def handle_reconnection_catchup(self, first_turn: bool,
                                    stored_turns: list[list["AbilityMessage"]], execution_order: list[list[int]],
                                    energy_pools: list[list[int]], all_random_expenditure: list[list[int]], time_remaining: int):

        self.catching_up = True
        for manager in self.pteam:
            manager.selected_ability = manager.source.current_abilities[0]
            manager.selected_button = manager.current_ability_sprites[0]

        if not stored_turns:
            self.waiting_for_turn = not first_turn
            self.catching_up = False
            self.moving_first = first_turn
            if not self.waiting_for_turn:
                self.timer = self.start_timer(time_remaining)
            self.full_update()
        else:
            self.waiting_for_turn = True
            if first_turn:
                self.player_catchup_execution(stored_turns, execution_order, energy_pools, all_random_expenditure, time_remaining)
            else:
                self.enemy_catchup_execution(stored_turns, execution_order, energy_pools, all_random_expenditure, time_remaining)

    def player_catchup_execution(self, stored_turns: list[list["AbilityMessage"]], execution_order: list[list[int]], energy_pools: list[list[int]], all_random_expenditure: list[list[int]], time_remaining: int):
        current_turn = stored_turns[0]
        stored_turns = stored_turns[1:]
        current_execution_order = execution_order[0]
        execution_order = execution_order[1:]
        current_random_expenditure = all_random_expenditure[0]
        all_random_expenditure = all_random_expenditure[1:]
        for ability in current_turn:
            
            self.pteam[ability.user_id].acted = True
            self.pteam[ability.user_id].used_ability = self.pteam[
                ability.user_id].source.current_abilities[ability.ability_id]

            if ability.primary_id != 69:
                if ability.primary_id < 3:
                    self.pteam[ability.user_id].primary_target = self.pteam[ability.primary_id]
                else:
                    self.pteam[ability.user_id].primary_target = self.eteam[ability.primary_id - 3]

            for num in ability.ally_targets:
                self.pteam[ability.user_id].current_targets.append(
                    self.pteam[num])

            for num in ability.enemy_targets:
                self.pteam[ability.user_id].current_targets.append(
                    self.eteam[num])

        self.get_execution_order_base("ally")
        
        for action in current_execution_order:
            
            if action < 3:
                if self.pteam[action].acted:
                    self.pteam[action].execute_ability()
                    self.pteam[action].acted = False
                    self.pteam[action].current_targets.clear()
                    self.pteam[action].primary_target = None
                    for i in range(4):
                        self.player_display.team.energy_pool[i] -= self.pteam[action].used_ability.cost[i]
                        self.player_display.team.energy_pool[4] -= self.pteam[action].used_ability.cost[i]
                    self.pteam[action].used_ability = None
            elif action > 2:
                self.resolve_ticking_ability(self.cont_list[action - 3])
        
        
        
        

        for i, energy in enumerate(current_random_expenditure):
            self.player_display.team.energy_pool[i] -= energy
            self.player_display.team.energy_pool[4] -= energy



        self.turn_end()
        #TODO if stored_turns still has turns left, activate enemy_catchup_execution, else set player state to waiting
        if stored_turns:
            self.enemy_catchup_execution(stored_turns, execution_order, energy_pools, all_random_expenditure, time_remaining)
        else:
            self.catching_up = False
            self.timer = self.start_timer(time_remaining)



    def enemy_catchup_execution(self, stored_turns: list[list["AbilityMessage"]], execution_order: list[list[int]], energy_pools: list[list[int]], all_random_expenditure: list[list[int]], time_remaining: int):
        current_turn = stored_turns[0]
        stored_turns = stored_turns[1:]
        this_turn_pool = energy_pools[0]
        energy_pools = energy_pools[1:]
        current_execution_order = execution_order[0]
        execution_order = execution_order[1:]
    
        all_random_expenditure = all_random_expenditure[1:]
        #TODO Execute all abilities in current_turn
        self.enemy_execution_loop(current_turn, current_execution_order, this_turn_pool)

        #TODO if stored_turns still has turns left, and activate player_catchup_execution,
        #else set player state to active
        if stored_turns:
            self.player_catchup_execution(stored_turns, execution_order, energy_pools, all_random_expenditure, time_remaining)
        else:
            self.timer = self.start_timer(time_remaining)
            self.waiting_for_turn = False
            self.catching_up = False
            self.full_update()



    def execution_loop(self):
        
        for action in self.execution_order:
            if action < 3:
                if self.pteam[action].acted:
                    #build ability message
                    self.ability_messages.append(AbilityMessage(self.pteam[action]))
                    self.pteam[action].execute_ability()
            elif action > 2:
                self.resolve_ticking_ability(self.cont_list[action - 3])

    def enemy_execution_loop(self, executed_abilities: list["AbilityMessage"], execution_order: list[int],
                             potential_energy: list[int]):

        logging.debug("Started enemy execution loop")
        for ability in executed_abilities:
            
            self.eteam[ability.user_id].used_ability = self.eteam[
                ability.user_id].source.current_abilities[ability.ability_id]
            self.eteam[ability.user_id].acted = True
            
            if ability.primary_id != 69: #lol
                if ability.primary_id < 3:
                    self.eteam[ability.user_id].primary_target = self.eteam[ability.primary_id]
                else:
                    self.eteam[ability.user_id].primary_target = self.pteam[ability.primary_id - 3]
            
            for num in ability.ally_targets:
                self.eteam[ability.user_id].current_targets.append(
                    self.eteam[num])

            for num in ability.enemy_targets:
                self.eteam[ability.user_id].current_targets.append(
                    self.pteam[num])
        self.get_execution_order_base("enemy")
        for action in execution_order:
            
            if action < 3:
                if self.eteam[action].acted:
                    #build ability message
                    self.eteam[action].free_execute_ability(self.eteam, self.pteam)
                    self.eteam[action].acted = False
                    self.eteam[action].used_ability = None
                    self.eteam[action].current_targets.clear()
                    self.eteam[action].primary_target = None
            elif action > 2:
                self.resolve_ticking_ability(self.cont_list[action - 3])
                
        self.tick_effect_duration(enemy_tick=True)
        for character in self.eteam:
            character.check_ability_swaps(ffs_shokuhou=True)
        self.handle_energy_gain(potential_energy)

        self.turn_start()

    def handle_energy_gain(self, potential_pool: list[int]):

        new_energy = [0, 0, 0, 0, 0]

        for character in self.pteam:
            if not character.source.dead:
                personal_contribution = character.check_energy_contribution()
                for i in range(5):
                    new_energy[i] += personal_contribution[i]

        #TODO add energy removal at some point?

        for i in range(new_energy[4]):
            if potential_pool[i] != 5:
                new_energy[potential_pool[i]] += 1


        for i in range(4):
            self.ally_energy_pool[Energy(i)] += new_energy[i]
            self.ally_energy_pool[Energy(4)] += new_energy[i]

    def reset_id(self):
        for i, manager in enumerate(
                self.player_display.team.character_managers):
            manager.id = "ally"
            manager.char_id = i
        for i, manager in enumerate(
                self.enemy_display.team.character_managers):
            manager.id = "enemy"
            manager.char_id = i

    def is_allied_effect(self, effect: Effect, team_id: str) -> bool:
        return effect.user.id == team_id

    def return_character(self, char_name) -> Character:
        return Character(get_character_db()[char_name].name,
                         get_character_db()[char_name].desc)

    def is_allied_character(self, character: "CharacterManager"):
        return character in self.player_display.team.character_managers

    def resolve_ticking_ability(self, eff: Effect):
        team_id = eff.user.id
        
        
        for tar in self.cont_storage[eff.signature]:
            if tar < 3:
                target = self.pteam[tar]
            else:
                target = self.eteam[tar - 3]
            logging.debug("Executing %s on %s", eff.name, target.source.name)
            if target.contains_sig(eff):
                if eff.eff_type == EffectType.CONT_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id) and (eff.mag >= 20 or not target.deflecting()):
                        eff.user.deal_eff_damage(eff.mag, target, eff, DamageType.NORMAL)
                elif eff.eff_type == EffectType.CONT_PIERCE_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id) and (eff.mag >= 20 or not target.deflecting()):
                        eff.user.deal_eff_damage(eff.mag, target, eff, DamageType.PIERCING)
                elif eff.eff_type == EffectType.CONT_AFF_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id) and (eff.mag >= 20 or not target.deflecting()):
                        if eff.name == "Doping Rampage":
                            self.dying_to_doping = True
                        eff.user.deal_eff_damage(eff.mag, target, eff, DamageType.AFFLICTION)
                elif eff.eff_type == EffectType.CONT_HEAL and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id):
                        eff.user.give_eff_healing(eff.mag, target, eff)
                elif eff.eff_type == EffectType.CONT_DEST_DEF and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id):
                        if target.has_effect(EffectType.DEST_DEF, eff.name):
                            target.get_effect(EffectType.DEST_DEF,
                                            eff.name).alter_dest_def(eff.mag)
                        else:
                            target.add_effect(
                                Effect(
                                    eff.source, EffectType.DEST_DEF, eff.user,
                                    280000, lambda eff:
                                    f"This character has {eff.mag} destructible defense.",
                                    eff.mag))
                elif eff.eff_type == EffectType.CONT_UNIQUE and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user:
                    if eff.check_waiting() and self.is_allied_effect(eff, team_id):
                        target.check_unique_cont(eff, team_id)
            
        
    # def resolve_ticking_ability(self, team_id: str):
    #     """Checks all Character Managers for continuous effects.
        
    #     All continuous effects that belong to the player whose turn
    #     is currently ending are triggered and resolved."""
    #     for manager in self.player_display.team.character_managers:
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.NORMAL)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_PIERCE_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.PIERCING)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_AFF_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 if eff.name == "Doping Rampage":
    #                     self.dying_to_doping = True
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.AFFLICTION)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_HEAL and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 eff.user.give_eff_healing(eff.mag, manager, eff)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_DEST_DEF and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 if manager.has_effect(EffectType.DEST_DEF, eff.name):
    #                     manager.get_effect(EffectType.DEST_DEF,
    #                                     eff.name).alter_dest_def(eff.mag)
    #                 else:
    #                     manager.add_effect(
    #                         Effect(
    #                             eff.source, EffectType.DEST_DEF, eff.user,
    #                             280000, lambda eff:
    #                             f"This character has {eff.mag} destructible defense.",
    #                             eff.mag))
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_UNIQUE and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 manager.check_unique_cont(eff, team_id)

    #     for manager in self.enemy_display.team.character_managers:
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.NORMAL)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_PIERCE_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.PIERCING)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_AFF_DMG and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(
    #                     eff, team_id) and (eff.mag >= 20
    #                                     or not manager.deflecting()):
    #                 if eff.name == "Doping Rampage":
    #                     self.dying_to_doping = True
    #                 eff.user.deal_eff_damage(eff.mag, manager, eff, DamageType.AFFLICTION)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_HEAL and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 eff.user.give_eff_healing(eff.mag, manager, eff)
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_DEST_DEF and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 if manager.has_effect(EffectType.DEST_DEF, eff.name):
    #                     manager.get_effect(EffectType.DEST_DEF,
    #                                     eff.name).alter_dest_def(eff.mag)
    #                 else:
    #                     manager.add_effect(
    #                         Effect(
    #                             eff.source, EffectType.DEST_DEF, eff.user,
    #                             280000, lambda eff:
    #                             f"This character has {eff.mag} destructible defense.",
    #                             eff.mag))
    #         gen = (eff for eff in manager.source.current_effects
    #             if eff.eff_type == EffectType.CONT_UNIQUE and not (EffectType.MARK, "Enkidu, Chains of Heaven") in eff.user)
    #         for eff in gen:
    #             if eff.check_waiting() and self.is_allied_effect(eff, team_id):
    #                 manager.check_unique_cont(eff, team_id)

    def handle_timeout(self):
        #TODO
        #     lock player out of continued input (Set waiting for turn, full_update)
        #     refund spent energy
        #     clear character's acted status
        #     resolve continuous effects
        #
        self.waiting_for_turn = True
        self.exchanging_energy = False
        self.return_targeting_to_default()
        self.reset_targeting()
        for manager in self.pteam:
            if manager.acted:
                self.refund_energy_costs(manager.used_ability)
        self.ability_messages.clear()
        self.acting_order.clear()
        self.random_spent = [0,0,0,0]
        self.turn_end(timeout=True)
        self.full_update()
        pass

    def tick_ability_cooldown(self):
        for manager in self.player_display.team.character_managers:
            for ability in manager.source.main_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)
            for ability in manager.source.alt_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)
                
    def tick_enemy_cooldowns(self):
        # For testing purposes only, typically this is handled by another client
        for manager in self.enemy_display.team.character_managers:
            for ability in manager.source.main_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)
            for ability in manager.source.alt_abilities:
                ability.cooldown_remaining = max(
                    ability.cooldown_remaining - 1, 0)
    
    def turn_end(self, timeout=False):
        self.sharingan_reflecting = False
        self.sharingan_reflector = None


        # Kuroko invulnerability check #
        for manager in self.player_display.team.character_managers:
            if manager.source.name == "kuroko" and manager.check_invuln():
                manager.progress_mission(1, 1)
            if manager.source.name == "cmary" and manager.check_invuln(
            ) and manager.has_effect(EffectType.ALL_INVULN,
                                     "Quickdraw - Sniper"):
                manager.progress_mission(4, 1)

        self.tick_effect_duration()
        self.tick_ability_cooldown()
        self.has_exchanged = False
        self.waiting_for_turn = True
        self.traded_away_energy = 5
        self.traded_for_energy = 5
        self.exchanging_energy = False

        if self.collapsing_enemy_inviolate_shield:
            for manager in self.eteam:
                if manager.has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield"):
                    manager.full_remove_effect("Five-God Inviolate Shield", manager.get_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield").user)
                    self.collapsing_enemy_inviolate_shield = False
        if self.collapsing_ally_inviolate_shield:
            for manager in self.eteam:
                if manager.has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield"):
                    manager.full_remove_effect("Five-God Inviolate Shield", manager.get_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield").user)
                    self.collapsing_ally_inviolate_shield = False
        
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
                yatsu.user.progress_mission(1, 1)
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

        self.timer = self.start_timer()
        
        self.full_update()



        if not self.catching_up:
            if not timeout:
                self.scene_manager.connection.send_match_communication(
                    self.ability_messages, self.execution_order, self.random_spent)
            self.ability_messages.clear()
            self.random_spent = [0, 0, 0, 0]
        self.execution_order.clear()
        self.acting_order.clear()
        if game_lost:
            self.lose_game()
        if game_won and not game_lost:
            self.win_game()

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

    def tick_effect_duration(self, enemy_tick: bool = False):
        player_team = self.player_display.team.character_managers
        enemy_team = self.enemy_display.team.character_managers
        for i, manager in enumerate(player_team):
            for eff in manager.source.current_effects:
                if not enemy_tick:
                    #region Spend Turn Under Effect Mission Check
                    if not eff.eff_type == EffectType.SYSTEM:
                        #region Spend Enemy Turn Under Effect
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
                        if eff.name == "Loyal Guard" and manager.check_invuln(
                        ):
                            manager.progress_mission(3, 1)
                        if eff.name == "Fog of London" and eff.eff_type == EffectType.MARK and not eff.user.has_effect(
                                EffectType.SYSTEM, "JackMission5Success"):
                            if not eff.user.has_effect(EffectType.SYSTEM,
                                                       "JackMission5Tracker"):
                                eff.user.add_effect(
                                    Effect("JackMission5Tracker",
                                           EffectType.SYSTEM,
                                           eff.user,
                                           280000,
                                           lambda eff: "",
                                           mag=0,
                                           system=True))
                            else:
                                eff.user.get_effect(
                                    EffectType.SYSTEM,
                                    "JackMission5Tracker").alter_mag(1)
                                if eff.user.get_effect(
                                        EffectType.SYSTEM,
                                        "JackMission5Tracker").mag >= 10:
                                    eff.user.add_effect(
                                        Effect("JackMission5Success",
                                               EffectType.SYSTEM,
                                               eff.user,
                                               280000,
                                               lambda eff: "",
                                               system=True))
                                    eff.user.remove_effect(eff.user.get_effect(
                                        EffectType.SYSTEM,
                                        "JackMission5Tracker"))
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
                    if not manager.has_effect(EffectType.CONSECUTIVE_BUFFER,
                                              eff.name):
                        eff.removing = True
                eff.tick_duration()
                #Effects that trigger upon ending

                if eff.duration == 0:

                    if eff.name == "Bridal Chest":
                        if eff.user.has_effect(EffectType.SYSTEM, "FrankensteinMission2Counter"):
                            eff.user.remove_effect(eff.user.get_effect(EffectType.SYSTEM, "FrankensteinMission2Counter"))

                    if eff.name == "Lightning Palm" or eff.name == "Narukami" or eff.name == "Whirlwind Rush":
                        if not eff.user.has_effect(EffectType.SYSTEM,
                                                   "KilluaMission5Tracker"):
                            eff.user.add_effect(
                                Effect("KilluaMission5Failure",
                                       EffectType.SYSTEM,
                                       eff.user,
                                       280000,
                                       lambda eff: "",
                                       system=True))

                    if eff.name == "Quirk - Transform":
                        manager.toga_flush_effects()
                        manager.toga_transform("toga")

                    if eff.name == "Bunny Assault" and eff.eff_type == EffectType.CONT_USE:
                        if manager.has_effect(EffectType.DEST_DEF,
                                              "Perfect Paper - Rampage Suit"):
                            manager.get_effect(
                                EffectType.DEST_DEF,
                                "Perfect Paper - Rampage Suit").alter_dest_def(
                                    30)
                            manager.progress_mission(3, 20)
                    if eff.name == "Thunder Palace":
                        for enemy in self.enemy_display.team.character_managers:
                            if enemy.final_can_effect(
                                    manager.check_bypass_effects()):
                                eff.user.deal_eff_damage(40, enemy, eff, DamageType.NORMAL)
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
                                    manager.deal_eff_damage(30, emanager, eff, DamageType.NORMAL)
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
                                    manager.deal_eff_damage(25, emanager, eff, DamageType.NORMAL)
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
                                    manager.deal_eff_damage(45, emanager, eff, DamageType.NORMAL)
                    if eff.name == "Illusory World Destruction" and eff.mag > 0:
                        for emanager in enemy_team:
                            if emanager.final_can_effect(
                                    manager.check_bypass_effects()):
                                manager.deal_eff_damage(30, emanager, eff, DamageType.NORMAL)
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

        for i, manager in enumerate(enemy_team):
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.name == "Consecutive Normal Punches":
                    if manager.has_effect(
                            EffectType.SYSTEM, "SaitamaMission2Tracker"
                    ) and not eff.user.source.mission2complete:
                        manager.get_effect(
                            EffectType.SYSTEM,
                            "SaitamaMission2Tracker").alter_mag(1)
                        if manager.get_effect(
                                EffectType.SYSTEM,
                                "SaitamaMission2Tracker").mag >= 7:
                            eff.user.source.mission2complete = True
                            eff.user.progress_mission(2, 1)
                        else:
                            manager.get_effect(
                                EffectType.SYSTEM,
                                "SaitamaMission2Tracker").duration += 2
                if eff.duration == 0:
                    if eff.invisible and not manager.has_effect(
                            EffectType.INVIS_END, eff.name):
                        manager.add_effect(
                            Effect(eff.source, EffectType.INVIS_END, eff.user,
                                   2, lambda eff: f"{eff.name} has ended."))
                    if eff.name == "In The Name Of Ruler!" and eff.eff_type == EffectType.ALL_STUN:
                        eff.user.progress_mission(1, 1)
                    if eff.name == "Quirk - Transform":
                        manager.toga_flush_effects()
                        manager.toga_transform("toga")    
                    if eff.name == "Bunny Assault" and eff.eff_type == EffectType.CONT_USE:
                        if manager.has_effect(EffectType.DEST_DEF,
                                              "Perfect Paper - Rampage Suit"):
                            manager.get_effect(
                                EffectType.DEST_DEF,
                                "Perfect Paper - Rampage Suit").alter_dest_def(
                                    30)
                            manager.progress_mission(3, 20)
                    if eff.name == "Thunder Palace":
                        for enemy in self.pteam:
                            if enemy.final_can_effect(
                                    manager.check_bypass_effects()):
                                eff.user.deal_eff_damage(40, enemy, eff, DamageType.NORMAL)
                    if eff.name == "Hidden Mine" and eff.eff_Type == EffectType.UNIQUE:
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Illusory Disorientation":
                        eff.user.progress_mission(5, 1)
                    if eff.name == "Mahapadma" and eff.eff_type == EffectType.MARK:
                        manager.add_effect(
                            Effect(Ability("esdeathalt1"), EffectType.ALL_STUN,
                                   manager, 5,
                                   lambda eff: "Esdeath is stunned."))
                    if eff.name == "Lightning Dragon's Roar":
                        manager.add_effect(
                            Effect(Ability("laxus2"),
                                   EffectType.ALL_DR,
                                   eff.user,
                                   2,
                                   lambda eff:
                                   "This character will take 10 more damage.",
                                   mag=-10))
                    if eff.name == "Illusory Breakdown" and eff.mag > 0:
                        for emanager in self.pteam:
                            if emanager.has_effect(
                                    EffectType.SYSTEM, "Chrome1Target"
                            ) and emanager.get_effect(
                                    EffectType.SYSTEM, "Chrome1Target").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(30, emanager, eff, DamageType.NORMAL)
                                    emanager.add_effect(
                                        Effect(
                                            Ability("chrome2"),
                                            EffectType.ALL_STUN, manager, 2,
                                            lambda eff:
                                            "This character is stunned."))
                                    if emanager.meets_stun_check():
                                        manager.check_on_stun(emanager)
                    if eff.name == "Mental Immolation" and eff.mag > 0:
                        for emanager in self.pteam:
                            if emanager.has_effect(
                                    EffectType.SYSTEM, "Chrome2Target"
                            ) and emanager.get_effect(
                                    EffectType.SYSTEM, "Chrome2Target").user == manager:
                                if emanager.final_can_effect(
                                        manager.check_bypass_effects()):
                                    manager.deal_eff_damage(25, emanager, eff, DamageType.NORMAL)
                                    eff.user.progress_mission(3, 1)
                                    emanager.source.energy_contribution -= 1
                                    manager.check_on_drain(emanager)
                    if eff.name == "Mental Annihilation" and eff.mag > 0:
                        for emanager in self.pteam:
                            if emanager.has_effect(
                                    EffectType.SYSTEM, "MukuroTarget"
                            ) and emanager.get_effect(
                                    EffectType.SYSTEM, "MukuroTarget").user == manager:
                                if emanager.final_can_effect("BYPASS"):
                                    manager.deal_eff_damage(45, emanager, eff, DamageType.NORMAL)
                    if eff.name == "Illusory World Destruction" and eff.mag > 0:
                        for emanager in self.pteam:
                            if emanager.final_can_effect(
                                    manager.check_bypass_effects()):
                                manager.deal_eff_damage(30, emanager, eff, DamageType.NORMAL)
                                emanager.add_effect(
                                    Effect(
                                        Ability("chromealt2"),
                                        EffectType.ALL_STUN, manager, 2, lambda
                                        eff: "This character is stunned."))
                                if emanager.meets_stun_check():
                                    manager.check_on_stun(emanager)
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
            new_list = [
                eff for eff in manager.source.current_effects
                if eff.duration > 0 and not eff.removing
            ]
            manager.source.current_effects = new_list
        new_reflected_list = [
            eff for eff in self.sharingan_reflected_effects
            if eff.duration > 0 and not eff.removing
        ]
        self.sharingan_reflected_effects = new_reflected_list

    def scene_remove_effect(self, effect_name: str, user: CharacterManager):
        for character in self.pteam:
            character.full_remove_effect(effect_name, user)
        for character in self.eteam:
            character.full_remove_effect(effect_name, user)

    def turn_start(self):
        self.sharingan_reflecting = False
        self.sharingan_reflector = None
        if not self.catching_up:
            self.waiting_for_turn = False
            self.timer = self.start_timer()
        self.round_any_cost = 0
        self.acting_character = None
        
        play_sound(self.scene_manager.sounds["turnstart"])
        game_lost = True
        for manager in self.player_display.team.character_managers:

            if manager.source.name == "nemurin":
                if manager.has_effect(
                        EffectType.CONT_UNIQUE,
                        "Nemurin Nap") and manager.get_effect(
                            EffectType.CONT_UNIQUE, "Nemurin Nap").mag <= 0:
                    if not (manager.has_effect(EffectType.SYSTEM,
                                               "NemurinMission5Tracker")
                            or manager.has_effect(EffectType.SYSTEM,
                                                  "NemurinMission5Failure")):
                        manager.add_effect(
                            Effect("NemurinMission5Tracker",
                                   EffectType.SYSTEM,
                                   manager,
                                   280000,
                                   lambda eff: "",
                                   mag=1,
                                   system=True))
                    else:
                        manager.add_effect(
                            Effect("NemurinMission5Failure",
                                   EffectType.SYSTEM,
                                   manager,
                                   280000,
                                   lambda eff: "",
                                   system=True))
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
        if self.timer:
            self.timer.cancel()
        for i in range(3):
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][0] += self.player_display.team.character_managers[
                    i].source.mission1progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][1] += self.player_display.team.character_managers[
                    i].source.mission2progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][2] += self.player_display.team.character_managers[
                    i].source.mission3progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][3] += self.player_display.team.character_managers[
                    i].source.mission4progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][4] += self.player_display.team.character_managers[
                    i].source.mission5progress

        
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
        self.scene_manager.connection.send_match_ending(won=False)
        self.scene_manager.connection.send_player_update(self.player)
        self.scene_manager.connection.send_match_statistics([
            manager.source.name
            for manager in self.player_display.team.character_managers
        ], False)

    def return_to_char_select(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        for manager in self.pteam:
            manager.targeted = False
            manager.targeting = False
            manager.used_ability = False
            manager.current_targets.clear()
            manager.primary_target = None
            manager.used_ability = None
            manager.received_ability.clear()
            manager.acted = False
            if manager.source.name == "orihime":
                manager.source.current_effects.clear()
                rename_i_reject(manager)
        self.scene_manager.return_to_select(self.player)
        self.window_up = False

    def saber_is_the_strongest_servant(self,
                                       saber: "CharacterManager") -> bool:
        saber_damage = 0
        manager_damage = 0
        if saber.has_effect(EffectType.SYSTEM, "SaberDamageTracker"):
            saber_damage = saber.get_effect(EffectType.SYSTEM,
                                            "SaberDamageTracker").mag
            for manager in self.player_display.team.character_managers:
                if manager != saber:
                    if manager.has_effect(EffectType.SYSTEM,
                                          "SaberDamageTracker"):
                        manager_damage = manager.get_effect(
                            EffectType.SYSTEM, "SaberDamageTracker").mag
                    else:
                        manager_damage = 0
                    if manager_damage > saber_damage:
                        return False
            for manager in self.enemy_display.team.character_managers:
                if manager != saber:
                    if manager.has_effect(EffectType.SYSTEM,
                                          "SaberDamageTracker"):
                        manager_damage = manager.get_effect(
                            EffectType.SYSTEM, "SaberDamageTracker").mag
                    else:
                        manager_damage = 0
                    if manager_damage > saber_damage:
                        return False
            return True

    def lose_game_mission_check(self):
        for character in self.pteam:
            MissionHandler.handle_loss_mission(character)

    def win_game_mission_check(self):
        for character in self.pteam:
            MissionHandler.handle_win_mission(character)


    def get_character_from_team(self, name: str,
                                team: list["CharacterManager"]):
        for character in team:
            if character.source.name == name:
                return character
        return None

    def win_game(self, surrendered=False):
        self.player.wins += 1

        self.win_game_mission_check()
        if self.timer:
            self.timer.cancel()
        for i in range(3):
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][0] += self.player_display.team.character_managers[
                    i].source.mission1progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][1] += self.player_display.team.character_managers[
                    i].source.mission2progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][2] += self.player_display.team.character_managers[
                    i].source.mission3progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][3] += self.player_display.team.character_managers[
                    i].source.mission4progress
            self.player.missions[
                self.player_display.team.character_managers[i].source.
                name][4] += self.player_display.team.character_managers[
                    i].source.mission5progress
        
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
        
        self.scene_manager.connection.send_match_ending(won=True)
        self.scene_manager.connection.send_player_update(self.player)
        self.scene_manager.connection.send_match_statistics([
            manager.source.name
            for manager in self.player_display.team.character_managers
        ], True)
    

    def update_energy_region(self):
        self.show_energy_display()
        if self.exchanging_energy:
            self.show_energy_exchange()
        
        

    def show_energy_display(self):
        self.energy_region.clear()
        
        energy_panel = self.border_sprite(self.sprite_factory.from_color(MENU_TRANSPARENT, self.energy_region.size()), AQUA, 2)
        
        
        
        physical_count = "x " + f"{self.player_display.team.energy_pool[Energy.PHYSICAL]}"
        special_count = "x " + f"{self.player_display.team.energy_pool[Energy.SPECIAL]}"
        mental_count = "x " + f"{self.player_display.team.energy_pool[Energy.MENTAL]}"
        weapon_count = "x " + f"{self.player_display.team.energy_pool[Energy.WEAPON]}"
        total_count = "x " + f"{self.player_display.team.energy_pool[Energy.RANDOM]}"
        energy_panel = self.render_bordered_text(self.font, physical_count, WHITE, BLACK, energy_panel, 35, 4, 1)
        energy_panel = self.render_bordered_text(self.font, special_count, WHITE, BLACK, energy_panel, 93, 4, 1)
        energy_panel = self.render_bordered_text(self.font, mental_count, WHITE, BLACK, energy_panel, 151, 4, 1)
        energy_panel = self.render_bordered_text(self.font, weapon_count, WHITE, BLACK, energy_panel, 209, 4, 1)
        energy_panel = self.render_bordered_text(self.font, total_count, WHITE, BLACK, energy_panel, 267, 4, 1)
        
        can_exchange = False
        for i in range(4):
            if self.player_display.team.energy_pool[Energy(i)] >= 2:
                can_exchange = True

        self.energy_region.add_sprite(energy_panel, 0, 0)
        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["PHYSICAL"], 13, 13)),
                                      x=18,
                                      y=9)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["SPECIAL"], 13, 13)),
                                      x=76,
                                      y=9)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["MENTAL"], 13, 13)),
                                      x=134,
                                      y=9)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["WEAPON"], 13, 13)),
                                      x=192,
                                      y=9)
        
        self.energy_region.add_sprite(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.scene_manager.surfaces["RANDOM"], 13, 13)),
                                      x=250,
                                      y=9)
        
        if can_exchange and not self.has_exchanged and not self.waiting_for_turn:
            exchange_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU_TRANSPARENT, (31, 30))
            exchange_button = self.border_sprite(exchange_button, AQUA, 2)
            exchange_button = self.blit_surface(exchange_button, self.get_scaled_surface(self.scene_manager.surfaces["exchange_icon"]), (2, 2))
            exchange_button.click += self.exchange_button_click
            self.energy_region.add_sprite(exchange_button, 298, 0)

    def show_energy_exchange(self):
        self.window_up = True
        exchange_panel = self.sprite_factory.from_color(MENU, (150, 120))
        exchange_panel = self.border_sprite(exchange_panel, AQUA, 2)
        exchange_panel = self.render_bordered_text(self.font, "Trade 2", WHITE, BLACK, exchange_panel, 5, 2, 1)
        exchange_panel = self.render_bordered_text(self.font, "Receive", WHITE, BLACK, exchange_panel, 92, 2, 1)
        self.energy_region.add_sprite(exchange_panel, 75, 30)
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
                                             offered_energy_symbol, ELECTRIC_BLUE, 101,
                                             55 + (rows * 15))
                else:
                    offered_energy_symbol = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces[Energy(i).name]))
                    offered_energy_symbol.energy_type = i
                    offered_energy_symbol.click += self.offered_click
                    self.energy_region.add_sprite(offered_energy_symbol, 101,
                                                  55 + (rows * 15))

            if i == self.traded_for_energy:
                received_energy_symbol = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[Energy(i).name]))
                received_energy_symbol.energy_type = i
                received_energy_symbol.click += self.received_click
                self.add_bordered_sprite(self.energy_region,
                                         received_energy_symbol, ELECTRIC_BLUE, 189,
                                         55 + (rows * 15))
            else:
                received_energy_symbol = self.ui_factory.from_surface(
                    sdl2.ext.BUTTON,
                    self.get_scaled_surface(
                        self.scene_manager.surfaces[Energy(i).name]))
                received_energy_symbol.energy_type = i
                received_energy_symbol.click += self.received_click
                self.energy_region.add_sprite(received_energy_symbol, 189,
                                              55 + (rows * 15))

            rows += 1

        cancel_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU, (60, 25))
        cancel_button = self.border_sprite(cancel_button, AQUA, 2)
        cancel_button = self.render_bordered_text(self.font, "Cancel", WHITE, BLACK, cancel_button, 6, 1, 1)
        cancel_button.click += self.exchange_cancel_click
        self.energy_region.add_sprite(cancel_button, 160, 120)

        if self.traded_for_energy != 5 and self.traded_away_energy != 5 and self.traded_for_energy != self.traded_away_energy:
            accept_button = self.ui_factory.from_color(sdl2.ext.BUTTON, MENU, (60, 25))
            accept_button = self.border_sprite(accept_button, AQUA, 2)
            accept_button = self.render_bordered_text(self.font, "Accept", WHITE, BLACK, accept_button, 6, 1, 1)
            accept_button.click += self.exchange_accept_click
            self.energy_region.add_sprite(accept_button, 80, 120)

    def handle_unique_startup(self, character: "CharacterManager"):
        if character.source.name == "gokudera":
            character.add_effect(
                Effect(
                    Ability("gokudera1"),
                    EffectType.STACK,
                    character,
                    280000,
                    lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.",
                    mag=1, print_mag=True))
        if character.source.name == "aizen":
            character.add_effect(
                Effect("AizenMission5Tracker",
                       EffectType.SYSTEM,
                       character,
                       280000,
                       lambda eff: "",
                       mag=0,
                       system=True))
        if character.source.name == "orihime":
            rename_i_reject(character)
        if character.source.name == "jiro":
            character.add_effect(
                Effect("JiroMission5Tracker",
                       EffectType.SYSTEM,
                       character,
                       2,
                       lambda eff: "",
                       system=True))
        if character.source.name == "toga":
            character.is_toga = True

    def setup_scene(self,
                    ally_team: list[Character],
                    enemy_team: list[Character],
                    player: Player = None,
                    enemy: Player = None,
                    energy=[0, 0, 0, 0], seed: int = 0):
        self.window_closing = True
        self.sharingan_reflecting = False
        self.sharingan_reflector = None
        self.clicked_surrender = False
        self.round_any_cost = 0
        self.d20 = random.Random(x = seed)
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
                            char_manager.source.main_abilities[j].db_name], 80, 80))
                    for j in range(4)
                ]
                for j, sprite in enumerate(char_manager.main_ability_sprites):
                    sprite.selected_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["selected"], 80, 80),
                        free=True)
                    sprite.ability = char_manager.source.main_abilities[j]
                    char_manager.source.main_abilities[
                        j].cooldown_remaining = 0
                    sprite.null_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["locked"], 80, 80),
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
                        sdl2.ext.BUTTON, BLACK, (84, 84))
                    sprite.click += char_manager.set_selected_ability

                char_manager.alt_ability_sprites = [
                    self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(self.scene_manager.surfaces[
                            char_manager.source.alt_abilities[j].db_name], 80, 80))
                    for j in range(len(char_manager.source.alt_abilities))
                ]
                for j, sprite in enumerate(char_manager.alt_ability_sprites):
                    sprite.selected_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["selected"], 80, 80),
                        free=True)
                    sprite.ability = char_manager.source.alt_abilities[j]
                    char_manager.source.alt_abilities[j].cooldown_remaining = 0
                    sprite.null_pane = self.ui_factory.from_surface(
                        sdl2.ext.BUTTON,
                        self.get_scaled_surface(
                            self.scene_manager.surfaces["locked"], 80, 80),
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
                        sdl2.ext.BUTTON, BLACK, (84, 84))
                    sprite.click += char_manager.set_selected_ability

                char_manager.current_ability_sprites = [
                    ability for ability in char_manager.main_ability_sprites
                ]
                for j, sprite in enumerate(
                        char_manager.current_ability_sprites):
                    sprite.ability = char_manager.source.current_abilities[j]

                char_manager.in_battle_desc = self.create_text_display(
                    self.font, char_manager.source.desc, BLACK, WHITE, 5, 0,
                    520, 110)
                char_manager.text_border = self.ui_factory.from_color(
                    sdl2.ext.BUTTON, BLACK, (524, 129))
                for sprite in char_manager.main_ability_sprites:
                    sprite.in_battle_desc = self.create_text_display(
                        self.font,
                        sprite.ability.name + ": " + sprite.ability.desc,
                        BLACK, WHITE, 5, 0, 520, 110)
                    sprite.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))
                for sprite in char_manager.alt_ability_sprites:
                    sprite.in_battle_desc = self.create_text_display(
                        self.font,
                        sprite.ability.name + ": " + sprite.ability.desc,
                        BLACK, WHITE, 5, 0, 520, 110)
                    sprite.text_border = self.ui_factory.from_color(
                        sdl2.ext.BUTTON, BLACK, (524, 129))
            char_manager.id = "ally"
            char_manager.char_id = i
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
                        self.scene_manager.surfaces[e_char_manager.source.name
                                                    + "enemyprof"]),
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
            e_char_manager.id = "enemy"
            e_char_manager.char_id = i
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
        
        self.timer = self.start_timer()
        self.draw_timer_region()
        if player:
            self.update_energy_region()

            for manager in self.player_display.team.character_managers:
                manager.source.current_hp = 200
                manager.update()

            for manager in self.enemy_display.team.character_managers:
                manager.source.current_hp = 200
                manager.update_limited()
            self.draw_player_region()
            self.draw_enemy_region()
            self.draw_surrender_region()

    def targeting_all_allies(self, primary_target: "CharacterManager"):
        return self.selected_ability.target_type == Target.MULTI_ALLY or self.selected_ability.target_type == Target.ALL_TARGET or (
            self.selected_ability.target_type == Target.MULTI_EITHER
            and primary_target in self.pteam)
        
    def targeting_all_enemies(self, primary_target: "CharacterManager"):
        return self.selected_ability.target_type == Target.MULTI_ENEMY or self.selected_ability.target_type == Target.ALL_TARGET or (
            self.selected_ability.target_type == Target.MULTI_EITHER
            and primary_target in self.eteam)

    def apply_targeting(self, primary_target: "CharacterManager"):
        self.selected_ability.primary_target = primary_target
        if self.selected_ability.target_type == Target.SINGLE:
            self.acting_character.add_current_target(primary_target)
            primary_target.add_received_ability(self.selected_ability)
        else:
            if self.targeting_all_allies(primary_target):
                for manager in self.player_display.team.character_managers:
                    if manager.targeted:
                        self.acting_character.add_current_target(manager)
                        manager.add_received_ability(self.selected_ability)
            if self.targeting_all_enemies(primary_target):
                for manager in self.enemy_display.team.character_managers:
                    if manager.targeted:
                        self.acting_character.add_current_target(manager)
                        manager.add_received_ability(self.selected_ability)
        self.reset_targeting()
        self.acting_character.primary_target = primary_target
        self.selected_ability.user = self.acting_character
        self.acting_character.used_ability = self.selected_ability
        self.acting_character.used_slot.ability = self.selected_ability
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

    def get_ally_characters(self) -> list[Character]:
        output = []
        for manager in self.player_display.team.character_managers:
            output.append(manager.source)
        return output

    def get_enemy_characters(self) -> list[Character]:
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
            ability.user.set_used_slot_to_none()
            ability.user.acted = False
            ability.user.used_ability = None
            self.acting_order.remove(ability.user)
        self.refund_energy_costs(ability)
        self.full_update()


def make_battle_scene(scene_manager) -> BattleScene:

    scene = BattleScene(scene_manager, sdl2.ext.SOFTWARE)

    return scene