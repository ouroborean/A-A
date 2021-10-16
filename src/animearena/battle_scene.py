import math
import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import dill as pickle
import itertools
import textwrap
import copy
from animearena import engine
from animearena import character
from animearena.character import Character, character_db
from animearena.ability import Ability, Target
from animearena.energy import Energy
from animearena.effects import Effect, EffectType
from random import randint

from pathlib import Path
from typing import Optional

FONT_FILENAME = "Basic-Regular.ttf"
FONTSIZE = 16
COOLDOWN_FONTSIZE = 100
RESOURCES = Path(__file__).parent.parent.parent / "resources"
BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)
TRANSPARENT = sdl2.SDL_Color(255,255,255,255)




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
        self.team_region = self.scene.region.subregion(x=5, y=145, width = 670, height = 750)
        self.character_regions = [self.team_region.subregion(x = 0, y=i * 250, width=670, height = 230) for i in range(3)]
        
        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.text_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.character_regions:
            self.effect_regions.append(region.subregion(-3, 124, 106, 103))
            self.targeting_regions.append(region.subregion(x=105, y=0, width=25, height=100))
            self.text_regions.append(region.subregion(x=150, y=110, width=520, height=110))
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
        self.enemy_region = self.scene.region.subregion(x=795, y = 145, width = 130, height = 750)
        self.enemy_regions = [self.enemy_region.subregion(x = 0, y = i * 250, width = 130, height = 230) for i in range(3)]
        
        self.effect_regions: list[engine.Region] = []
        self.targeting_regions: list[engine.Region] = []
        self.hp_bar_regions: list[engine.Region] = []
        for region in self.enemy_regions:
            self.effect_regions.append(region.subregion(-3, 124, 106, 103))
            self.targeting_regions.append(region.subregion(x=-30, y=0, width=25, height=100))
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
    ally_energy_pool: dict[Energy, int]
    enemy_energy_pool: dict[Energy, int]
    offered_pool: dict[Energy, int]
    current_button: Optional[sdl2.ext.SoftwareSprite]
    round_any_cost: int
    waiting_for_turn: bool
    window_up: bool

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window_up = False
        self.waiting_for_turn = False
        self.scene_manager = scene_manager
        self.ally_managers = []
        self.enemy_managers = []
        self.round_any_cost = 0
        self.current_button = None
        self.player_display = ActiveTeamDisplay(self)
        self.enemy_display = EnemyTeamDisplay(self)
        fontpath = str.encode(f"{RESOURCES / FONT_FILENAME}")
        self.font = sdl2.sdlttf.TTF_OpenFont(fontpath, FONTSIZE)
        self.cooldown_font = sdl2.sdlttf.TTF_OpenFont(fontpath, COOLDOWN_FONTSIZE)
        self.selected_ability = None
        self.acting_character = None
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
        self.energy_region = self.region.subregion(x=185, y=5, width=185, height = 53)
        self.turn_end_region = self.region.subregion(x=375, y=5, width=150, height = 200)
        self.turn_expend_region = self.region.subregion(x=335, y=5, width=220, height=140)
        self.hover_effect_region = self.region.subregion(0, 0, 0, 0)

    def draw_turn_end_region(self):
        self.turn_end_region.clear()
        turn_end_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.surfaces["end"], width=150,  height=50))
        turn_end_button.click += self.turn_end_button_click
        self.turn_end_region.add_sprite(turn_end_button, x=0, y=0)

    def draw_any_cost_expenditure_window(self):
        self.turn_expend_region.clear()
        any_cost_panel = self.sprite_factory.from_color(WHITE, size=(220, 140))
        self.add_bordered_sprite(self.turn_expend_region, any_cost_panel, BLACK, 0, 0)
        left_buffer = 20
        top_buffer = 40
        vertical_spacing = 25
        cost_display = self.create_text_display(self.font,
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
                                                      x=22,
                                                      y=10,
                                                      width=60,
                                                      height=30)
            confirm_button.click += self.confirm_button_click
            self.turn_expend_region.add_sprite(confirm_button, x=150, y=40)

        cancel_button = self.create_text_display(self.font,
                                                 "Cancel",
                                                 WHITE,
                                                 BLACK,
                                                 x=5,
                                                 y=10,
                                                 width=60,
                                                 height=30)
        cancel_button.click += self.any_expenditure_cancel_click
        self.turn_expend_region.add_sprite(cancel_button, x=150, y=90)

        energy_rows = [
            self.turn_expend_region.subregion(left_buffer, y, width=150, height=20)
            for y in itertools.islice(range(top_buffer, 10000, vertical_spacing), 4)
        ]

        for idx, row in enumerate(energy_rows):
            self.draw_energy_row(row, idx)

    def draw_energy_row(self, region: engine.Region, idx: int):

        plus_button_x = 80
        minus_button_x = 50
        current_pool_x = 20
        offered_pool_x = 110

        region.add_sprite_vertical_center(self.sprite_factory.from_surface(
            self.get_scaled_surface(self.surfaces[Energy(idx).name])),
                                          x=0)
        plus_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.surfaces["add"]))
        plus_button.energy = Energy(idx)
        plus_button.click += self.plus_button_click
        minus_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.surfaces["remove"]))
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
        offered_pool = self.create_text_display(self.font,
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

    def execution_loop(self):
        for manager in self.player_display.team.character_managers:
            if manager.acted:
                manager.used_ability.execute(manager, self.player_display.team.character_managers,
                                             self.enemy_display.team.character_managers)
                manager.used_ability.cooldown += manager.check_for_cooldown_mod()
                if manager.used_ability.cooldown < 0:
                    manager.used_ability.cooldown = 0
                manager.used_ability.start_cooldown()
        self.resolve_ticking_ability()

    def is_allied(self, effect: Effect) -> bool:
        for manager in self.player_display.team.character_managers:
            if effect.user == manager:
                return True
        return False

    def return_character(self, char_name) -> Character:
        return character_db[char_name]

    def resolve_ticking_ability(self):
        for manager in self.player_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_PIERCE_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_pierce_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_aff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_HEAL)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.give_eff_healing(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DEST_DEF)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    if manager.has_effect(EffectType.DEST_DEF, eff.name):
                        manager.get_effect(EffectType.DEST_DEF,
                                           eff.name).alter_dest_def(eff.mag)
                    else:
                        manager.add_effect(
                            Effect(
                                eff.source, EffectType.DEST_DEF, eff.user, 280000,
                                lambda eff: f"This character has {eff.mag} destructible defense.",
                                eff.mag))
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_UNIQUE)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    manager.check_unique_cont(eff)

        for manager in self.enemy_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_PIERCE_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_pierce_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff) and (eff.mag > 15 or not manager.deflecting()):
                    eff.user.deal_eff_aff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_HEAL)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.give_eff_healing(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DEST_DEF)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    if manager.has_effect(EffectType.DEST_DEF, eff.name):
                        manager.get_effect(EffectType.DEST_DEF,
                                           eff.name).alter_dest_def(eff.mag)
                    else:
                        manager.add_effect(
                            Effect(
                                eff.source, EffectType.DEST_DEF, eff.user, 280000,
                                lambda eff: f"This character has {eff.mag} destructible defense.",
                                eff.mag))
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_UNIQUE)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    manager.check_unique_cont(eff)

    

    def confirm_button_click(self, _button, _sender):
        self.execution_loop()
        for attr, _ in self.offered_pool.items():
            self.offered_pool[attr] = 0
        self.turn_expend_region.clear()
        self.draw_turn_end_region()
        self.window_up = False
        self.turn_end()

    def tick_ability_cooldown(self):
        for manager in self.player_display.team.character_managers:
            for ability in manager.source.main_abilities:
                ability.cooldown_remaining = max(ability.cooldown_remaining - 1, 0)
            for ability in manager.source.alt_abilities:
                ability.cooldown_remaining = max(ability.cooldown_remaining - 1, 0)
            


    def any_expenditure_cancel_click(self, _button, _sender):
        for attr, energy in self.offered_pool.items():
            if energy > 0 and attr != Energy.RANDOM:
                self.round_any_cost += energy
                self.ally_energy_pool[attr] += energy
                self.offered_pool[attr] = 0
        self.turn_expend_region.clear()
        self.window_up = False
        self.draw_turn_end_region()

    def plus_button_click(self, button, _sender):
        attr = button.energy
        if self.player_display.team.energy_pool[attr] > 0 and self.round_any_cost > 0:
            self.player_display.team.energy_pool[attr] -= 1
            self.offered_pool[attr] += 1
            self.round_any_cost -= 1
        self.draw_any_cost_expenditure_window()

    def minus_button_click(self, button, _sender):
        attr = button.energy
        if self.offered_pool[attr] > 0:
            self.player_display.team.energy_pool[attr] += 1
            self.offered_pool[attr] -= 1
            self.round_any_cost += 1
        self.draw_any_cost_expenditure_window()

    def turn_end_button_click(self, _button, _sender):
        if not self.waiting_for_turn:
            self.reset_targeting()
            self.return_targeting_to_default()
            self.full_update()
            if self.round_any_cost == 0:
                self.execution_loop()
                self.turn_end()
            else:
                self.window_up = True
                self.turn_end_region.clear()
                self.draw_any_cost_expenditure_window()

    def turn_end(self):
        self.tick_effect_duration()
        self.tick_ability_cooldown()
        self.waiting_for_turn = True

        for manager in self.player_display.team.character_managers:
            manager.received_ability.clear()
        for manager in self.enemy_display.team.character_managers:
            manager.received_ability.clear()

        self.full_update()
        pouch1, pouch2 = self.pickle_match(self.player_display.team, self.enemy_display.team)

        match = MatchPouch(pouch1, pouch2)
        msg = pickle.dumps(match)
        self.scene_manager.connection.send_match_communication(msg)

    def pickle_match(self, team1: Team, team2: Team):
        team1_pouch = []
        for manager in team1.character_managers:
            effects_pouch = []
            character_pouch = []
            character_pouch.append(manager.source.hp)
            character_pouch.append(manager.source.energy_contribution)
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
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
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
                effect_pouch.append(effect.waiting)
                effects_pouch.append(effect_pouch)
            character_pouch.append(effects_pouch)
            team2_pouch.append(character_pouch)
        return (team1_pouch, team2_pouch)
    
    def unpickle_match(self, data: bytes):
        match = pickle.loads(data)
        
        team1pouch = match.team2_pouch
        team2pouch = match.team1_pouch
        for i, character_pouch in enumerate(team1pouch):
            self.player_display.team.character_managers[i].source.hp = character_pouch[0]
            self.player_display.team.character_managers[i].source.energy_contribution = character_pouch[1]
            self.player_display.team.character_managers[i].source.current_effects.clear()
            for j, effect_pouch in enumerate(character_pouch[2]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[effect_pouch[5]]
                
                effect = Effect(Ability(effect_pouch[4]), EffectType(effect_pouch[0]), user, effect_pouch[2], effect_pouch[3], effect_pouch[1], effect_pouch[6])
                effect.waiting = effect_pouch[7]
                self.player_display.team.character_managers[i].source.current_effects.append(effect)
        for i, character_pouch in enumerate(team2pouch):
            self.enemy_display.team.character_managers[i].source.hp = character_pouch[0]
            self.enemy_display.team.character_managers[i].source.energy_contribution = character_pouch[1]
            self.enemy_display.team.character_managers[i].source.current_effects.clear()
            for j, effect_pouch in enumerate(character_pouch[2]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[effect_pouch[5]]
                
                effect = Effect(Ability(effect_pouch[4]), EffectType(effect_pouch[0]), user, effect_pouch[2], effect_pouch[3], effect_pouch[1], effect_pouch[6])
                effect.waiting = effect_pouch[7]
                self.enemy_display.team.character_managers[i].source.current_effects.append(effect)
        self.turn_start()
        


    def tick_effect_duration(self):
        for manager in self.player_display.team.character_managers:
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.duration == 0:
                    if eff.name == "Quirk - Transform":
                        for effect in manager.source.current_effects:
                            if effect.user == manager:
                                manager.remove_effect(effect)
                        swap_hp = manager.source.hp
                        swap_effects = manager.source.current_effects
                        manager.source = Character("toga")
                        manager.source.hp = swap_hp
                        manager.source.current_effects = swap_effects
                    if eff.name == "Bunny Assault":
                        if manager.has_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit"):
                            manager.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").alter_dest_def(20)
                    if eff.name == "Lightning Dragon's Roar":
                        manager.add_effect(Effect(Ability("laxus2"), EffectType.ALL_DR, eff.user, 2, lambda eff: "This character will take 10 more damage.", mag=-10))
                    if eff.name == "Mahapadma" and eff.eff_type == EffectType.MARK:
                        manager.add_effect(Effect(Ability("esdeathalt1"), EffectType.ALL_STUN, manager, 5, lambda eff: "Esdeath is stunned."))
                    if eff.name == "Quickdraw - Rifle" and eff.eff_type == EffectType.CONT_USE:
                        manager.full_remove_effect("Quickdraw - Rifle", manager)
                        manager.add_effect(Effect(Ability("cmaryalt2"), EffectType.ABILITY_SWAP, manager, 280000, lambda eff: "Quickdraw - Rifle has been replaced by Quickdraw - Sniper", mag=12))
                    if eff.name == "Illusory Breakdown" and eff.mag > 0: 
                        for emanager in self.enemy_display.team.character_managers:
                            if emanager.has_effect(EffectType.MARK, "Illusory Breakdown") and emanager.get_effect(EffectType.MARK, "Illusory Breakdown").user == manager:
                                if emanager.final_can_effect(manager.check_bypass_effects()):
                                    manager.deal_eff_damage(25, emanager)
                                    emanager.add_effect(Effect(Ability("chrome2"), EffectType.ALL_STUN, manager, 2, lambda eff: "This character is stunned."))
                                    manager.check_on_stun(emanager)
                    if eff.name == "Mental Immolation" and eff.mag > 0: 
                        for emanager in self.enemy_display.team.character_managers:
                            if emanager.has_effect(EffectType.MARK, "Mental Immolation") and emanager.get_effect(EffectType.MARK, "Mental Immolation").user == manager:
                                if emanager.final_can_effect(manager.check_bypass_effects()):
                                    manager.deal_eff_damage(20, emanager)
                                    emanager.source.energy_contribution -= 1
                                    manager.check_on_drain(emanager)
                    if eff.name == "Mental Annihilation" and eff.mag > 0:
                        for emanager in self.enemy_display.team.character_managers:
                            if emanager.has_effect(EffectType.MARK, "Mental Annihilation") and emanager.get_effect(EffectType.MARK, "Mental Annihilation").user == manager:
                                if emanager.final_can_effect("BYPASS"):
                                    manager.deal_eff_damage(35, emanager)
                    if eff.name == "Illusory World Destruction" and eff.mag > 0:
                        for emanager in self.enemy_display.team.character_managers:
                            if emanager.final_can_effect(manager.check_bypass_effects()):
                                manager.deal_eff_damage(25, emanager)
                                emanager.add_effect(Effect(Ability("chromealt2"), EffectType.ALL_STUN, manager, 2, lambda eff: "This character is stunned."))
                                manager.check_on_stun(emanager)
            new_list = [eff for eff in manager.source.current_effects if eff.duration > 0]                
            manager.source.current_effects = new_list

        for manager in self.enemy_display.team.character_managers:
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.duration == 0:
                    if eff.invisible:
                        manager.add_effect(Effect(eff.source, EffectType.UNIQUE, eff.user, 2, lambda eff: f"{eff.name} has ended."))
            new_list = [eff for eff in manager.source.current_effects if eff.duration > 0]
            manager.source.current_effects = new_list


    def turn_start(self):
        self.waiting_for_turn = False
        self.round_any_cost = 0
        self.acting_character = None
        self.generate_energy()
        for manager in self.player_display.team.character_managers:
            manager.refresh_character()
        for manager in self.enemy_display.team.character_managers:
            manager.refresh_character(True)
        self.full_update()

    

    def generate_energy(self):
        total_energy = 0
        for manager in self.player_display.team.character_managers:
            pool = manager.check_energy_contribution()
            total_energy += pool[Energy.RANDOM.value]
            for i in range(4):
                self.player_display.team.energy_pool[i] += pool[i]
            manager.source.energy_contribution = 1
        for _ in range(total_energy):
            self.player_display.team.energy_pool[randint(0, 3)] += 1
            self.player_display.team.energy_pool[4] += 1
        
        self.update_energy_region()

    def update_energy_region(self):
        self.energy_region.clear()
        self.add_bordered_sprite(self.energy_region, self.sprite_factory.from_color(BLACK, self.energy_region.size()), WHITE, 0, 0)
        self.energy_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["PHYSICAL"])),
                                      x=5,
                                      y=6)

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

        self.energy_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["SPECIAL"])),
                                      x=60,
                                      y=6)

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

        self.energy_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["MENTAL"])),
                                      x=5,
                                      y=26)

        MENTAL_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.MENTAL]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(MENTAL_counter, x=17, y=20)

        self.energy_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["WEAPON"])),
                                      x=60,
                                      y=26)

        WEAPON_counter = self.create_text_display(
            self.font,
            "x " + f"{self.player_display.team.energy_pool[Energy.WEAPON]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=30,
            height=4)
        self.energy_region.add_sprite(WEAPON_counter, x=72, y=20)

        total_counter = self.create_text_display(
            self.font,
            "Total: " + f"{self.player_display.team.energy_pool[Energy.RANDOM]}",
            WHITE,
            BLACK,
            x=0,
            y=0,
            width=80,
            height=4)
        self.energy_region.add_sprite(total_counter, x=102, y=13)

    def handle_unique_startup(self, character: "CharacterManager"):
        if character.source.name == "gokudera":
            character.add_effect(Effect(Ability("gokudera1"), EffectType.STACK, character, 280000, lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.", mag=1))

    def setup_scene(self, ally_team: list[Character],
                                  enemy_team: list[Character]):
        self.region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        self.draw_turn_end_region()
        ally_roster: list[CharacterManager] = []
        enemy_roster: list[CharacterManager] = []
        for i, ally in enumerate(ally_team):
            char_manager = CharacterManager(ally, self)
            char_manager.id = i
            self.handle_unique_startup(char_manager)
            ally_roster.append(char_manager)
        for i, enemy in enumerate(enemy_team):
            char_manager = CharacterManager(enemy, self)
            char_manager.id = i + 3
            self.handle_unique_startup(char_manager)
            enemy_roster.append(char_manager)

        scene_ally_team = Team(ally_roster)
        scene_enemy_team = Team(enemy_roster)

        self.player_display.assign_team(scene_ally_team)
        self.enemy_display.assign_team(scene_enemy_team)

        self.generate_energy()
        self.update_energy_region()

        for manager in self.player_display.team.character_managers:
            manager.update()

        for manager in self.enemy_display.team.character_managers:
            manager.update_limited()

    def full_update(self):
        self.region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        self.player_display.update_display()
        self.enemy_display.update_display()
        self.update_energy_region()
        self.draw_turn_end_region()
        self.draw_effect_hover()

    def draw_effect_hover(self):
        self.hover_effect_region.clear()
        for manager in self.player_display.team.character_managers:
            manager.show_hover_text()
        for manager in self.enemy_display.team.character_managers:
            manager.show_hover_text()

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
        self.reset_targeting()
        self.acting_character.primary_target = primary_target
        self.selected_ability.user = self.acting_character
        self.acting_character.used_ability = self.selected_ability
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
    id: int

    def __init__(self, source: character.Character, scene: BattleScene):
        self.source = source
        self.scene = scene
        self.selected_ability = None
        self.used_ability = None
        self.targeted = False
        self.acted = False
        self.received_ability = []
        self.current_targets = []

    def get_ability_by_name(self, name: str) -> Optional[Ability]:
        for ability in self.source.current_abilities:
            if ability.name == name:
                return ability
        return None

    def update_text(self):
        
        self.text_region.clear()
        if self.selected_ability is not None:
            text_to_display = self.selected_ability.name + ": " + self.selected_ability.desc
            text_sprite = self.scene.create_text_display(self.scene.font,
                                                            text_to_display,
                                                            BLACK,
                                                            WHITE,
                                                            x=5,
                                                            y=0,
                                                            width=520,
                                                            height=110)
            self.scene.add_bordered_sprite(self.text_region, text_sprite, BLACK, 0, 0)
            energy_display_region = self.text_region.subregion(
                x=10,
                y=self.text_region.from_bottom(2),
                width=(4 + 10) * self.selected_ability.total_cost,
                height=10)
            cost_to_display: list[Energy] = sorted(self.selected_ability.cost_iter())
            energy_squares = [
                energy_display_region.subregion(x, y=0, width=10, height=10)
                for x in itertools.islice(range(0, 1000, 10 + 4),
                                            self.selected_ability.total_cost)
            ]
            for cost, energy_square in zip(cost_to_display, energy_squares):
                energy_surface = self.scene.surfaces[cost.name]
                energy_sprite = self.scene.sprite_factory.from_surface(self.scene.get_scaled_surface(energy_surface))
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
            text_to_display = self.source.desc
            text_sprite = self.scene.create_text_display(self.scene.font,
                                                            text_to_display,
                                                            BLACK,
                                                            WHITE,
                                                            x=5,
                                                            y=0,
                                                            width=520,
                                                            height=110)
            self.scene.add_bordered_sprite(self.text_region, text_sprite, BLACK, 0, 0)

    def adjust_targeting_types(self):
        for i, ability in enumerate(self.source.current_abilities):
            ability.target_type = Target(ability._base_target_type.value)
            gen = (eff for eff in self.source.current_effects
                   if eff.eff_type == EffectType.TARGET_SWAP)
            for eff in gen:
                ability_target = eff.mag // 10
                target_type = eff.mag - (ability_target * 10)
                if ability_target - 1 == i:
                    ability.target_type = Target(target_type)
            if ability.name == "Hyper Eccentric Ultra Great Giga Extreme Hyper Again Awesome Punch" and self.has_effect(EffectType.STACK, "Guts") and self.get_effect(EffectType.STACK, "Guts").mag >= 3:
                ability.target_type = Target.MULTI_ENEMY

    def adjust_ability_costs(self):
        for i, ability in enumerate(self.source.current_abilities):
            ability.reset_costs()
            if self.has_effect(EffectType.STACK, "Quirk - Half-Cold"):
                ability.modify_ability_cost(Energy(4), self.get_effect(EffectType.STACK, "Quirk - Half-Cold").mag)
            if ability.name == "Knight's Sword" and self.has_effect(EffectType.STACK, "Magic Sword"):
                ability.modify_ability_cost(Energy(4), self.get_effect(EffectType.STACK, "Magic Sword").mag)
            if ability.name == "Roman Artillery - Pumpkin" and self.source.hp < 30:
                ability.modify_ability_cost(Energy(3), -1)
            if ability.name == "Kangaryu" and self.has_effect(EffectType.STACK, "To The Extreme!"):
                if not self.has_effect(EffectType.MARK, "Vongola Headgear"):
                    ability.modify_ability_cost(Energy(4), self.get_effect(EffectType.STACK, "To The Extreme!").mag)
            if ability.name == "Maximum Cannon" and self.has_effect(EffectType.STACK, "To The Extreme!"):
                if not self.has_effect(EffectType.MARK, "Vongola Headgear"):
                    ability.modify_ability_cost(Energy(4), self.get_effect(EffectType.STACK, "To The Extreme!").mag)
            gen = (eff for eff in self.source.current_effects
                   if eff.eff_type == EffectType.COST_ADJUST)
            for eff in gen:
                negative_cost = False
                if eff.mag < 0:
                    negative_cost = True
                ability_to_modify = math.trunc(eff.mag / 100)
                cost_type = math.trunc((eff.mag - (ability_to_modify * 100)) / 10)
                magnitude = eff.mag - (ability_to_modify * 100) - (cost_type * 10)
                if negative_cost:
                    ability_to_modify = ability_to_modify * -1
                    cost_type = cost_type * -1
                if ability_to_modify - 1 == i or ability_to_modify == 0:
                    ability.modify_ability_cost(Energy(cost_type - 1), magnitude)
    
    def check_on_harm(self):
        for character in self.current_targets:
            if character.id > 2:
                if character.has_effect(EffectType.UNIQUE, "Hear Distress"):
                    character.source.energy_contribution += 1
                if character.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon") and not character.is_ignoring():
                    character.add_effect(Effect(Ability("gajeel3"), EffectType.IGNORE, character, 1, lambda eff: ""))
                if character.has_effect(EffectType.MARK, "Quirk - Permeation"):
                    character.add_effect(Effect(Ability("mirio2"), EffectType.MARK, character, 2, lambda eff: "This character will take 15 more piercing damage from Phantom Menace, and it will automatically target them."))
                if character.has_effect(EffectType.MARK, "Protect Ally"):
                    character.add_effect(Effect(Ability("mirio2"), EffectType.MARK, character, 2, lambda eff: "This character will take 15 more piercing damage from Phantom Menace, and it will automatically target them."))
                if character.has_effect(EffectType.DEST_DEF, "Four-God Resisting Shield"):
                    self.receive_eff_damage(15)
        if self.has_effect(EffectType.UNIQUE, "Porcospino Nuvola"):
            self.receive_eff_damage(10)
        
                    



    def check_on_help(self):
        for target in self.current_targets:
            if target.has_effect(EffectType.UNIQUE, "Tsukuyomi"):
                target.full_remove_effect("Tsukuyomi", target.get_effect(EffectType.UNIQUE, "Tsukuyomi").user)

    def check_on_use(self):
        for target in self.current_targets:
            if (target.has_effect(EffectType.MARK, "Shredding Wedding") and not self.has_effect(EffectType.MARK, "Shredding Wedding")) or (self.has_effect(EffectType.MARK, "Shredding Wedding") and not target.has_effect(EffectType.MARK, "Shredding Wedding")):
                if self.final_can_effect():
                    self.receive_pierce_damage(20)
        if self.has_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame"):
            self.get_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame").alter_mag(1)
            self.get_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame").desc = lambda eff: "This character will take 40 damage and Yamamoto will gain 3 stacks of Asari Ugetsu."
        if self.has_effect(EffectType.MARK, "Hidden Mine"):
            if self.final_can_effect():
                self.receive_eff_pierce_damage(20)
            self.full_remove_effect("Hidden Mine", self.get_effect(EffectType.MARK, "Hidden Mine").user)
        if self.has_effect(EffectType.MARK, "Illusory Disorientation"):
            self.full_remove_effect("Illusory Disorientation", self.get_effect(EffectType.MARK, "Illusory Disorientation").user)
        if self.has_effect(EffectType.MARK, "Solid Script - Fire"):
            self.receive_eff_aff_damage(10)

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

        if target.is_stunned():
            target.cancel_control_effects()


    def cancel_control_effects(self):
        for eff in self.source.current_effects:
            if eff.eff_type == EffectType.CONT_USE and eff.name == "Quickdraw - Rifle":
                self.remove_effect(self.get_effect(EffectType.CONT_USE, "Quickdraw - Rifle"))
                for manager in self.scene.player_display.team.character_managers:
                    manager.remove_effect(manager.get_effect(EffectType.CONT_DMG, "Quickdraw - Rifle"))
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.remove_effect(manager.get_effect(EffectType.CONT_DMG, "Quickdraw - Rifle"))
            elif eff.eff_type == EffectType.CONT_USE:
                self.full_remove_effect(eff.name, self)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect(eff.name, self)
                for manager in self.scene.enemy_display.team.character_managers:
                    manager.full_remove_effect(eff.name, self)
                

    def check_on_drain(self, target: "CharacterManager"):
        
        if target.has_effect(EffectType.MARK, "Counter-Balance"):
            self.add_effect(Effect(Ability("jiro1"), EffectType.ALL_STUN, target.get_effect(EffectType.MARK, "Counter-Balance").user, 3, lambda eff: "This character is stunned."))

    def check_damage_drain(self) -> int:
        gen = [eff for eff in self.source.current_effects if eff.eff_type == EffectType.ALL_BOOST and eff.mag < 0]

        total_drain = 0
        for eff in gen:
            total_drain += eff.mag
        
        return total_drain


    def check_unique_cont(self, eff: Effect):
        if eff.name == "Utsuhi Ame":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                self.receive_eff_damage(eff.mag * 20)
                if eff.mag == 1:
                    eff.user.apply_stack_effect(Effect(Ability("yamamoto3"), EffectType.STACK, eff.user, 280000, lambda eff: f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.", mag = 1))
                else:
                    eff.user.apply_stack_effect(Effect(Ability("yamamoto3"), EffectType.STACK, eff.user, 280000, lambda eff: f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.", mag = 3))
        if eff.name == "Vacuum Syringe":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                self.receive_eff_aff_damage(10)
                self.apply_stack_effect(Effect(Ability("toga3"), EffectType.STACK, eff.user, 280000, lambda eff: f"Toga has drawn blood from this character {eff.mag} time(s).", mag = 1), eff.user)
        if eff.name == "Decaying Touch":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                self.receive_eff_aff_damage((5 * (2 ** eff.mag)))
        if eff.name == "Nemurin Nap":
            eff.alter_mag(1)
            if eff.mag == 2:
                self.add_effect(Effect(Ability("nemu1"), EffectType.COST_ADJUST, eff.user, 280000, lambda eff:"Nemurin Beam will cost one less random energy.", mag = -251))
                self.add_effect(Effect(Ability("nemu1"), EffectType.COST_ADJUST, eff.user, 280000, lambda eff:"Dream Manipulation will cost one less random energy.", mag = -351))
            if eff.mag == 3:
                self.add_effect(Effect(Ability("nemu1"), EffectType.TARGET_SWAP, eff.user, 280000, lambda eff:"Nemurin Beam will target all enemies.", mag = 21))
                self.add_effect(Effect(Ability("nemu1"), EffectType.TARGET_SWAP, eff.user, 280000, lambda eff:"Dream Manipulation will target all allies.", mag = 31))
        if eff.name == "Eight Trigrams - 128 Palms":
            if self.final_can_effect(eff.user.check_bypass_effects()) and (not self.deflecting() or (2 * (eff.mag ** 2) > 15)):
                base_damage = (2 * (eff.mag ** 2))
                eff.user.deal_eff_damage(base_damage, self)
                eff.alter_mag(1)
                if self.has_effect(EffectType.MARK, "Chakra Point Strike") and base_damage > self.check_for_dmg_reduction():
                    self.source.energy_contribution -= 1
        if eff.name == "Relentless Assault":
            if self.final_can_effect(eff.user.check_bypass_effects()) and not self.deflecting():
                if self.check_for_dmg_reduction() < 15:
                    eff.user.deal_eff_pierce_damage(15, self)
                else:
                    eff.user.deal_eff_damage(15, self)
        if eff.name == "Titania's Rampage":
            valid_targets: list["CharacterManager"] = []
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()) and not enemy.deflecting():
                    valid_targets.append(enemy)
            if valid_targets:
                damage = 15 + (eff.mag * 5)
                target = randint(0, len(valid_targets) - 1)
                print(f"Dealing {damage} damage to {valid_targets[target].source.name}")
                self.deal_eff_pierce_damage(damage, valid_targets[target])
                eff.alter_mag(1)
        if eff.name == "Circle Blade":
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()) and not enemy.deflecting():
                    self.deal_eff_damage(15, enemy)
        if eff.name == "Butou Renjin":
            if self.final_can_effect(eff.user.check_bypass_effects()) and not self.deflecting():
                eff.user.deal_eff_damage(15, self)
                self.apply_stack_effect(Effect(Ability("ichimaru3"), EffectType.STACK, eff.user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1), eff.user)

    def check_countered(self, pteam: list["CharacterManager"], eteam: list["CharacterManager"]) -> bool:

        def is_harmful(self: "CharacterManager", eteam: list["CharacterManager"]) -> bool:
            for enemy in eteam:
                if eteam in self.current_targets:
                    return True
            return False

        if is_harmful(self, eteam):
            if not self.has_effect(EffectType.MARK, "Mental Radar"):
                #self reflect effects:
                gen = (eff for eff in self.source.current_effects
                    if eff.eff_type == EffectType.REFLECT and not self.scene.is_allied(eff))
                for eff in gen:
                    pass

                #self counter check
                gen = (eff for eff in self.source.current_effects if eff.eff_type == EffectType.COUNTER and not self.scene.is_allied(eff))
                for eff in gen:
                    if eff.name == "Hear Distress":
                        src = Ability("snowwhite2")
                        self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Hear Distress."))
                        self.source.energy_contribution -= 1
                        eff.user.check_on_drain(self)
                        if self.has_effect(EffectType.MARK, "Third Dance - Shirafune"):
                            self.full_remove_effect("Third Dance - Shirafune", self)
                            if eff.user.final_can_effect():
                                eff.user.receive_eff_damage(30)
                                eff.user.add_effect(Effect(Ability("rukia3"), EffectType.ALL_STUN, self, 2, lambda eff: "This character is stunned."))
                                self.check_on_stun(eff.user)
                        return True
                
                #target counter check
                for target in self.current_targets:

                    gen = (eff for eff in target.source.current_effects if eff.eff_type == EffectType.COUNTER and not self.scene.is_allied(eff))
                    for eff in gen:
                        if eff.name == "Zero Point":
                            src = Ability("tsunayoshi3")
                            self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Zero Point Breakthrough."))
                            self.add_effect(Effect(src, EffectType.ALL_STUN, eff.user, 5, lambda eff: "This character is stunned."))
                            eff.user.add_effect(Effect(src, EffectType.ALL_BOOST, eff.user, 4, lambda eff: "X-Burner will deal 10 more damage.", mag = 110))
                            if self.has_effect(EffectType.MARK, "Third Dance - Shirafune"):
                                self.full_remove_effect("Third Dance - Shirafune", self)
                                if target.final_can_effect():
                                    target.receive_eff_damage(30)
                                    target.add_effect(Effect(Ability("rukia3"), EffectType.ALL_STUN, self, 2, lambda eff: "This character is stunned."))
                                    self.check_on_stun(target)
                            return True
                        if eff.name == "One For All - Shoot Style":
                            src = Ability("midoriya3")
                            self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by One For All - Shoot Style."))
                            if self.has_effect(EffectType.MARK, "Third Dance - Shirafune"):
                                self.full_remove_effect("Third Dance - Shirafune", self)
                                if target.final_can_effect():
                                    target.receive_eff_damage(30)
                                    target.add_effect(Effect(Ability("rukia3"), EffectType.ALL_STUN, self, 2, lambda eff: "This character is stunned."))
                                    self.check_on_stun(target)
                            return True
                        if eff.name == "Minion - Tama":
                            src = Ability("ruler3")
                            self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Minion - Tama."))
                            eff.user.source.main_abilities[2].cooldown_remaining = 2
                            if not self.final_can_effect():
                                self.receive_eff_pierce_damage(20)
                            if self.has_effect(EffectType.MARK, "Third Dance - Shirafune"):
                                self.full_remove_effect("Third Dance - Shirafune", self)
                                if target.final_can_effect():
                                    target.receive_eff_damage(30)
                                    target.add_effect(Effect(Ability("rukia3"), EffectType.ALL_STUN, self, 2, lambda eff: "This character is stunned."))
                                    self.check_on_stun(target)
                            return True
                        if eff.name == "Casseur de Logistille":
                            src = Ability("astolfo1")
                            if self.used_ability._base_cost[Energy.SPECIAL] > 0 or self.used_ability._base_cost[Energy.MENTAL] > 0:
                                self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Casseur de Logistille."))
                                if not self.final_can_effect():
                                    self.add_effect(Effect(src, EffectType.ALL_STUN, eff.user, 3, lambda eff: "This character is stunned."))
                                    self.add_effect(Effect(src, EffectType.ISOLATE, eff.user, 3, lambda eff: "This character is isolated."))
                                    eff.user.check_on_stun(self)
                                if self.has_effect(EffectType.MARK, "Third Dance - Shirafune"):
                                    self.full_remove_effect("Third Dance - Shirafune", self)
                                    if target.final_can_effect():
                                        target.receive_eff_damage(30)
                                        target.add_effect(Effect(Ability("rukia3"), EffectType.ALL_STUN, self, 2, lambda eff: "This character is stunned."))
                                        self.check_on_stun(target)
                                return True
                    
                    gen = (eff for eff in target.source.current_effects
                    if eff.eff_type == EffectType.REFLECT and not self.scene.is_allied(eff))
                    for eff in gen:
                        if eff.name == "Copy Ninja Kakashi":
                            alt_targets = [char for char in self.current_targets if char != target]
                            alt_targets.append(self) 
                            self.current_targets = alt_targets
                            self.used_ability.execute(self, pteam, eteam)
                            return True


        return False

    def check_on_damage_dealt(self, target: "CharacterManager"):
        #TODO check user effects

        #TODO check target effects
        if target.has_effect(EffectType.ALL_DR, "Arrest Assault"):
            target.get_effect(EffectType.ALL_DR, "Arrest Assault").user.get_effect(EffectType.UNIQUE, "Arrest Assault").alter_mag(1)
        if target.has_effect(EffectType.MARK, "Doll Trap"):
            target_dolls = [eff for eff in target.source.current_effects if eff.eff_type == EffectType.STACK and eff.name == "Doll Trap"]
            for eff in target_dolls:
                if not self.has_effect_with_user(EffectType.MARK, "Doll Trap", eff.user):
                    self.add_effect(Effect(Ability("frenda2"), EffectType.MARK, eff.user, 280000, lambda leff: f"If an enemy damages this character, all stacks of Doll Trap will be transferred to them.", invisible=True))
                self.apply_stack_effect(Effect(Ability("frenda2"), EffectType.STACK, eff.user, 280000, lambda leff: f"Detonate will deal {20 * leff.mag} damage to this character.", mag=eff.mag, invisible=True), eff.user)
                target.full_remove_effect("Doll Trap", eff.user)
        if target.has_effect(EffectType.ALL_DR, "Conductivity"):
            target.get_effect(EffectType.ALL_DR, "Conductivity").user.receive_eff_damage(10)

        if target.source.hp <= 0:
            if self.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct"):
                self.get_effect(EffectType.STUN_IMMUNE, "Beast Instinct").duration = 5
            if target.has_effect(EffectType.MARK, "Beast Instinct"):
                self.receive_eff_healing(20)

    def apply_stack_effect(self, effect: Effect, user: "CharacterManager"):
        gen = [eff for eff in self.source.current_effects if (eff.eff_type == effect.eff_type and eff.name == effect.name and eff.user == user)]
        if gen:
            for eff in gen:
                eff.alter_mag(effect.mag)
        else:
            self.add_effect(effect)        

    def get_dest_def_total(self) -> int:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEST_DEF)
        dest_def = 0
        for eff in gen:
            dest_def += eff.mag
        return dest_def

    def will_die(self, damage:int) -> bool:
        total_life = self.get_dest_def_total() + self.source.hp
        return damage >= total_life

    def deal_damage(self, damage: int, target: "CharacterManager"):
        mod_damage = self.get_boosts(damage)

        if mod_damage > target.check_for_dmg_reduction():
            if self.has_effect(EffectType.UNIQUE, "Three-God Empowering Shield"):
                self.receive_eff_healing(10)

        target.receive_damage(mod_damage)

        if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
            self.receive_eff_damage(mod_damage)
            target.full_remove_effect("Thunder Palace", target)
        if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
            user = target.get_effect(EffectType.UNIQUE, "Burning Axle").user
            target.full_remove_effect("Burning Axle", user)
            target.add_effect(Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
            user.check_on_stun(target)

        self.check_on_damage_dealt(target)

    def receive_damage(self, damage: int):
        mod_damage = damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True

        mod_damage = self.pass_through_dest_def(mod_damage)
        
        
        self.source.hp -= mod_damage
        
        if mod_damage > 0:
            self.damage_taken_check(mod_damage)
            if self.has_effect(EffectType.MARK, "Electric Rage"):
                self.scene.player_display.team.energy_pool[Energy.SPECIAL] += 1

        self.death_check()

    def deal_eff_damage(self, damage: int, target: "CharacterManager"):
        damage = self.get_boosts(damage)
        target.receive_eff_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_eff_damage(self, damage: int):
        mod_damage = damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True

        mod_damage = self.pass_through_dest_def(mod_damage)
        self.source.hp -= mod_damage
        if mod_damage > 0:
            self.damage_taken_check(mod_damage)
        
        self.death_check()

    def deal_pierce_damage(self, damage: int, target: "CharacterManager"):
        mod_damage = self.get_boosts(damage)

        if mod_damage > target.check_for_dmg_reduction():
            if self.has_effect(EffectType.UNIQUE, "Three-God Empowering Shield"):
                self.receive_eff_healing(10)

        target.receive_pierce_damage(mod_damage)

        if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
            self.receive_eff_damage(mod_damage)
            target.full_remove_effect("Thunder Palace", target)
        if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
            user = target.get_effect(EffectType.UNIQUE, "Burning Axle").user
            target.full_remove_effect("Burning Axle", user)
            target.add_effect(Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
            user.check_on_stun(target)

        self.check_on_damage_dealt(target)

    def receive_pierce_damage(self, damage: int):
        mod_damage = damage
        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2
        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True

        

        mod_damage = self.pass_through_dest_def(mod_damage)
        self.source.hp -= mod_damage
        if mod_damage > 0:
            self.damage_taken_check(mod_damage)
            if self.has_effect(EffectType.MARK, "Electric Rage"):
                self.scene.player_display.team.energy_pool[Energy.SPECIAL] += 1
        
        self.death_check()

    

    def deal_eff_pierce_damage(self, damage: int, target: "CharacterManager"):
        damage = self.get_boosts(damage)
        target.receive_eff_pierce_damage(damage)
        self.check_on_damage_dealt(target)

    

    def receive_eff_pierce_damage(self, damage: int):
        mod_damage = damage

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True
        mod_damage = self.pass_through_dest_def(mod_damage)
        self.source.hp -= mod_damage
        if mod_damage > 0:
            self.damage_taken_check(mod_damage)
        if self.source.hp <= 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_aff_damage(self, damage: int, target: "CharacterManager"):
        #TODO check for affliction boosts

        if not target.is_aff_immune():
            
            if self.has_effect(EffectType.UNIQUE, "Three-God Empowering Shield"):
                self.receive_eff_healing(10)

            target.receive_aff_dmg(damage)

            if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
                self.receive_eff_damage(damage)
                target.full_remove_effect("Thunder Palace", target)
            if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
                user = target.get_effect(EffectType.UNIQUE, "Burning Axle").user
                target.full_remove_effect("Burning Axle", user)
                target.add_effect(Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)

            self.check_on_damage_dealt(target)

    def receive_aff_dmg(self, damage: int):
        #TODO add affliction damage received boosts
        mod_damage = damage

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True
        self.source.hp -= mod_damage

        if mod_damage > 0:
            self.damage_taken_check(mod_damage)
            if self.has_effect(EffectType.MARK, "Electric Rage"):
                self.scene.player_display.team.energy_pool[Energy.SPECIAL] += 1
            

        self.death_check()

    def deal_eff_aff_damage(self, damage: int, target: "CharacterManager"):
        #TODO add affliction damage boosts
        if not target.is_aff_immune():
            target.receive_eff_aff_damage(damage)
            self.check_on_damage_dealt(target)

    def receive_eff_aff_damage(self, damage: int):
        #TODO add affliction damage received boosts
        mod_damage = damage

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2
        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius"):
                mod_damage = 0
                self.add_effect(Effect(Ability("neji3"), EffectType.ALL_BOOST, self.get_effect(EffectType.MARK, "Selfless Genius").user, 2, lambda eff: "This character will deal 10 more damage with non-affliction abilities.", mag = 10))
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.hp = 0
                self.get_effect(EffectType.MARK, "Selfless Genius").user.source.dead = True
        self.source.hp -= mod_damage

        if mod_damage > 0:
            self.damage_taken_check(mod_damage)

        self.death_check()

    def get_boosts(self, damage: int) -> int:
        mod_damage = damage
        no_boost = False
        which = 0
        for i, ability in enumerate(self.source.current_abilities):
            if self.used_ability == ability:
                which = i + 1
                if ability.name == "Knight's Sword" and self.has_effect(EffectType.STACK, "Magic Sword"):
                    mod_damage += (20 * self.get_effect(EffectType.STACK, "Magic Sword").mag)
                if ability.name == "Maximum Cannon" and self.has_effect(EffectType.STACK, "To The Extreme!"):
                    mod_damage += (15 * self.get_effect(EffectType.STACK, "To The Extreme!").mag)
        
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.BOOST_NEGATE)
        for eff in gen:
            no_boost = True
            break

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
            if self.has_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!") and not no_boost:
                mod_damage += (self.get_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!").mag * 5)

        return mod_damage

    def can_boost(self) -> bool:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.BOOST_NEGATE)
        for eff in gen:
            return False
        return True

    def has_boosts(self) -> bool:
        gen = (eff for eff in self.source.current_effects if eff.eff_type == EffectType.ALL_BOOST)
        for eff in gen:
            if eff.mag > 0:
                return True
        
        if self.has_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!"):
            return True
        if self.has_effect(EffectType.STACK, "Zangetsu Strike"):
            return True
        if self.has_effect(EffectType.MARK, "Teleporting Strike"):
            return True
        if self.has_effect(EffectType.STACK, "Magic Sword"):
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

    def check_for_cooldown_mod(self) -> int:
        cd_mod = 0
        which = 0
        
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.COOLDOWN_MOD)
        for i, ability in enumerate(self.source.current_abilities):
            if self.used_ability == ability:
                if ability.name == "Knight's Sword" and self.has_effect(EffectType.STACK, "Magic Sword"):
                    cd_mod += self.get_effect(EffectType.STACK, "Magic Sword").mag
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
        gen = (eff for eff in self.source.current_effects if eff.eff_type == eff_type)
        for eff in gen:
            if eff.name == eff_name:
                return eff

    def get_effect_with_user(self, eff_type: EffectType, eff_name: str, user: "CharacterManager"):
        gen = (eff for eff in self.source.current_effects if eff.eff_type == eff_type and eff.user == user)
        for eff in gen:
            if eff.name == eff_name:
                return eff

    def has_effect_with_user(self, eff_type: EffectType, eff_name: str, user: "CharacterManager") -> bool:
        gen = (eff for eff in self.source.current_effects if eff.eff_type == eff_type and eff.user == user)
        for eff in gen:
            if eff.name == eff_name:
                return True
        return False

    def get_ability(self, name: str):
        for ability in self.source.current_abilities:
            if ability.name == name:
                return ability

    def has_effect(self, eff_type: EffectType, eff_name: str) -> bool:
        gen = (eff for eff in self.source.current_effects if eff.eff_type == eff_type)
        for eff in gen:
            if eff.name == eff_name:
                return True
        return False

    def check_for_collapsing_dest_def(self, eff: Effect):
        if eff.mag == 0:
            if eff.name == "Five-God Inviolate Shield":
                self.full_remove_effect("Five-God Inviolate Shield", eff.user)
                for manager in self.scene.player_display.team.character_managers:
                    manager.full_remove_effect("Five-God Inviolate Shield", eff.user)
            if eff.name == "Four-God Resisting Shield":
                self.full_remove_effect("Four-God Resisting Shield", eff.user)
            if eff.name == "Three-God Linking Shield":
                self.full_remove_effect("Three-God Linking Shield", eff.user)
            if eff.name == "Perfect Paper - Rampage Suit":
                self.full_remove_effect("Perfect Paper - Rampage Suit", eff.user)
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
            eff.alter_dest_def(-dmg)
            self.check_for_collapsing_dest_def(eff)
            dmg = engine.sat_subtract(current_def, dmg)
            if dmg == 0:
                return dmg
        return dmg

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

    def damage_taken_check(self, damage: int):
        if self.source.name == "seiryu" and self.source.hp < 30:
            self.add_effect(Effect(Ability("seiryualt1"), EffectType.ABILITY_SWAP, self, 280000, lambda eff: "Body Modification - Arm Gun has been replaced by Body Modification - Self Destruct.", mag = 11))
        if self.has_effect(EffectType.MARK, "To The Extreme!"):
            extreme = self.get_effect(EffectType.MARK, "To The Extreme!")
            extreme.alter_mag(damage)
            if extreme.mag > 20:
                stacks = extreme.mag // 20
                extreme.alter_mag(-(stacks * 20))
                self.apply_stack_effect(Effect(Ability("ryohei4"), EffectType.STACK, self, 280000, lambda eff: f"Maximum Cannon will deal {eff.mag * 15} more damage and cost {eff.mag} more random energy.", mag=stacks))
                self.apply_stack_effect(Effect(Ability("ryohei4"), EffectType.STACK, self, 280000, lambda eff: f"Kangaryu will heal {eff.mag * 20} more health and cost {eff.mag} more random energy.", mag=stacks))
        if self.has_effect(EffectType.CONT_UNIQUE, "Nemurin Nap"):
            self.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").alter_mag(-1)
            if self.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").mag == 2:
                self.remove_effect(self.get_effect(EffectType.TARGET_SWAP, "Nemurin Nap"))
                self.remove_effect(self.get_effect(EffectType.TARGET_SWAP, "Nemurin Nap"))
            if self.get_effect(EffectType.CONT_UNIQUE, "Nemurin Nap").mag == 1:
                self.remove_effect(self.get_effect(EffectType.COST_ADJUST, "Nemurin Nap"))
                self.remove_effect(self.get_effect(EffectType.COST_ADJUST, "Nemurin Nap"))
        if self.has_effect(EffectType.MARK, "You Are Needed") and self.source.hp < 30:
            self.full_remove_effect("You Are Needed", self)
            src = Ability("chrome1")
            self.add_effect(Effect(src, EffectType.PROF_SWAP, self, 280000, lambda eff: "Rokudou Mukuro has intervened, replacing Chrome for the rest of the match.", mag=1))
            self.add_effect(Effect(src, EffectType.ABILITY_SWAP, self, 280000, lambda eff: "You Are Needed has been replaced by Trident Combat.", mag=11))
            self.add_effect(Effect(src, EffectType.ABILITY_SWAP, self, 280000, lambda eff: "Illusory Breakdown has been replaced by Illusory World Destruction.", mag=22))
            self.add_effect(Effect(src, EffectType.ABILITY_SWAP, self, 280000, lambda eff: "Mental Immolation has been replaced by Mental Annihilation.", mag=33))
            self.add_effect(Effect(src, EffectType.ABILITY_SWAP, self, 280000, lambda eff: "Mental Substitution has been replaced by Trident Deflection.", mag=44))
            if self.has_effect(EffectType.DEST_DEF, "Illusory Breakdown"):
                self.remove_effect(self.get_effect(EffectType.DEST_DEF, "Illusory Breakdown"))
            if self.has_effect(EffectType.DEST_DEF, "Mental Immolation"):
                self.remove_effect(self.get_effect(EffectType.DEST_DEF, "Mental Immolation"))
            for manager in self.scene.enemy_display.team.character_managers:
                if manager.has_effect(EffectType.MARK, "Illusory Breakdown") and manager.get_effect(EffectType.MARK, "Illusory Breakdown").user == self:
                    manager.remove_effect(manager.get_effect(EffectType.MARK, "Illusory Breakdown"))
                if manager.has_effect(EffectType.MARK, "Mental Immolation") and manager.get_effect(EffectType.MARK, "Mental Immolation").user == self:
                    manager.remove_effect(manager.get_effect(EffectType.MARK, "Mental Immolation"))
        if self.has_effect(EffectType.CONT_AFF_DMG, "Susano'o"):
            if self.source.hp < 20 or self.get_effect(EffectType.DEST_DEF, "Susano'o").mag <= 0:
                self.full_remove_effect("Susano'o", self)


    def deflecting(self) -> bool:
        return self.has_effect(EffectType.MARK, "Flashing Deflection")

    

    def death_check(self):

        if self.source.hp <= 0:
            if self.has_effect(EffectType.MARK, "Electric Rage"):
                self.source.hp = 1
            elif self.has_effect(EffectType.MARK, "Lucky Rabbit's Foot"):
                self.source.hp = 35
            else:
                self.source.hp = 0
                self.source.dead = True
                self.source.current_effects.clear()


    def check_energy_contribution(self) -> list[int]:
        output = [0, 0, 0, 0, 0]
        output[4] += self.source.energy_contribution
        gen = [eff for eff in self.source.current_effects if eff.eff_type == EffectType.ENERGY_GAIN]
        for eff in gen:
            negative = False
            if eff.mag < 0:
                negative = True
            energy_type = math.trunc(eff.mag / 10) - 1
            if negative:
                energy_type = energy_type * -1
            mod_value = eff.mag - (energy_type * 10)
            output[energy_type] += mod_value
        return output

    def give_healing(self, healing: int, target: "CharacterManager"):
        #TODO add healing boosts
        mod_healing = healing

        if self.used_ability.name == "Kangaryu":
            if self.has_effect(EffectType.STACK, "To The Extreme!"):
                mod_healing += (20 * self.get_effect(EffectType.STACK, "To The Extreme!").mag)

        target.receive_healing(mod_healing)

    def receive_healing(self, healing: int):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation

        if self.source.name == "seiryu" and self.source.hp >= 30:
            self.full_remove_effect("Body Modification - Self Destruct", self)

        self.source.hp += mod_healing
        if self.source.hp > 100:
            self.source.hp = 100

    def give_eff_healing(self, healing: int, target: "CharacterManager"):
        #TODO add healing boosts
        target.receive_eff_healing(healing)

    def receive_eff_healing(self, healing: int):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation
        self.source.hp += mod_healing
        if self.source.hp > 100:
            self.source.hp = 100

    def check_isolated(self) -> bool:
        return any(eff.eff_type == EffectType.ISOLATE for eff in self.source.current_effects)

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

    def special_targeting_exemptions(self, targeter: "CharacterManager") -> bool:
        target = self
        if targeter.has_effect(EffectType.MARK, "Frozen Castle") and not target.has_effect(EffectType.UNIQUE, "Frozen Castle"):
            return True
        if not targeter.has_effect(EffectType.MARK, "Frozen Castle") and target.has_effect(EffectType.UNIQUE, "Frozen Castle"):
            return True
        if not targeter.has_effect(EffectType.UNIQUE, "Frozen Castle") and target.has_effect(EffectType.MARK, "Frozen Castle"):
            return True
        if targeter.has_effect(EffectType.UNIQUE, "Streets of the Lost") and targeter != targeter.get_effect(EffectType.UNIQUE, "Streets of the Lost").user:
            return True
        return False

    def hostile_target(self, targeter: "CharacterManager", def_type = "NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_invuln() or self.has_effect(EffectType.UNIQUE, "Shadow Pin") or self.source.dead or self.source.untargetable or self.special_targeting_exemptions(targeter))
        elif def_type == "BYPASS":
            return not (self.source.dead or self.has_effect(EffectType.UNIQUE, "Shadow Pin") or self.source.untargetable or self.special_targeting_exemptions(targeter))

    def final_can_effect(self, def_type = "NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_invuln() or self.source.dead or self.is_ignoring())
        elif def_type == "BYPASS":
            return not (self.source.dead or self.is_ignoring())
        elif def_type == "FULLBYPASS":
            return not (self.source.dead)

    def is_ignoring(self) -> bool:
        for effect in self.source.current_effects:
            if effect.eff_type == EffectType.IGNORE:
                return True
        return False

    def helpful_target(self, targeter: "CharacterManager", def_type = "NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.check_isolated() or self.source.dead or self.special_targeting_exemptions(targeter))
        elif def_type == "BYPASS":
            return not (self.source.dead or self.special_targeting_exemptions(targeter))

    def add_effect(self, effect: Effect):
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
            effect_sprite = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON,
                                                               self.scene.get_scaled_surface(effect_set[0].eff_img, 25, 25))
            effect_sprite.effects = effect_set
            effect_sprite.ID = f"{idx}/{self.id}"
            effect_sprite.is_enemy = self.is_enemy()
            effect_sprite.click += self.set_current_effect
            self.scene.add_bordered_sprite(self.effect_region, effect_sprite, BLACK, row * x_offset, column * y_offset)

    def set_current_effect(self, button, _sender):
        if self.scene.current_button == None or self.scene.current_button.ID != button.ID:
            self.scene.current_button = button
        else:
            self.scene.current_button = None
            self.scene.hover_effect_region.clear()
        self.scene.full_update()

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

    def show_hover_text(self):
        if self.scene.current_button is not None and self.is_in_bounds():
            self.scene.hover_effect_region.clear()
            max_line_width = 270
            base_height = 50
            additional_height = 0
            for effect in self.scene.current_button.effects:
                additional_height += len(textwrap.wrap(effect.get_desc(), 35))
            hover_panel_sprite = self.scene.sprite_factory.from_color(WHITE,
                                                                      size=(max_line_width,
                                                                            base_height + (additional_height * 18) + (len(self.scene.current_button.effects) * 20)))
            mouse_x, mouse_y = engine.get_mouse_position()
            self.scene.hover_effect_region.x = mouse_x - hover_panel_sprite.size[
                0] if self.scene.current_button.is_enemy else mouse_x
            if self.scene.current_button.y > 600:
                self.scene.hover_effect_region.y = mouse_y - (base_height + (additional_height * 18) + (len(self.scene.current_button.effects) * 20))
            else:
                self.scene.hover_effect_region.y = mouse_y
            self.scene.add_bordered_sprite(self.scene.hover_effect_region, hover_panel_sprite, BLACK, 0, 0)
            effect_lines = self.get_effect_lines(self.scene.current_button.effects)
            self.scene.hover_effect_region.add_sprite(effect_lines[0], 5, 5)
            effect_lines.remove(effect_lines[0])
            effect_y = 26
            is_duration = False
            
            for effect in effect_lines:
                is_duration = not is_duration
                if is_duration:
                    effect_x = 265 - effect.size[0]
                else:
                    effect_x = 0
                self.scene.hover_effect_region.add_sprite(effect, effect_x, effect_y)
                effect_y += effect.size[1] - 5
            

    def get_effect_lines(self, effect_list: list[Effect]) -> list[sdl2.ext.SoftwareSprite]:
        output: list[sdl2.ext.SoftwareSprite] = []
        
        output.append(
            self.scene.create_text_display(self.scene.font, effect_list[0].name, BLUE, WHITE, 0, 0,
                                           260))

        for i, effect in enumerate(effect_list):
            output.append(
                self.scene.create_text_display(self.scene.font,
                                               self.get_duration_string(effect.duration), RED,
                                               WHITE, 0, 0,
                                               len(self.get_duration_string(effect.duration) * 8)))
            output.append(
                self.scene.create_text_display(self.scene.font, effect.get_desc(), BLACK, WHITE, 5,
                                               0, 270))

        
        return output

    def get_duration_string(self, duration: int) -> str:
        if (duration // 2) > 10000:
            return "Infinite"
        elif (duration // 2) > 0:
            return f"{duration // 2} turns remaining"
        else:
            return "Ends this turn"

    def make_effect_clusters(self) -> dict[str, list[Effect]]:
        output: dict[str, list[Effect]] = {}
        for effect in self.source.current_effects:
            if effect.eff_type == EffectType.DEST_DEF and effect.mag == 0:
                continue
            if effect.invisible == True and effect.user.is_enemy():
                continue
            if effect.name in output.keys() and effect.user == output[effect.name][0].user:
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
        if self.source.hp == 100:
            hp_bar = self.scene.sprite_factory.from_color(GREEN, size=(100, 20))
        elif self.source.hp == 0:
            hp_bar = self.scene.sprite_factory.from_color(RED, size=(100, 20))
        else:
            hp_bar = self.scene.sprite_factory.from_color(BLACK, size=(100, 20))
            green_bar = self.scene.sprite_factory.from_color(GREEN, size=(self.source.hp, 20))
            red_bar = self.scene.sprite_factory.from_color(RED, size=(100 - self.source.hp, 20))
            sdl2.surface.SDL_BlitSurface(green_bar.surface, None, hp_bar.surface,
                                         sdl2.SDL_Rect(0, 0, 0, 0))
            sdl2.surface.SDL_BlitSurface(red_bar.surface, None, hp_bar.surface,
                                         sdl2.SDL_Rect(self.source.hp + 1, 0, 0, 0))
        hp_text = sdl2.sdlttf.TTF_RenderText_Blended(self.scene.font,
                                                     str.encode(f"{self.source.hp}"), BLACK)

        if self.source.hp == 100:
            hp_text_x = 38
        elif self.source.hp > 9:
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
        self.targeted = False
        self.targeting = False
        for ability in self.source.current_abilities:
            ability.reset_cooldown()
        if enemy:
            self.update_limited()
        else:
            self.update()

    def add_received_ability(self, ability: Ability):
        self.received_ability.append(ability)

    def update(self):
        self.character_region.clear()
        self.update_profile()
        self.adjust_ability_costs()
        self.update_ability()
        self.update_targeted_sprites()
        self.update_text()
        self.update_effect_region()
        self.draw_hp_bar()

    def update_limited(self):
        self.character_region.clear()
        self.adjust_ability_costs()
        self.update_enemy_profile()
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
                self.source.profile_image = self.source.altprof1
            elif eff.mag == 2:
                self.source.profile_image = self.source.altprof2

    def update_profile(self):

        self.source.profile_image = self.source.main_prof
        self.check_profile_swaps()

        if self.targeted:
            profile_sprite = self.scene.create_selected_version(self.scene.get_scaled_surface(self.source.profile_image),
                                                                engine.FilterType.SELECTED)
        else:
            profile_sprite = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON,
                                                                self.scene.get_scaled_surface(self.source.profile_image))
        profile_sprite.click += self.profile_click
        self.scene.add_bordered_sprite(self.character_region, profile_sprite, BLACK, 0, 0)

    def update_enemy_profile(self):

        self.source.profile_image = self.source.main_prof
        self.check_profile_swaps()

        if self.targeted:
            profile_sprite = self.scene.create_selected_version(self.scene.get_scaled_surface(self.source.profile_image, flipped = True),
                                                                engine.FilterType.SELECTED)
        else:
            profile_sprite = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON,
                                                                self.scene.get_scaled_surface(self.source.profile_image, flipped = True))
        profile_sprite.click += self.profile_click
        self.scene.add_bordered_sprite(self.character_region, profile_sprite, BLACK, 0, 0)

    def update_targeted_sprites(self):
        vertical_offset = 12
        for idx, ability in enumerate(self.received_ability):
            target_sprite = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON, self.scene.get_scaled_surface(ability.image, 25, 25))
            target_sprite.idx = idx
            target_sprite.click += self.target_sprite_click
            self.scene.add_bordered_sprite(self.targeting_region, target_sprite, BLACK, 0, (vertical_offset * idx) + (idx * 25))

    def target_sprite_click(self, button, _sender):
        self.scene.remove_targets(self.received_ability[button.idx])

    def profile_click(self, _button, _sender):
        if self.scene.selected_ability is not None and self.targeted:
            self.scene.expend_energy(self.scene.selected_ability)
            self.scene.apply_targeting(self)
            self.scene.return_targeting_to_default()
        self.scene.full_update()

    def set_selected_ability(self, button, _sender):
        self.selected_ability = button.ability
        self.scene.reset_targeting()
        if button.ability.can_use(self.scene,
                                  self) and not self.acted:
            self.scene.selected_ability = button.ability
            self.scene.acting_character = self
            button.ability.target(self, self.scene.player_display.team.character_managers,
                                  self.scene.enemy_display.team.character_managers)
        else:
            self.scene.selected_ability = None
            self.scene.acting_character = None
        self.scene.full_update()
            
    
    



    def check_ability_swaps(self):
        self.source.current_abilities = copy.copy(self.source.main_abilities)
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ABILITY_SWAP)
        for eff in gen:
            swap_from = eff.mag // 10
            swap_to = eff.mag - (swap_from * 10)
            self.source.current_abilities[swap_from - 1] = copy.copy(self.source.alt_abilities[swap_to - 1])

    def update_ability(self):

        
        
        self.check_ability_swaps()
        self.adjust_targeting_types()
        

        for i, chosen_ability in enumerate(self.source.current_abilities):

            if chosen_ability == self.scene.selected_ability:
                ability_button = self.scene.create_selected_version(self.scene.get_scaled_surface(chosen_ability.image),
                                                                    engine.FilterType.SELECTED)
            else:
                if chosen_ability.can_use(self.scene, self) and not self.acted:
                    ability_button = self.scene.ui_factory.from_surface(
                        sdl2.ext.BUTTON, self.scene.get_scaled_surface(chosen_ability.image))
                else:
                    if chosen_ability.cooldown_remaining > 0:
                        ability_button = self.scene.create_selected_version(
                            self.stamp_cooldown(chosen_ability.cooldown_remaining, self.scene.get_scaled_surface(chosen_ability.image)),
                            engine.FilterType.LOCKED)
                    else:
                        ability_button = self.scene.create_selected_version(
                            self.scene.get_scaled_surface(chosen_ability.image), engine.FilterType.LOCKED)

            ability_button.ability = chosen_ability
            ability_button.click += self.set_selected_ability
            self.scene.add_bordered_sprite(self.character_region, ability_button, BLACK, 150 + (i * 140), 0)

    def stamp_cooldown(self, cooldown: int, surface: sdl2.SDL_Surface) -> sdl2.SDL_Surface:
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(self.scene.cooldown_font,
                                                          str.encode(f"{cooldown}"), BLACK)
        sdl2.surface.SDL_BlitSurface(text_surface, None, surface, sdl2.SDL_Rect(25, -20, 0, 0))
        return surface

    
def make_battle_scene(scene_manager) -> BattleScene:

    scene = BattleScene(scene_manager, sdl2.ext.SOFTWARE, RESOURCES)

    assets = {
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
        "start": "start_button.png",
        "end": "end_button.png",
        "add": "add_button.png",
        "remove": "remove_button.png"
    }

    
    scene.load_assets(**assets)

    return scene