from operator import add
from random import randint
import PIL
from PIL import Image
from pathlib import Path
import sdl2
import sdl2.ext
import enum
import copy
import sys
import os
import importlib.resources
from animearena.effects import EffectType, Effect

def get_path(file_name: str) -> Path:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return path


RESOURCES = Path(__file__).parent.parent.parent / "resources"
import typing
from typing import Iterable, Callable
from animearena.energy import Energy
if typing.TYPE_CHECKING:
    from animearena.battle_scene import CharacterManager, BattleScene
    from animearena.character import Character



@enum.unique
class Target(enum.IntEnum):
    "A component for determining the targeting style of an ability"
    SINGLE = 0
    MULTI_ENEMY = 1
    MULTI_ALLY = 2
    ALL_TARGET = 3


@enum.unique
class DamageType(enum.IntEnum):
    "A component for specifying the type of damage an ability deals"
    NORMAL = 0
    PIERCING = 1
    AFFLICTION = 2


class Ability():

    image: Image
    name: str = ""
    db_name: str = ""
    desc: str = ""
    target_type: Target
    _base_target_type: Target
    _base_cost: dict[Energy, int]
    cost: dict[Energy, int]
    targeting: bool = False
    _base_cooldown: int = 0
    cooldown: int = 0
    cooldown_remaining: int = 0
    types: list[str]
    target: Callable
    execute: Callable

    def __init__(self, name: str = None):
        if name:
            self.db_name = name
            self.image = Image.open(get_path(name + ".png"))
        try:
            details_package = ability_info_db[name]
            self.unpack_details(details_package)
        except KeyError:
            pass

    def resources_available(self, energy: list[int]) -> bool:
        for k, v in self.cost.items():
            if v > 0:
                if energy[k] < v:
                    return False
        if self.total_cost > energy[4]:
            return False
        return True

    @property
    def total_base_cost(self):
        costs = self._base_cost.values()
        total = 0
        for cost in costs:
            total += cost
        return total

    def placeholder_exe(self, user, playerTeam, enemyTeam):
        print("used placeholder execution")

    def placeholder_tar(self,
                        user,
                        playerTeam,
                        enemyTeam,
                        fake_targeting=False):
        return 0

    def unpack_details(self, details_package):

        self.name = details_package[0]
        self.desc = details_package[1]
        self._base_cost = {Energy(i): details_package[2][i] for i in range(5)}
        self.cost = {k: v for k, v in self._base_cost.items()}
        self._base_cooldown = details_package[2][5]
        self.cooldown = details_package[2][5]
        self._base_target_type = details_package[3]
        self.target_type = details_package[3]
        if len(details_package) == 4:
            self.target = self.placeholder_tar
            self.execute = self.placeholder_exe
        elif len(details_package) == 5:
            self.target = details_package[4]
            self.execute = self.placeholder_exe
        else:
            self.target = details_package[4]
            self.execute = details_package[5]


    # pylint: enable=too-many-arguments
    # pylint: disable=line-too-long

    # pylint: enable=line-too-long
    @property
    def total_cost(self) -> int:
        costs = self.cost.values()
        total = 0
        for cost in costs:
            total += cost
        return total

    @property
    def all_costs(self) -> list[int]:
        return [
            self.cost[Energy.PHYSICAL], self.cost[Energy.SPECIAL],
            self.cost[Energy.MENTAL], self.cost[Energy.WEAPON],
            self.cost[Energy.RANDOM]
        ]

    def can_use(self, scene: "BattleScene",
                character: "CharacterManager") -> bool:
        if self.total_cost > scene.player_display.team.energy_pool[
                Energy.RANDOM]:
            return False
        else:
            for idx, cost in enumerate(self.all_costs):
                if cost > 0 and scene.player_display.team.energy_pool[Energy(
                        idx)] < cost:
                    return False
        if character.is_stunned():
            return False
        if self.target(character, scene.player_display.team.character_managers,
                       scene.enemy_display.team.character_managers, True) == 0:
            return False
        if scene.waiting_for_turn:
            return False
        if self.cooldown_remaining > 0:
            return False
        if character.source.dead:
            return False
        if scene.window_up:
            return False
        return True

    def modify_ability_cost(self, energy_type: Energy, mod: int):
        self.cost[energy_type] = max(self.cost[energy_type] + mod, 0)
        
    def reset_costs(self):
        self.cost = copy.copy(self._base_cost)

    def get_desc(self) -> str:
        return self.desc

    def cost_iter(self) -> Iterable[Energy]:
        for _ in range(self.cost[Energy.PHYSICAL]):
            yield Energy.PHYSICAL
        for _ in range(self.cost[Energy.SPECIAL]):
            yield Energy.SPECIAL
        for _ in range(self.cost[Energy.MENTAL]):
            yield Energy.MENTAL
        for _ in range(self.cost[Energy.WEAPON]):
            yield Energy.WEAPON
        for _ in range(self.cost[Energy.RANDOM]):
            yield Energy.RANDOM

    def reset_cooldown(self):
        self.cooldown = self._base_cooldown

    def change_cooldown(self, cooldown: int):
        self.cooldown += cooldown
        if self.cooldown < 0:
            self.cooldown = 0

    def has_class(self, ability_class: str):
        return any(abi_class == ability_class for abi_class in self.types)

    def start_cooldown(self):
        self.cooldown_remaining = self.cooldown + 1

#region Targeting
#region default targeting methods
def default_target(target_type,
                   def_type: str = "NORMAL",
                   prep_req: str = "NONE",
                   mark_req: str = "NONE",
                   lockout="NONE",
                   protection="NONE"):
    def inner(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
        total_targets = 0
        if def_type != "BYPASS":
            targeting = user.check_bypass_effects()
        else:
            targeting = def_type

        if target_type == "HOSTILE" or target_type == "ALL":
            for enemy in enemyTeam:
                if enemy.hostile_target(user, def_type) and (
                        prep_req == "NONE"
                        or user.has_effect(EffectType.MARK, prep_req)) and (
                            mark_req == "NONE"
                            or enemy.has_effect(EffectType.MARK, mark_req)
                        ) and (lockout == "NONE" or not user.has_effect(
                            lockout[0], lockout[1])) and (
                                protection == "NONE" or not enemy.has_effect(
                                    protection[0], protection[1])):
                    if not fake_targeting:
                        enemy.set_targeted()
                    total_targets += 1
        if target_type == "HELPFUL" or target_type == "ALL":
            for ally in playerTeam:
                if ally.helpful_target(user, def_type) and (
                        prep_req == "NONE"
                        or user.has_effect(EffectType.MARK, prep_req)) and (
                            mark_req == "NONE"
                            or ally.has_effect(EffectType.MARK, mark_req)
                        ) and (lockout == "NONE" or not user.has_effect(
                            lockout[0], lockout[1])) and (
                                protection == "NONE" or not ally.has_effect(
                                    protection[0], protection[1])):
                    if not fake_targeting:
                        ally.set_targeted()
                    total_targets += 1
        if target_type == "SELFLESS":
            for ally in playerTeam:
                if ally != user and ally.helpful_target(user, def_type) and (
                        prep_req == "NONE"
                        or user.has_effect(EffectType.MARK, prep_req)) and (
                            mark_req == "NONE"
                            or ally.has_effect(EffectType.MARK, mark_req)
                        ) and (lockout == "NONE" or not user.has_effect(
                            lockout[0], lockout[1])) and (
                                protection == "NONE" or not ally.has_effect(
                                    protection[0], protection[1])):
                    if not fake_targeting:
                        ally.set_targeted()
                    total_targets += 1
        if target_type == "SELF":
            if (mark_req == "NONE"
                    or user.has_effect(EffectType.MARK, mark_req)
                ) and (prep_req == "NONE"
                       or user.has_effect(EffectType.MARK, prep_req)) and (
                           lockout == "NONE" or not user.has_effect(
                               lockout[0], lockout[1])) and (
                                   protection == "NONE" or not user.has_effect(
                                       protection[0], protection[1])):
                if not fake_targeting:
                    user.set_targeted()
                total_targets += 1
        return total_targets

    return inner

#endregion

# (user: "CharacterManager",
#               playerTeam: list["CharacterManager"],
#               enemyTeam: list["CharacterManager"],
#               fake_targeting: bool = False) -> int:
#     total_targets = 0

#     return total_targets   

#region unique targeting methods
def target_one_cut_killing(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()
    if user.has_effect(EffectType.MARK, "Little War Horn"):
        for enemy in enemyTeam:
            if not enemy.source.dead:
                enemy.set_targeted()
            total_targets += 1
    else:
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting) and enemy.has_effect(EffectType.MARK, "Red-Eyed Killer"):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets

def target_detonate(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    for ally in playerTeam:
        if ally.hostile_target(user, targeting) and ((ally.has_effect(EffectType.STACK, "Doll Trap") and ally.get_effect(EffectType.STACK, "Doll Trap").user == user) or ((ally.has_effect(EffectType.STACK, "Close Combat Bombs")) and (ally.get_effect(EffectType.STACK, "Close Combat Bombs").user == user))):
            if not fake_targeting:
                ally.set_targeted()
            total_targets += 1
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting) and ((enemy.has_effect(EffectType.STACK, "Doll Trap") and enemy.get_effect(EffectType.STACK, "Doll Trap").user == user) or ((enemy.has_effect(EffectType.STACK, "Close Combat Bombs")) and (enemy.get_effect(EffectType.STACK, "Close Combat Bombs").user == user))):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_sistema_CAI(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    if user.source.sistema_CAI_stage == 4:
        for ally in playerTeam:
            if ally.helpful_target(user, targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_eight_trigrams(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    for ally in playerTeam:
        if ally.helpful_target(user, targeting):
            if not fake_targeting:
                ally.set_targeted()
            total_targets += 1
    if user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets

def target_getsuga_tenshou(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if user.has_effect(EffectType.MARK, "Tensa Zengetsu"):
        targeting = "BYPASS"
    
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets 

def target_kill_shinso(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for enemy in enemyTeam:
        if enemy.hostile_target(user, "BYPASS"):
            if enemy.has_effect(EffectType.STACK, "Kill, Kamishini no Yari"):
                total_targets += 1
                if not fake_targeting:
                    enemy.set_targeted()
    return total_targets

def target_maria_the_ripper(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting) and ((enemy.has_effect(EffectType.MARK, "Fog of London") or enemy.has_effect(EffectType.MARK, "Streets of the Lost"))):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_heartbeat_distortion(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    #AOE

    targeting = user.check_bypass_effects()

    if not user.has_effect(EffectType.CONT_USE, "Heartbeat Distortion"):
        for enemy in enemyTeam:
            if enemy.has_effect(EffectType.MARK, "Heartbeat Surround"):
                targeting = "BYPASS"
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
            
               
    return total_targets

def target_heartbeat_surround(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if not user.has_effect(EffectType.CONT_USE, "Heartbeat Surround"):
        for enemy in enemyTeam:
            if enemy.has_effect(EffectType.MARK, "Heartbeat Distortion"):
                targeting = "BYPASS"
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
            
    return total_targets

def target_kamui(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    
    for enemy in enemyTeam:
        if enemy.hostile_target(user, "BYPASS"):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    if not fake_targeting:
        user.set_targeted()
    total_targets += 1
    return total_targets

def target_needle_pin(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if user.has_effect(EffectType.MARK, "Teleporting Strike"):
        targeting = "BYPASS"

    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_ideal_strike(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    if user.source.hp <= 50:
        for enemy in enemyTeam:
            if enemy.hostile_target(user, "BYPASS"):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets

def target_beast_instinct(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    if user.has_effect(EffectType.MARK, "King of Beasts Transformation - Lionel"):
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
        if not fake_targeting:
            user.set_targeted()
        total_targets += 1
    return total_targets

def target_lion_fist(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    if user.has_effect(EffectType.MARK, "King of Beasts Transformation - Lionel"):
        for enemy in enemyTeam:
            if enemy.has_effect(EffectType.MARK, "Beast Instinct"):
                targeting = "BYPASS"
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets


def target_pumpkin(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if user.has_effect(EffectType.MARK, "Pumpkin Scouter"):
        targeting = "BYPASS"
    
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_cutdown_shot(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if user.has_effect(EffectType.MARK, "Pumpkin Scouter"): 
        targeting = "BYPASS"
    
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_shun_shun_rikka(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    def one():
        return user.has_effect(EffectType.MARK, "Tsubaki!")

    def two():
        return user.has_effect(EffectType.MARK, "Ayame! Shun'o!")
    
    def three():
        return user.has_effect(EffectType.MARK, "Lily! Hinagiku! Baigon!")
    
    if one() and two() and three():
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
        for ally in playerTeam:
            if ally.helpful_target(user, targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    elif (one() and three()) or (one() and two()) or (two() and three()) or (two()) or (three()):
        for ally in playerTeam:
            if ally.helpful_target(user, targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    elif one():
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1


    return total_targets

def target_minion_minael_yunael(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    if not fake_targeting:
        user.set_targeted()
    total_targets += 1
    return total_targets

def target_insatiable_justice(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for enemy in enemyTeam:
        if enemy.hostile_target(user, "BYPASS") and enemy.source.hp < 30:
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def get_controlled_character(user: "CharacterManager", enemyTeam: list["CharacterManager"]) -> "CharacterManager":
    for enemy in enemyTeam:
        if enemy.has_effect_with_user(EffectType.MARK, "Mental Out", user):
            return enemy

def target_mental_out(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for enemy in enemyTeam:
        if enemy.hostile_target(user, user.check_bypass_effects()) and enemy.source.name != "misaki":
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_mental_out_order(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    controlled_character = get_controlled_character(user, enemyTeam)
    stolen_ability = user.get_effect_with_user(EffectType.MARK, "Mental Out", user).mag
    if stolen_ability < 4:
        total_targets = controlled_character.source.main_abilities[stolen_ability].target(controlled_character, playerTeam, enemyTeam, fake_targeting)
    else:
        total_targets = controlled_character.source.alt_abilities[stolen_ability - 4].target(controlled_character, playerTeam, enemyTeam, fake_targeting)
    return total_targets

def target_loyal_guard(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for ally in playerTeam:
        if ally != user and not ally.source.dead:
            if not fake_targeting:
                user.set_targeted()
            total_targets += 1
    return total_targets

def target_ruler(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if user.has_effect(EffectType.MARK, "Dive"):
        targeting = "BYPASS"
    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets

def target_transform(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for enemy in enemyTeam:
        if enemy.has_effect_with_user(EffectType.STACK, "Quirk - Transform", user):
            if enemy.hostile_target(user, "BYPASS"):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets

def target_titanias_rampage(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    if not user.has_effect(EffectType.CONT_UNIQUE, "Titania's Rampage"):
        if not fake_targeting:
            user.set_targeted()
        total_targets += 1
    return total_targets

#endregion
#endregion


#region Execution
#(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass



#region Naruto Execution
def exe_rasengan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 25
        stun_duration = 2
        if user.has_effect(EffectType.ALL_BOOST, "Sage Mode"):
            stun_duration = 4
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(Ability("naruto2"), EffectType.ALL_STUN, user, stun_duration, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_clones(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("naruto1"), EffectType.ALL_DR, user, 5, lambda eff: "Naruto has 10 points of damage reduction.", mag=10))
    user.add_effect(Effect(Ability("naruto1"), EffectType.ABILITY_SWAP, user, 5, lambda eff: "Shadow Clones has been replaced by Sage Mode.", mag=11))
    user.add_effect(Effect(Ability("naruto1"), EffectType.ABILITY_SWAP, user, 5, lambda eff: "Naruto Taijutsu has been replaced by Uzumaki Barrage.", mag=32))
    user.add_effect(Effect(Ability("naruto1"), EffectType.TARGET_SWAP, user, 5, lambda eff: "Rasengan will target all enemies.", mag=21))
    user.check_on_use()

def exe_naruto_taijutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 30
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_substitution(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("naruto4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Naruto is invulnerable."))
    user.check_on_use()

def exe_sage_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.full_remove_effect("Shadow Clones", user)
    user.scene.player_display.team.energy_pool[Energy.SPECIAL] += 1
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.ALL_INVULN, user, 3, lambda eff: "Naruto is invulnerable."))
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.ABILITY_SWAP, user, 3, lambda eff: "Uzumaki Barrage has been replaced by Toad Taijutsu.", mag=33))
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.ALL_BOOST, user, 3, lambda eff: "Rasengan stun duration and damage are doubled.", mag=225))
    user.check_on_use()

def exe_uzumaki_barrage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 15
        stunned = False
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
                if user.has_effect(EffectType.MARK, "Uzumaki Barrage"):
                    target.add_effect(Effect(Ability("narutoalt2"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
            user.add_effect(Effect(Ability("narutoalt2"), EffectType.MARK, user, 3, lambda eff: "Uzumaki Barrage will stun its target for one turn."))
        
        user.check_on_use()
        user.check_on_harm()

def exe_toad_taijutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 35
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(Ability("narutoalt3"), EffectType.COST_ADJUST, user, 4, lambda eff: "This character's ability costs have been increased by 2 random energy.", mag=52))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Aizen Execution
def exe_shatter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(Ability("aizen1"), EffectType.COST_ADJUST, user, 2, lambda eff: "This character's ability costs are increased by one random energy.", mag=51))
                target.add_effect(Effect(Ability("aizen1"), EffectType.MARK, user, 3, lambda eff: "This character will take 20 additional damage from Overwhelming Power."))
                target.add_effect(Effect(Ability("aizen1"), EffectType.MARK, user, 3, lambda eff: "If Black Coffin is used on this enemy, it will also affect their allies."))
            
                #Black Coffin
                if target.has_effect(EffectType.MARK, "Black Coffin"):
                    for ability in target.source.current_abilities:
                        if ability.cooldown_remaining > 0:
                            ability.cooldown_remaining += 2
                if target.has_effect(EffectType.MARK, "Overwhelming Power"):
                    user.add_effect(Effect(Ability("aizen1"), EffectType.COST_ADJUST, user, 2, lambda eff: "Aizen's ability costs have been reduced by one random energy.", mag=-51))

        user.check_on_use()
        user.check_on_harm()

def exe_overwhelming_power(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage=25
            if target.has_effect(EffectType.MARK, "Shatter, Kyoka Suigetsu"):
                base_damage += 20
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(Ability("aizen2"), EffectType.MARK, user, 3, lambda eff: "If Shatter, Kyoka Suigetsu is used on this character, Aizen's abilities will cost one fewer random energy for one turn."))
                target.add_effect(Effect(Ability("aizen2"), EffectType.MARK, user, 3, lambda eff: "If Black Coffin is used on this enemy, they will take 20 damage."))
                if target.has_effect(EffectType.MARK, "Black Coffin"):
                    target.add_effect(Effect(Ability("aizen2"), EffectType.DEF_NEGATE, user, 3, lambda eff: "This character cannot reduce damage or become invulnerable."))
        user.check_on_use()
        user.check_on_harm()

def exe_black_coffin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        if user.primary_target.final_can_effect(user.check_bypass_effects()):
            if user.primary_target.has_effect(EffectType.MARK, "Shatter, Kyoka Suigetsu"):
                for enemy in enemyTeam:
                    if enemy != user.primary_target and enemy.hostile_target(user, user.check_bypass_effects()):
                        user.current_targets.append(enemy)

        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(Ability("aizen3"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                target.add_effect(Effect(Ability("aizen3"), EffectType.MARK, user, 3, lambda eff: "If Shatter, Kyoka Suigetsu is used on this character, all of their active cooldowns will be increased by 2."))
                target.add_effect(Effect(Ability("aizen3"), EffectType.MARK, user, 3, lambda eff: "If Overwhelming Power is used on this character, they will be unable to reduce damage or become invulnerable for 2 turns."))
                user.check_on_stun(target)
                if target.has_effect(EffectType.MARK, "Overwhelming Power"):
                    base_damage = 20
                    user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_effortless_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("aizen4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Aizen is invulnerable."))
    user.check_on_use()
#endregion
#region Akame Execution
def exe_red_eyed_killer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            target.add_effect(Effect(Ability("akame1"), EffectType.MARK, user, 3, lambda eff: "Akame can use One Cut Killing on this character."))
    user.check_on_use()

def exe_one_cut_killing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) or (user.has_effect(EffectType.MARK, "Little War Horn") and target.final_can_effect("FULLBYPASS")):
                base_damage = 100
                user.deal_aff_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_little_war_horn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("akame3"), EffectType.MARK, user, 5, lambda eff: "Akame can use One Cut Killing on any target."))
    user.check_on_use()

def exe_rapid_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("akame4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Akame is invulnerable."))
    user.check_on_use()
#endregion
#region Astolfo Execution
def exe_casseur(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        target.add_effect(Effect(user.used_ability, EffectType.COUNTER, user, 2, lambda eff: "Astolfo will counter the first harmful Special or Mental ability used against this character. This effect is invisible until triggered.", invisible = True))
    user.check_on_help()
    user.check_on_use()

def exe_trap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 20
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.BOOST_NEGATE, user, 2, lambda eff: "This character cannot have their damage boosted over its base value."))
                if target.has_boosts():
                    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=1), user)
                
        user.check_on_use()
        user.check_on_harm()
            

def exe_luna(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id < 3:
                hostile_effects = [eff for eff in target.source.current_effects if eff.user.is_enemy()]
                if hostile_effects:
                    num = randint(0, len(hostile_effects) - 1)
                    print(f"Removing effect at index {num}")
                    target.full_remove_effect(hostile_effects[num].name, hostile_effects[num].user)
                    user.apply_stack_effect(Effect(Ability("astolfo2"), EffectType.STACK, user, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=1), user)
            if target.id > 2:
                if target.final_can_effect(user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.BOOST_NEGATE, user, 4, lambda eff: "This character cannot have their damage boosted over its base value."))
        user.check_on_use()
        user.check_on_help()
        user.check_on_harm()
        

                    

def exe_kosmos(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Astolfo is invulnerable."))
    user.check_on_use()

#endregion
#region Calamity Mary Execution
def exe_pistol(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
            user.add_effect(Effect(Ability("cmaryalt1"), EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Quickdraw - Pistol has been replaced by Quickdraw - Rifle.", mag=11))
        user.check_on_use()
        user.check_on_harm()

def exe_mine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "If this character uses a new ability, they will take 20 piercing damage and this effect will end."))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 4, lambda eff: "Grenade Toss will deal 20 additional damage to this character."))
        user.check_on_use()
        user.check_on_harm()

def exe_grenade_toss(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 20
            if target.final_can_effect(user.check_bypass_effects()):
                if target.has_effect(EffectType.UNIQUE, "Hidden Mine"):
                    base_damage += 20
                user.deal_damage(base_damage, target)

        user.check_on_use()
        user.check_on_harm()

def exe_rifle_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Calamity Mary is invulnerable."))
    user.check_on_use()

def exe_rifle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Calamity Mary is using Quickdraw - Rifle. This effect will end if she is stunned. If this effect expires normally, Quickdraw - Rifle will be replaced by Quickdraw - Sniper."))


        user.check_on_use()
        user.check_on_harm()

def exe_sniper(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 55
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(base_damage, target)
            user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Calamity Mary is invulnerable."))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Chachamaru Execution
def exe_target_lock(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character can be targeted with Orbital Satellite Cannon."))
    user.check_on_use()

def exe_satellite_cannon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 35
            if target.final_can_effect("BYPASS"):
                user.deal_pierce_damage(base_damage, target)
        user.check_on_harm()
        user.check_on_use()

def exe_active_combat_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 10
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 10 damage.", mag=10))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_DEST_DEF, user, 5, lambda eff: "This character will gain 15 points of destructible defense.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Chachamaru cannot use Orbital Satellite Cannon."))
        user.check_on_use()
        user.check_on_harm()

def exe_take_flight(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Chachamaru is invulnerable."))
    user.check_on_use()
#endregion
#region Chrome Execution

def exe_you_are_needed(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Chrome can use her abilities. If she is brought below 30 health, she will switch out with Rokudou Mukuro, and her abilities will be replaced by their alternate forms."))
    user.check_on_use()

def exe_illusory_breakdown(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Chrome's destructible defense is not broken, this character will receive 25 damage and be stunned for one turn."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=20))
        user.check_on_use()
        user.check_on_harm()


def exe_mental_immolation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Chrome's destructible defense is not broken, this character will receive 20 damage and Chrome will remove one random energy from them."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_mental_substitution(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Chrome is invulnerable."))
    user.check_on_use()

def exe_trident_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 25
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_illusory_world_destruction(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: "If this destructible defense is not destroyed, Mukuro will deal 25 damage to all enemies and stun them for one turn."))
    user.check_on_use()

def exe_mental_annihilation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Mukuro's destructible defense is not broken, this character will receive 35 damage that ignores invulnerability."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30))
        user.check_on_use()
        user.check_on_harm()

def exe_trident_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mukuro is invulnerable."))
    user.check_on_use()

#endregion
#region Chu Execution


def exe_relentless_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target.check_for_dmg_reduction() < 15:
                    user.deal_pierce_damage(base_damage, target)
                else:
                    user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: "This character will take 15 damage. If this character has less than 15 points of damage reduction, this damage will be piercing.", mag=15))
                user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Chu is using Relentless Assault. This effect will end if he is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_flashing_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 6, lambda eff: "Chu has 15 points of damage reduction.", mag=15))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "Chu will ignore any hostile damaging ability that deals less than 15 original damage."))
    user.check_on_use()

def exe_gae_bolg(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 40
            if target.final_can_effect("BYPASS"):
                for eff in target.source.current_effects:
                    if eff.eff_type==EffectType.DEST_DEF:
                        eff.mag = 0
                        target.check_for_collapsing_dest_def(eff)
                user.deal_pierce_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()



def exe_chu_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Chu is invulnerable."))
    user.check_on_use()


#endregion
#region Cranberry Execution
def exe_illusory_disorientation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 6, lambda eff: "This character's ability costs are increased by 1 random.", mag=51))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "This effect will end if this character uses a new ability."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "This character can be targeted by Merciless Finish."))
            user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Illusory Disorientation has been replaced by Merciless Finish.", mag = 11))
        user.check_on_use()
        user.check_on_harm()

def exe_fortissimo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("FULLBYPASS"):
                base_damage = 25
                if target.is_ignoring() or target.check_invuln():
                    base_damage = 50
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_mental_radar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.helpful_target(user, user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "This character will ignore counter effects."))
    user.check_on_use()
    user.check_on_help()

def exe_cranberry_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Cranberry is invulnerable."))
    user.check_on_use()

def exe_merciless_finish(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting:
                user.deal_aff_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 15 affliction damage.", mag=15))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Cranberry is using Merciless Finish. This effect will end if she is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Erza Execution
def exe_clear_heart_clothing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Clear Heart Clothing."))
    user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 280000, lambda eff: "Erza cannot be stunned."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Clear Heart Clothing has been replaced by Titania's Rampage.", mag=11))
    user.check_on_use()

def exe_heavens_wheel_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Heaven's Wheel Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.AFF_IMMUNE, user, 280000, lambda eff: "Erza will ignore affliction damage."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Heaven's Wheel Armor has been replaced by Circle Blade.", mag = 22))
    user.check_on_use()

def exe_nakagamis_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Nakagami's Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.ENERGY_GAIN, user, 280000, lambda eff: "Erza will gain one random energy.", mag=51))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Nakagami's Armor has been replaced by Nakagami's Starlight.", mag = 33))
    user.check_on_use()


def exe_adamantine_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Adamantine Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "Erza has 15 points of damage reduction.", mag=15))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Adamantine Armor has been replaced by Adamantine Barrier.", mag = 44))

def exe_titanias_rampage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"Erza will deal {(eff.mag * 5) + 15} piercing damage to a random enemy.", mag = 1))
    valid_targets: list["CharacterManager"] = []
    for enemy in enemyTeam:
        if enemy.final_can_effect(user.check_bypass_effects()) and not enemy.deflecting():
            valid_targets.append(enemy)
    if valid_targets:
        target = randint(0, len(valid_targets) - 1)
        user.deal_pierce_damage(15, valid_targets[target])
    user.check_on_use()
    if valid_targets:
        user.check_on_harm()


def exe_circle_blade(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "Erza will deal 15 damage to all enemies.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_nakagamis_starlight(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(35, target)
                target.source.energy_contribution -= 1
                user.check_on_drain(target)
        user.check_on_use()
        user.check_on_harm()

def exe_adamantine_barrier(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.helpful_target(user, ):
            target.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "This character is invulnerable."))
    user.check_on_use()
    user.check_on_help()
#endregion
#region Esdeath Execution
def exe_demons_extract(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 9, lambda eff: "Esdeath has activated her Teigu, and can use her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 9, lambda eff: "Demon's Extract has been replaced by Mahapadma.", mag = 11))
    user.check_on_use()

def exe_frozen_castle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "This character cannot target Esdeath's allies."))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "Esdeath is using Frozen Castle. This effect will end if she dies."))
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 5, lambda eff: "Weiss Schnabel will target all enemies.", mag=41))
    user.check_on_use()
    user.check_on_harm()

def exe_weiss_schnabel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.has_effect(EffectType.COST_ADJUST, "Weiss Schnabel"):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will receive 10 damage.", mag=10))
        if user.current_targets:
            user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 5, lambda eff: "Weiss Schnabel will cost one fewer special energy and deal 15 piercing damage to its target.", mag = -321))
    else:
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_pierce_damage(15, target)
    user.check_on_use()
    user.check_on_harm()            

def exe_esdeath_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Esdeath is invulnerable."))
    user.check_on_use()

def exe_mahapadma(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target != user:
            if target.id < 3:
                duration = 5
            else:
                duration = 4
            target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, duration, lambda eff: "This character is stunned."))
            user.check_on_stun(target)
        else:
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "When Mahapadma ends, Esdeath will be stunned for two turns."))
    user.check_on_use()
#endregion
#region Frenda Execution
def exe_close_combat_bombs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect():
                target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 5, lambda eff: f"Detonate will deal {15 * eff.mag} damage to this character.", mag=1), user)
        user.check_on_use()

def exe_doll_trap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if not target.has_effect_with_user(EffectType.MARK, "Doll Trap", user):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "If an enemy damages this character, all stacks of Doll Trap will be transferred to them.", invisible=True))
        target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Detonate will deal {20 * eff.mag} damage to this character.", mag=1, invisible=True), user)
    user.check_on_use()

def exe_detonate(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 0
                if target.has_effect_with_user(EffectType.STACK, "Doll Trap", user):
                    base_damage += 20 * target.get_effect_with_user(EffectType.STACK, "Doll Trap", user).mag
                if target.has_effect_with_user(EffectType.STACK, "Close Combat Bombs", user):
                    base_damage += 15 * target.get_effect_with_user(EffectType.STACK, "Close Combat Bombs", user).mag
                target.full_remove_effect("Doll Trap", user)
                target.full_remove_effect("Close Combat Bobms", user)
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_frenda_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Frenda is invulnerable."))
    user.check_on_use()
#endregion
#region Gajeel Execution
def exe_iron_dragon_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(35, target)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_shadow_dragon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.ALL_DR, "Blacksteel Gajeel"):
        user.full_remove_effect("Blacksteel Gajeel", user)
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 280000, lambda eff: "The first time each turn that Gajeel receives a harmful ability, he will ignore all hostile effects for the rest of the turn."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Iron Dragon's Roar has been replaced by Iron Shadow Dragon's Roar.", mag=11))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Iron Dragon's Club has been replaced by Iron Shadow Dragon's Club", mag=22))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Iron Shadow Dragon has been replaced by Blacksteel Gajeel.", mag=33))
    user.check_on_use()

def exe_gajeel_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Gajeel is invulnerable."))
    user.check_on_use()

def exe_iron_shadow_dragon_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_shadow_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_damage(25, target)
        user.check_on_use()
        user.check_on_harm()

def exe_blacksteel_gajeel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon"):
        user.full_remove_effect("Iron Shadow Dragon", user)
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "Gajeel has 15 points of damage reduction."))
    user.check_on_use()



#endregion
#region Gokudera Execution

def advance_sistema_cai(sistema: Effect):
    sistema.alter_mag(1)
    if sistema.mag == 5:
        sistema.mag = 1

def exe_sistema_cai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    stage = user.get_effect(EffectType.STACK, "Sistema C.A.I.").mag
    
    if not user.check_countered(playerTeam, enemyTeam):
        if stage == 1:
            for target in user.current_targets:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(10, target)
            user.check_on_use()
            user.check_on_harm()
            if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
                advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
        elif stage == 2:
            for target in user.current_targets:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(10, target)
                    if target == user.primary_target:
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        user.check_on_stun(target)
            user.check_on_use()
            user.check_on_harm()
            if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
                advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
        elif stage == 3:
            for target in user.current_targets:
                if target == user.primary_target:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_damage(20, target)
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        user.check_on_stun(target)
                else:
                    if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                        user.deal_damage(10, target)
            user.give_healing(15, user)
            user.check_on_use()
            user.check_on_harm()
            if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
                advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
        elif stage == 4:
            for target in user.current_targets:
                if target.id < 2:
                    user.give_healing(25, target)
                else:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_damage(25, target)
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        user.check_on_stun(target)
            
            user.check_on_use()
            user.check_on_harm()
            user.check_on_help()
            if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
                advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))


def exe_vongola_ring(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
        advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
    user.check_on_use()

def exe_vongola_bow(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "The Sistema C.A.I. stage will not advance when Sistema C.A.I. is used."))
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 5, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30))
    user.check_on_use()

def exe_gokudera_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Gokudera is invulnerable."))
    user.check_on_use()

#endregion
#region Hibari Execution
def exe_bite_you_to_death(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_handcuffs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Hibari cannot use Porcospino Nuvola."))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Hibari is using Alaudi's Handcuffs. This effect will end if Hibari is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_porcospino(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 4, lambda eff: "If this character uses a new harmful ability, they will take 10 damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Hibari cannot use Alaudi's Handcuffs."))
        user.check_on_use()
        user.check_on_harm()

def exe_tonfa_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Hibari is invulnerable."))
    user.check_on_use()
#endregion
#region Gray Execution
def exe_ice_make(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Gray can use his abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Ice, Make... has been replaced by Ice, Make Unlimited.", mag=11))
    user.check_on_use()

def exe_freeze_lancer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
        user.check_on_use()
        user.check_on_harm()        


def exe_hammer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Gray is invulnerable."))
    user.check_on_use()

def exe_unlimited(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id < 3:
                target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=5))
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DEST_DEF, user, 280000, lambda eff: f"This character will gain 5 points of destructible defense.", mag=5))
                helped = True
            elif target.id > 2:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(5, target)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 280000, lambda eff: f"This character will take 5 damage.", mag=5))
                    harmed = True
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: f"Gray is using Ice, Make Unlimited."))
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()
#endregion
#region Gunha Execution

def consume_guts(gunha :"CharacterManager", max: int) -> int:
    if not gunha.has_effect(EffectType.STACK, "Guts"):
        return 0
    if gunha.get_effect(EffectType.STACK, "Guts").mag >= max:
        gunha.get_effect(EffectType.STACK, "Guts").alter_mag(max * -1)
        if gunha.get_effect(EffectType.STACK, "Guts").mag < 3:
            gunha.source.main_abilities[2].target_type = Target.SINGLE
        if gunha.get_effect(EffectType.STACK, "Guts").mag == 0:
            gunha.remove_effect(gunha.get_effect(EffectType.STACK, "Guts"))
        return max
    else:
        output = gunha.get_effect(EffectType.STACK, "Guts").mag
        gunha.remove_effect(gunha.get_effect(EffectType.STACK, "Guts"))
        gunha.source.main_abilities[2].target_type = Target.SINGLE
        return output


def exe_guts(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Guts"):
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Gunha has {eff.mag} Guts.", mag=2), user)
        if user.get_effect(EffectType.STACK, "Guts").mag > 2:
            user.source.main_abilities[2].target_type = Target.MULTI_ENEMY
        user.give_healing(25, user)
    else:
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Gunha can use his abilities."))
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Gunha has {eff.mag} Guts.", mag=5), user)
        user.source.main_abilities[2].target_type = Target.MULTI_ENEMY
    user.check_on_use()
    
def exe_super_awesome_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        charges = consume_guts(user, 5)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 35
                if charges >= 2 and user.can_boost():
                    base_damage = 45
                user.deal_pierce_damage(base_damage, target)
                if charges == 5:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()
                
def exe_overwhelming_suppression(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        charges = consume_guts(user, 3)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                suppression = 5
                if charges >= 2:
                    suppression = 10
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: f"This character will deal {eff.mag} less damage.", mag=(suppression * -1)))
                if charges == 3:
                    target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 3, lambda eff: "This character cannot reduce damage or become invulnerable."))
        user.check_on_use()
        user.check_on_harm()

def exe_hyper_eccentric_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        charges = consume_guts(user, 3)
        base_damage = 20
        if charges >= 2 and user.can_boost():
            base_damage = 25
        for target in user.current_targets:
            if charges >= 2:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_pierce_damage(base_damage, target)
            else:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Hinata Execution
def exe_twin_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    used = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
                used = True
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
                used = True
    if used:
        user.check_on_use()
        user.check_on_harm()

def exe_hinata_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    counterable = False
    for target in user.current_targets:
        if target.id > 2:
            counterable = True
    if counterable and not user.check_countered(playerTeam, enemyTeam):
        drained = False
        for target in user.current_targets:
            if target.id > 2 and target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                if user.has_effect(EffectType.MARK, "Byakugan") and not drained:
                    target.source.energy_contribution -= 1
                    drained = True
                    user.check_on_drain(target)
            elif target.id < 3 and target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 10 points of damage reduction.", mag=10))
        if not user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Eight Trigrams - 64 Palms will deal 15 damage to all enemies."))
        else:
            user.get_effect(EffectType.MARK, "Eight Trigrams - 64 Palms").duration = 3
        user.check_on_use()
        user.check_on_harm()
    else:
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 10 points of damage reduction.", mag=10))
        if not user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Eight Trigrams - 64 Palms will deal 15 damage to all enemies."))
        else:
            user.get_effect(EffectType.MARK, "Eight Trigrams - 64 Palms").duration = 3
        user.check_on_use()
        user.check_on_harm()
    

def exe_hinata_byakugan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Hinata will remove one energy from any enemy she damages, once per turn."))
    user.check_on_use()


def exe_gentle_fist_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Hinata is invulnerable."))
#endregion
#region Ichigo Execution
def exe_getsuga_tenshou(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Tensa Zangetsu"):
        def_type = "BYPASS"
        dmg_pierce = True
    else:
        def_type = user.check_bypass_effects()
        dmg_pierce = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                if dmg_pierce:
                    user.deal_pierce_damage(40, target)
                else:
                    user.deal_damage(40, target)
        user.check_on_use()
        user.check_on_harm()

def exe_tensa_zangetsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 4, lambda eff: "Ichigo is invulnerable."))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Getsuga Tenshou deals piercing damage and ignores invulnerabilty."))
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 3, lambda eff: "Zangetsu Strike will target all enemies.", mag=31))
    user.source.energy_contribution += 1
    user.check_on_use()

def exe_zangetsu_slash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        affected = 0
        for target in user.current_targets:
            base_damage = 20
            if user.has_effect(EffectType.STACK, "Zangetsu Strike") and user.can_boost():
                base_damage += (5 * user.get_effect(EffectType.STACK, "Zangetsu Strike").mag)
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
                affected += 1
        if affected > 0:
            user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Zangetsu Strike will deal {5 * eff.mag} more damage.", mag = affected), user)
        user.check_on_use()
        user.check_on_harm()

def exe_zangetsu_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ichigo is invulnerable."))
    user.check_on_use()
#endregion
#region Ichimaru Execution
def exe_butou_renjin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(15, target)
                target.apply_stack_effect(Effect(Ability("ichimaru3"), EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1), user)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "This character will take 15 damage."))
        user.check_on_use()
        user.check_on_harm()

def exe_13_kilometer_swing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                target.apply_stack_effect(Effect(Ability("ichimaru3"), EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1), user)
        user.check_on_use()
        user.check_on_harm()

def exe_kamishini_no_yari(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 10 * target.get_effect_with_user(EffectType.STACK, "Kill, Kamishini no Yari", user).mag
                stack_addition = base_damage
                if target.has_effect_with_user(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari", user):
                    base_damage += target.get_effect(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari").mag
                    target.get_effect(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari").waiting = True
                user.deal_aff_damage(base_damage, target)
                if target.has_effect_with_user(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari", user):
                    target.get_effect_with_user(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari", user).mag += stack_addition
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: f"This character will take {eff.mag} affliction damage.", mag = base_damage))
                target.remove_effect(target.get_effect_with_user(EffectType.STACK, "Kill, Kamishini no Yari", user))
        user.check_on_use()
        user.check_on_harm()

def exe_shinso_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ichimaru is invulnerable."))
    user.check_on_use()

#endregion
#region Jack Execution
def exe_maria_the_ripper(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                user.deal_aff_damage(10, target)
        user.check_on_use()
        user.check_on_harm()

def exe_fog_of_london(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
            user.deal_aff_damage(5, target)
            target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 5, lambda eff: "This character will take 5 affliction damage.", mag=5))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda efF: "Jack can use Maria the Ripper."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Fog of London has been replaced by Streets of the Lost.", mag = 22))
    user.check_on_use()
    user.check_on_harm()

def exe_we_are_jack(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_aff_damage(30, target)
        user.check_on_use()
        user.check_on_harm()

def exe_smokescreen_defense(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Jack is invulnerable."))
    user.check_on_use()

def exe_streets_of_the_lost(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "This character can be targeted by We Are Jack."))
                target.add_effect(Effect(user.used_ability, EffectType.ISOLATE, user, 6, lambda eff: "This character is isolated."))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "This character can only target Jack."))
    user.check_on_use()
    user.check_on_harm()
#endregion
#region Itachi Execution
def exe_amaterasu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_aff_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()


def exe_tsukuyomi(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "If this character is aided by an ally, this effect will end."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 6, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_susanoo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=45))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "Itachi will take 10 affliction damage. If his health falls below 20, Susano'o will end.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Amaterasu has been replaced by Totsuka Blade.", mag=11))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Tsukuyomi has been replaced by Yata Mirror.", mag=22))
    user.receive_eff_aff_damage(10, user)
    user.check_on_use()

def exe_crow_genjutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 280000, lambda eff: f"Itachi is invulnerable."))
    user.check_on_use()

def exe_totsuka_blade(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(35, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_yata_mirror(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.get_effect(EffectType.DEST_DEF, "Susano'o").alter_dest_def(20)
    user.receive_eff_aff_damage(5, user)
    user.check_on_use()
#endregion
#region Jiro Execution
def exe_counter_balance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that stuns this character will lose one energy.", invisible=True))
        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that drains energy this character will be stunned for one turn.", invisible=True))
    user.check_on_use()

def exe_heartbeat_distortion(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.CONT_USE, "Heartbeat Surround"):
        def_type = "BYPASS"
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 15
                if target.final_can_effect(def_type) and not target.deflecting():
                    user.deal_damage(base_damage, target)
            user.check_on_use()
            user.check_on_harm()
    else:
        def_type = user.check_bypass_effects()
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 5
                if target.final_can_effect(def_type) and not target.deflecting():
                    user.deal_damage(base_damage, target)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 7, lambda eff:"This character will take 5 damage.", mag=5))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 7, lambda eff: "Jiro is using Hearbeat Distortion. This effect will end if Jiro is stunned."))
            user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 7, lambda eff: "Heartbeat Surround will ignore invulnerability and deal 20 damage to a single enemy."))
            user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 7, lambda eff: "Heartbeat Surround will cost one less random energy.", mag = -351))
            user.check_on_use()
            user.check_on_harm()

def exe_heartbeat_surround(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.CONT_USE, "Heartbeat Distortion"):
        def_type = "BYPASS"
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 20
                if target.final_can_effect(def_type):
                    user.deal_damage(base_damage, target)
            user.check_on_use()
            user.check_on_harm()
    else:
        def_type = user.check_bypass_effects()
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 10
                if target.final_can_effect(def_type) and not target.deflecting():
                    user.deal_damage(base_damage, target)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 7, lambda eff:"This character will take 10 damage.", mag=10))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 7, lambda eff: "Jiro is using Hearbeat Surround. This effect will end if Jiro is stunned."))
            user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 7, lambda eff: "Heartbeat Distortion will ignore invulnerability and deal 15 damage to all enemies."))
            user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 7, lambda eff: "Heartbeat Distortion will cost one less random energy.", mag = -251))
            user.check_on_use()
            user.check_on_harm()

def exe_early_detection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Jiro is invulnerable."))
    user.check_on_use()
#endregion
#region Kakashi Execution
def exe_copy_ninja(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.REFLECT, user, 2, lambda eff: "Kakashi will reflect the first hostile ability that targets him.", invisible=True))
    user.check_on_use()

def exe_nindogs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "This character will take double damage from Raikiri."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_raikiri(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 40
            if target.has_effect(EffectType.MARK, "Summon - Nin-dogs"):
                base_damage = 80
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_kamui(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user in user.current_targets:
        user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Kakashi will ignore all harmful effects."))
        user.check_on_use()
    else:
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                if target.final_can_effect("BYPASS"):
                    user.deal_pierce_damage(20, target)
                    if target.check_invuln():
                        target.add_effect(Effect(user.used_ability, EffectType.ISOLATE, user, 2, lambda eff: "This character is isolated."))
            user.check_on_use()
            user.check_on_harm()

#endregion
#region Kuroko Execution
def exe_teleporting_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 10
            if user.has_effect(EffectType.MARK, "Judgement Throw") and user.can_boost():
                base_damage = 25
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
        if user.has_effect(EffectType.MARK, "Needle Pin"):
            user.used_ability.cooldown = 0
        user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Kuroko is invulnerable."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Needle Pin will ignore invulnerability and deal 15 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Judgement Throw will have double effect."))
        user.check_on_use()
        user.check_on_harm()

def exe_needle_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Teleporting Strike"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                if user.has_effect(EffectType.MARK, "Teleporting Strike") and not target.deflecting():
                    user.deal_pierce_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 3, lambda eff: "This character cannot reduce damage or become invulnerable."))
                if user.has_effect(EffectType.MARK, "Judgement Throw"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Teleporting Strike will have no cooldown."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Judgement Throw will remove one random energy from its target."))
        user.check_on_use()
        user.check_on_harm()  

def exe_judgement_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Teleporting Strike"):
            if user.can_boost():
                base_damage = 30
            else:
                base_damage = 15
            weaken = 20
        else:
            base_damage = 15 
            weaken = 10
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
                if user.has_effect(EffectType.MARK, "Needle Pin"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: f"This character will deal {eff.mag} less damage.", mag = -weaken))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Teleporting Strike will deal 15 more damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Needle Pin will stun its target for one turn."))
        user.check_on_use()
        user.check_on_harm()

def exe_kuroko_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Kuroko is invulnerable."))
    user.check_on_use()
#endregion
#region Lambo Execution
def exe_ten_year_bazooka(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.full_remove_effect("Summon Gyudon", user)
    for p in playerTeam:
        p.full_remove_effect("Summon Gyudon", user)
    for e in enemyTeam:
        e.full_remove_effect("Summon Gyudon", user)
    if user.has_effect(EffectType.MARK, "Ten-Year Bazooka"):
        user.full_remove_effect("Ten-Year Bazooka", user)
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "Lambo has used the Ten-Year Bazooka."))
        user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 5, lambda eff: "Teen Lambo has been replaced by Adult Lambo.", mag = 2))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Thunder, Set, Charge! has been replaced by Elettrico Cornata.", mag = 22))
    elif user.has_effect(EffectType.UNIQUE, "Ten-Year Bazooka"):
        user.full_remove_effect("Ten-Year Bazooka", user)
    else:
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Lambo has used the Ten-Year Bazooka."))
        user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 7, lambda eff: "Lambo has been replaced by Teen Lambo.", mag = 1))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 7, lambda eff: "Summon Gyudon has been replaced by Thunder, Set, Charge!", mag= 21))
    user.check_on_use()

def exe_conductivity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target != user:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 20 points of damage reduction. If they receive a new damaging ability during this time, Lambo will take 10 damage.", mag = 20))
        else:
            user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 4, lambda eff: "If an ally affected by Conductivity receives a new harmful ability, Lambo will take 10 damage."))
    user.check_on_use()

def exe_summon_gyudon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    harmed = False
    helped = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id > 2:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(5, target)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 280000, lambda eff: "This character will take 5 damage.", mag=5))
                    harmed = True
            elif target.id < 3:
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "This character has 10 points of damage reduction.", mag=10))
                    helped = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()



def exe_lampows_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Lambo is invulnerable."))
    user.check_on_use()

def exe_thunder_set_charge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
        user.check_on_use()
        user.check_on_harm()

def exe_elettrico_cornata(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(35, target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region La Pucelle Execution
def exe_knights_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_magic_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Knight's Sword deals {eff.mag * 20} bonus damage, costs {eff.mag} more random energy, and has its cooldown increased by {eff.mag}.", mag=1), user)
    user.check_on_use()

def exe_ideal_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect("BYPASS"):
            user.deal_damage(40, target)
    user.check_on_use()
    user.check_on_harm()

def exe_knights_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "La Pucelle is invulnerable."))
    user.check_on_use()
#endregion
#region Laxus Execution
def exe_fairy_law(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id < 3 and target.helpful_target(user, user.check_bypass_effects()):
                user.give_healing(20, target)
                helped = True
            elif target.id > 2 and target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                harmed = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

def exe_lightning_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(40, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_thunder_palace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff:"If this effect expires naturally, Laxus will deal 40 damage to the entire enemy team. If he is damaged by a new ability during this time, this effect will end and the offending character will take damage equal to the original damage of the ability they used."))
    user.check_on_use()

def exe_laxus_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Laxus is invulnerable."))
    user.check_on_use()
#endregion
#region Leone Execution
def exe_lionel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Leone can use her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 280000, lambda eff:"Leone will heal 10 health."))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 280000, lambda eff: "Leone will heal 10 health when she damages an enemy or uses Instinctual Dodge."))
    user.check_on_use()

def exe_beast_instinct(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target != user:
                if target.final_can_effect(user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Lion Fist will ignore invulnerability and deal 20 more damage to this target."))
                    harmed = True
            else:
                user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 5, lambda eff: "Leone will ignore stun and counter effects."))
        user.check_on_use()
        if harmed:
            user.check_on_harm()

def exe_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct") or not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Beast Instinct"):
                def_type = "BYPASS"
                base_damage = 55
            else:
                def_type = user.check_bypass_effects()
                base_damage = 35
            if target.final_can_effect(def_type):
                user.deal_damage(55, target)
                user.receive_eff_healing(10)
        user.check_on_use()
        user.check_on_harm()
                

def exe_instinctual_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Leone is invulnerable."))
    user.receive_eff_healing(10)
    user.check_on_use()
#endregion
#region Levy Execution
def exe_solidscript_fire(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If this character uses a new ability, they will take 10 affliction damage."))
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()

def exe_solidscript_silent(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect("FULLBYPASS"):
            target.add_effect(Effect(user.used_ability, EffectType.ISOLATE, user, 4, lambda eff: "This character is isolated."))
    user.check_on_use()


def exe_solidscript_mask(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.helpful_target(user, user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 4, lambda eff: "This character will ignore stun effects."))
            target.add_effect(Effect(user.used_ability, EffectType.AFF_IMMUNE, user, 4, lambda eff: "This character will ignore affliction damage."))
    user.check_on_use()

def exe_solidscript_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Levy is invulnerable."))
    user.check_on_use()
#endregion
#region Raba Execution

def all_marked(team: list["CharacterManager"], mark_name: str):
    for char in team:
        if not char.has_effect(EffectType.MARK, mark_name):
            return False
    return True

def exe_crosstail_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if all_marked(enemyTeam, "Cross-Tail Strike"):
            user.current_targets.clear()
            for enemy in enemyTeam:
                if enemy.final_can_effect("BYPASS"):
                    enemy.full_remove_effect("Cross-Tail Strike", user)
                    user.deal_pierce_damage(20, enemy)
        else:
            for target in user.current_targets:
                if not user.has_effect(EffectType.COST_ADJUST, "Cross-Tail Strike"):
                    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "Until Lubbock uses Cross-Tail Strike on a marked enemy, it costs one less weapon energy.", mag = -141))
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(15, target)
                    if target.has_effect(EffectType.MARK, "Cross-Tail Strike"):
                        user.remove_effect(user.get_effect(EffectType.COST_ADJUST, "Cross-Tail Strike"))
                    else:
                        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character has been marked by Cross-Tail Strike."))
            
        user.check_on_use()
        user.check_on_harm()



def exe_wire_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if all_marked(playerTeam, "Wire Shield"):
            user.current_targets.clear()
            for player in playerTeam:
                if player.helpful_target(user, user.check_bypass_effects()):
                    player.remove_effect(player.get_effect(EffectType.MARK, "Wire Shield"))
                    player.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "This character is invulnerable."))
        else:
            for target in user.current_targets:
                if not user.has_effect(EffectType.COST_ADJUST, "Wire Shield"):
                    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "Until Lubbock uses Wire Shield on a marked ally, it costs one less weapon energy.", mag = -241))
       
                if target.helpful_target(user, user.check_bypass_effects()):
                    if target.has_effect(EffectType.DEST_DEF, "Wire Shield"):
                        target.get_effect(EffectType.DEST_DEF, "Wire Shield").alter_dest_def(15)
                    else:
                        target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15))
                    if target.has_effect(EffectType.MARK, "Wire Shield"):
                        user.remove_effect(user.get_effect(EffectType.COST_ADJUST, "Wire Shield"))
                    else:
                        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character has been marked by Wire Shield."))
        user.check_on_use()
        user.check_on_harm()

def exe_heartseeker_thrust(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(30, target)
                if user.has_effect(EffectType.MARK, "Wire Shield"):
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will receive 15 affliction damage.", mag=15))
                if target.has_effect(EffectType.MARK, "Cross-Tail Strike"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_defensive_netting(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Lubbock is invulnerable."))
    user.check_on_use()
#endregion
#region Lucy Execution (Tests)
def exe_aquarius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id < 3 and target.helpful_target(user, user.check_bypass_effects()):
                helped = True
                if user.has_effect(EffectType.MARK, "Gemini"):
                    help_duration = 4
                else:
                    help_duration = 2
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, help_duration, lambda eff: "This character has 10 points of damage reduction.", mag=10))
            if target.id > 2 and target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                harmed = True
                user.deal_damage(15, target)
                if user.has_effect(EffectType.MARK, "Gemini"):
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 10 damage.", mag=15))
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()


def exe_gemini(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Lucy's abilities will stay active for one extra turn."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 7, lambda eff: "Gemini has been replaced by Urano Metria.", mag = 21))
    user.check_on_use()

def exe_capricorn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                if user.has_effect(EffectType.MARK, "Gemini"):
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 20 damage.", mag=20))
        user.check_on_use()
        user.check_on_harm()

def exe_leo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Gemini"):
        duration = 4
    else:
        duration = 2
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, duration, lambda eff: "Lucy is invulnerable."))
    user.check_on_use()

def exe_urano_metria(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 20 damage.", mag=20))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Midoriya Execution (Tests)
def exe_smash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(45, target)
                user.receive_eff_aff_damage(20, user)
                user.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 3, lambda eff: "This character is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_air_force_gloves(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                user.add_effect(Effect(user.used_ability, EffectType.COOLDOWN_MOD, user, 2, lambda eff: "This character's cooldowns have been increased by 1.", mag = 1))
        user.check_on_use()
        user.check_on_harm()

def exe_shoot_style(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.add_effect(Effect(user.used_ability, EffectType.COUNTER, user, 2, lambda eff: "Midoriya will counter the first harmful ability used on him.", invisible=True))
        user.check_on_use()
        user.check_on_harm()

def exe_enhanced_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Midoriya is invulnerable."))
    user.check_on_use()
#endregion
#region Minato Execution (Tests)
def exe_flying_raijin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_pierce_damage(35, target)
                if target.has_effect(EffectType.MARK, "Marked Kunai"):
                    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Minato is invulnerable."))
                    target.full_remove_effect("Marked Kunai", user)
                    user.used_ability.cooldown = 0
        user.check_on_use()
        user.check_on_harm()

def exe_marked_kunai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_pierce_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character has been marked."))
        user.check_on_use()
        user.check_on_harm()

def exe_partial_shiki_fuujin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.COOLDOWN_MOD, user, 280000, lambda eff: "This character's cooldowns have been increased by 1.", mag = 1))
                target.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "This character's ability costs have been increased by one random.", mag = 51))

def exe_minato_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Minato is invulnerable."))
    user.check_on_use()
#endregion
#region Mine Execution (Tests)
def exe_roman_artillery_pumpkin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Pumpkin Scouter"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                base_damage = 25
                if user.source.hp < 60 and user.can_boost():
                    base_damage = 35
                if user.has_effect(EffectType.MARK, "Pumpkin Scouter") and user.can_boost():
                    base_damage += 5
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_cutdown_shot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Pumpkin Scouter"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                base_damage = 25
                if user.source.hp < 25 and user.can_boost():
                    base_damage = 50
                if user.has_effect(EffectType.MARK, "Pumpkin Scouter") and user.can_boost():
                    base_damage += 5
                user.deal_damage(base_damage, target)
                if user.source.hp < 50:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_pumpkin_scouter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Mine's abilities will ignore invulnerabilty and deal 5 additional damage."))
    user.check_on_use()

def exe_closerange_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mine is invulnerable."))
#endregion
#region Mirai Execution (Tests)
def exe_blood_suppression_removal(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Mirai's abilities cause their target to receive 10 affliction damage for 2 turns."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Blood Suppression Removal has been replaced by Blood Bullet.", mag = 11))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 5, lambda eff: "Mirai will take 10 affliction damage.", mag=10))
    user.receive_eff_aff_damage(10, user)
    user.check_on_use()

def exe_blood_sword_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(30, target)
                if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
                    user.deal_eff_aff_damage(10, target)
                    target.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
        user.check_on_use()
        user.check_on_harm()

def exe_blood_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 20))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: f"This character has {eff.mag} points of damage reduction.", mag = 20))
    if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
        user.receive_eff_aff_damage(10, user)
        user.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
    user.check_on_use()
    

def exe_mirai_deflect(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mirai is invulnerable."))
    user.check_on_use()

def exe_blood_bullet(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_aff_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
                if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
                    user.deal_eff_aff_damage(10, target)
                    target.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
        user.check_on_use()
        user.check_on_harm()

#endregion
#region Mirio Execution (Tests)
def exe_permeation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that uses a new harmful effect on Mirio will be marked for Phantom Menace.", invisible=True))
    user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Mirio will ignore all harmful effects.", invisible=True))
    user.check_on_use()

def exe_phantom_menace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Phantom Menace") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 20
                if target.has_effect(EffectType.MARK, "Phantom Menace"):
                    base_damage = 35
                user.deal_pierce_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_protect_ally(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that uses a new harmful effect on this character will be marked for Phantom Menace.",invisible=True))
        target.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "This character will ignore all harmful effects.",invisible=True))
    user.check_on_use()
    user.check_on_help()
    

def exe_mirio_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mirio is invulnerable."))
    user.check_on_use()
#endregion
#region Misaka Execution (Tests)
def exe_railgun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect("BYPASS"):
            user.deal_damage(45, target)
    user.check_on_use()
    user.check_on_harm()

def exe_iron_sand(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id > 2 and target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                harmed = True
            elif target.id < 3 and target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=20))
                helped = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

def exe_electric_rage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "Misaka cannot be killed."))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "If Misaka is damaged by a new ability, she will gain one special energy."))
    user.check_on_use()

def exe_electric_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, 2, lambda eff: "Misaka is invulnerable."))
    user.check_on_use()
#endregion
#region Mugen Execution (Incomplete)
def exe_unpredictable_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_way_of_the_rooster(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_unpredictable_spinning(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_mugen_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_hidden_knife(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Naruha Execution (Tests)
def exe_bunny_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 15 damage.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_rampage_suit(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: f"Naruha is in her paper suit, enabling her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"Naruha has {eff.mag} points of destructible defense.", mag = 70))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Perfect Paper - Rampage Suit has been replaced by Enraged Blow.", mag=21))
    user.check_on_use()

def exe_piercing_umbrella(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                base_damage = 15
                if user.has_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit"):
                    if user.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").mag > 0 and user.can_boost():
                      base_damage = 25
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_rabbit_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit") and user.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").mag > 0:
        user.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").alter_dest_def(25)
    user.check_on_use()

def exe_enraged_blow(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 40
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "Naruha will take double damage."))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Natsu Execution (Tests)
def exe_fire_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()

def exe_fire_dragons_iron_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                if target.has_effect(EffectType.CONT_AFF_DMG, "Fire Dragon's Roar") or target.has_effect(EffectType.CONT_AFF_DMG, "Fire Dragon's Sword Horn"):
                    user.deal_eff_aff_damage(10, target)
        user.check_on_use()
        user.check_on_harm()

def exe_fire_dragons_sword_horn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(40, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "This character will take 5 affliction damage.", mag=5))
        user.check_on_use()
        user.check_on_harm()

def exe_natsu_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Natsu is invulnerable."))
    user.check_on_use()
#endregion
#region Neji Execution (Tests)
def exe_neji_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(2, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 13, lambda eff: f"This character will take {2 * (eff.mag ** 2)} affliction damage.", mag=1))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 13, lambda eff: "Neji is using Eight Trigrams - 128 Palms. This effect will end if Neji is stunned."))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 13, lambda eff: "Eight Trigrams - 128 Palms has been replaced by Chakra Point Strike.", mag=11))
        user.check_on_use()
        user.check_on_harm()

def exe_neji_mountain_crusher(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 25
                if target.check_invuln() and user.can_boost():
                    base_damage = 40
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_selfless_genius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.helpful_target(user, user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "If this ally would die this turn, instead they take no damage and deal 10 more damage on the following turn. If this ability triggers, Neji will die.", invisible=True))
    user.check_on_use()
    user.check_on_help()

def exe_revolving_heaven(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Neji is invulnerable."))
    user.check_on_use()

def exe_chakra_point_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 1, lambda eff: ""))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Nemurin Execution (Tests)
def exe_nemurin_nap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: "Nemurin has entered the dreamworld, allowing the user of her abilities. Every turn her sleep grows one stage deeper, improving her abilities. If Nemurin takes non-absorbed damage, she loses one stage of sleep depth.", mag = 1))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 280000, lambda eff: "Nemurin is dozing, and will heal 10 health.", mag = 10))
    user.receive_eff_healing(10)
    user.check_on_use()


def exe_nemurin_beam(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: "This character will deal 10 less damage.", mag = -10))
        user.check_on_use()
        user.check_on_harm()

def exe_dream_manipulation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 5, lambda eff: "This character will heal 10 health.", mag = 10))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "This character will deal 10 more damage.", mag = 10))
                user.give_healing(10, target)
        user.check_on_use()
        user.check_on_help()

def exe_dream_sovereignty(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Nemurin is invulnerable."))
    user.check_on_use()
#endregion
#region Orihime Execution (Tests)


def rename_i_reject(user: "CharacterManager"):
    def one():
        return user.has_effect(EffectType.MARK, "Tsubaki!")

    def two():
        return user.has_effect(EffectType.MARK, "Ayame! Shun'o!")
    
    def three():
        return user.has_effect(EffectType.MARK, "Lily! Hinagiku! Baigon!")
    
    if one() and two() and three():
        user.source.main_abilities[3].name = "Dance of the Heavenly Six"
        user.source.main_abilities[3].desc = "All allies heal 25 health and become invulnerable for one turn. All enemies take 25 damage."
    elif one() and two():
        user.source.main_abilities[3].name = "Three-God Empowering Shield"
        user.source.main_abilities[3].desc = "Target ally deals 5 more damage with all abilities, and will heal 10 health each time they damage an enemy with a new ability."
    elif two() and three():
        user.source.main_abilities[3].name = "Five-God Inviolate Shield"
        user.source.main_abilities[3].desc = "All allies gain 30 points of destructible defense, and will heal 10 health per turn. This effect ends on all allies once any of the destructible defense is fully depleted."
    elif one() and three():
        user.source.main_abilities[3].name = "Four-God Resisting Shield"
        user.source.main_abilities[3].desc = "Target ally gains 35 points of destructible defense. While active, any enemy that uses a new harmful ability on them will take 15 damage. This damage will not trigger on damage that breaks the destructible defense."
    elif three():
        user.source.main_abilities[3].name = "Three-God Linking Shield"
        user.source.main_abilities[3].desc = "Target ally gains 30 points of destructible defense for one turn."
    elif two():
        user.source.main_abilities[3].name = "Two-God Returning Shield"
        user.source.main_abilities[3].desc = "Target ally heals 20 health for two turns."
    elif one():
        user.source.main_abilities[3].name = "Lone-God Slicing Shield"
        user.source.main_abilities[3].desc = "All allies gain 30 points of destructible defense, and will heal 10 health per turn. This effect ends on all allies once any of the destructible defense is fully depleted."

def exe_tsubaki(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared an offensive effect."))
    user.check_on_use()

def exe_ayame_shuno(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared a healing effect."))
    user.check_on_use()

def exe_lily_hinagiku_baigon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared a defensive effect."))
    user.check_on_use()

def exe_i_reject(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):

    def one():
        return user.has_effect(EffectType.MARK, "Tsubaki!")

    def two():
        return user.has_effect(EffectType.MARK, "Ayame! Shun'o!")
    
    def three():
        return user.has_effect(EffectType.MARK, "Lily! Hinagiku! Baigon!")

    if not user.check_countered(playerTeam, enemyTeam):
        helped = False
        harmed = False
        for ally in playerTeam:
            ally.full_remove_effect("I Reject!", user)
        for enemy in enemyTeam:
            enemy.full_remove_effect("I Reject!", user)
        for target in user.current_targets:
            if one() and two() and three():
                if target.id > 2:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_damage(25, target)
                        harmed = True
                if target.id < 3:
                    if target.helpful_target(user, user.check_bypass_effects()):
                        user.give_healing(25, target)
                        target.add_effect(Effect(Ability("shunshunrikka1"), EffectType.ALL_INVULN, user, 2, lambda eff: "This character is invulnerable."))
                        helped = True
            elif one() and two():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka4"), EffectType.UNIQUE, user, 280000, lambda eff: "If this character deals new damage to an enemy, they will heal 10 health."))
                    target.add_effect(Effect(Ability("shunshunrikka4"), EffectType.ALL_BOOST, user, 280000, lambda eff: "This character will deal 5 more damage.", mag = 5))
                    helped = True
            elif two() and three():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 30))
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.CONT_HEAL, user, 280000, lambda eff: f"This character will heal 10 health.", mag=10))
                    user.give_healing(10, target)
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.UNIQUE, user, 280000, lambda eff: "This effect will end on all characters if this destructible defense is destroyed."))
                    helped = True
            elif one() and three():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka3"), EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 35))
                    target.add_effect(Effect(Ability("shunshunrikka3"), EffectType.UNIQUE, user, 280000, lambda eff: "While the destructible defense holds, this character will deal 15 damage to any enemy that uses a new harmful ability on them."))
                    helped = True
            elif three():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka5"), EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 30))
                    helped = True
            elif two():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka6"), EffectType.CONT_HEAL, user, 3, lambda eff: f"This character will heal 10 health.", mag=20))
                    user.give_healing(20, target)
                    helped = True
            elif one():
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(15, target)
                    harmed = True
                    target.add_effect(Effect(Ability("shunshunrikka7"), EffectType.ALL_DR, user, 280000, lambda eff: f"This character will take 5 more damage from non-affliction abilities.", mag=-5))
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

#endregion
#region Ripple Execution (Tests)
def exe_perfect_accuracy(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Shuriken Throw will always target this enemy, ignore their invulnerability, and deals 5 additional damage to them."))
        user.check_on_use()
        user.check_on_harm()

def exe_shuriken_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Perfect Accuracy") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Perfect Accuracy"):
                def_type = "BYPASS"
            else:
                def_type = user.check_bypass_effects()
            if target.final_can_effect(def_type) and not target.deflecting():
                base_damage = 15
                if target.has_effect(EffectType.MARK, "Perfect Accuracy"):
                    base_damage = 20
                user.deal_pierce_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_countless_stars(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                base_damage = 5
                user.deal_pierce_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_PIERCE_DMG, user, 5, lambda eff: "This character will take 5 piercing damage.", mag=5))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "Shuriken Throw deals 10 more damage.", mag = 210))
        user.check_on_use()
        user.check_on_harm()

def exe_ripple_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ripple is invulnerable."))
    user.check_on_use()
#endregion
#region Rukia Execution (Tests)
def exe_first_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 25
                if target.check_invuln():
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_second_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target == user.primary_target:
                    base_damage = 15
                else:
                    base_damage = 10
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_third_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff:"The next time Rukia is countered, the countering enemy will take 30 damage and be stunned for one turn.", invisible=True))
    user.check_on_use()

def exe_rukia_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff:"Rukia is invulnerable."))
    user.check_on_use()
#endregion
#region Ruler Execution (Tests)
def exe_in_the_name_of_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 6, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "In The Name Of Ruler! will end if Ruler is damaged."))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 5, lambda eff: "Ruler is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_minael_yunael(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        harmed = False
        for target in user.current_targets:
            if target.id > 2:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(15, target)
                    harmed = True
            else:
                if user.has_effect(EffectType.DEST_DEF, "Minion - Minael and Yunael"):
                    user.get_effect(EffectType.DEST_DEF, "Minion - Minael and Yunael").alter_dest_def(15)
                else:
                    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: "This character has {eff.mag} points of destructible defense.", mag=15))
        user.check_on_use()
        if harmed:
            user.check_on_harm()
                

def exe_tama(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for ally in playerTeam:
            ally.full_remove_effect("Minion - Tama", user)
        for target in user.current_targets:
            target.add_effect(Effect(user.used_ability, EffectType.COUNTER, user, 280000, lambda eff: "The first harmful ability used on this character will be countered and take 20 piercing damage.", invisible=True))
        user.check_on_use()

def exe_swim_swim(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ruler is invulnerable."))
    user.check_on_use()
#endregion
#region Ryohei Execution (Tests)
def exe_maximum_cannon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        if not user.has_effect(EffectType.MARK, "Vongola Headgear"):  
            if user.has_effect(EffectType.STACK, "To The Extreme!"):
                user.remove_effect(EffectType.STACK, "To The Extreme!")
            if user.has_effect(EffectType.STACK, "To The Extreme!"):
                user.remove_effect(EffectType.STACK, "To The Extreme!")
        user.check_on_use()
        user.check_on_harm()

def exe_kangaryu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                user.give_healing(15, target)
        if not user.has_effect(EffectType.MARK, "Vongola Headgear"):  
            if user.has_effect(EffectType.STACK, "To The Extreme!"):
                user.remove_effect(EffectType.STACK, "To The Extreme!")
            if user.has_effect(EffectType.STACK, "To The Extreme!"):
                user.remove_effect(EffectType.STACK, "To The Extreme!")
        user.check_on_use()
        user.check_on_harm()

def exe_vongola_headgear(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Ryohei will ignore all random cost increases to Maximum Cannon and Kangaryu, and using them will not consume stacks of To The Extreme!"))
    user.check_on_use()

def exe_to_the_extreme(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "For every 20 unabsorbed damage Ryohei takes, he gains one stack of To The Extreme!"))
    user.check_on_use()
#endregion
#region Saber Execution (Tests)
def exe_excalibur(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            user.deal_pierce_damage(50, target)
    user.check_on_use()
    user.check_on_harm()

def exe_wind_blade_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
            user.deal_damage(10, target)
            target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 10 damage.", mag = 10))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Saber is using Wind Blade Combat."))
        user.check_on_use()
        user.check_on_harm()


def exe_avalon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for player in playerTeam:
            if player.has_effect_with_user(EffectType.CONT_HEAL, "Avalon", user):
                player.full_remove_effect("Avalon", user)
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                user.give_healing(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 280000, lambda eff: "This character will heal 10 health.", mag = 10))
        user.check_on_use()
        user.check_on_help()


def exe_saber_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda efF: "Saber is invulnerable."))
    user.check_on_use()
#endregion
#region Saitama Execution (Tests)
def exe_one_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(75, target)
        user.check_on_use()
        user.check_on_harm()

def exe_consecutive_normal_punches(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 15 damage.", mag = 15))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Saitama is using Consecutive Normal Punches."))
        user.check_on_use()
        user.check_on_harm()

def exe_serious_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 35 damage.", mag = 35))
        user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Saitama is ignoring all hostile effects."))
        user.check_on_use()
        user.check_on_harm()

def exe_sideways_jumps(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Saitama is invulnerable."))
    user.check_on_use()
#endregion
#region Seiryu Execution (Tests)
def exe_body_mod_arm_gun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_raging_koro(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(20, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff:"This character will take 20 damage.", mag = 20))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Raging Koro has been replaced by Insatiable Justice.", mag = 22))
        user.check_on_use()
        user.check_on_harm()

def exe_berserker_howl(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 4, lambda eff:"This character will deal 10 less damage.", mag = -10))
        user.check_on_use()
        user.check_on_harm()

def exe_koro_defense(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Seiryu is invulnerable."))
    user.check_on_use()

def exe_self_destruct(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            user.deal_pierce_damage(30, target)
            
    user.check_on_use()
    user.check_on_harm()
    user.source.hp = 0
    user.source.dead = True
    user.source.current_effects.clear()
    

def exe_insatiable_justice(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and target.source.hp < 30:
                target.source.hp = 0
                target.source.dead = True
                user.source.current_effects.clear()
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Shigaraki Execution (Tests)
def exe_decaying_touch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target.has_effect(EffectType.CONT_UNIQUE, "Decaying Touch"):
                    target.get_effect(EffectType.CONT_UNIQUE, "Decaying Touch").alter_mag(1)
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {5 * (2 ** eff.mag)} affliction damage.", mag = 0))
                    user.deal_aff_damage(5, target)
        user.check_on_use()
        user.check_on_harm()


def exe_decaying_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target.has_effect(EffectType.CONT_UNIQUE, "Decaying Touch"):
                    target.get_effect(EffectType.CONT_UNIQUE, "Decaying Touch").alter_mag(1)
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {5 * (2 ** eff.mag)} affliction damage.", mag = 0))
                    user.deal_aff_damage(5, target)
        user.check_on_use()
        user.check_on_harm()

def exe_destroy_what_you_love(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.helpful_target(user, user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 4, lambda eff: "This character will deal 10 more damage.", mag = 10))
            target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character will take 5 more non-affliction damage.", mag = -5))
            target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 4, lambda eff: "This character cannot reduce damage or become invulnerable."))
    user.check_on_use()
    user.check_on_help()

def exe_kurogiri_escape(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Shigaraki is invulnerable."))
    user.check_on_use()
#endregion
#region Shikamaru Execution (Tests)
def exe_shadow_bind_jutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Shadow Pin") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)

    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Shadow Pin"):
                def_type = "BYPASS"
            else:
                def_type = user.check_bypass_effects()
            if target.final_can_effect(def_type):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_neck_bind(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Shadow Pin") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)

    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Shadow Pin"):
                def_type = "BYPASS"
            else:
                def_type = user.check_bypass_effects()
            if target.final_can_effect(def_type) and not target.deflecting():
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag = 15))
                user.deal_damage(15, target)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, "This character cannot target enemies."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Shadow Neck Bind and Shadow Bind Jutsu will affect this character in addition to their normal targets."))
        user.check_on_use()
        user.check_on_harm()

def exe_hide(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Shikamaru is invulnerable."))
    user.check_on_use()
#endregion
#region Shokuhou Execution (Tests)

def mental_out_ability_switch(target: "CharacterManager") -> int:
    if target.source.name == "naruto":
        return 1
    if target.source.name == "aizen":
        return 0
    if target.source.name == "akame":
        return 1
    if target.source.name == "astolfo":
        return 1
    if target.source.name == "cmary":
        return 2
    if target.source.name == "chrome":
        return 1
    if target.source.name == "chu":
        return 2
    if target.source.name == "cranberry":
        return 1
    if target.source.name == "erza":
        return 7
    if target.source.name == "esdeath":
        return 2
    if target.source.name == "frenda":
        return 2
    if target.source.name == "gajeel":
        return 0
    if target.source.name == "gokudera":
        return 0
    if target.source.name == "hibari":
        return 1
    if target.source.name == "gray":
        return 1
    if target.source.name == "gunha":
        return 1
    if target.source.name == "hinata":
        return 1
    if target.source.name == "ichigo":
        return 0
    if target.source.name == "ichimaru":
        return 1
    if target.source.name == "jack":
        return 0
    if target.source.name == "itachi":
        return 0
    if target.source.name == "jiro":
        return 0
    if target.source.name == "kakashi":
        return 2
    if target.source.name == "kuroko":
        return 0
    if target.source.name == "lambo":
        return 1
    if target.source.name == "pucelle":
        return 0
    if target.source.name == "laxus":
        return 0
    if target.source.name == "leone":
        return 2
    if target.source.name == "levy":
        return 0
    if target.source.name == "raba":
        return 1
    if target.source.name == "lucy":
        return 0
    if target.source.name == "midoriya":
        return 0
    if target.source.name == "minato":
        return 0
    if target.source.name == "mine":
        return 0
    if target.source.name == "mirai":
        return 1
    if target.source.name == "mirio":
        return 2
    if target.source.name == "misaka":
        return 1
    if target.source.name == "naruha":
        return 2
    if target.source.name == "natsu":
        return 0
    if target.source.name == "neji":
        return 1
    if target.source.name == "nemurin":
        return 1
    if target.source.name == "orihime":
        return 3
    if target.source.name == "ripple":
        return 1
    if target.source.name == "rukia":
        return 0
    if target.source.name == "ruler":
        return 2
    if target.source.name == "ryohei":
        return 0
    if target.source.name == "saber":
        return 0
    if target.source.name == "saitama":
        return 0
    if target.source.name == "seiryu":
        return 2
    if target.source.name == "shigaraki":
        return 2
    if target.source.name == "shikamaru":
        return 1
    if target.source.name == "snowwhite":
        return 0
    if target.source.name == "swimswim":
        return 0
    if target.source.name == "tatsumaki":
        return 0
    if target.source.name == "todoroki":
        return 0
    if target.source.name == "tatsumi":
        return 0
    if target.source.name == "toga":
        return 1
    if target.source.name == "tsunayoshi":
        return 0
    if target.source.name == "uraraka":
        return 2
    if target.source.name == "wendy":
        return 0
    if target.source.name == "yamamoto":
        return 0

def exe_mental_out(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_duration = 4
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, base_duration, lambda eff: "Shokuhou is controlling this character."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, base_duration, lambda eff: "This character is stunned."))
                user.add_effect(Effect(user.used_ability, EffectType.MARK, user, base_duration - 1, lambda eff: "Shokuhou is controlling a character, and can command them to act for her."))
                stolen_slot = mental_out_ability_switch(target)
                user.get_effect_with_user(EffectType.MARK, "Mental Out", user).alter_mag(stolen_slot)
                if stolen_slot > 3:
                    stolen_ability = target.source.alt_abilities[stolen_slot - 4]
                else:
                    stolen_ability = target.source.main_abilities[stolen_slot]
                user.source.alt_abilities[0].name = stolen_ability.name
                user.source.alt_abilities[0].desc = stolen_ability.desc
                user.source.alt_abilities[0].cost = stolen_ability.cost
                user.source.alt_abilities[0]._base_cooldown = stolen_ability._base_cooldown
                user.source.alt_abilities[0].target_type = stolen_ability.target_type
                user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, base_duration - 1, lambda eff: f"Mental Out has been replaced by {stolen_ability.name}.", mag = 11))
                user.check_on_stun(target)


def exe_exterior(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.receive_eff_aff_damage(25, user)
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 9, lambda eff: "Mental Out lasts 1 more turn."))
    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 9, lambda eff: "Mental Out costs 1 less mental energy.", mag = -131))
    user.check_on_use()

def exe_ally_mobilization(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 4, lambda eff: "This character will ignore stuns."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 15 points of damage reduction.", mag=15))
        user.check_on_help()
        user.check_on_use()

def exe_loyal_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Shokuhou is invulnerable."))
    user.check_on_use()

def exe_mental_out_order(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    stolen_slot = user.get_effect_with_user(EffectType.MARK, "Mental Out", user).mag
    controlled_character = get_controlled_character(user, enemyTeam)
    if stolen_slot < 4:
        stolen_ability = controlled_character.source.main_abilities[stolen_slot]
    else:
        stolen_ability = controlled_character.source.alt_abilities[stolen_slot - 4]
    
    stolen_ability.execute(controlled_character, playerTeam, enemyTeam)

#endregion
#region Snow White Execution (Tests)
def exe_enhanced_strength(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
        user.check_on_use()
        user.check_on_harm()

def exe_hear_distress(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    for target in user.current_targets:
        if target.id < 3:
            if target.helpful_target("BYPASS"):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: "This character has 25 points of damage reduction.", mag=25, invisible=True))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "This character will gain one random energy if they are affected by a new harmful ability.", invisible=True))
                helped = True
        elif target.id > 2:
            if target.final_can_effect("BYPASS"):
                target.add_effect(Effect(user.used_ability, EffectType.COUNTER, user, 2, lambda eff: "The first harmful ability used by this character will be countered, and they will lose one random energy.", invisible=True))
    user.check_on_use()
    if helped:
        user.check_on_help()

def exe_rabbits_foot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "If this character dies, they will instead be set to 35 health.", invisible=True))
    user.check_on_use()
    user.check_on_help()

def exe_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Snow White is invulnerable."))
    user.check_on_use()
#endregion
#region SwimSwim Execution (Tests)
def exe_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(25, target)
        user.check_on_use()
        user.check_on_harm()

def exe_dive(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Swim Swim will ignore all hostile effects."))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: "Swim Swim will ignore invulnerability."))
    user.check_on_use()

def exe_vitality_pills(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 6, lambda eff: "Swim Swim has 10 points of damage reduction.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "Swim Swim will deal 10 more damage.", mag=10))
    user.check_on_use()

def exe_water_body(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Swim Swim is invulnerable."))
    user.check_on_use()
#endregion
#region Tatsumaki Execution (Tests)
def exe_rubble_barrage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.STACK, "Gather Power"):
            stacks = user.get_effect(EffectType.STACK, "Gather Power").mag
        else:
            stacks = 0
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if user.can_boost():
                    base_damage = 10 + (5 * stacks)
                else:
                    base_damage = 10
                user.deal_damage(base_damage, target)
                user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: f"This character will take {eff.mag} damage.", mag=base_damage))
        user.check_on_use()
        user.check_on_harm()

def exe_arrest_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.STACK, "Gather Power"):
        stacks = user.get_effect(EffectType.STACK, "Gather Power").mag
    else:
        stacks = 0
    for target in user.current_targets:
        if target.helpful_target(user, user.check_bypass_effects()):
            base_dr = 10 + (5 * stacks)
            target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: f"This character has {base_dr} points of damage reduction", mag = base_dr, invisible=True))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Arrest Assault has been replaced by Return Assault.", mag = 21, invisible=True))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: f"Arrest Assault has received {eff.mag} abilities.", mag = 0))
    user.check_on_use()
    user.check_on_help()

def exe_gather_power(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Rubble Barrage will deal {eff.mag * 5} more damage, Arrest Assault grants {eff.mag * 5} more damage reduction, and Gather Power has {eff.mag} less cooldown.", mag = 1))
    user.source.energy_contribution += 1
    user.used_ability._base_cooldown -= 1
    if user.used_ability._base_cooldown < 0:
        user.used_ability._base_cooldown = 0
    user.check_on_use()

def exe_psionic_barrier(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: f"Tatsumaki is invulnerable."))
    user.check_on_use()

def exe_return_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        stacks = user.get_effect(EffectType.UNIQUE, "Arrest Assault").mag
        for target in user.current_targets:
            base_damage = 0
            if user.can_boost():
                base_damage += (stacks * 20)
            user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Todoroki Execution (Tests)
def exe_half_cold(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: "This character will deal 10 less damage.", mag=-10))
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Todoroki's ability costs are increased by {eff.mag} random energy until he uses Flashfreeze Heatwave.", mag = 1))
        user.check_on_use()
        user.check_on_harm()

def exe_half_hot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(30, target)
        for ally in playerTeam:
            if user.has_effect(EffectType.STACK, "Quirk - Half-Hot"):
                base_ally_damage = 10 + (user.get_effect(EffectType.STACK, "Quirk - Half-Hot").mag * 10)
            else:
                base_ally_damage = 10
            if ally != user and ally.final_can_effect(user.check_bypass_effects()) and not ally.deflecting():
                user.deal_damage(base_ally_damage, ally)
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Quirk - Half-Hot will deal {eff.mag * 10} more damage to Todoroki's allies until he uses Flashfreeze Heatwave.", mag = 1))
        user.check_on_use()
        user.check_on_harm()

def exe_flashfreeze_heatwave(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    hot_stacks = 0
    cold_stacks = 0
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.STACK, "Quirk - Half-Hot"):
            hot_stacks = user.get_effect(EffectType.STACK, "Quirk - Half-Hot").mag
        if user.has_effect(EffectType.STACK, "Quirk - Half-Cold"):
            cold_stacks = user.get_effect(EffectType.STACK, "Quirk - Half-Cold").mag
        primary_damage = 10
        splash_damage = 5
        if user.can_boost():
            primary_damage += (10 * hot_stacks) + (10 * cold_stacks)
            splash_damage += (10 * hot_stacks)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target == user.primary_target:
                    user.deal_damage(primary_damage, target)
                else:
                    user.deal_damage(splash_damage, target)
        user.full_remove_effect("Quirk - Half Hot", user)
        user.full_remove_effect("Quirk - Half-Cold", user)
        user.check_on_use()
        user.check_on_harm()

def exe_ice_rampart(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Todoroki is invulnerable."))
    user.check_on_use()
#endregion
#region Tatsumi Execution (Tests)
def exe_killing_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 25
                if target.source.hp < 50:
                    base_damage += 10
                if target.is_stunned():
                    base_damage += 10
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_stun()

def exe_incursio(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 7, lambda eff: f"Tatsumi has {eff.mag} points of destructible defense.", mag=25))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Tatsumi can use Neuntote."))
    user.check_on_use()

def exe_neuntote(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                multiplier = 1
                for eff in target.source.current_effects:
                    if eff.eff_type == EffectType.UNIQUE and eff.name == "Neuntote":
                        multiplier = multiplier * 2
                base_damage = 15 * multiplier
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "This character will take double damage from Neuntote."))
        user.check_on_use()
        user.check_on_stun()

def exe_invisibility(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Tatsumi is invulnerable."))
    user.check_on_use()
#endregion
#region Toga Execution (Tests)
def exe_thirsting_knife(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(10, target)
                target.apply_stack_effect(Effect(Ability("toga3"), EffectType.STACK, user, 280000, lambda eff: f"Toga has drawn blood from this character {eff.mag} time(s).", mag = 1), user)
        user.check_on_use()
        user.check_on_harm()

def exe_vacuum_syringe(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_aff_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag=10))
                target.apply_stack_effect(Effect(Ability("toga3"), EffectType.STACK, user, 280000, lambda eff: f"Toga has drawn blood from this character {eff.mag} time(s).", mag = 1), user)
        user.check_on_use()
        user.check_on_harm()

def exe_transform(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        blood_stacks = target.get_effect(EffectType.STACK, "Quirk - Transform").mag
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, (1 + (2 * blood_stacks)), lambda eff: "Toga has transformed."))
        swap_hp = user.source.hp
        swap_effects = user.source.current_effects
        user.source = user.scene.return_character(target.source.name)
        user.source.hp = swap_hp
        user.source.current_effects = swap_effects
    user.check_on_use()

def exe_toga_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Toga is invulnerable."))
    user.check_on_use()
#endregion
#region Tsunayoshi Execution (Tests)
def exe_xburner(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target == user.primary_target:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_damage(25, target)
            else:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_damage(15, target)
        user.check_on_use()
        user.check_on_harm()

def exe_zero_point_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.COUNTER, user, 2, lambda eff: "The first harmful ability used on Tsuna will be countered and the countered enemy will be stunned. X-Burner will deal 10 more damage for two turns after this effect is triggered.", invisible=True))
    user.check_on_use()

def exe_burning_axle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(35, target)
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 1, lambda eff: ""))
        user.check_on_use()
        user.check_on_harm()

def exe_flare_burst(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Tsuna is invulnerable."))
    user.check_on_use()
#endregion
#region Uraraka Execution (Tests)
def exe_zero_gravity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id < 3:
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "This character will ignore invulnerability."))
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 6, lambda eff: "This character has 10 points of damage reduction."))
                    helped = True
            if target.id > 2: 
                if target.final_can_effect(user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 5, lambda eff: "This character will take 10 more non-affliction damage.", mag = -10))
                    target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 5, lambda eff: "This character cannot reduce damage or become invulnerable."))
                    harmed = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

def exe_meteor_storm(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                if target.has_effect(EffectType.DEF_NEGATE, "Quirk - Zero Gravity"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    user.check_on_stun(target)
                for ally in playerTeam:
                    if ally.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity") and ally.helpful_target(user, user.check_bypass_effects()):
                        ally.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 3, lambda eff: "This character will deal 5 more non-affliction damage.", mag=5))
        user.check_on_use()
        user.check_on_harm()

def exe_comet_home_run(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
                if target.has_effect(EffectType.DEF_NEGATE, "Quirk - Zero Gravity"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
                for ally in playerTeam:
                    if ally.has_effect(EffectType.UNIQUE, "Quirk - Zero Gravity") and ally.helpful_target(user, user.check_bypass_effects()):
                        ally.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 3, lambda eff: "This character is invulnerable."))
        user.check_on_use()
        user.check_on_harm()

def exe_float(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 3, lambda eff: "Uraraka is invulnerable."))
    user.check_on_use()
#endregion
#region Wendy Execution (Tests)
def exe_troia(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_healing = 40
        multiplier = 0
        for eff in user.source.current_effects:
            if eff.name == "Troia":
                multiplier += 1
        base_healing = base_healing // (2 ** multiplier)
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                user.give_healing(base_healing, target)
        user.check_on_use()
        user.check_on_help()

def exe_shredding_wedding(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "This character will take 20 piercing damage if they target a character that isn't under the effect of Shredding Wedding. Any character that isn't under the effect of Shredding Wedding that targets this character will take 20 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "This character will take 20 piercing damage if they target a character that isn't under the effect of Shredding Wedding. Any character that isn't under the effect of Shredding Wedding that targets this character will take 20 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Shredding Wedding has been replaced by Piercing Winds.", mag=21))
        user.check_on_use()
        user.check_on_harm()


def exe_sky_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
   if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.give_healing(15, user)
        user.check_on_use()
        user.check_on_harm()

def exe_wendy_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Wendy is invulnerable."))
    user.check_on_use()

def exe_piercing_winds(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(25, target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Yamamoto Execution (Tests)
def exe_shinotsuku_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(30, target)
                if target.has_effect(EffectType.ALL_BOOST, "Shinotsuku Ame"):
                    target.get_effect(EffectType.ALL_BOOST, "Shinotsuku Ame").duration = 6
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 6, lambda eff: "This character will deal 10 less damage.", mag=-10))
        user.apply_stack_effect(Effect(Ability("yamamoto3"), EffectType.STACK, user, 280000, lambda eff: f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.", mag = 1))
        user.check_on_use()
        user.check_on_harm()

def exe_utsuhi_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "This character will take 20 damage and Yamamoto will gain one stack of Asari Ugetsu.", mag = 1, invisible = True))
        user.check_on_use()
        user.check_on_harm()

def exe_asari_ugetsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    rain_flames = 0
    if user.has_effect(EffectType.STACK, "Asari Ugetsu"):
        rain_flames = user.get_effect(EffectType.STACK, "Asari Ugetsu").mag
    duration = (1 + (2 * rain_flames))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, duration, lambda eff: "Yamamoto has 20 points of damage reduction.", mag = 20))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, duration, lambda eff: "Shinotsuku Ame has been replaced by Scontro di Rondine.", mag = 11))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, duration, lambda eff: "Utsuhi Ame has been replaced by Beccata di Rondine.", mag=22))
    user.check_on_use()

def exe_sakamaku_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Yamamoto is invulnerable."))
    user.check_on_use()

def exe_scontro_di_rondine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 20
                if target.check_damage_drain() >= 10 and user.can_boost():
                    base_damage = 30
                user.deal_damage(base_damage, target)
        user.check_on_use()
        user.check_on_harm()

def exe_beccata_di_rondine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(5, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 5 damage.", mag=5))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "This character will deal 5 less damage.", mag=-5))
        if user.has_effect(EffectType.CONT_USE, "Beccata di Rondine"):
            user.get_effect(EffectType.CONT_USE, "Beccata di Rondine").duration = 5
        else:
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Yamamoto is using Beccata di Rondine. This effect will end if he is stunned."))
        user.check_on_use()
        user.check_on_harm()
#endregion

ability_info_db = {
    "naruto1": [
        "Shadow Clones",
        "Naruto summons an army of substantial clones. For 3 turns, he gains 10 points of damage reduction, Rasengan is improved, Naruto Taijutsu is replaced with Uzumaki Barrage, and this ability is replaced with Sage Mode.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_shadow_clones
    ],
    "naruto2": [
        "Rasengan",
        "Naruto slams one opponent with a spinning ball of condensed chakra. This deals 25 damage to one"
        +
        " enemy and stuns them for one turn. During Shadow Clones, this attack deals 10 less damage but affects all enemies."
        +
        " During Sage Mode, this ability deals double damage and stuns for two turns.",
        [0, 1, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_rasengan
    ],
    "naruto3": [
        "Naruto Taijutsu",
        "Naruto strikes one enemy with his fist, dealing 30 physical damage.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_naruto_taijutsu
    ],
    "naruto4": [
        "Substitution", "Naruto becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_substitution
    ],
    "narutoalt1": [
        "Sage Mode",
        "Naruto gains 1 special energy and becomes invulnerable for 2 turns. During"
        +
        " this time, Rasengan is improved and Uzumaki Barrage is replaced with Toad Taijutsu.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_sage_mode
    ],
    "narutoalt2": [
        "Uzumaki Barrage",
        "Naruto deals 15 damage to one enemy. If he uses this ability again next turn, it will stun its target for one turn.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_uzumaki_barrage
    ],
    "narutoalt3": [
        "Toad Taijutsu",
        "Naruto deals 35 damage to one enemy. For 2 turns, that enemy will have their ability"
        + " costs increased by 2 random.", [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_toad_taijutsu
    ],
    "aizen1": [
        "Shatter, Kyoka Suigetsu",
        "Target enemy has their ability costs increased by one random and are marked by Kyoka Suigetsu for 1 turn. If the enemy is marked with Black Coffin, "
        +
        "all their currently active cooldowns are increased by 2. If the enemy is marked by Overwhelming Power, Aizen's abilities will cost one less random energy on the following turn.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_shatter
    ],
    "aizen2": [
        "Overwhelming Power",
        "Aizen deals 25 damage to target enemy and marks them with Overwhelming Power for one turn. If the enemy is marked with Black Coffin,"
        +
        " that enemy will be unable to reduce damage or become invulnerable for 2 turns. If that enemy is marked with Shatter, Kyoka Suigetsu, Overwhelming Power deals 20 bonus damage to them.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_overwhelming_power
    ],
    "aizen3": [
        "Black Coffin",
        "Target enemy is stunned and marked with Black Coffin for 1 turn. If the enemy is marked with Overwhelming Power, they will also take 20 damage. If the"
        +
        " enemy is marked with Shatter, Kyoka Suigetsu, then Black Coffin also affects their allies.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_black_coffin
    ],
    "aizen4": [
        "Effortless Guard", "Aizen becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_effortless_guard
    ],
    "akame1": [
        "Red-Eyed Killer",
        "Akame marks an enemy for 1 turn. During this time, she can use One-Cut Killing on the target.",
        [0, 0, 1, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_red_eyed_killer
    ],
    "akame2": [
        "One Cut Killing",
        "Akame instantly kills a target marked with Red-Eyed Killer.",
        [0, 0, 0, 2, 1, 1], Target.SINGLE, target_one_cut_killing, exe_one_cut_killing
    ],
    "akame3": [
        "Little War Horn",
        "For two turns, Akame can use One Cut Killing on any target, regardless of their effects.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF"), exe_little_war_horn
    ],
    "akame4": [
        "Rapid Deflection", "Akame becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rapid_deflection
    ],
    "astolfo1": [
        "Casseur de Logistille",
        "Astolfo targets himself or another ally for one turn. During this time, if they are targeted by a hostile Special or Mental ability, that ability"
        +
        " will be countered and the user will be stunned and isolated for 1 turn. This ability is invisible until triggered.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HELPFUL"), exe_casseur
    ],
    "astolfo2": [
        "Trap of Argalia - Down With A Touch!",
        "Astolfo deals 20 piercing damage to target enemy. For one turn, they cannot have their damage boosted above its default value. If the target's damage is currently boosted, Trap of Argalia will permanently "
        + "deal 5 additional damage.", [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_trap
    ],
    "astolfo3": [
        "La Black Luna",
        "Astolfo removes one hostile effect from every member of his team, and for 2 turns, no enemy can have their damage boosted above its default value. For every hostile effect removed, Trap of Argalia will permanently"
        + " deal 5 additional damage.", [0, 1, 0, 0, 1, 2], Target.ALL_TARGET,
        default_target("ALL"), exe_luna
    ],
    "astolfo4": [
        "Akhilleus Kosmos", "Astolfo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kosmos
    ],
    "cmary1": [
        "Quickdraw - Pistol",
        "Calamity Mary deals 15 damage to target enemy. This ability will become Quickdraw - Rifle after being used.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_pistol
    ],
    "cmary2": [
        "Hidden Mine",
        "Traps one enemy for two turns. During this time, if that enemy used a new ability, they will take 20 piercing damage and this effect will end.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_mine
    ],
    "cmary3": [
        "Grenade Toss",
        "Calamity Mary deals 20 damage to all enemy targets. This ability deals 20 more damage to enemies affected by Hidden Mine.",
        [0, 0, 0, 1, 1, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_grenade_toss
    ],
    "cmary4": [
        "Rifle Guard", "Calamity Mary becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rifle_guard
    ],
    "cmaryalt1": [
        "Quickdraw - Rifle",
        "Calamity Mary deals 15 damage to target enemy for 2 turns. This ability will become Quickdraw - Sniper after it ends.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE", lockout=(EffectType.CONT_USE, "Quickdraw - Rifle")), exe_rifle
    ],
    "cmaryalt2": [
        "Quickdraw - Sniper",
        "Calamity Mary deals 55 piercing damage to one enemy and becomes invulnerable for one turn.",
        [0, 0, 0, 2, 1, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_sniper
    ],
    "chachamaru1": [
        "Target Lock",
        "Chachamaru marks a single target for Orbital Satellite Cannon.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", protection=(EffectType.MARK, "Target Lock")), exe_target_lock
    ],
    "chachamaru2": [
        "Orbital Satellite Cannon",
        "Deals 35 piercing damage that ignores invulnerability to all targets marked by Target Lock.",
        [0, 0, 0, 0, 3, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE",
                       def_type="BYPASS",
                       mark_req="Target Lock",
                       lockout=(EffectType.MARK, "Active Combat Mode")), exe_satellite_cannon
    ],
    "chachamaru3": [
        "Active Combat Mode",
        "Chachamaru gains 15 points of destructible defense each turn and deals 10 damage to one enemy for 3 turns. During this time, she cannot use"
        + " Orbital Satellite Cannon.", [0, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_active_combat_mode
    ],
    "chachamaru4": [
        "Take Flight", "Chachamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_take_flight
    ],
    "chrome1": [
        "You Are Needed",
        "Chrome accepts Mukuro's offer to bond their souls, enabling the user of her abilities. If Chrome ends a turn below 40 health, she transforms into Rokudou Mukuro.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", protection=(EffectType.MARK, "You Are Needed")), exe_you_are_needed
    ],
    "chrome2": [
        "Illusory Breakdown",
        "Illusory Breakdown: Chrome targets one enemy and gains 20 points of destructible defense for one turn. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 25 damage to the targeted enemy and stun them for one turn.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed"), exe_illusory_breakdown
    ],
    "chrome3": [
        "Mental Immolation",
        "Mental Immolation: Chrome targets one enemy and gains 15 points of destructible defense. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 20 damage to the targeted enemy and remove one random energy from them.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed"), exe_mental_immolation
    ],
    "chrome4": [
        "Mental Substitution",
        "Mental Substitution: Chrome becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_mental_substitution
    ],
    "chromealt1": [
        "Trident Combat",
        "Trident Combat: Mukuro deals 25 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_trident_combat
    ],
    "chromealt2": [
        "Illusory World Destruction",
        "Illusory World Destruction: Mukuro gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        + "he will deal 25 damage to all enemies and stun them for one turn.",
        [0, 0, 1, 0, 2, 2], Target.SINGLE,
        default_target("SELF"), exe_illusory_world_destruction
    ],
    "chromealt3": [
        "Mental Annihilation",
        "Mental Annihilation: Mukuro targets one enemy and gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        +
        "he will deal 35 piercing damage to the targeted enemy. This damage ignores invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_mental_annihilation
    ],
    "chromealt4": [
        "Trident Deflection", "Mukuro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_trident_deflection
    ],
    "chu1": [
        "Relentless Assault",
        "Chu deals 15 damage to one enemy for three turns. If that enemy has less"
        +
        " than 15 points of damage reduction, this damage is considered piercing.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_relentless_assault
    ],
    "chu2": [
        "Flashing Deflection",
        "Chu gains 15 points of damage reduction for 3 turns. If he would be affected by a move that"
        +
        " deals less than 15 points of damage, he will fully ignore that move instead.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_flashing_deflection
    ],
    "chu3": [
        "Gae Bolg",
        "Chu removes all destructible defense from target enemy, then deals 40 piercing damage"
        + " to them. This ability ignores invulnerability.",
        [2, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_gae_bolg
    ],
    "chu4": [
        "Chu Block", "Chu becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_chu_block
    ],
    "cranberry1": [
        "Illusory Disorientation",
        "For 3 turns, one enemy has their ability costs increased by 1 random and this ability is replaced by Merciless Finish. This effect is removed on ability use.",
        [0, 1, 0, 0, 1, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_illusory_disorientation
    ],
    "cranberry2": [
        "Fortissimo",
        "Cranberry deals 25 damage to all enemies, ignoring invulnerability. This ability cannot be ignored and invulnerable or ignoring enemies take double damage from it.",
        [0, 2, 0, 0, 0, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS"), exe_fortissimo
    ],
    "cranberry3": [
        "Mental Radar",
        "For 2 turns, Cranberry's team will ignore counter effects.",
        [0, 0, 1, 0, 1, 4], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_mental_radar
    ],
    "cranberry4": [
        "Cranberry Block", "Cranberry becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_cranberry_block
    ],
    "cranberryalt1": [
        "Merciless Finish",
        "Cranberry stuns target enemy for 2 turns, and deals 15 affliction damage to them each turn. Only usable on a target currently affected by Illusory Disorientation.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE", mark_req="Illusory Disorientation"), exe_merciless_finish
    ],
    "erza1": [
        "Clear Heart Clothing",
        "Until Erza requips another armor set, she cannot be stunned and Clear Heart Clothing is replaced by Titania's Rampage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_clear_heart_clothing
    ],
    "erza2": [
        "Heaven's Wheel Armor",
        "Until Erza requips another armor set, she will ignore all affliction damage and Heaven's Wheel Armor is replaced by Circle Blade.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_heavens_wheel_armor
    ],
    "erza3": [
        "Nakagami's Armor",
        "Until Erza requips another armor set, she gains 1 additional random energy per turn and Nakagami's Armor is replaced by Nakagami's Starlight.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_nakagamis_armor
    ],
    "erza4": [
        "Adamantine Armor",
        "Until Erza requips another armor set, she gains 15 damage reduction and Adamantine Armor is replaced by Adamantine Barrier.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_adamantine_armor
    ],
    "erzaalt1": [
        "Titania's Rampage",
        "Until Erza is killed or requips another armor set, she deals 15 piercing damage to a random enemy. Each turn that this ability"
        +
        " remains active, it deals 5 more damage. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        target_titanias_rampage, exe_titanias_rampage
    ],
    "erzaalt2": [
        "Circle Blade",
        "Erza deals 20 damage to one enemy. On the following turn, all enemies take 15 damage, ignoring invulnerability.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_circle_blade
    ],
    "erzaalt3": [
        "Nakagami's Starlight",
        "Erza deals 35 damage to one enemy and removes 1 random energy from them.",
        [0, 1, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_nakagamis_starlight
    ],
    "erzaalt4": [
        "Adamantine Barrier",
        "Both of Erza's allies become invulnerable for one turn.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_adamantine_barrier
    ],
    "esdeath1": [
        "Demon's Extract",
        "Esdeath calls forth the power of her Teigu, enabling the user of her abilities for 5 turns. During this time, this ability changes to Mahapadma, "
        + "and Esdeath cannot be countered.", [0, 1, 0, 0, 0,
                                               4], Target.SINGLE,
        default_target("SELF"), exe_demons_extract
    ],
    "esdeath2": [
        "Frozen Castle",
        "For the next two turns, no enemy can target any of Esdeath's allies. Esdeath's allies cannot target enemies affected by Frozen Castle. During this time, "
        + "Weiss Schnabel will affect all enemies.", [0, 2, 0, 0, 0,
                                                      7], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_frozen_castle
    ],
    "esdeath3": [
        "Weiss Schnabel",
        "Deals 10 damage to target enemy for 3 turns. While active, Weiss Schnabel costs one fewer special energy and deals 15 piercing damage to target enemy.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", prep_req="Demon's Extract"), exe_weiss_schnabel
    ],
    "esdeath4": [
        "Esdeath Guard",
        "Esdeath Guard: Esdeath becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_esdeath_guard
    ],
    "esdeathalt1": [
        "Mahapadma",
        "Mahapadma: Esdeath stuns every living character except for her for 2 turns. At the end of those turns, Esdeath is stunned for 2 turns.",
        [0, 2, 0, 0, 1, 8], Target.ALL_TARGET,
        default_target("ALL"), exe_mahapadma
    ],
    "frenda1": [
        "Close Combat Bombs",
        "Frenda hurls a handful of bombs at an enemy, marking them with a stack of Close Combat Bombs for 3 turns. If Detonate is used, "
        +
        "the marked enemy will take 15 damage per stack of Close Combat Bombs.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_close_combat_bombs
    ],
    "frenda2": [
        "Doll Trap",
        "Frenda traps an ally or herself, permanently marking them with a Doll Trap. During this time, if any enemy damages the marked ally, all stacks of Doll Trap on that ally are transferred to"
        +
        " the damaging enemy. If Detonate is used, characters marked with Doll Trap receive 20 damage per stack of Doll Trap on them. Doll Trap is invisible until transferred.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_doll_trap
    ],
    "frenda3": [
        "Detonate",
        "Frenda consumes all her stacks of Close Combat Bombs and Doll Trap from all characters. This ability ignores invulnerability.",
        [0, 0, 0, 0, 2, 0], Target.ALL_TARGET, target_detonate, exe_detonate
    ],
    "frenda4": [
        "Frenda Dodge", "Frenda becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_frenda_dodge
    ],
    "gajeel1": [
        "Iron Dragon's Roar", "Gajeel deals 35 piercing damage to one enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_iron_dragon_roar
    ],
    "gajeel2": [
        "Iron Dragon's Club", "Gajeel deals 20 piercing damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_iron_dragon_club
    ],
    "gajeel3": [
        "Iron Shadow Dragon",
        "If Gajeel is targeted with a new harmful ability, he will ignore all further hostile effects that turn. This changes Gajeel's abilities to their special versions.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_iron_shadow_dragon
    ],
    "gajeel4": [
        "Gajeel Block", "Gajeel becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gajeel_block
    ],
    "gajeelalt1": [
        "Iron Shadow Dragon's Roar",
        "Gajeel deals 15 damage to all enemies, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS"), exe_iron_shadow_dragon_roar
    ],
    "gajeelalt2": [
        "Iron Shadow Dragon's Club",
        "Gajeel deals 20 damage to one enemy, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_iron_shadow_dragon_club
    ],
    "gajeelalt3": [
        "Blacksteel Gajeel",
        "Gajeel permanently gains 15 damage reduction. This changes Gajeel's abilities back to their physical versions.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_blacksteel_gajeel
    ],
    "gokudera1": [
        "Sistema C.A.I.",
        "Gokudera causes an effect based on the CAI stage, and moves the stage forward one. All effects are cumulative except for Stage 4."
        +
        " Stage 1: Deals 10 damage to all enemies.\nStage 2: Stuns target enemy for one turn.\nStage 3: Deals 10 damage to one enemy and heals Gokudera for 15 health.\nStage 4: Deals 25 damage to all enemies and stuns them for 1 turn. This heals Gokudera's entire team for 20 health. Resets the C.A.I. stage to 1.",
        [0, 0, 0, 1, 1, 0], Target.ALL_TARGET, target_sistema_CAI, exe_sistema_cai
    ],
    "gokudera2": [
        "Vongola Skull Rings", "Moves the C.A.I. stage forward by one.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("SELF"), exe_vongola_ring
    ],
    "gokudera3": [
        "Vongola Box Weapon - Vongola Bow",
        "Gokudera gains 30 points of destructible defense for 2 turns. During this time, the C.A.I. stage will not advance.",
        [0, 1, 0, 1, 0, 5], Target.SINGLE,
        default_target("SELF"), exe_vongola_bow
    ],
    "gokudera4": [
        "Gokudera Block", "Gokudera becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gokudera_block
    ],
    "hibari1": [
        "Bite You To Death", "Hibari deals 20 damage to target enemy.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_bite_you_to_death
    ],
    "hibari2": [
        "Alaudi's Handcuffs",
        "Hibari stuns one enemy for 2 turns. During this time, they take 10 damage per turn and Hibari cannot use Porcospino Nuvola.",
        [0, 1, 0, 1, 0, 5], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Porcospino Nuvola")), exe_handcuffs
    ],
    "hibari3": [
        "Porcospino Nuvola",
        "For 2 turns, any enemy that uses a new harmful ability will take 10 damage. During this time, Hibari cannot use Alaudi's Handcuffs.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Alaudi's Handcuffs")), exe_porcospino
    ],
    "hibari4": [
        "Tonfa Block", "Hibari becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_tonfa_block
    ],
    "gray1": [
        "Ice, Make...",
        "Gray prepares to use his ice magic. On the following turn, all of his abilities are enabled and Ice, Make... becomes Ice, Make Unlimited.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_ice_make
    ],
    "gray2": [
        "Ice, Make Freeze Lancer",
        "Gray deals 15 damage to all enemies for 2 turns.", [0, 1, 0, 0, 1, 2],
        Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Ice, Make..."), exe_freeze_lancer
    ],
    "gray3": [
        "Ice, Make Hammer",
        "Gray deals 20 damage to one enemy and stuns them for 1 turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="Ice, Make..."), exe_hammer
    ],
    "gray4": [
        "Ice, Make Shield", "Gray becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF", prep_req="Ice, Make..."), exe_shield
    ],
    "grayalt1": [
        "Ice, Make Unlimited",
        "Gray deals 5 damage to all enemies and grants all allies 5 destructible defense every turn.",
        [0, 1, 0, 0, 2, 0], Target.ALL_TARGET,
        default_target("ALL", prep_req="Ice, Make...", lockout=(EffectType.MARK, "Ice, Make Unlimited")), exe_unlimited
    ],
    "sogiita1": [
        "Super Awesome Punch",
        "Gunha does 35 piercing damage to target enemy. Using this ability consumes up to 5 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, Super Awesome Punch deals 10 additional damage. If Gunha consumes 5 stacks, Super Awesome Punch will "
        + "stun its target for 1 turn.", [1, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Guts"), exe_super_awesome_punch
    ],
    "sogiita2": [
        "Overwhelming Suppression",
        "Gunha reduces the damage dealt by all enemies by 5 for 1 turn. Using this ability consumes up to 3 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, then the damage reduction is increased by 5. If Gunha consumes 3 stacks, then all affected enemies cannot reduce"
        + " damage or become invulnerable for 2 turns.", [0, 0, 1, 0, 0, 0
                                                         ], Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Guts"), exe_overwhelming_suppression
    ],
    "sogiita3": [
        "Hyper Eccentric Ultra Great Giga Extreme Hyper Again Awesome Punch",
        "Gunha does 20 damage to target enemy. Using this ability consumes up to "
        +
        "3 stacks of Guts from Gunha. If Gunha consumes at least 2 stacks, this ability deals 5 extra damage and becomes piercing. If Gunha consumes 3 stacks, this ability"
        +
        " will target all enemies.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", prep_req="Guts"), exe_hyper_eccentric_punch
    ],
    "sogiita4": [
        "Guts",
        "Gunha permanently activates Guts, enabling his other abilities and granting him 5 stacks of Guts. After the initial use, Gunha can activate "
        +
        "Guts again to grant himself 2 stacks of Guts and heal for 25 health.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF"), exe_guts
    ],
    "hinata1": [
        "Gentle Step - Twin Lion Fists",
        "Hinata deals 20 damage to one enemy, then deals 20 damage to the same enemy. The second instance of damage will occur even if this ability is "
        + "countered or reflected.", [1, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_twin_lion_fist
    ],
    "hinata2": [
        "Eight Trigrams - 64 Palms",
        "Hinata gives her entire team 10 points of damage reduction for 2 turns. If used again within 2 turns, this ability will also deal 15 damage to the enemy team.",
        [1, 0, 0, 0, 0, 0], Target.ALL_TARGET, target_eight_trigrams, exe_hinata_trigrams
    ],
    "hinata3": [
        "Byakugan",
        "For 3 turns, Hinata removes one energy from one of her targets whenever she deals damage.",
        [0, 1, 0, 0, 0, 3], Target.SINGLE, 
        default_target("SELF"), exe_hinata_byakugan
    ],
    "hinata4": [
        "Gentle Fist Block", "Hinata becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gentle_fist_block
    ],
    "ichigo1": [
        "Getsuga Tenshou",
        "Ichigo fires a wave of energy from the edge of his zanpakutou, dealing"
        +
        " 40 damage to one enemy. If used on the turn after Tensa Zangetsu, it will "
        + "ignore invulnerability and deal piercing damage.",
        [0, 0, 0, 1, 2, 1], Target.SINGLE, target_getsuga_tenshou, exe_getsuga_tenshou
    ],
    "ichigo2": [
        "Tensa Zangetsu",
        "Ichigo activates his zanpakutou's true strength, gaining enhanced combat abilities and speed. "
        + "Ichigo gains one random energy and is invulnerable for two turns." +
        " The turn after this ability " +
        "is used, Getsuga Tenshou and Zangetsu Strike are improved.",
        [1, 0, 0, 1, 0, 6], Target.SINGLE,
        default_target("SELF"), exe_tensa_zangetsu
    ],
    "ichigo3": [
        "Zangetsu Strike",
        "Ichigo slashes one enemy with Zangetsu, dealing 20 damage to them and permanently "
        +
        "increasing Zangetsu Strike's damage by 5. If used on the turn after "
        +
        "Tensa Zangetsu, it will target all enemies and permanently increase Zangetsu Strike's "
        + "damage by 5 per enemy struck.", [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_zangetsu_slash
    ],
    "ichigo4": [
        "Zangetsu Block", "Ichigo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_zangetsu_block
    ],
    "ichimaru1": [
        "Butou Renjin",
        "Ichimaru deals 15 damage to one enemy for two turns, adding a stack of Kamishini no Yari to the target each turn when it damages them.",
        [0, 0, 0, 1, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_butou_renjin
    ],
    "ichimaru2": [
        "13 Kilometer Swing",
        "Ichimaru deals 25 damage to all enemies and adds a stack of Kamishini no Yari to each enemy damaged.",
        [0, 0, 0, 1, 2, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_13_kilometer_swing
    ],
    "ichimaru3": [
        "Kill, Kamishini no Yari",
        "Ichimaru consumes all stacks of Kamishini no Yari, dealing 10 affliction damage to each enemy for the rest of the game for each stack of consumed from them. This effect ignores invulnerability.",
        [0, 0, 0, 2, 0, 2], Target.MULTI_ENEMY,
        target_kill_shinso, exe_kamishini_no_yari
    ],
    "ichimaru4": [
        "Shinso Parry", "Ichimaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_shinso_parry
    ],
    "jack1": [
        "Maria the Ripper",
        "Jack deals 15 damage and 10 affliction damage to one enemy. Can only target enemies affected by Fog of London or Streets of the Lost.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", prep_req = "Fog of London"), exe_maria_the_ripper
    ],
    "jack2": [
        "Fog of London",
        "Jack deals 5 affliction damage to all enemies for 3 turns. During this time, Fog of London is replaced by Streets of the Lost. This ability cannot be countered.",
        [0, 0, 1, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_fog_of_london
    ],
    "jack3": [
        "We Are Jack",
        "Jack deals 30 affliction damage to an enemy affected by Streets of the Lost.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Streets of the Lost"), exe_we_are_jack
    ],
    "jack4": [
        "Smokescreen Defense", "Jack becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_smokescreen_defense
    ],
    "jackalt1": [
        "Streets of the Lost",
        "For 3 turns, target enemy is isolated and can only target Jack. During this time, We Are Jack is usable.",
        [0, 0, 1, 0, 1, 5], Target.SINGLE,
        default_target("HOSTILE"), exe_streets_of_the_lost
    ],
    "itachi1": [
        "Amaterasu",
        "Itachi deals 10 affliction damage to one enemy for the rest of the game. This effect does not stack.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.CONT_AFF_DMG, "Amaterasu")), exe_amaterasu
    ],
    "itachi2": [
        "Tsukuyomi",
        "Itachi stuns one target for 3 turns. This effect will end early if an ally uses a skill on them.",
        [0, 0, 2, 0, 0, 4], Target.SINGLE,
        default_target("HOSTILE"), exe_tsukuyomi
    ],
    "itachi3": [
        "Susano'o",
        "Itachi gains 45 destructible defense, and takes 10 affliction damage each turn. During this time, Amaterasu is replaced by Totsuka Blade and Tsukuyomi is replaced by"
        +
        " Yata Mirror. If Itachi falls below 20 health or he loses all his destructible defense, Susano'o will end.",
        [0, 2, 0, 0, 0, 6], Target.SINGLE,
        default_target("SELF"), exe_susanoo
    ],
    "itachi4": [
        "Crow Genjutsu", "Itachi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_crow_genjutsu
    ],
    "itachialt1": [
        "Totsuka Blade",
        "Itachi deals 35 damage to one enemy and stuns them for one turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_totsuka_blade
    ],
    "itachialt2": [
        "Yata Mirror",
        "Itachi's Susano'o regains 20 destructible defense and Itachi loses 5 health.",
        [0, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("SELF"), exe_yata_mirror
    ],
    "jiro1": [
        "Counter-Balance",
        "For one turn, any enemy that stuns Jiro or her allies will lose one energy, and any enemy that drains energy from Jiro or her allies will be stunned for one turn. This effect is invisible.",
        [0, 1, 0, 0, 0, 2], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_counter_balance
    ],
    "jiro2": [
        "Heartbeat Distortion",
        "Jiro deals 5 damage to the enemy team for 4 turns. During this time, Heartbeat Distortion cannot be used and Heartbeat Surround will cost one less random energy and deal 20 damage to a single enemy. This ability"
        +
        " ignores invulnerability against enemies affected by Heartbeat Surround.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, target_heartbeat_distortion, exe_heartbeat_distortion
    ],
    "jiro3": [
        "Heartbeat Surround",
        "Jiro deals 10 damage to one enemy for 4 turns. During this time, Heartbeat Surround cannot be used and Heartbeat Distortion will cost one less random energy and deal 15 damage to all enemies. This ability ignores invulnerability "
        + "against enemies affected by Heartbeat Distortion.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE, target_heartbeat_surround, exe_heartbeat_surround
    ],
    "jiro4": [
        "Early Detection", "Jiro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_early_detection
    ],
    "kakashi1": [
        "Copy Ninja Kakashi",
        "For one turn, Kakashi will reflect the first hostile ability that targets him. This ability is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF"), exe_copy_ninja
    ],
    "kakashi2": [
        "Summon - Nin-dogs",
        "Target enemy takes 20 damage and is stunned for one turn. During this time, they take double damage from Raikiri.",
        [0, 1, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_nindogs
    ],
    "kakashi3": [
        "Raikiri", "Kakashi deals 40 piercing damage to target enemy.",
        [0, 2, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_raikiri
    ],
    "kakashi4": [
        "Kamui",
        "Kakashi targets one enemy or himself, ignoring invulnerability. If used on himself, Kakashi will ignore all harmful effects for one turn. If used on an enemy, this ability will deal"
        +
        " 20 piercing damage to them. If they are invulnerable, they will become isolated for one turn.",
        [0, 1, 0, 0, 0, 4], Target.SINGLE, target_kamui, exe_kamui
    ],
    "kuroko2": [
        "Teleporting Strike",
        "Kuroko deals 10 damage to one enemy and becomes invulnerable for one turn. If used on the turn after "
        +
        "Needle Pin, this ability will have no cooldown. If used on the turn after Judgement Throw, this ability will deal 15 extra damage.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_teleporting_strike
    ],
    "kuroko3": [
        "Needle Pin",
        "One enemy becomes unable to reduce damage or become invulnerable for two turns. If used on the turn after Teleporting Strike, "
        +
        "this ability ignores invulnerability and deals 15 piercing damage to its target. If used on the turn after Judgement Throw, this ability will stun its target for one turn.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_needle_pin, exe_needle_pin
    ],
    "kuroko1": [
        "Judgement Throw",
        "Kuroko deals 15 damage to one enemy and reduces their damage dealt by 10 for one turn. If used on the turn"
        +
        " after Teleporting Strike, this ability will have double effect. If used on the turn after Needle Pin, this ability will remove one energy from its target.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_judgement_throw
    ],
    "kuroko4": [
        "Kuroko Dodge", "Kuroko is invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kuroko_dodge
    ],
    "lambo1": [
        "Ten-Year Bazooka",
        "Lambo switches places with himself ten years in the future. The first time this is used, Summon Gyudon"
        +
        " will be replaced by Thunder, Set, Charge! for the next three turns. If used again, Thunder, Set, Charge! will be replaced by Elettrico Cornata for the next two turns. If used again, Lambo will return to his normal state.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_ten_year_bazooka
    ],
    "lambo2": [
        "Conductivity",
        "For two turns, Lambo's allies receive 20 points of damage reduction. If they receive damaging abilities during this time, "
        + "Lambo will take 10 damage.", [0, 0, 0, 0, 1, 2], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_conductivity
    ],
    "lambo3": [
        "Summon Gyudon",
        "Lambo's team gains 10 points of damage reduction permanently. During this time, the enemy team receives 5 points of damage each turn. This skill will end if "
        + "Ten-Year Bazooka is used.", [0, 0, 0, 1, 2, 4], Target.ALL_TARGET,
        default_target("ALL"), exe_summon_gyudon
    ],
    "lambo4": [
        "Lampow's Shield", "Lambo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_lampows_shield
    ],
    "lamboalt1": [
        "Thunder, Set, Charge!", "Lambo deals 25 damage to one enemy.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_thunder_set_charge
    ],
    "lamboalt2": [
        "Elettrico Cornata", "Lambo deals 35 damage to all enemies.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_elettrico_cornata
    ],
    "pucelle1": [
        "Knight's Sword", "La Pucelle deals 20 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_knights_sword
    ],
    "pucelle2": [
        "Magic Sword",
        "La Pucelle commands her sword to grow, permanently increasing its damage by 20, its cost by 1 random, and its cooldown by 1.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_magic_sword
    ],
    "pucelle3": [
        "Ideal Strike",
        "La Pucelle deals 40 piercing damage to one enemy. This ability ignores invulnerability, cannot be countered, and can only be used if La Pucelle is below 50 health.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE, target_ideal_strike, exe_ideal_strike
    ],
    "pucelle4": [
        "Knight's Guard", "La Pucelle becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_knights_guard
    ],
    "laxus1": [
        "Fairy Law",
        "Laxus deals 20 damage to all enemies and restores 20 health to all allies.",
        [0, 0, 0, 0, 3, 5], Target.ALL_TARGET,
        default_target("ALL"), exe_fairy_law
    ],
    "laxus2": [
        "Lightning Dragon's Roar",
        "Laxus deals 40 damage to one enemy and stuns them for one turn. When the stun wears off, the target receives 10 more damage for 1 turn.",
        [0, 2, 0, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_lightning_dragons_roar
    ],
    "laxus3": [
        "Thunder Palace",
        "After 2 turns, Laxus deals 40 damage to the entire enemy team. Dealing damage to Laxus during these two turns will cancel this effect,"
        +
        " dealing damage equal to the original damage of the move that damaged him to the user.",
        [0, 1, 0, 0, 2, 4], Target.SINGLE,
        default_target("SELF"), exe_thunder_palace
    ],
    "laxus4": [
        "Laxus Block", "Laxus becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_laxus_block
    ],
    "leone1": [
        "King of Beasts Transformation - Lionel",
        "Leone activates her Teigu, permanently allowing the use of her other moves and causing her to heal 10 health per turn."
        +
        " This healing is increased by 10 at the end of a turn in which she did damage to an enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_lionel
    ],
    "leone2": [
        "Beast Instinct",
        "Leone targets herself or an enemy for 3 turns. If used on an enemy, Lion Fist will ignore invulnerability and deal 20 additional damage to them. If"
        +
        " used on Leone, she will ignore counters and stuns for the duration.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, target_beast_instinct, exe_beast_instinct
    ],
    "leone3": [
        "Lion Fist",
        "Leone deals 35 damage to target enemy. If this ability kills an enemy while Leone is affected by Beast Instinct, Beast Instinct's duration will refresh. "
        +
        "If this ability kills an enemy that is affected by Beast Instinct, Leone will heal for 20 health.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        target_lion_fist, exe_lion_fist, 
    ],
    "leone4": [
        "Instinctual Dodge",
        "Leone becomes invulnerable for one turn. Using this ability counts as a damaging ability for triggering King of Beasts Transformation - Lionel's healing.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="King of Beasts Transformation - Lionel"), exe_instinctual_dodge
    ],
    "levy1": [
        "Solid Script - Fire",
        "Levy marks all enemies for one turn. During this time, if they use a new ability, they will take 10 affliction damage. When this ability"
        + " ends, all affected enemies take 10 affliction damage.",
        [0, 0, 1, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_solidscript_fire
    ],
    "levy2": [
        "Solid Script - Silent",
        "For two turns, all characters become isolated. This ability cannot be countered or ignored and ignores invulnerability.",
        [0, 0, 1, 0, 2, 3], Target.ALL_TARGET,
        default_target("ALL", def_type="BYPASS"), exe_solidscript_silent
    ],
    "levy3": [
        "Solid Script - Mask",
        "For two turns, target ally will ignore all stuns and affliction damage.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("HELPFUL"), exe_solidscript_mask
    ],
    "levy4": [
        "Solid Script - Guard", "Levy becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_solidscript_guard
    ],
    "raba1": [
        "Cross-Tail Strike",
        "Lubbock deals 15 damage to one target and marks them with Cross-Tail Strike. Until Lubbock uses this ability on an enemy already marked with Cross-Tail Strike, this ability will cost no energy. "
        +
        "If this ability targets a marked enemy and all living enemies are marked, this ability will deal 20 piercing damage to all marked enemies, ignoring invulnerability. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_crosstail_strike
    ],
    "raba2": [
        "Wire Shield",
        "Target ally gains 15 permanent destructible defense and is marked with Wire Shield. Until Lubbock uses this ability on an ally already targeted with Wire Shield, this ability will costs no energy. "
        +
        "If this ability targets an enemy marked with Wire Shield and all living allies are marked, all marked allies become invulnerable for one turn. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_wire_shield
    ],
    "raba3": [
        "Heartseeker Thrust",
        "Lubbock deals 30 piercing damage to one target. If Lubbock is marked by Wire Shield, the damaged enemy will receive 15 affliction damage on the following turn. If the target is marked by Cross-Tail Strike, "
        + "the target will become stunned for one turn.", [0, 0, 0, 1, 1,
                                                           1], Target.SINGLE,
        default_target("HOSTILE"), exe_heartseeker_thrust
    ],
    "raba4": [
        "Defensive Netting", "Lubbock becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_defensive_netting
    ],
    "lucy1": [
        "Aquarius",
        "Lucy deals 15 damage to all enemies and grants her team 10 points of damage reduction.",
        [0, 0, 0, 1, 1, 2], Target.ALL_TARGET,
        default_target("ALL"), exe_aquarius
    ],
    "lucy2": [
        "Gemini",
        "For the next three turns, Lucy's abilities will stay active for one extra turn. During this time, this ability is replaced by Urano Metria.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_gemini
    ],
    "lucy3": [
        "Capricorn", "Lucy deals 20 damage to one enemy.", [0, 0, 0, 1, 0, 0],
        Target.SINGLE,
        default_target("HOSTILE"), exe_capricorn
    ],
    "lucy4": [
        "Leo", "Lucy becomes invulnerable for one turn.", [0, 0, 0, 0, 1, 4],
        Target.SINGLE,
        default_target("SELF"), exe_leo
    ],
    "lucyalt1": [
        "Urano Metria", "Lucy deals 20 damage to all enemies.",
        [0, 1, 0, 1, 0, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_urano_metria
    ],
    "midoriya1": [
        "SMASH!",
        "Midoriya unleashes the full power of his quirk, dealing 45 damage to one enemy. The backlash"
        +
        " from unleashing One For All's strength deals 20 affliction damage to Midoriya and stuns him for"
        + " one turn.", [1, 0, 0, 0, 2, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_smash
    ],
    "midoriya2": [
        "Air Force Gloves",
        "Midoriya fires a compressed ball of air with a flick, dealing 15 damage to one enemy and"
        + " increasing the cooldown of any move they use by one for one turn.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_air_force_gloves
    ],
    "midoriya3": [
        "One For All - Shoot Style",
        "Midoriya unleashes his own style of One For All, dealing 20 damage to all enemies. For 1 turn,"
        + " Midoriya will counter the first ability used on him.",
        [1, 0, 0, 0, 1, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_shoot_style
    ],
    "midoriya4": [
        "Enhanced Leap", "Midoriya becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_enhanced_leap
    ],
    "minato1": [
        "Flying Raijin",
        "Minato deals 35 piercing damage that ignores invulnerability to one enemy. If used on a target marked with Marked Kunai, Minato becomes invulnerable for "
        +
        "one turn and the cooldown on Flying Raijin is reduced to 0. This effect consumes Marked Kunai's mark.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_flying_raijin
    ],
    "minato2": [
        "Marked Kunai",
        "Minato deals 10 piercing damage to one enemy and permanently marks them.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_marked_kunai
    ],
    "minato3": [
        "Partial Shiki Fuujin",
        "Minato permanently increases the cooldowns and random cost of target enemy by one. After using this skill, Minato dies.",
        [0, 0, 0, 0, 3, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_partial_shiki_fuujin
    ],
    "minato4": [
        "Minato Parry", "Minato becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("HOSTILE"), exe_minato_parry
    ],
    "mine1": [
        "Roman Artillery - Pumpkin",
        "Mine deals 25 damage to one enemy. If Mine is below 60 health, this ability deals 10 more damage. If Mine is below 30 health, this ability"
        + "costs one less weapon energy.", [0, 0, 0, 1, 1, 0], Target.SINGLE, target_pumpkin, exe_roman_artillery_pumpkin
    ],
    "mine2": [
        "Cut-Down Shot",
        "Deals 25 damage to all enemies. If Mine is below 50 health, this ability will stun all targets hit for 1 turn. If Mine is below 25 health, this ability deals double damage and the damage it deals "
        + "is piercing.", [0, 0, 0, 1, 2, 3], Target.MULTI_ENEMY, target_cutdown_shot, exe_cutdown_shot
    ],
    "mine3": [
        "Pumpkin Scouter",
        "For the next two turns, all of Mine's abilities will ignore invulnerability and deal 5 additional damage.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_pumpkin_scouter
    ],
    "mine4": [
        "Close-Range Deflection", "Mine becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_closerange_deflection
    ],
    "mirai1": [
        "Blood Suppression Removal",
        "For 3 turns, Mirai's abilities will cause their target to receive 10 affliction damage for 2 turns. During this time, this ability is replaced with Blood Bullet and Mirai receives 10 affliction damage per turn.",
        [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF"), exe_blood_suppression_removal
    ],
    "mirai2": [
        "Blood Sword Combat", "Mirai deals 30 damage to target enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_blood_sword_combat
    ],
    "mirai3": [
        "Blood Shield",
        "Mirai gains 20 points of destructible defense and 20 points of damage reduction for one turn.",
        [0, 1, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF"), exe_blood_shield
    ],
    "mirai4": [
        "Mirai Deflect", "Mirai becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_mirai_deflect
    ],
    "miraialt1": [
        "Blood Bullet",
        "Mirai deals 10 affliction damage to target enemy for 2 turns.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_blood_bullet
    ],
    "mirio1": [
        "Quirk - Permeation",
        "For one turn, Mirio will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_permeation
    ],
    "mirio2": [
        "Phantom Menace",
        "Mirio deals 20 piercing damage to one enemy. This ability ignores invulnerability, always damages marked targets, and deals 15 bonus damage to them.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", def_type="BYPASS"), exe_phantom_menace
    ],
    "mirio3": [
        "Protect Ally",
        "For one turn, target ally will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("HELPFUL"), exe_protect_ally
    ],
    "mirio4": [
        "Mirio Dodge", "Mirio becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_mirio_dodge
    ],
    "misaka1": [
        "Railgun",
        "Misaka deals 45 damage to one enemy. This ability ignores invulnerability and cannot be countered or reflected.",
        [0, 1, 1, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_railgun
    ],
    "misaka2": [
        "Iron Sand",
        "Misaka targets an ally or an enemy. If used on an ally, that ally gains 20 points of destructible defense"
        +
        " for one turn and this ability goes on cooldown for one turn. If used on an enemy, it deals 20 damage to them.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("ALL"), exe_iron_sand
    ],
    "misaka3": [
        "Electric Rage",
        "For 2 turns, Misaka will gain one special energy whenever she takes new damage. She cannot"
        + " be killed while this ability is active.", [0, 0, 1, 0, 0,
                                                       6], Target.SINGLE,
        default_target("SELF"), exe_electric_rage
    ],
    "misaka4": [
        "Electric Deflection", "Misaka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_electric_deflection
    ],
    "mugen1": [
        "Unpredictable Strike",
        "Mugen deals 20 damage to target enemy. This ability has a random extra effect that changes each turn.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="Way of the Rooster")
    ],
    "mugen2": [
        "Way of the Rooster",
        "Enables the use of Mugen's other abilities. This effect will notify Mugen of what "
        + "random effects he has queued at the moment.", [0, 0, 0, 0, 1,
                                                          0], Target.SINGLE,
        default_target("SELF")
    ],
    "mugen3": [
        "Unpredictable Spinning",
        "Mugen gains 10 points of damage reduction for two turns. This ability has a random extra effect that changes each turn.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF", prep_req="Way of the Rooster")
    ],
    "mugen4": [
        "Mugen Block", "Mugen becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "mugenalt1": [
        "Hidden Dagger",
        "For 2 turns, Mugen will deal 10 piercing damage to any enemy that damages him.",
        [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "naruha1": [
        "Bunny Assault",
        "Naru deals 15 damage to one enemy for 3 turns. If she finishes using this ability without being stunned, Perfect Paper - Rampage Suit gains 20 destructible defense. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit"), exe_bunny_assault
    ],
    "naruha2": [
        "Perfect Paper - Rampage Suit",
        "Naru permanently gains 70 points of destructible defense. After being used, Naru can use Bunny Assault and this ability is replaced by Enraged Blow.",
        [0, 0, 0, 0, 2, 0], Target.SINGLE,
        default_target("SELF"), exe_rampage_suit
    ],
    "naruha3": [
        "Perfect Paper - Piercing Umbrella",
        "Naru deals 15 damage to target enemy. If Naru has destructible defense remaining on Perfect Paper - Rampage Suit, this ability will deal 10 bonus damage.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_piercing_umbrella
    ],
    "naruha4": [
        "Rabbit Guard",
        "Perfect Paper - Rampage Suit gains 25 points of destructible defense. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="Perfect Paper - Rampage Suit"), exe_rabbit_guard
    ],
    "naruhaalt1": [
        "Enraged Blow",
        "Naru deals 40 damage to one enemy and stuns them for a turn. During the following turn, Naru takes double damage. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [1, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit"), exe_enraged_blow
    ],
    "natsu1": [
        "Fire Dragon's Roar",
        "Natsu deals 25 damage to one enemy. The following turn, they take 10 affliction damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_roar
    ],
    "natsu2": [
        "Fire Dragon's Iron Fist",
        "Natsu deals 15 damage to one enemy. If they are currently affected by one of Natsu's affliction damage-over-time"
        + " effects, they take 10 affliction damage.", [0, 1, 0, 0, 0,
                                                        0], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_iron_fist
    ],
    "natsu3": [
        "Fire Dragon's Sword Horn",
        "Natsu deals 40 damage to one enemy. For the rest of the game, that enemy"
        + " takes 5 affliction damage per turn.", [1, 1, 0, 0, 1,
                                                   3], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_sword_horn
    ],
    "natsu4": [
        "Natsu Dodge", "Natsu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_natsu_dodge
    ],
    "neji1": [
        "Eight Trigrams - 128 Palms",
        "Neji deals 2 damage to target enemy for seven turns. The damage this ability deals doubles each turn. While active, this ability is replaced by "
        +
        "Chakra Point Strike, which removes one random energy from the target if they take damage from Eight Trigrams - 128 Palms this turn.",
        [1, 0, 0, 0, 1, 8], Target.SINGLE,
        default_target("HOSTILE"), exe_neji_trigrams
    ],
    "neji2": [
        "Eight Trigrams - Mountain Crusher",
        "Neji deals 25 damage to target enemy, ignoring invulnerability. If used on an invulnerable target, this ability will deal 15 additional damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_neji_mountain_crusher
    ],
    "neji3": [
        "Selfless Genius",
        "If a target ally would die this turn, they instead take no damage and deal 10 additional damage on the following turn. If this ability is triggered, Neji dies. This skill is invisible until "
        + "triggered and the death cannot be prevented.", [0, 0, 0, 0, 2,
                                                           3], Target.SINGLE,
        default_target("SELFLESS"), exe_selfless_genius
    ],
    "neji4": [
        "Eight Trigrams - Revolving Heaven",
        "Neji becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                    4], Target.SINGLE,
        default_target("SELF"), exe_revolving_heaven
    ],
    "nejialt1": [
        "Chakra Point Strike",
        "If target enemy takes damage from Eight Trigrams - 128 Palms this turn, they will lose 1 random energy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Eight Trigrams - 128 Palms"), exe_chakra_point_strike
    ],
    "nemu1": [
        "Nemurin Nap",
        "Nemurin heads for the dream world, enabling the use of her other abilities. Every turn, her sleep grows one stage deeper. While dozing, Nemurin heals "
        +
        "10 health per turn. While fully asleep, Nemurin Beam and Dream Manipulation cost one less random energy. While deeply asleep, Nemurin Beam and Dream Manipulation become area-of-effect. When Nemurin takes non-absorbed damage, she loses one stage of sleep depth.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF"), exe_nemurin_nap
    ],
    "nemu2": [
        "Nemurin Beam",
        "Nemurin deals 25 damage to target enemy and reduces the damage they deal by 10 for one turn.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", prep_req = "Nemurin Nap"), exe_nemurin_nap
    ],
    "nemu3": [
        "Dream Manipulation",
        "For 3 turns, target ally deals 10 additional damage and heals 10 health per turn. Cannot be used on Nemurin.",
        [0, 0, 1, 0, 1, 2], Target.SINGLE,
        default_target("SELFLESS", prep_req = "Nemurin Nap"), exe_dream_manipulation
    ],
    "nemu4": [
        "Dreamland Sovereignty", "Nemurin becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req = "Nemurin Nap"), exe_dream_sovereignty
    ],
    "orihime1": [
        "Tsubaki!",
        "Orihime prepares the Shun Shun Rikka with an offensive effect.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Tsubaki!")), exe_tsubaki
    ],
    "orihime2": [
        "Ayame! Shun'o!",
        "Orihime prepares the Shun Shun Rikka with a healing effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Ayame! Shun'o!")), exe_ayame_shuno
    ],
    "orihime3": [
        "Lily! Hinagiku! Baigon!",
        "Orihime prepares the Shun Shun Rikka with a defensive effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF",
                       lockout=(EffectType.MARK, "Lily! Hinagiku! Baigon!")), exe_lily_hinagiku_baigon
    ],
    "orihime4": [
        "I Reject!",
        "Orihime activates her Shun Shun Rikka, with a composite effect depending on the flowers she has activated. This will end any active Shun Shun Rikka effect.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, target_shun_shun_rikka, exe_i_reject
    ],
    "shunshunrikka1": [
        "Dance of the Heavenly Six",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka2": [
        "Five-God Inviolate Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka3": [
        "Four-God Resisting Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka4": [
        "Three-God Empowering Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka5": [
        "Three-God Linking Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka6": [
        "Two-God Returning Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "shunshunrikka7": [
        "Lone-God Slicing Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE
    ],
    "ripple1": [
        "Perfect Accuracy",
        "Targets one enemy with Ripple's perfect accuracy. For the rest of the game, Shuriken Throw will target that enemy in addition to any other targets, ignoring invulnerability and dealing 5 additional damage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.MARK, "Perfect Accuracy")), exe_perfect_accuracy
    ],
    "ripple2": [
        "Shuriken Throw", "Ripple deals 15 piercing damage to target enemy.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_shuriken_throw
    ],
    "ripple3": [
        "Night of Countless Stars",
        "Ripple deals 5 piercing damage to all enemies for three turns. During this time, Shuriken Throw deals 10 additional damage.",
        [0, 0, 0, 1, 1, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_countless_stars
    ],
    "ripple4": [
        "Ripple Block", "Ripple becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_ripple_block
    ],
    "rukia1": [
        "First Dance - Tsukishiro",
        "Rukia deals 25 damage to one enemy, ignoring invulnerability. If that enemy is invulnerable, they are stunned for one turn.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_first_dance
    ],
    "rukia2": [
        "Second Dance - Hakuren",
        "Rukia deals 15 damage to one enemy and 10 damage to all others.",
        [0, 1, 0, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_second_dance
    ],
    "rukia3": [
        "Third Dance - Shirafune",
        "The next time Rukia is countered, the countering enemy receives 30 damage and is stunned for one turn. This effect is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF"), exe_third_dance
    ],
    "rukia4": [
        "Rukia Parry", "Rukia becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rukia_parry
    ],
    "ruler1": [
        "In The Name Of Ruler!",
        "Ruler stuns one enemy and herself for 3 turns. This skill cannot be used while active and will end if Ruler is damaged.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "In The Name Of Ruler!")), exe_in_the_name_of_ruler
    ],
    "ruler2": [
        "Minion - Minael and Yunael",
        "Deals 15 damage to target enemy or gives 10 destructible defense to Ruler.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, target_minion_minael_yunael, exe_minael_yunael
    ],
    "ruler3": [
        "Minion - Tama",
        "The next time target ally receives a new harmful ability, that ability is countered and its user takes 20 piercing damage. This effect can only be active on one target at a time.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HELPFUL"), exe_tama
    ],
    "ruler4": [
        "Minion - Swim Swim", "Ruler becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_swim_swim
    ],
    "ryohei1": [
        "Maximum Cannon", "Ryohei deals 20 damage to a single target.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_maximum_cannon
    ],
    "ryohei2": [
        "Kangaryu", "Ryohei heals target ally for 15 health.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_kangaryu
    ],
    "ryohei3": [
        "Vongola Headgear",
        "For the next 3 turns, Ryohei will ignore all random cost increases to Maximum Cannon and Kangaryu, and using them will not consume stacks of To The Extreme!",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_vongola_headgear
    ],
    "ryohei4": [
        "To The Extreme!",
        "For the rest of the game, whenever Ryohei takes 20 damage, he will gain one stack of To The Extreme! For each stack of To The Extreme! on him, Maximum Cannon will deal 15 more damage and cost one more random"
        +
        " energy, and Kangaryu will restore 20 more health and cost one more random energy. Using either ability will reset all stacks of To The Extreme!",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_to_the_extreme
    ],
    "saber1": [
        "Excalibur",
        "Saber deals 50 piercing damage to one enemy. This ability cannot be countered.",
        [0, 1, 0, 1, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_excalibur
    ],
    "saber2": [
        "Wind Blade Combat",
        "Saber deals 10 damage to one enemy for three turns. During this time, Saber"
        + " cannot be stunned. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_wind_blade_combat
    ],
    "saber3": [
        "Avalon",
        "One ally permanently heals 10 health per turn. This ability can only affect one ally at a time.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL", protection=(EffectType.MARK, "Avalon")), exe_avalon
    ],
    "saber4": [
        "Saber Parry", "Saber becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_saber_parry
    ],
    "saitama1": [
        "One Punch", "Saitama deals 75 piercing damage to one enemy.",
        [2, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_one_punch
    ],
    "saitama2": [
        "Consecutive Normal Punches",
        "Saitama deals 15 damage to one enemy for 3 turns.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_consecutive_normal_punches
    ],
    "saitama3": [
        "Serious Series - Serious Punch",
        "On the following turn Saitama deals 35 damage to target enemy. During this time, Saitama will ignore all effects.",
        [1, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_serious_punch
    ],
    "saitama4": [
        "Serious Series - Serious Sideways Jumps",
        "Saitama becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                       4], Target.SINGLE,
        default_target("SELF"), exe_sideways_jumps
    ],
    "seiryu1": [
        "Body Modification - Arm Gun",
        "Seiryu deals 20 damage to one enemy. Becomes Body Modification - Self Destruct if Seiryu falls below 30 health.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_body_mod_arm_gun
    ],
    "seiryu2": [
        "Raging Koro",
        "Koro deals 20 damage to one enemy for two turns. Becomes Insatiable Justice while active.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_raging_koro
    ],
    "seiryu3": [
        "Berserker Howl",
        "Koro deals 15 damage to all enemies and lowers the damage they deal by 10 for 2 turns.",
        [0, 0, 0, 0, 3, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_berserker_howl
    ],
    "seiryu4": [
        "Koro Defense", "Seiryu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_koro_defense
    ],
    "seiryualt1": [
        "Body Modification - Self Destruct",
        "Seiryu deals 30 damage to all enemies. After using this ability, Seiryu dies. Effects that prevent death cannot prevent Seiryu from dying. This ability cannot be countered.",
        [0, 0, 0, 0, 2, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_self_destruct
    ],
    "seiryualt2": [
        "Insatiable Justice",
        "Koro instantly kills one enemy that is below 30 health. Effects that prevent death cannot prevent this ability.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE, target_insatiable_justice, exe_insatiable_justice
    ],
    "shigaraki1": [
        "Decaying Touch",
        "Shigaraki deals 5 affliction damage to target enemy for the rest of the game. This damage is doubled each time Decaying Touch is applied.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_decaying_touch
    ],
    "shigaraki2": [
        "Decaying Breakthrough",
        "Shigaraki applies a stack of Decaying Touch to all enemies.",
        [1, 0, 0, 0, 2, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_decaying_breakthrough
    ],
    "shigaraki3": [
        "Destroy What You Hate, Destroy What You Love",
        "Shigaraki's allies deal 10 more damage for 2 turns. During this time they take 5 more damage from all effects and cannot reduce damage or become invulnerable.",
        [0, 0, 1, 0, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_destroy_what_you_love
    ],
    "shigaraki4": [
        "Kurogiri Escape", "Shigaraki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kurogiri_escape
    ],
    "shikamaru1": [
        "Shadow Bind Jutsu",
        "Shikamaru stuns one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 4], Target.SINGLE, default_target("HOSTILE"), exe_shadow_bind_jutsu
    ],
    "shikamaru2": [
        "Shadow Neck Bind",
        "Shikamaru deals 15 damage to one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_shadow_neck_bind
    ],
    "shikamaru3": [
        "Shadow Pin",
        "For one turn, target enemy cannot target enemies.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_shadow_pin
    ],
    "shikamaru4": [
        "Shikamaru Hide", "Shikamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_hide
    ],
    "misaki1": [
        "Mental Out",
        "Shokuhou stuns target enemy for 2 turns. During this time, Mental Out is replaced by one of their abilities, and Shokuhou can use that ability as though she were the stunned enemy. All negative effects applied to Misaki as a result of this ability's use are applied to the stunned enemy instead.",
        [0, 0, 2, 0, 0, 3], Target.SINGLE,
        target_mental_out, exe_mental_out
    ],
    "misaki2": [
        "Exterior",
        "Shokuhou takes 25 affliction damage. For the next 4 turns, Mental Out costs 1 less mental energy and lasts 1 more turn.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF"), exe_exterior
    ],
    "misaki3": [
        "Ally Mobilization",
        "For 2 turns, both of Shokuhou's allies will ignore stuns and gain 15 damage reduction.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_ally_mobilization
    ],
    "misaki4": [
        "Loyal Guard",
        "Shokuhou becomes invulnerable for 1 turn. This ability is only usable if Shokuhou has a living ally.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE, target_loyal_guard, exe_loyal_guard
    ],
    "misakialt1": [
        "Mental Out - Order",
        "Placeholder ability to be replaced by a controlled enemy's ability.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, target_mental_out_order, exe_mental_out_order
    ],
    "snowwhite1": [
        "Enhanced Strength", "Snow White deals 15 damage to one enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_enhanced_strength
    ],
    "snowwhite2": [
        "Hear Distress",
        "Snow White targets an ally or an enemy for 1 turn. If used on an ally, that ally will "
        +
        "gain 25 points of damage reduction and will gain one random energy if a new harmful ability is used on them. If used on an"
        +
        " enemy, that enemy will have their first new harmful ability countered, and they will lose one random energy. This"
        +
        " skill is invisible until triggered and ignores invulnerability and isolation.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE,
        default_target("ALL", def_type="BYPASS"), exe_hear_distress
    ],
    "snowwhite3": [
        "Lucky Rabbit's Foot",
        "Snow White targets an ally other than herself. For 1 turn, if that ally dies, they instead"
        + " return to 35 health. This healing cannot be prevented.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELFLESS"), exe_rabbits_foot
    ],
    "snowwhite4": [
        "Leap", "Snow White becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_leap
    ],
    "swimswim1": [
        "Ruler", "Swim Swim deals 25 damage to target enemy.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_ruler, exe_ruler
    ],
    "swimswim2": [
        "Dive",
        "Swim Swim ignores all hostile effects for one turn. The following turn, her abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("SELF"), exe_dive
    ],
    "swimswim3": [
        "Vitality Pills",
        ("For 3 turns, Swim Swim gains 10 points of damage reduction and her"
        " abilities will deal 10 more damage."),
        [0, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("SELF"), exe_vitality_pills
    ],
    "swimswim4": [
        "Water Body", "Swim Swim becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_water_body
    ],
    "tatsumaki1": [
        "Rubble Barrage",
        "Tatsumaki deals 10 damage to all enemies for two turns.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_rubble_barrage
    ],
    "tatsumaki2": [
        "Arrest Assault",
        ("Tatsumaki's team gains 10 points of damage reduction for one turn."
        " This effect is invisible. After being used, this ability is replaced "
        "by Return Assault for one turn."), [0, 0, 1, 0, 0,
                                              3], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_arrest_assault
    ],
    "tatsumaki3": [
        "Gather Power",
        "Tatsumaki gains one random energy and one stack of Gather Power. For each stack of Gather Power on her, Rubble Barrage"
        +
        " deals 5 more damage, Arrest Assault grants 5 more damage reduction, and Gather Power has one less cooldown.",
        [0, 0, 1, 0, 0, 4], Target.SINGLE, default_target("SELF"), exe_gather_power
    ],
    "tatsumaki4": [
        "Psionic Barrier", "Tatsumaki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_psionic_barrier
    ],
    "tatsumakialt1": [
        "Return Assault",
        "Tatsumaki deals 0 damage to all enemies. This ability deals 20 more damage for every damaging ability Tatsumaki's team received on the previous turn.",
        [0, 0, 1, 0, 1, 2], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_return_assault
    ],
    "todoroki1": [
        "Quirk - Half-Cold",
        "Deals 20 damage to all enemies and lowers their damage dealt by 10 for one turn. Increases the cost of all of Todoroki's abilities by one random energy until he uses Quirk - Half-Hot or Flashfreeze Heatwave.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_half_cold
    ],
    "todoroki2": [
        "Quirk - Half-Hot",
        "Deals 30 damage to one enemy and 10 damage to Todoroki's allies. The damage dealt to Todoroki's allies is permanently increased by 10 with each use.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_half_hot
    ],
    "todoroki3": [
        "Flashfreeze Heatwave",
        "Deals 10 damage to target enemy and 5 damage to all other enemies. The damage to the primary target is increased by 10 for each stack of Quirk - Half-Hot on Todoroki, and the "
        +
        "damage to all targets is increased by 10 for each stack of Quirk - Half-Cold on Todoroki. Consumes all stacks of Quirk - Half-Hot and Quirk - Half-Cold.",
        [0, 2, 0, 0, 0, 2], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_flashfreeze_heatwave
    ],
    "todoroki4": [
        "Ice Rampart", "Todoroki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_ice_rampart
    ],
    "tatsumi1": [
        "Killing Strike",
        "Tatsumi deals 25 damage to one enemy. If that enemy is stunned or below half"
        + " health, they take 10 more damage. Both damage boosts can occur.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_killing_strike
    ],
    "tatsumi2": [
        "Incursio",
        "For four turns, Tatsumi gains 25 points of destructible defense and "
        + "Neuntote becomes usable.", [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_incursio
    ],
    "tatsumi3": [
        "Neuntote",
        "Tatsumi deals 15 damage to target enemy. For two turns, that enemy receives double"
        + " damage from Neuntote. This effect stacks.", [0, 0, 0, 1, 1,
                                                         0], Target.SINGLE, default_target("HOSTILE", prep_req="Incursio"), exe_neuntote
    ],
    "tatsumi4": [
        "Invisibility", "Tatsumi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_invisibility
    ],
    "toga1": [
        "Thirsting Knife",
        "Toga deals 10 damage to one enemy and applies a stack of Thirsting Knife to them.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, default_target("HOSTILE"), exe_thirsting_knife
    ],
    "toga2": [
        "Vacuum Syringe",
        "Toga deals 10 affliction damage to one enemy for 2 turns. Each turn, she applies a stack of Vacuum"
        + " Syringe to them.", [0, 0, 0, 0, 2, 1], Target.SINGLE, default_target("HOSTILE"), exe_vacuum_syringe
    ],
    "toga3": [
        "Quirk - Transform",
        "Toga consumes all stacks of Thirsting Knife and Vacuum Syringe on one enemy, turning into a copy of them"
        + " for one turn per stack consumed. This effect ignores invulnerability.", [0, 0, 0, 0, 1,
                                                5], Target.SINGLE, target_transform, exe_transform
    ],
    "toga4": [
        "Toga Dodge", "Toga becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_toga_dodge
    ],
    "tsunayoshi1": [
        "X-Burner",
        "Tsuna deals 25 damage to one enemy and 10 damage to all others.",
        [0, 1, 0, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_xburner
    ],
    "tsunayoshi2": [
        "Zero Point Breakthrough",
        "For one turn, the first harmful ability used on Tsuna" +
        " will be countered, and the countered enemy will be stunned for two turns. If this successfully"
        +
        " counters an ability, Tsuna will deal 10 additional damage with X-Burner for two turns.",
        [0, 0, 0, 0, 2, 4], Target.SINGLE, default_target("SELF"), exe_zero_point_breakthrough
    ],
    "tsunayoshi3": [
        "Burning Axle",
        "Tsuna deals 35 damage to one enemy. For one turn, if that enemy takes new"
        + " damage, they are stunned for one turn and take 15 damage.",
        [0, 1, 0, 1, 1, 3], Target.SINGLE, default_target("HOSTILE"), exe_burning_axle
    ],
    "tsunayoshi4": [
        "Flare Burst", "Tsuna becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_flare_burst
    ],
    "uraraka1": [
        "Quirk - Zero Gravity",
        "Uraraka targets one enemy or one ally for 3 turns. If used on an enemy, that enemy will take 10 more damage from all sources and be unable to reduce damage"
        +
        " or become invulnerable. If used on an ally, that ally will gain 10 points of damage reduction and their abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("ALL"), exe_zero_gravity
    ],
    "uraraka2": [
        "Meteor Storm",
        "Uraraka deals 15 damage to all enemies. If a damaged enemy is currently targeted by Zero Gravity, that enemy will be stunned for one turn. If an ally is currently targeted by "
        +
        "Zero Gravity, they will deal 5 more damage with abilities this turn.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_meteor_storm
    ],
    "uraraka3": [
        "Comet Home Run",
        "Uraraka deals 20 damage to one enemy. If the damaged enemy is currently targeted by Zero Gravity, that enemy will lose one random energy. If an ally is currently targeted by "
        + "Zero Gravity, they will become invulnerable for one turn.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_comet_home_run
    ],
    "uraraka4": [
        "Float", "Uraraka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_float
    ],
    "wendy1": [
        "Troia",
        "Wendy heals target ally for 40 health. For 3 turns, this ability will have 50% effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HELPFUL"), exe_troia
    ],
    "wendy2": [
        "Shredding Wedding",
        "For three turns, Wendy and target enemy will take 20 piercing damage when they attempt to target anyone that isn't each other. During this time, any other characters that attempt to target either will take 20 piercing damage and Shredding Wedding becomes Piercing Winds.",
        [0, 2, 0, 0, 0, 5], Target.SINGLE, default_target("HOSTILE"), exe_shredding_wedding
    ],
    "wendy3": [
        "Sky Dragon's Roar",
        "Deals 20 damage to all enemies and heals Wendy for 15 health.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_sky_dragons_roar
    ],
    "wendy4": [
        "Wendy Dodge", "Wendy becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_wendy_dodge
    ],
    "wendyalt1": [
        "Piercing Winds",
        "Wendy deals 25 piercing damage to the enemy affected by Shredding Wedding.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", mark_req="Shredding Wedding"), exe_piercing_winds
    ],
    "yamamoto1": [
        "Shinotsuku Ame",
        "Yamamoto deals 30 damage to one enemy and reduces the damage they deal by 10 for three turns. Grants Yamamoto"
        +
        " one stack of Asari Ugetsu. Using this ability on an enemy already affected by it will refresh the effect.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_shinotsuku_ame
    ],
    "yamamoto2": [
        "Utsuhi Ame",
        "On the following turn, Yamamoto will deal 20 damage to target enemy and grant himself one stack of"
        + " Asari Ugetsu. If that enemy uses a new ability " +
        "during this time, Yamamoto deals 40 damage to them and grants himself 3 stacks of Asari Ugetsu instead.",
        [0, 0, 0, 1, 0, 2], Target.SINGLE, default_target("HOSTILE"), exe_utsuhi_ame
    ],
    "yamamoto3": [
        "Asari Ugetsu",
        "Consumes all stacks of Asari Ugetsu on use, and remains active for one turn plus one per stack consumed. While active, replaces Shinotsuku Ame with Scontro di Rondine and "
        +
        "Utsuhi Ame with Beccata di Rondine, and Yamamoto gains 20 points of damage reduction.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE, default_target("SELF", lockout=(EffectType.ALL_DR, "Asari Ugetsu")), exe_asari_ugetsu
    ],
    "yamamoto4": [
        "Sakamaku Ame", "Yamamoto becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_sakamaku_ame
    ],
    "yamamotoalt1": [
        "Scontro di Rondine",
        "Yamamoto deals 20 damage to one enemy. If that enemy's damage is being reduced by at least 10, this ability deals 10 bonus damage.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_scontro_di_rondine
    ],
    "yamamotoalt2": [
        "Beccata di Rondine",
        "Yamamoto deals 5 damage to all enemies and reduces their damage dealt by 5 for 3 turns.",
        [0, 0, 0, 1, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_beccata_di_rondine
    ],
    #"" : ["", "", [], Target.],
}
