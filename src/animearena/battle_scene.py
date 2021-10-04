import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
import dill as pickle
import itertools
import textwrap
from animearena import engine
from animearena import character
from animearena import energy
from animearena.character import Character, character_db
from animearena.ability import Ability, Target, ability_info_db
from animearena.engine import FilterType
from animearena.energy import Energy
from animearena.effects import Effect, EffectType
from random import seed, randint

from pathlib import Path
from typing import Union, Optional

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
    waiting_for_turn: bool = False

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
                manager.used_ability.start_cooldown()
        self.resolve_ticking_ability()

    def is_allied(self, effect: Effect) -> bool:
        for manager in self.player_display.team.character_managers:
            if effect.user == manager:
                return True
        return False

    def resolve_ticking_ability(self):
        for manager in self.player_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.deal_eff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
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
                self.check_unique_cont(eff)

        for manager in self.enemy_display.team.character_managers:
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.deal_eff_damage(eff.mag, manager.source)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_AFF_DMG)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.deal_eff_aff_damage(eff.mag, manager)
            gen = (eff for eff in manager.source.current_effects
                   if eff.eff_type == EffectType.CONT_HEAL)
            for eff in gen:
                if eff.check_waiting() and self.is_allied(eff):
                    eff.user.give_eff_healing(eff.mag, manager.source)
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
                self.check_unique_cont(eff)

    def check_unique_cont(self, eff: Effect):
        pass

    def confirm_button_click(self, _button, _sender):
        self.execution_loop()
        for attr, _ in self.offered_pool.items():
            self.offered_pool[attr] = 0
        self.turn_expend_region.clear()
        self.draw_turn_end_region()
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
            if self.round_any_cost == 0:
                self.execution_loop()
                self.turn_end()
            else:
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
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
                effects_pouch.append(effect_pouch)
            character_pouch.append(effects_pouch)
            team1_pouch.append(character_pouch)
        team2_pouch = []
        for manager in team2.character_managers:
            effects_pouch = []
            character_pouch = []
            character_pouch.append(manager.source.hp)
            for effect in manager.source.current_effects:
                effect_pouch = []
                effect_pouch.append(effect.eff_type.value)
                effect_pouch.append(effect.mag)
                effect_pouch.append(effect.duration)
                effect_pouch.append(effect.desc)
                effect_pouch.append(effect.db_name)
                effect_pouch.append(effect.user_id)
                effect_pouch.append(effect.invisible)
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
            self.player_display.team.character_managers[i].source.current_effects.clear()
            for j, effect_pouch in enumerate(character_pouch[1]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[effect_pouch[5]]
                
                effect = Effect(Ability(effect_pouch[4]), EffectType(effect_pouch[0]), user, effect_pouch[2], effect_pouch[3], effect_pouch[1], effect_pouch[6])
                self.player_display.team.character_managers[i].source.current_effects.append(effect)
        for i, character_pouch in enumerate(team2pouch):
            self.enemy_display.team.character_managers[i].source.hp = character_pouch[0]
            self.enemy_display.team.character_managers[i].source.current_effects.clear()
            for j, effect_pouch in enumerate(character_pouch[1]):
                if effect_pouch[5] > 2:
                    user = self.player_display.team.character_managers[effect_pouch[5] - 3]
                else:
                    user = self.enemy_display.team.character_managers[effect_pouch[5]]
                
                effect = Effect(Ability(effect_pouch[4]), EffectType(effect_pouch[0]), user, effect_pouch[2], effect_pouch[3], effect_pouch[1], effect_pouch[6])
                self.enemy_display.team.character_managers[i].source.current_effects.append(effect)
        self.turn_start()
        


    def tick_effect_duration(self):
        for manager in self.player_display.team.character_managers:
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.duration == 0:
                    manager.remove_effect(eff)
        for manager in self.enemy_display.team.character_managers:
            for eff in manager.source.current_effects:
                eff.tick_duration()
                if eff.duration == 0:
                    manager.remove_effect(eff)

    

    def turn_start(self):
        self.waiting_for_turn = False
        self.round_any_cost = 0
        self.acting_character = None
        self.selected_ability = None
        self.generate_energy()
        for manager in self.player_display.team.character_managers:
            manager.refresh_character()
        for manager in self.enemy_display.team.character_managers:
            manager.refresh_character(True)
        self.full_update()

    

    def generate_energy(self):
        total_energy = 0

        for manager in self.player_display.team.character_managers:
            total_energy = total_energy + manager.source.energy_contribution
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

    def setup_scene(self, ally_team: list[Character],
                                  enemy_team: list[Character]):
        self.region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        self.draw_turn_end_region()
        ally_roster: list[CharacterManager] = []
        enemy_roster: list[CharacterManager] = []
        for i, ally in enumerate(ally_team):
            char_manager = CharacterManager(ally, self)
            char_manager.id = i
            ally_roster.append(char_manager)

        for i, enemy in enumerate(enemy_team):
            char_manager = CharacterManager(enemy, self)
            char_manager.id = i + 3
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

    def adjust_ability_costs(self):
        for i, ability in enumerate(self.source.current_abilities):
            ability.reset_costs()
            gen = (eff for eff in self.source.current_effects
                   if eff.eff_type == EffectType.COST_ADJUST)
            for eff in gen:
                ability_to_modify = eff.mag // 100
                cost_type = (eff.mag - (ability_to_modify * 100)) // 10
                magnitude = eff.mag - (ability_to_modify * 100) - (cost_type * 10)
                if ability_to_modify - 1 == i or ability_to_modify == 0:
                    ability.modify_ability_cost(Energy(cost_type - 1), magnitude)
        

    def check_on_use(self):
        if self.has_effect(EffectType.MARK, "Mug"):
            self.source.energy_contribution -= 1
        if self.has_effect(EffectType.MARK, "Sneak"):
            self.get_ability("Sneak").cooldown_remaining = 3
            self.remove_effect(self.get_effect(EffectType.MARK, "Sneak"))

    def check_bypass_effects(self) -> str:

        return "NORMAL"

    def receive_stun(self):
        #TODO Stun receipt checks
        pass

    def check_on_stun(self, target: "CharacterManager"):
        #TODO stun checks
        target.receive_stun()
        pass

    def check_countered(self) -> bool:
        #self counter/reflect effects:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.REFLECT)
        for eff in gen:
            if eff.name == "Taunt":
                self.current_targets.clear()
                self.current_targets.append(eff.user)

        for target in self.current_targets:
            #TODO check for individual counters on target
            pass
        return False

    def check_on_damage_dealt(self, target: "CharacterManager"):
        #TODO check user effects

        #TODO check target effects
        if target.has_effect(EffectType.MARK, "Sneak"):
            target.get_ability("Sneak").cooldown_remaining = 3
            target.remove_effect(target.get_effect(EffectType.MARK, "Sneak"))

    def check_for_boosts(self, damage: int) -> int:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_BOOST)
        for eff in gen:
            damage += eff.mag
        return damage

    def check_for_dmg_reduction(self) -> int:
        dr = 0
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ALL_DR)
        for eff in gen:
            dr += eff.mag
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEF_NEGATE)
        for eff in gen:
            dr = 0
            break
        return dr

    def check_for_cooldown_mod(self) -> int:
        cd_mod = 0
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.COOLDOWN_MOD)
        for eff in gen:
            cd_mod += eff.mag
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

    def pass_through_dest_def(self, dmg: int) -> int:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEST_DEF)
        for eff in gen:
            current_def = eff.mag
            eff.alter_dest_def(-dmg)
            dmg = engine.sat_subtract(current_def, dmg)
            if dmg == 0:
                return dmg
        return dmg

    def can_act(self) -> bool:
        if self.is_stunned():
            return False
        return True

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

    def deal_aff_damage(self, damage: int, target: "CharacterManager"):
        #TODO check for affliction boosts
        target.receive_aff_dmg(damage)
        self.check_on_damage_dealt(target)

    def receive_aff_dmg(self, damage: int):
        #TODO add affliction damage received boosts
        self.source.hp -= damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_eff_aff_damage(self, damage: int, target: "CharacterManager"):
        #TODO add affliction damage boosts
        target.receive_eff_aff_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_eff_aff_damage(self, damage: int):
        #TODO add affliction damage received boosts
        self.source.hp -= damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_damage(self, damage: int, target: "CharacterManager"):
        damage = self.check_for_boosts(damage)
        target.receive_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_damage(self, damage: int):
        mod_damage = damage - self.check_for_dmg_reduction()
        mod_damage = self.pass_through_dest_def(mod_damage)
        self.source.hp -= mod_damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_pierce_damage(self, damage: int, target: "CharacterManager"):
        damage = self.check_for_boosts(damage)
        target.receive_pierce_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_pierce_damage(self, damage: int):
        mod_damage = self.pass_through_dest_def(damage)
        self.source.hp -= mod_damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_eff_damage(self, damage: int, target: "CharacterManager"):
        damage = self.check_for_boosts(damage)
        target.receive_eff_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_eff_damage(self, damage: int):
        mod_damage = damage - self.check_for_dmg_reduction()
        mod_damage = self.pass_through_dest_def(mod_damage)
        self.source.hp -= mod_damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def deal_eff_pierce_damage(self, damage: int, target: "CharacterManager"):
        damage = self.check_for_boosts(damage)
        target.receive_eff_pierce_damage(damage)
        self.check_on_damage_dealt(target)

    def receive_eff_pierce_damage(self, damage: int):
        self.source.hp -= damage
        if self.source.hp < 0:
            self.source.hp = 0
            self.source.dead = True

    def give_healing(self, healing: int, target: "CharacterManager"):
        #TODO add healing boosts
        target.receive_healing(healing)

    def receive_healing(self, healing: int):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation
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

    def hostile_target(self, def_type = "NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.source.invulnerable or self.source.dead or self.source.untargetable)
        elif def_type == "BYPASS":
            return not (self.source.dead or self.source.untargetable)

    def helpful_target(self, def_type = "NORMAL") -> bool:
        if def_type == "NORMAL":
            return not (self.source.isolated or self.source.dead)
        elif def_type == "BYPASS":
            return not (self.source.dead)

    def add_effect(self, effect: Effect):
        self.source.current_effects.append(effect)

    def remove_effect(self, effect: Effect):
        self.source.current_effects.remove(effect)

    def full_remove_effect(self, eff_name: str):
        gen = (eff for eff in self.source.current_effects if eff.name == eff_name)
        for eff in gen:
            self.source.current_effects.remove(eff)

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
                additional_height += len(textwrap.wrap(effect.get_desc(), 26))
            hover_panel_sprite = self.scene.sprite_factory.from_color(WHITE,
                                                                      size=(max_line_width,
                                                                            base_height + 19 + (additional_height * 23)))
            mouse_x, mouse_y = engine.get_mouse_position()
            self.scene.hover_effect_region.x = mouse_x - hover_panel_sprite.size[
                0] if self.scene.current_button.is_enemy else mouse_x
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
                effect_y += effect.size[1] - 26
            

    def get_effect_lines(self, effect_list: list[Effect]) -> list[sdl2.ext.SoftwareSprite]:
        output: list[sdl2.ext.SoftwareSprite] = []
        
        output.append(
            self.scene.create_text_display(self.scene.font, effect_list[0].name, BLUE, WHITE, 0, 0,
                                           260))

        for effect in effect_list:
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
            if effect.name in output.keys():
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
        self.acted = False
        self.current_targets.clear()
        self.received_ability.clear()
        self.selected_ability = None
        self.used_ability = None
        self.targeted = False
        self.targeting = False
        self.source.energy_contribution = 1
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

    def update_profile(self):
        if self.targeted:
            profile_sprite = self.scene.create_selected_version(self.scene.get_scaled_surface(self.source.profile_image),
                                                                engine.FilterType.SELECTED)
        else:
            profile_sprite = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON,
                                                                self.scene.get_scaled_surface(self.source.profile_image))
        profile_sprite.click += self.profile_click
        self.scene.add_bordered_sprite(self.character_region, profile_sprite, BLACK, 0, 0)

    def update_enemy_profile(self):
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
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ABILITY_SWAP)
        for eff in gen:
            swap_from = eff.mag // 10
            swap_to = eff.mag - (swap_from * 10)
            self.source.current_abilities[swap_from - 1] = self.source.alt_abilities[swap_to - 1]

    def update_ability(self):

        self.source.current_abilities = self.source.main_abilities

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