import sdl2
import sdl2.ext
import typing
import itertools
from animearena import engine, character
from animearena.effects import Effect, EffectType
from animearena.ability import Ability, Target, one, two, three, DamageType
from animearena.ability_type import AbilityType
from animearena.energy import Energy
from animearena.mission import Mission
from animearena.mission_handler import MissionHandler, TriggerHandler
import math
from random import randint
import logging
from typing import Optional, Union, Tuple
import collections.abc


def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass

if typing.TYPE_CHECKING:
    from animearena.battle_scene import BattleScene

BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)

class CharacterManager(collections.abc.Container):
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-branches
    # pylint: disable=no-self-use
    character_region: engine.Region
    source: character.Character
    text_region: engine.Region
    scene: "BattleScene"
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
    id: str
    char_id: int
    main_ability_sprites: list[sdl2.ext.SoftwareSprite]
    alt_ability_sprites: list[sdl2.ext.SoftwareSprite]
    

    def __init__(self, source: character.Character, scene: "BattleScene"):
        self.source = source
        self.scene = scene
        self.selected_ability = None
        self.selected_button = None
        self.used_ability = None
        self.targeted = False
        self.acted = False
        self.is_toga = False
        self.received_ability = list()
        self.current_targets = list()
        self.primary_target = None
        self.used_slot = self.scene.ui_factory.from_surface(sdl2.ext.BUTTON, self.scene.get_scaled_surface(self.scene.scene_manager.surfaces["used_slot"], 80, 80))
        self.used_slot.border = self.scene.sprite_factory.from_color(BLACK, (84, 84))
        self.used_slot.click += self.used_slot_click
        self.used_slot.ability = None

    def __contains__(self, __x: Tuple[EffectType, str]) -> bool:
        for eff in self.source.current_effects:
            if eff == __x:
                return True
        return False

    def __str__(self) -> str:
        list_of_effects = f"{self.source.name} ID: {self.id}"
        for eff in self.source.current_effects:
            list_of_effects += "\n" + f"{eff.name} ({eff.eff_type.name})"
        return "Current effects:" + list_of_effects

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, CharacterManager):
            return (self.source.name == __o.source.name and self.id == __o.id and self.char_id == __o.char_id)

    @property
    def player_team(self):
        return self.scene.player_display.team.character_managers
    
    @property
    def enemy_team(self):
        return self.scene.enemy_display.team.character_managers

    @property
    def hp(self):
        return self.source.hp

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
            if self.selected_ability.total_cost > 0:
                energy_squares = [
                    energy_display_region.subregion(x, y=0, width=10, height=10)
                    for x in itertools.islice(range(0, 1000, 14 + 4),
                                            self.selected_ability.total_cost)
                ]
                for cost, energy_square in zip(cost_to_display, energy_squares):
                    energy_surface = self.scene.scene_manager.surfaces[cost.name]
                    energy_sprite = self.scene.sprite_factory.from_surface(
                        self.scene.get_scaled_surface(energy_surface, 14, 14), free=True)
                    energy_square.add_sprite(energy_sprite, x=0, y=0)
            else:
                energy_display_region.add_sprite(self.scene.create_text_display(self.scene.font, "No Cost", BLACK, WHITE, 0, 0, 80, 4), 0, -6)
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
            ffs_shokuhou = False
            shokuhou_locker = None
            if abi.name == "Mental Out - Order":
                ffs_shokuhou = True
                controlled_character = self.get_controlled_character(self)
                stolen_slot = self.get_effect(EffectType.UNIQUE, "Mental Out").mag
                stolen_ability = controlled_character.source.main_abilities[stolen_slot] if stolen_slot < 4 else controlled_character.source.alt_abilities[stolen_slot - 4]
                abi.name = stolen_ability.name
                abi.target_type = stolen_ability._base_target_type
                shokuhou_locker = self
                self = controlled_character
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
            if abi.name == "Dance of the Heavenly Six" and one(self) and two(self) and three(
                    self):
                abi.target_type = Target.ALL_TARGET
            if abi.name == "Five-God Inviolate Shield" and two(self) and three(self):
                abi.target_type = Target.MULTI_ALLY
            if ffs_shokuhou:
                self = shokuhou_locker
                abi.name = "Mental Out - Order"

    def get_controlled_character(self, user: "CharacterManager") -> "CharacterManager":
        for enemy in self.scene.eteam:
            if enemy.has_effect_with_user(EffectType.MARK, "Mental Out", user):
                return enemy

    def adjust_ability_costs(self):
        for i, ability in enumerate(self.source.current_abilities):
            ability.reset_costs()
            ffs_shokuhou = False
            shokuhou_locker = None
            if ability.name == "Mental Out - Order":
                ffs_shokuhou = True
                controlled_character = self.get_controlled_character(self)
                logging.debug(f"Mental Out Order holder effect list: {self}")
                stolen_slot = self.get_effect(EffectType.UNIQUE, "Mental Out").mag
                stolen_ability = controlled_character.source.main_abilities[stolen_slot] if stolen_slot < 4 else controlled_character.source.alt_abilities[stolen_slot - 4]
                
                for i in range(5):
                    ability.cost[Energy(i)] = 0
                    ability.modify_ability_cost(Energy(i), stolen_ability.all_costs[i])
                ability.name = stolen_ability.name
                shokuhou_locker = self
                self = controlled_character
            if self.has_effect(EffectType.STACK, "Quirk - Half-Cold"):
                ability.modify_ability_cost(
                    Energy(4),
                    self.get_effect(EffectType.STACK, "Quirk - Half-Cold").mag)
            if ability.name == "Knight's Sword" and self.has_effect(
                    EffectType.STACK, "Magic Sword"):
                ability.modify_ability_cost(
                    Energy(4),
                    self.get_effect(EffectType.STACK, "Magic Sword").mag)
            if ability.name == "Roman Artillery - Pumpkin" and self.source.hp < 60:
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
            if ffs_shokuhou:
                self = shokuhou_locker
                ability.name = "Mental Out - Order"

    def check_on_harm(self):
        for character in self.current_targets:
            if character.id != self.id:
                
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
                    if self.final_can_effect(character.check_bypass_effects()):
                        character.progress_mission(3, 1)
                        character.used_ability = Ability("accelerator1")
                        character.deal_active_damage(20, self, DamageType.NORMAL)
                        self.add_effect(Effect(Ability("accelerator1"), EffectType.ALL_STUN, character, 3, lambda eff: "This character is stunned."))
                        if self.meets_stun_check():
                            character.check_on_stun(self)

                if character.has_effect(EffectType.UNIQUE, "Hear Distress"):
                    character.source.change_energy_cont(1)
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
                            "This character will take 20 more piercing damage from Phantom Menace, and it will automatically target them."
                        ))
                if character.has_effect(EffectType.MARK, "Protect Ally"):
                    character.get_effect(EffectType.MARK, "Protect Ally").user.progress_mission(2, 1)
                    
                    self.add_effect(
                        Effect(
                            Ability("mirio2"), EffectType.MARK, character, 2,
                            lambda eff:
                            "This character will take 20 more piercing damage from Phantom Menace, and it will automatically target them."
                        ))
                if character.has_effect(EffectType.DEST_DEF,
                                        "Four-God Resisting Shield"):
                    self.receive_eff_damage(
                        15,
                        character.get_effect(EffectType.DEST_DEF,
                                             "Four-God Resisting Shield"), DamageType.NORMAL)
        if self.has_effect(EffectType.UNIQUE, "Porcospino Nuvola"):
            self.receive_eff_damage(
                15, self.get_effect(EffectType.UNIQUE,
                                         "Porcospino Nuvola"), DamageType.NORMAL)

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
                    self.receive_eff_damage(
                        20,
                        target.get_effect(EffectType.MARK,
                                          "Shredding Wedding"), DamageType.PIERCING)
            if self.has_effect(EffectType.MARK,
                               "Shredding Wedding") and not target.has_effect(
                                   EffectType.MARK, "Shredding Wedding"):
                if self.final_can_effect():
                    self.receive_eff_damage(
                        20,
                        self.get_effect(EffectType.MARK,
                                        "Shredding Wedding"), DamageType.PIERCING)
        if self.has_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame"):
            self.get_effect(EffectType.CONT_UNIQUE, "Utsuhi Ame").alter_mag(1)
            self.get_effect(
                EffectType.CONT_UNIQUE, "Utsuhi Ame"
            ).desc = lambda eff: "This character will take 50 damage and Yamamoto will gain 3 stacks of Asari Ugetsu."
        if self.has_effect(EffectType.MARK, "Hidden Mine"):
            if self.final_can_effect():
                self.receive_eff_damage(
                    20,
                    self.get_effect(EffectType.MARK, "Hidden Mine"), DamageType.PIERCING)
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
            self.receive_eff_damage(
                15,
                self.get_effect(EffectType.MARK, "Solid Script - Fire"), DamageType.AFFLICTION)

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

        if self.has_effect(EffectType.MARK, "Counter-Balance"):
            self.source.change_energy_cont(-1)
            self.add_effect(Effect("JiroMission4Tracker", EffectType.SYSTEM, self.get_effect(EffectType.MARK, "Counter-Balance").user, 2, lambda eff:"", system=True))
            self.get_effect(EffectType.MARK, "Counter-Balance").user.progress_mission(1, 1)

        if target.is_stunned():
            for eff in target.source.current_effects:
                if eff.eff_type == EffectType.CONT_USE:
                    target.scene.scene_remove_effect(eff.name, eff.user)

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

        if self.has_effect(EffectType.MARK, "Counter-Balance"):
            self.add_effect(
                Effect(
                    Ability("jiro1"), EffectType.ALL_STUN,
                    self.get_effect(EffectType.MARK, "Counter-Balance").user,
                    3, lambda eff: "This character is stunned."))
            self.add_effect(Effect("JiroMission4Tracker", EffectType.SYSTEM, self.get_effect(EffectType.MARK, "Counter-Balance").user, 2, lambda eff:"", system=True))
            self.get_effect(EffectType.MARK, "Counter-Balance").user.progress_mission(1, 1)
        if target.has_effect(EffectType.UNIQUE, "Sage Mode"):
            if not self.is_aff_immune() and not self.is_ignoring():
                target.deal_eff_damage(20, self, target.get_effect(EffectType.UNIQUE, "Sage Mode"), DamageType.AFFLICTION)

    def check_damage_drain(self) -> int:
        gen = [
            eff for eff in self.source.current_effects
            if eff.eff_type == EffectType.ALL_BOOST and eff.mag < 0
        ]

        total_drain = 0
        for eff in gen:
            total_drain += eff.mag

        
        
        return total_drain * -1

    def check_unique_cont(self, eff: Effect, team_id: str):
        if eff.name == "Kill, Kamishini no Yari":
            if self.final_can_effect("BYPASS"):
                eff.user.deal_eff_damage(eff.mag * 10, self, eff, DamageType.AFFLICTION)
        if eff.name == "Utsuhi Ame":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                eff.user.deal_eff_damage(eff.mag * 25, self, eff, DamageType.NORMAL)
                if eff.mag == 1:
                    eff.user.apply_stack_effect(
                        Effect(
                            Ability("yamamoto3"),
                            EffectType.STACK,
                            eff.user,
                            280000,
                            lambda eff:
                            f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.",
                            mag=1, print_mag=True), eff.user)
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
                eff.user.deal_eff_damage(eff.mag, self, eff, DamageType.AFFLICTION)
                self.apply_stack_effect(
                    Effect(
                        Ability("toga3"),
                        EffectType.STACK,
                        eff.user,
                        280000,
                        lambda eff:
                        f"Toga has drawn blood from this character {eff.mag} time(s).",
                        mag=1, print_mag=True), eff.user)
                eff.user.progress_mission(2, 1)
        if eff.name == "Fire Dragon's Sword Horn":
            if self.final_can_effect("BYPASS"):
                eff.user.deal_eff_damage(eff.mag, self, eff, DamageType.AFFLICTION)
        if eff.name == "Decaying Touch":
            if self.final_can_effect(eff.user.check_bypass_effects()):
                eff.user.deal_eff_damage((10 * (2**eff.mag)), self, eff, DamageType.AFFLICTION)
        if eff.name == "Nemurin Nap":
            if not self.has_effect(EffectType.SYSTEM, "NemurinActivityMarker"):
                eff.alter_mag(1, 3)
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
                    not self.deflecting() or (2 * (2 ** eff.mag) >= 20)):
                base_damage = (2 * (2**eff.mag))
                eff.user.deal_eff_damage(base_damage, self, eff, DamageType.NORMAL)
                
                eff.alter_mag(1)
                if self.has_effect(
                        EffectType.MARK, "Chakra Point Strike"
                ) and base_damage > self.check_for_dmg_reduction():
                    self.source.change_energy_cont(-1)
                    eff.user.check_on_drain(self)
                    eff.user.progress_mission(2, 1)
        if eff.name == "Relentless Assault":
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                if self.check_for_dmg_reduction() < 15:
                    eff.user.deal_eff_damage(20, self, eff, DamageType.PIERCING)
                else:
                    eff.user.deal_eff_damage(20, self, eff, DamageType.NORMAL)
        if eff.name == "Bridal Chest":
            if team_id != "enemy":
                team = self.scene.eteam
            else:
                team = self.scene.pteam
            valid_targets: list["CharacterManager"] = []
                
            for target in team:
                if target.hostile_target(eff.user, eff.user.check_bypass_effects()):
                    valid_targets.append(target)
            if valid_targets:
                damage = eff.mag
                if eff.user.has_effect(EffectType.STACK, "Galvanism"):
                    damage = damage + (eff.user.get_effect(EffectType.STACK, "Galvanism").mag * 10)
                target = self.scene.d20.randint(0, len(valid_targets) - 1)
                if valid_targets[target].final_can_effect(self.check_bypass_effects()):
                    self.deal_eff_damage(damage, valid_targets[target], eff, DamageType.NORMAL)
        if eff.name == "Titania's Rampage":
            
            valid_targets: list["CharacterManager"] = []
            if eff.user.id == "enemy":
                target_team = self.scene.pteam
            else:
                target_team = self.scene.eteam
            for enemy in target_team:
                if enemy.hostile_target(eff.user, eff.user.check_bypass_effects()):
                    valid_targets.append(enemy)
            if valid_targets:
                damage = 25 + (eff.mag * 5)
                target = self.scene.d20.randint(0, len(valid_targets) - 1)
                
                if valid_targets[target].final_can_effect(self.check_bypass_effects()):
                    self.deal_eff_damage(damage, valid_targets[target], eff, DamageType.PIERCING)
            eff.alter_mag(1)
        if eff.name == "Circle Blade":
            for enemy in self.scene.enemy_display.team.character_managers:
                if enemy.final_can_effect(self.check_bypass_effects()
                                          ) and not enemy.deflecting():
                    self.deal_eff_damage(20, enemy, eff, DamageType.NORMAL)
        if eff.name == "Butou Renjin":
            if eff.user.has_effect(EffectType.SYSTEM, "IchimaruMission4Tracker"):
                eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").duration = 3
                eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").alter_mag(1)
                if eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").mag >= 8:
                    eff.user.remove_effect(eff.user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker"))
                    eff.user.progress_mission(4, 1)
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                eff.user.deal_eff_damage(20, self, eff, DamageType.NORMAL)
                self.apply_stack_effect(
                    Effect(
                        Ability("ichimaru1"),
                        EffectType.STACK,
                        eff.user,
                        280000,
                        lambda eff:
                        f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.",
                        mag=1, print_mag=True), eff.user)
        if eff.name == "Rubble Barrage":
            if self.final_can_effect(
                    eff.user.check_bypass_effects()) and not self.deflecting():
                base_damage = 15
                if eff.user.has_effect(EffectType.STACK, "Gather Power"):
                    base_damage += (5 * eff.user.get_effect(
                        EffectType.STACK, "Gather Power").mag)
                eff.user.deal_eff_damage(base_damage, self, eff, DamageType.NORMAL)
        if eff.name == "Railgun":
            base_damage = 15
            if self.final_can_effect(eff.user.check_bypass_effects()):
                if eff.user.has_effect(EffectType.STACK, "Overcharge"):
                    base_damage += (5 * eff.user.get_effect(EffectType.STACK, "Overcharge").mag)
                eff.user.deal_eff_damage(base_damage, self, eff, DamageType.NORMAL)
        if eff.name == "Iron Sand":
            base_defense = 15
            if self.helpful_target(eff.user, eff.user.check_bypass_effects()):
                if eff.user.has_effect(EffectType.STACK, "Overcharge"):
                    base_defense += (5 * eff.user.get_effect(EffectType.STACK, "Overcharge").mag)
                self.apply_dest_def_effect(Effect(eff.source, EffectType.DEST_DEF, eff.user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = base_defense))
        if eff.name == "Overcharge":
            self.apply_stack_effect(Effect(eff.source, EffectType.STACK, eff.user, 280000, lambda eff: "", mag = 1, print_mag=True), eff.user)
            self.progress_mission(4, 1)
        if eff.name == "Level-6 Shift":
            if not eff.user.is_stunned():
                
                ability = self.scene.d20.randint(1, 3)
                
                if ability == 1:
                    if team_id != "enemy":
                        team = self.scene.pteam
                    else:
                        team = self.scene.eteam
                    valid_targets = [manager for manager in team if manager.helpful_target(eff.user, eff.user.check_bypass_effects())]
                    if valid_targets:
                        chosen_target = valid_targets[randint(0, len(valid_targets) - 1)]
                        eff.user.current_targets.append(chosen_target)
                        eff.user.acted = True
                        eff.user.used_ability = eff.user.source.main_abilities[0]
                        eff.user.execute_ability()
                    
                elif ability == 2:
                    if team_id != "enemy":
                        team = self.scene.pteam
                    else:
                        team = self.scene.eteam
                    valid_targets = [manager for manager in team if manager.hostile_target(eff.user, "BYPASS")]
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
                                counter.user.progress_mission(5, 1, once=True)
                            if counter.user.final_can_effect():
                                counter.user.receive_eff_damage(40, self.get_effect(EffectType.MARK, "Third Dance - Shirafune"), DamageType.NORMAL)
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
        def is_harmful(self: "CharacterManager") -> bool:
            for target in self.current_targets:
                if target.id != self.id:
                    return True
            return False

        def is_helpful(self: "CharacterManager") -> bool:
            for target in self.current_targets:
                if target.id == self.id:
                    return True
            return False

        if is_harmful(self):
            if not self.is_counter_immune():
                #self reflect effects:
                gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.REFLECT)
                for eff in gen:
                    pass

                #self counter check
                gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.COUNTER_USE)
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
                        self.source.change_energy_cont(-1)
                        eff.user.check_on_drain(self)
                        self.shirafune_check(eff)
                        return True
                    if eff.name == "Enkidu, Chains of Heaven":
                        src = Ability("gilgamesh2")
                        self.full_remove_effect("Enkidu, Chains of Heaven", eff.user)
                        self.add_effect(Effect("GilgameshMission4Tracker", EffectType.SYSTEM, eff.user, 280000, lambda eff:"", system=True))
                        self.add_effect(Effect(src, EffectType.UNIQUE, eff.user, 2, lambda eff: "This character was countered by Enkidu, Chains of Heaven."))
                        self.add_effect(Effect(src, EffectType.ALL_STUN, eff.user, 3, lambda eff: "This character is stunned."))
                        self.add_effect(Effect(src, EffectType.MARK, eff.user, 3, lambda eff: "This character's continuous abilities will not activate."))
                        self.shirafune_check(eff)
                        return True
                #target counter check
                for target in self.current_targets:

                    gen = (eff for eff in target.source.current_effects
                           if eff.eff_type == EffectType.COUNTER_RECEIVE)
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
                                self.receive_eff_damage(20, eff, DamageType.NORMAL)
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
                            src = Ability("tsunayoshi2")
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
                                self.receive_eff_damage(35, eff, DamageType.PIERCING)
                            self.shirafune_check(eff)
                            return True
                        if eff.name == "Casseur de Logistille":
                            src = Ability("astolfo1")
                            if AbilityType.ENERGY in self.used_ability.types or AbilityType.MENTAL in self.used_ability.types:
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
                           if eff.eff_type == EffectType.REFLECT)
                    for eff in gen:
                        if eff.name == "Copy Ninja Kakashi":
                            self.scene.sharingan_reflecting = True
                            self.scene.sharingan_reflector = target.get_effect(EffectType.REFLECT, "Copy Ninja Kakashi").user
                            target.full_remove_effect("Copy Ninja Kakashi",
                                                      eff.user)
                            alt_targets = [
                                char for char in self.current_targets
                                if char != target
                            ]
                            self.toggle_allegiance()
                            alt_targets.append(self)
                            self.current_targets = alt_targets
                            self.used_ability.execute(self, pteam, eteam)
                            return True
            else:
                if self.has_effect(EffectType.COUNTER_IMMUNE, "Mental Radar"):
                    self.get_effect(EffectType.COUNTER_IMMUNE, "Mental Radar").user.progress_mission(3, 1)
        if is_helpful(self):
            if not self.is_counter_immune():
                #self counter check
                gen = (eff for eff in self.source.current_effects
                       if eff.eff_type == EffectType.COUNTER_USE)
                for eff in gen:
                    pass
            for target in self.current_targets:
                gen = (eff for eff in target.source.current_effects
                        if eff.eff_type == EffectType.COUNTER_RECEIVE)
                
                for eff in gen:
                    if eff.name == "Those Who Fight In The Shadows":
                        src = Ability("chelsea2")
                        target.full_remove_effect("Those Who Fight In The Shadows", eff.user)
                        self.add_effect(
                            Effect(
                                src, EffectType.UNIQUE, eff.user, 2,
                                lambda eff:
                                "This character was countered by Those Who Fight In The Shadows"
                            ))
                        eff.user.progress_mission(2, 1)
                        self.add_effect(Effect(src, EffectType.MARK, eff.user, 5, lambda eff: "Mortal Wound will have triple effect against this character."))
                        self.add_effect(Effect(src, EffectType.ALL_STUN, eff.user, 5, lambda eff: "This character is stunned."))
                        return True

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
                        f"Detonate will deal {30 * leff.mag} damage to this character.",
                        mag=eff.mag,
                        invisible=True, print_mag=True), eff.user)
                eff.user.progress_mission(1, eff.mag)
                target.full_remove_effect("Doll Trap", eff.user)
        if target.source.hp <= 0:
            if self.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct"):
                self.get_effect(EffectType.STUN_IMMUNE,
                                "Beast Instinct").duration = 5
                self.get_effect(EffectType.COUNTER_IMMUNE,
                                "Beast Instinct").duration = 5
            

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

    def deal_active_damage(self, damage: int, target: "CharacterManager", damage_type: DamageType):
        mod_damage = damage
        if damage_type != DamageType.AFFLICTION or not target.is_aff_immune():
            if damage_type != DamageType.AFFLICTION:
                mod_damage = self.get_boosts(damage)
            else:
                #TODO add affliction boosts here
                pass
            
            if AbilityType.ENERGY in self.used_ability.types and target.has_effect(EffectType.UNIQUE, "Galvanism"):
                target.receive_eff_healing(mod_damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
                target.progress_mission(3, 1)
                target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1, print_mag=True), target)
                mod_damage = 0
            else:
                if self.mission_active("ryohei", self):
                    if mod_damage >= 100 and self.used_ability.name == "Maximum Cannon":
                        self.progress_mission(5, 1)


                if mod_damage > target.check_for_dmg_reduction() or damage_type != DamageType.NORMAL:
                    if self.has_effect(EffectType.UNIQUE,
                                    "Three-God Empowering Shield"):
                        self.receive_eff_healing(10, self.get_effect(EffectType.UNIQUE,
                                    "Three-God Empowering Shield"))
                    if self.has_effect(EffectType.UNIQUE, "King of Beasts Transformation - Lionel"):
                        self.give_eff_healing(10, self, self.get_effect(EffectType.UNIQUE, "King of Beasts Transformation - Lionel"))

                target.receive_active_damage(mod_damage, self, damage_type)

                if target.has_effect(EffectType.ALL_DR, "Flag of the Ruler"):
                    target.get_effect(EffectType.ALL_DR, "Flag of the Ruler").user.progress_mission(3, 1)
                
                if target.has_effect(EffectType.UNIQUE, "Thunder Palace"):
                    self.receive_eff_damage(mod_damage, target.get_effect(EffectType.UNIQUE, "Thunder Palace"), DamageType.NORMAL)
                    target.full_remove_effect("Thunder Palace", target)
                if target.has_effect(EffectType.UNIQUE, "Burning Axle"):
                    src = target.get_effect(EffectType.UNIQUE, "Burning Axle")
                    target.receive_eff_damage(20, src, DamageType.NORMAL)
                    target.full_remove_effect("Burning Axle", src.user)
                    target.add_effect(
                        Effect(Ability("tsunayoshi3"), EffectType.ALL_STUN, src.user, 2,
                            lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        src.user.check_on_stun(target)
                        src.user.progress_mission(3, 1)
        else:
            #Check for affliction negation missions
            #TODO add affliction damage received boosts
            mod_damage = damage

            if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
                mod_damage = mod_damage * 2
            if target.has_effect(EffectType.AFF_IMMUNE, "Heaven's Wheel Armor"):
                target.progress_mission(2, mod_damage)

    def receive_active_damage(self, damage: int, dealer: "CharacterManager", damage_type: DamageType):
        mod_damage = damage
        if damage_type == DamageType.NORMAL:
            mod_damage = mod_damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if self.has_effect(EffectType.ALL_DR, "Conductivity"):
            self.get_effect(EffectType.ALL_DR,
                              "Conductivity").user.receive_eff_damage(
                                  15,
                                  self.get_effect(EffectType.ALL_DR,
                                                    "Conductivity"), DamageType.AFFLICTION)

        if mod_damage < 0:
            mod_damage = 0

        #region Damage Dealt Mission Check
        
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
            if dealer.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon"):
                dealer.progress_mission(3, mod_damage)
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
        
        if damage_type == DamageType.AFFLICTION:
            if self.mission_active("natsu", dealer):
                dealer.progress_mission(1, mod_damage)
            if self.mission_active("jack", dealer):
                dealer.progress_mission(3, mod_damage)
            if self.mission_active("mirai", dealer):
                dealer.progress_mission(1, mod_damage)
                if dealer.used_ability.name == "Blood Suppression Removal":
                    dealer.progress_mission(3, mod_damage)
        #endregion

        if self.will_die(mod_damage):
            if self.has_effect(EffectType.MARK, "Selfless Genius") and self.active_redeemable(dealer):
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
                neji = self.get_effect(EffectType.MARK,
                                "Selfless Genius").user
                neji.progress_mission(4, 1)
                neji.source.hp = 0
                neji.source.dead = True
                neji.action_effect_cancel()
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

        if damage_type != DamageType.AFFLICTION:
            mod_damage = self.pass_through_dest_def(mod_damage)

        if self.has_effect(EffectType.SYSTEM, "SheelePunctureCounter"):
            if dealer.source.name == "sheele" and dealer.used_ability.name == "Extase - Bisector of Creation":
                dealer.progress_mission(4, self.get_effect(EffectType.SYSTEM, "SheelePunctureCounter").mag)

        self.apply_active_damage_taken(mod_damage, dealer)
        self.death_check(dealer)

    def deal_eff_damage(self, damage: int, target: "CharacterManager", source: Effect, damage_type: DamageType):
        if damage_type != DamageType.AFFLICTION or not target.is_aff_immune():
            if damage_type != DamageType.AFFLICTION:
                damage = self.get_boosts(damage, eff_boost=True)
            else:
                #TODO Add affliction damage boosts here
                pass
            
            if AbilityType.ENERGY in source.source.types and target.has_effect(EffectType.UNIQUE, "Galvanism"):
                target.receive_eff_healing(damage, target.get_effect(EffectType.UNIQUE, "Galvanism"))
                target.progress_mission(3, 1)
                target.apply_stack_effect(Effect(target.get_effect(EffectType.UNIQUE, "Galvanism").source, EffectType.STACK, target, 2, lambda eff:f"Frankenstein will deal {eff.mag * 10} damage with her abilities.", mag=1, print_mag=True), target)
                damage = 0
            else:
                
                
                target.receive_eff_damage(damage, source, damage_type)
        else:
            #Check for affliction negation missions
            #TODO add affliction damage received boosts
            mod_damage = damage

            if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
                mod_damage = mod_damage * 2
            if target.has_effect(EffectType.AFF_IMMUNE, "Heaven's Wheel Armor"):
                target.progress_mission(2, mod_damage)

    def progress_mission(self, mission_number: int, progress: int, once: bool = False):
        
        if mission_number == 1 and not self.source.mission1complete:
            self.source.mission1progress += progress
            if once:
                self.source.mission1complete = True
        elif mission_number == 2 and not self.source.mission2complete:
            self.source.mission2progress += progress
            if once:
                self.source.mission2complete = True
        elif mission_number == 3 and not self.source.mission3complete:
            self.source.mission3progress += progress
            if once:
                self.source.mission3complete = True
        elif mission_number == 4 and not self.source.mission4complete:
            self.source.mission4progress += progress
            if once:
                self.source.mission4complete = True
        elif mission_number == 5 and not self.source.mission5complete:
            self.source.mission5progress += progress
            if once:
                self.source.mission5complete = True

    def receive_eff_damage(self, damage: int, source: Effect, damage_type: DamageType):
        mod_damage = damage
        if damage_type == DamageType.NORMAL:
            mod_damage = mod_damage - self.check_for_dmg_reduction()

        if self.has_effect(EffectType.UNIQUE, "Enraged Blow"):
            mod_damage = mod_damage * 2

        if mod_damage < 0:
            mod_damage = 0

        if self.mission_active("shikamaru", source.user):
            if source.name == "Shadow Neck Bind":
                source.user.progress_mission(1, mod_damage)
        if "neji" in self.scene.missions_to_check:
            if source.name == "Eight Trigrams - 128 Palms":
                source.user.progress_mission(3, mod_damage)
        if "uraraka" in self.scene.missions_to_check:
            if source.user.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity"):
                source.user.get_effect(EffectType.UNIQUE, "Quirk - Zero Gravity").user.progress_mission(4, mod_damage)
        if "gray" in self.scene.missions_to_check:
            if source.user.source.name == "gray" and source.name == "Ice, Make Freeze Lancer":
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
            if source.name == "Raging Koro":
                source.user.progress_mission(1, mod_damage)
                if not self.has_effect(EffectType.SYSTEM, "SeryuKoroTracker"):
                    self.add_effect(Effect("SeryuKoroTracker", EffectType.SYSTEM, source.user, 280000, lambda eff:"", system=True))
        if self.mission_active("wendy", source.user):
            if source.name == "Shredding Wedding":
                source.user.progress_mission(3, mod_damage)        
        if self.mission_active("cmary", source.user):
            if source.name == "Hidden Mine":
                source.user.progress_mission(1, mod_damage)
        if damage_type == DamageType.PIERCING:
            if self.mission_active("chu", source.user):
                if source.name == "Relentless Assault":
                    source.user.progress_mission(1, mod_damage)
        elif damage_type == DamageType.AFFLICTION:
            if self.mission_active("shigaraki", source.user):
                source.user.progress_mission(1, mod_damage)
            if self.mission_active("natsu", source.user):
                source.user.progress_mission(1, mod_damage)
            if self.mission_active("levy", source.user):
                if source.name == "Solid Script - Fire":
                    source.user.progress_mission(4, mod_damage) 
            if self.mission_active("jack", source.user):
                source.user.progress_mission(3, mod_damage)    
            if self.mission_active("mirai", source.user):
                source.user.progress_mission(1, mod_damage)
                if source.name == "Blood Suppression Removal":
                    source.user.progress_mission(3, mod_damage)
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
                neji = self.get_effect(EffectType.MARK,
                                "Selfless Genius").user
                neji.progress_mission(4, 1)
                neji.source.hp = 0
                neji.source.dead = True
                neji.action_effect_cancel()
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
        if damage_type != DamageType.AFFLICTION:
            mod_damage = self.pass_through_dest_def(mod_damage)
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
        if self.source.hp > 200:
            self.source.hp = 200

    def apply_eff_damage_taken(self, damage: int, source: "Effect"):
        if damage < 0:
            damage = 0

        self.source.hp -= damage

        if damage > 0:
            self.eff_damage_taken_check(damage, source)

    

    def toga_flush_effects(self):
        DANGER_TYPES = (EffectType.ABILITY_SWAP, EffectType.PROF_SWAP, EffectType.ALL_BOOST, EffectType.COST_ADJUST, EffectType.TARGET_SWAP)
        for eff in self.source.current_effects:
            if eff.user == self:
                if eff.unique:
                    self.scene.scene_remove_effect(eff.name, self)
                elif eff.action:
                    self.scene.scene_remove_effect(eff.name, self)
                elif eff.eff_type in DANGER_TYPES:
                    self.remove_effect(eff)
                

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
            #TODO add test flag to remove code crime
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

    def get_boosts(self, damage: int, eff_boost: bool = False) -> int:
        mod_damage = damage
        no_boost = False
        which = 0
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.BOOST_NEGATE)
        for eff in gen:
            no_boost = True
            break
        if not eff_boost:
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

    def get_effect(self, eff_type: EffectType, eff_name: str) -> Optional[Effect]:
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == eff_type)
        for eff in gen:
            if eff.name == eff_name:
                return eff

    def get_effect_with_user(self, eff_type: EffectType, eff_name: str,
                             user: "CharacterManager") -> Optional[Effect]:
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
                if self.id == "ally":
                    self.scene.collapsing_ally_inviolate_shield = True
                elif self.id == "enemy":
                    self.scene.collapsing_enemy_inviolate_shield = True
            if eff.name == "Four-God Resisting Shield":
                self.full_remove_effect("Four-God Resisting Shield", eff.user)
            if eff.name == "Three-God Linking Shield":
                self.full_remove_effect("Three-God Linking Shield", eff.user)
            if eff.name == "Perfect Paper - Rampage Suit":
                self.full_remove_effect("Perfect Paper - Rampage Suit",
                                        eff.user)
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
        gen = [eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.DEST_DEF]
        gen.sort(key = lambda effect: effect.duration)
        if gen:
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

        if "kakashi" in self.scene.missions_to_check:
            if not self.has_effect(EffectType.SYSTEM, "KakashiMission4Tracker"):
                self.add_effect(Effect("KakashiMission4Tracker", EffectType.SYSTEM, source.user, 280000, lambda eff: "", system = True))
        
        if self.source.name == "seryu" and self.source.hp < 50:
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
            if extreme.mag >= 30:
                stacks = extreme.mag // 30
                extreme.user.progress_mission(3, stacks)
                extreme.alter_mag(-(stacks * 30))
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei1"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Maximum Cannon will deal {eff.mag * 20} more damage and cost {eff.mag} more random energy.",
                        mag=stacks, print_mag=True), self)
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei2"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Kangaryu will heal {eff.mag * 25} more health and cost {eff.mag} more random energy.",
                        mag=stacks, print_mag=True), self)
        if self.has_effect(EffectType.MARK,
                    "You Are Needed") and self.source.hp < 80:
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
            self.check_ability_swaps()
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
            if self.source.hp < 50 or self.get_effect(EffectType.DEST_DEF,
                                                      "Susano'o").mag <= 0:
                self.full_remove_effect("itachi3", self)
                self.full_remove_effect("Susano'o", self)
                if self.scene.player:
                    self.update_profile()
                    self.check_ability_swaps()
                if not self.has_effect(EffectType.SYSTEM, "ItachiMission4Tracker"):
                    self.add_effect(Effect("ItachiMission4Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system = True))


        

    def damage_taken_check(self, damage: int, damager: "CharacterManager"):

            
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
        if self.source.name == "seryu" and self.source.hp < 50:
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
            if extreme.mag >= 30:
                stacks = extreme.mag // 30
                extreme.user.progress_mission(3, stacks)
                extreme.alter_mag(-(stacks * 30))
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei1"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Maximum Cannon will deal {eff.mag * 20} more damage and cost {eff.mag} more random energy.",
                        mag=stacks, print_mag=True), self)
                self.apply_stack_effect(
                    Effect(
                        Ability("ryohei2"),
                        EffectType.STACK,
                        self,
                        280000,
                        lambda eff:
                        f"Kangaryu will heal {eff.mag * 25} more health and cost {eff.mag} more random energy.",
                        mag=stacks, print_mag=True), self)
        if self.has_effect(EffectType.CONT_UNIQUE, "Nemurin Nap"):
            self.get_effect(EffectType.CONT_UNIQUE,
                            "Nemurin Nap").alter_mag(-1)
            if self.get_effect(EffectType.CONT_UNIQUE,
                            "Nemurin Nap").mag < 1:
                self.get_effect(EffectType.CONT_UNIQUE,
                            "Nemurin Nap").mag = 1
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
                           "You Are Needed") and self.source.hp < 80:
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
            self.check_ability_swaps()
        if self.has_effect(EffectType.CONT_AFF_DMG, "Susano'o"):
            if self.source.hp < 50 or self.get_effect(EffectType.DEST_DEF,
                                                      "Susano'o").mag <= 0:
                self.full_remove_effect("itachi3", self)
                self.full_remove_effect("Susano'o", self)
                if self.scene.player:
                    self.update_profile()
                    self.check_ability_swaps()
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
                       if eff.eff_type == EffectType.COUNTER_RECEIVE)
        for eff in gen:
            return True
        return False

    def killing_blow_mission_check(self, targeter: Union["CharacterManager", Effect], active_killing_blow = True):
        if active_killing_blow:
            TriggerHandler.handle_killing_blow_trigger(targeter, self, targeter.used_ability.name)
            MissionHandler.handle_killing_blow_mission(targeter, self, targeter.used_ability.name)
        else:
            TriggerHandler.handle_killing_blow_trigger(targeter.user, self, targeter.name)
            MissionHandler.handle_killing_blow_mission(targeter.user, self, targeter.name)
            
    def action_effect_cancel(self):
        [self.scene.scene_remove_effect(eff.name, self) for eff in self.source.current_effects if eff.action and eff.user == self]
        
    def active_redeemable(self, targeter: "CharacterManager"):
        return not (targeter.used_ability.name == "Body Modification - Self Destruct" or targeter.used_ability.name == "Insatiable Justice" or targeter.used_ability.name == "Partial Shiki Fuujin" or targeter.used_ability.name == "Blasted Tree")
    
    

    def death_check(self, targeter: "CharacterManager"):
        if self.source.hp <= 0:
            if self.has_effect(
                    EffectType.MARK,
                    "Doping Rampage") and not self.scene.dying_to_doping and self.active_redeemable(targeter):
                self.source.hp = 1
                self.progress_mission(4, 1)
            elif self.has_effect(EffectType.MARK, "Lucky Rabbit's Foot") and self.active_redeemable(targeter):
                self.source.hp = 50
                self.get_effect(EffectType.MARK, "Lucky Rabbit's Foot").user.progress_mission(3, 1)
                self.add_effect(Effect("SnowWhiteMission5Tracker", EffectType.SYSTEM, self, 280000, lambda eff:"", system=True))
            else:
                
                self.action_effect_cancel()
                
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
                
                if targeter.used_ability != None and targeter.used_ability.name == "Yatsufusa":
                    if self.id == targeter.id:
                        self.add_effect(
                            Effect(
                                targeter.used_ability, EffectType.MARK, targeter, 3,
                                lambda eff:
                                "At the beginning of her next turn, Kurome will animate this character."
                            ))
                    else:
                        targeter.apply_stack_effect(
                            Effect(
                                targeter.used_ability,
                                EffectType.STACK,
                                targeter,
                                280000,
                                lambda eff:
                                f"Mass Animation will deal {eff.mag * 10} more damage.",
                                mag=1), targeter)        
                
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
            elif self.has_effect(EffectType.MARK, "Lucky Rabbit's Foot"):
                self.source.hp = 50
            else:
                self.action_effect_cancel()
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

        if self.source.name == "seryu" and self.source.hp >= 50:
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
        if self.source.hp > 200:
            self.source.hp = 200

    def give_eff_healing(self, healing: int, target: "CharacterManager", source: Effect):
        #TODO add healing boosts
        target.receive_eff_healing(healing, source)

    def receive_eff_healing(self, healing: int, source: Effect):
        mod_healing = healing  #TODO: Add healing reduction/boost checking
        #TODO: Check for healing negation

        if self.source.name == "seryu" and self.source.hp >= 50:
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
        if self.source.hp > 200:
            self.source.hp = 200

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
        self.source.change_energy_cont(-drain)

        #region Drain Mission Check

        if targeter.source.name == "hinata":
            targeter.source.mission1progress += 1

        #endregion

        targeter.check_on_drain(self)


    def special_targeting_exemptions(self,
                                     targeter: "CharacterManager") -> bool:
        target = self
        exempt = False
        if targeter.has_effect(EffectType.MARK,
                               "Frozen Castle") and not (target.has_effect(
                                   EffectType.UNIQUE, "Frozen Castle") or target.has_effect(EffectType.MARK, "Frozen Castle")):
            exempt = True
        if not targeter.has_effect(EffectType.MARK,
                                   "Frozen Castle") and target.has_effect(
                                       EffectType.UNIQUE, "Frozen Castle"):
            exempt = True
        if not targeter.has_effect(EffectType.UNIQUE,
                                   "Frozen Castle") and (target.has_effect(
                                       EffectType.MARK, "Frozen Castle") and not targeter.has_effect(EffectType.MARK, "Frozen Castle")):
            exempt = True
        if targeter.has_effect(
                EffectType.UNIQUE,
                "Streets of the Lost") and self != targeter.get_effect(
                    EffectType.UNIQUE, "Streets of the Lost").user:
            exempt = True
        return exempt

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
            if self.check_bypass_effects() == "BYPASS":
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
        
    def free_execute_ability(self, ally_team, enemy_team):
        self.used_ability.execute(self, ally_team, enemy_team)
        self.check_for_cost_increase_missions()
        self.scene.reset_id()
        self.scene.sharingan_reflector = None
        self.scene.sharingan_reflecting = False

    def toggle_allegiance(self):
        if self.id == "enemy":
            self.id = "ally"
        else:
            self.id = "enemy"  

    def is_ignoring(self) -> bool:
        for effect in self.source.current_effects:
            if effect.eff_type == EffectType.IGNORE:
                return True
        return False

    def helpful_target(self,
                       targeter: "CharacterManager",
                       def_type="NORMAL") -> bool:
        if def_type == "NORMAL":
            return not ((self.check_isolated() and self != targeter) or self.source.dead
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

        for idx, effect_cluster in enumerate(self.make_effect_clusters().items()):
            (column, row) = (idx // max_columns, idx % max_columns)
            cluster_name, effect_set = effect_cluster
            effect_sprite = self.scene.ui_factory.from_surface(
                sdl2.ext.BUTTON,
                self.scene.get_scaled_surface(effect_set[0].eff_img, 25, 25),
                free=True)
            for eff in effect_set:
                if eff.print_mag:
                    effect_sprite.surface = self.stamp_stack_count(eff.mag, effect_sprite.surface)
                    break
            effect_sprite.effects = effect_set
            effect_sprite.ID = f"{idx}/{self.id}"
            effect_sprite.is_enemy = self.is_enemy()
            self.scene.active_effect_buttons.append(effect_sprite)
            self.scene.add_bordered_sprite(self.effect_region, effect_sprite,
                                           BLACK, row * x_offset,
                                           column * y_offset)

    def stamp_stack_count(self, stacks: int,
                       surface: sdl2.SDL_Surface) -> sdl2.SDL_Surface:
        
        if stacks < 10:
            font = self.scene.stack_font
            x_offset = 7
            y_offset = -5
        elif stacks < 100:
            font = self.scene.large_stack_font
            x_offset = 2
            y_offset = -2
        elif stacks < 200:
            font = self.scene.huge_stack_font
            x_offset = 1
            y_offset = 2
        else:
            font = self.scene.huge_stack_font
            x_offset = 0
            y_offset = 2
        
        text_border_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            font, str.encode(f"{stacks}"), BLACK)
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            font, str.encode(f"{stacks}"), WHITE)
        
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset - 1, y_offset - 1, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset, y_offset - 1, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset + 1, y_offset - 1, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset - 1, y_offset, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset + 1, y_offset, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset - 1, y_offset + 1, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset, y_offset + 1, 25, 25))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset + 1, y_offset + 1, 25, 25))
        
        sdl2.surface.SDL_BlitSurface(text_surface, None, surface,
                                     sdl2.SDL_Rect(x_offset, y_offset, 25, 25))
        
        return surface
        
    def stamp_cooldown(self, cooldown: int,
                       surface: sdl2.SDL_Surface) -> sdl2.SDL_Surface:
        text_border_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.scene.cooldown_font, str.encode(f"{cooldown}"), BLACK)
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.scene.cooldown_font, str.encode(f"{cooldown}"), WHITE)
        
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(20, -15, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(22, -15, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(24, -15, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(20, -17, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(24, -17, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(20, -19, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(22, -19, 0, 0))
        sdl2.surface.SDL_BlitSurface(text_border_surface, None, surface,
                                     sdl2.SDL_Rect(24, -19, 0, 0))
        
        
        sdl2.surface.SDL_BlitSurface(text_surface, None, surface,
                                     sdl2.SDL_Rect(25, -20, 0, 0))
        return surface

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
        if self.source.current_hp == 200:
            hp_bar = self.scene.sprite_factory.from_color(GREEN,
                                                          size=(100, 20))
        elif self.source.current_hp == 0:
            hp_bar = self.scene.sprite_factory.from_color(RED, size=(100, 20))
        else:
            hp_bar = self.scene.sprite_factory.from_color(BLACK,
                                                          size=(100, 20))
            green_bar = self.scene.sprite_factory.from_color(
                GREEN, size=(self.source.current_hp // 2, 20))
            sdl2.surface.SDL_BlitSurface(green_bar.surface, None,
                                         hp_bar.surface,
                                         sdl2.SDL_Rect(0, 0, 0, 0))
            if self.source.current_hp <= 200:
                red_bar = self.scene.sprite_factory.from_color(
                    RED, size=((200 - self.source.current_hp) // 2, 20))
                sdl2.surface.SDL_BlitSurface(
                    red_bar.surface, None, hp_bar.surface,
                    sdl2.SDL_Rect((self.source.current_hp // 2)  + 1, 0, 0, 0))
        hp_text = sdl2.sdlttf.TTF_RenderText_Blended(
            self.scene.font, str.encode(f"{self.source.current_hp}"), BLACK)

        if self.source.current_hp >= 100:
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
        self.primary_target = None
        self.acted = False
        self.current_targets.clear()
        self.received_ability.clear()
        self.used_ability = None
        self.set_untargeted()
        self.targeting = False
        self.targeted = False
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
        self.update_ability()
        self.adjust_ability_costs()
        self.update_targeted_sprites()
        self.update_effect_region()
        self.draw_hp_bar()

    def update_limited(self, x: int = 0, y: int = 0):
        self.character_region.clear()
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
                                                    "enemyaltprof1"])
            elif eff.mag == 2:
                self.profile_sprite.surface = self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces[self.source.name +
                                                      "enemyaltprof2"])

    def update_profile(self, x: int = 0, y: int = 0):
        self.character_region.add_sprite(
            self.scene.sprite_factory.from_surface(
                self.scene.get_scaled_surface(
                    self.scene.scene_manager.surfaces["banner"],
                    width=520,
                    height=160),
                free=True), 100, -23)
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
        
    
    def used_slot_click(self, button, _sender):
        if self.used_slot.ability != None:
            self.scene.remove_targets(self.used_slot.ability)
            self.set_used_slot_to_none()

    def set_used_slot_to_none(self):
        logging.debug("Set %s's used slot to none", self.source.name)
        self.used_slot.ability = None

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
        if not self.scene.window_up and not self.scene.window_closing:
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

    def check_ability_swaps(self, ffs_shokuhou: bool = False):
        self.source.current_abilities = [
            ability for ability in self.source.main_abilities
        ]
        
        if self.scene.player and not ffs_shokuhou and hasattr(self, "main_ability_sprites"):
            self.current_ability_sprites = [
                sprite for sprite in self.main_ability_sprites
            ]
        gen = (eff for eff in self.source.current_effects
               if eff.eff_type == EffectType.ABILITY_SWAP)
        for eff in gen:
            swap_from = eff.mag // 10
            
            swap_to = eff.mag - (swap_from * 10)
            
            if self.scene.player and not ffs_shokuhou and hasattr(self, "alt_ability_sprites"):
                    self.current_ability_sprites[swap_from -
                                            1] = self.alt_ability_sprites[swap_to
                                                                        - 1]
            self.source.current_abilities[
                swap_from - 1] = self.source.alt_abilities[swap_to - 1]
        if self.scene.player and not ffs_shokuhou and hasattr(self, "current_ability_sprites"):
            for i, sprite in enumerate(self.current_ability_sprites):
                sprite.ability = self.source.current_abilities[i]

    

    def update_ability(self):

        self.check_ability_swaps()
        self.adjust_targeting_types()
        if self.used_slot.ability != None:
            logging.debug("%s used slot should show up as %s", self.source.name, self.used_slot.ability.name)
            surface = self.scene.get_scaled_surface(self.scene.scene_manager.surfaces[self.used_slot.ability.db_name], 80, 80)
        else:
            logging.debug("%s used slot should show up as nothing")
            surface = self.scene.get_scaled_surface(self.scene.scene_manager.surfaces["used_slot"], 80, 80)
        
        self.used_slot.surface = surface
        self.character_region.add_sprite(self.used_slot.border, 118, -2)
        self.character_region.add_sprite(self.used_slot, 120, 0)
        
        for i, button in enumerate(self.current_ability_sprites):
            self.scene.add_sprite_with_border(self.character_region, button,
                                              button.border, 225 + (i * 90),
                                              0)
            
            
            if self.scene.selected_ability and button.ability.name == self.scene.selected_ability.name:
                self.character_region.add_sprite(button.selected_pane,
                                                 225 + (i * 90), 0)
            else:
                if not button.ability.can_use(self.scene, self) or self.acted or not self.is_controllable():
                    if button.ability.cooldown_remaining > 0:
                        button.null_pane.surface = self.scene.get_scaled_surface(
                            self.scene.scene_manager.surfaces["locked"], 80, 80)
                        button.null_pane.surface = self.stamp_cooldown(
                            button.ability.cooldown_remaining,
                            button.null_pane.surface)
                        self.character_region.add_sprite(
                            button.null_pane, 225 + (i * 90), 0)
                    else:
                        button.null_pane.surface = self.scene.get_scaled_surface(
                            self.scene.scene_manager.surfaces["locked"], 80, 80)
                        self.character_region.add_sprite(
                            button.null_pane, 225 + (i * 90), 0)



