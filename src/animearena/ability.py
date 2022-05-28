from random import randint
from PIL import Image
from pathlib import Path
import sdl2
import sdl2.ext
import enum
import copy
import importlib.resources
from animearena.effects import EffectType, Effect
from animearena.ability_type import AbilityType
import logging

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

BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)

@enum.unique
class Target(enum.IntEnum):
    "A component for determining the targeting style of an ability"
    SINGLE = 0
    MULTI_ENEMY = 1
    MULTI_ALLY = 2
    ALL_TARGET = 3
    MULTI_EITHER = 4
    SELF_OR_ENEMIES = 5


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
    types: list[AbilityType]
    target: Callable
    execute: Callable

    def __init__(self, name: str = None):
        if name:
            self.db_name = name
            self.image = Image.open(get_path(name + ".png"))
        self.char_select_desc = None
        self.in_battle_desc = None
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
        if len(details_package) == 7:
            self.types = details_package[6]
        else:
            self.types = []


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
        if character.has_effect(EffectType.PROF_SWAP, "Level-6 Shift"):
            return False
        if character.has_specific_stun():
            for stun_type in character.get_specific_stun_types():
                if self._base_cost[Energy(stun_type - 1)] > 0:
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
        if def_type == "NORMAL":
            targeting = user.check_bypass_effects()
        else:
            targeting = def_type

        if target_type == "HOSTILE" or target_type == "ALL":
            for enemy in enemyTeam:
                if enemy.hostile_target(user, targeting) and (
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
                if ally.helpful_target(user, targeting) and (
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
                if ally != user and ally.helpful_target(user, targeting) and (
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

def target_blasted_tree(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    if user.source.hp < 200:
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
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

def target_gate_of_babylon(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0

    targeting = user.check_bypass_effects()

    if not fake_targeting:
        user.set_targeted()
    total_targets += 1

    for enemy in enemyTeam:
        if enemy.hostile_target(user, targeting):
            if not fake_targeting:
                enemy.set_targeted()
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
    if user.source.hp <= 75:
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

def target_yatsufusa(user: "CharacterManager",
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
    for ally in playerTeam:
        if ally != user and ally.hostile_target(user, targeting):
            if not fake_targeting:
                ally.set_targeted()
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

def target_summon_gyudon(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()

    if not user.has_effect(EffectType.PROF_SWAP, "Ten-Year Bazooka") and not user.has_effect(EffectType.MARK, "Summon Gyudon"):
        for enemy in enemyTeam:
            if enemy.hostile_target(user, targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
        for player in playerTeam:
            if player.helpful_target(user, targeting):
                if not fake_targeting:
                    player.set_targeted()
                total_targets += 1
    
    return total_targets

def target_insatiable_justice(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    for enemy in enemyTeam:
        if enemy.hostile_target(user, "BYPASS") and enemy.source.hp < 60:
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
            logging.debug("Shokuhou can be guarded by %s!", ally.source.name)
            if not fake_targeting:
                user.set_targeted()
            total_targets = 1
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




#region Naruto Execution

def naruto_mission5_complete(target: "CharacterManager") -> bool:
    if target.has_effect(EffectType.SYSTEM, "NarutoRasenganTracker") and target.has_effect(EffectType.SYSTEM, "NarutoOdamaTracker") and target.has_effect(EffectType.SYSTEM, "NarutoRasenrenganTracker"):
        target.remove_effect(target.get_effect(EffectType.SYSTEM, "NarutoRasenganTracker"))
        target.remove_effect(target.get_effect(EffectType.SYSTEM, "NarutoOdamaTracker"))
        target.remove_effect(target.get_effect(EffectType.SYSTEM, "NarutoRasenrenganTracker"))
        return True

def exe_rasengan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 25
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                target.add_effect(Effect("NarutoRasenganTracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
                if naruto_mission5_complete(target):
                    user.progress_mission(5, 1)
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_clones(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 5, lambda eff: "Naruto has 10 points of damage reduction.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Rasengan has been replaced by Odama Rasengan", mag=11))
    user.add_effect(Effect(user.used_ability, EffectType.COUNTER_IMMUNE, user, 5, lambda eff: "Naruto will ignore counter and reflect effects."))
    user.check_on_use()

def exe_substitution(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("naruto4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Naruto is invulnerable."))
    user.check_on_use()

def exe_sage_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 3, lambda eff: "", mag=1, system=True))
    if user.has_effect(EffectType.ABILITY_SWAP, "Shadow Clones"):
        user.remove_effect(user.get_effect(EffectType.ABILITY_SWAP, "Shadow Clones"))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Odama Rasengan has been replaced by Rasenshuriken", mag=13))
    else:
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Rasengan has been replaced by Senpou - Rasenrengan", mag=12))
    user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 3, lambda eff: "Naruto will ignore stun effects."))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: "Naruto will deal 20 affliction damage to any enemy that drains energy from him."))
    user.check_on_use()


def exe_odama_rasengan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                if target == user.primary_target:
                    user.deal_active_damage(35, target, DamageType.NORMAL)
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    target.add_effect(Effect("NarutoOdamaTracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
                    if naruto_mission5_complete(target):
                        user.progress_mission(5, 1)
                        if target.meets_stun_check():
                            user.check_on_stun(target)
                else:
                    user.deal_active_damage(25, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_rasenrengan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(50, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                target.add_effect(Effect("NarutoRasenrenganTracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
                if naruto_mission5_complete(target):
                    user.progress_mission(5, 1)
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_rasenshuriken(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(35, target, DamageType.PIERCING)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

#endregion
#region Accelerator Execution
def exe_vector_scatter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                user.add_effect(Effect("AcceleratorMission2Tracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=False))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_plasma_bomb(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 15 damage.", mag = 15))
        if user.last_man_standing():
            user.add_effect(Effect("AcceleratorMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
        if not user.has_effect(EffectType.SYSTEM, "AcceleratorMission2Failure"):
            user.add_effect(Effect("AcceleratorMission2Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff:"Accelerator is using Plasma Bomb. This effect will end if he is stunned."))
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff:"Only stun effects can be applied to Accelerator."))
        user.check_on_use()
        user.check_on_harm()

def exe_vector_reflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Accelerator will ignore all harmful effects.", invisible = True))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "Any enemy that targets Accelerator with a new harmful ability will be targeted by Vector Scatter.", invisible = True))
    if not user.has_effect(EffectType.SYSTEM, "AcceleratorMission2Failure"):
        user.add_effect(Effect("AcceleratorMission2Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    user.check_on_use()

def exe_vector_immunity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Accelerator is invulnerable."))
    if not user.has_effect(EffectType.SYSTEM, "AcceleratorMission2Failure"):
        user.add_effect(Effect("AcceleratorMission2Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    user.check_on_use()

#endregion
#region Aizen Execution

def invoke_order(user: "CharacterManager", num: int):
    if user.get_effect(EffectType.SYSTEM, "AizenMission5Tracker").mag == num:
        user.remove_effect(user.get_effect(EffectType.SYSTEM, "AizenMission5Tracker"))
    else:
        user.get_effect(EffectType.SYSTEM, "AizenMission5Tracker").mag = num

def exe_shatter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        invoke_order(user, 1)

        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(Ability("aizen1"), EffectType.COST_ADJUST, user, 2, lambda eff: "This character's ability costs are increased by one random energy.", mag=51))
                target.add_effect(Effect(Ability("aizen1"), EffectType.MARK, user, 3, lambda eff: "This character will take 20 additional damage from Overwhelming Power."))
                target.add_effect(Effect(Ability("aizen1"), EffectType.MARK, user, 3, lambda eff: "If Black Coffin is used on this enemy, it will also affect their allies."))

                #Black Coffin
                if target.has_effect(EffectType.MARK, "Black Coffin"):
                    user.progress_mission(1, 1)
                    for ability in target.source.current_abilities:
                        if ability.cooldown_remaining > 0:
                            ability.cooldown_remaining += 2
                if target.has_effect(EffectType.MARK, "Overwhelming Power"):
                    user.progress_mission(1, 1)
                    user.add_effect(Effect(Ability("aizen1"), EffectType.COST_ADJUST, user, 3, lambda eff: "Aizen's ability costs have been reduced by one random energy.", mag=-51))

        user.check_on_use()
        user.check_on_harm()

def exe_overwhelming_power(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        invoke_order(user, 2)

        for target in user.current_targets:
            base_damage=25
            if target.has_effect(EffectType.MARK, "Shatter, Kyoka Suigetsu"):
                base_damage += 20
                user.progress_mission(1, 1)
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(Ability("aizen2"), EffectType.MARK, user, 3, lambda eff: "If Shatter, Kyoka Suigetsu is used on this character, Aizen's abilities will cost one fewer random energy for one turn."))
                target.add_effect(Effect(Ability("aizen2"), EffectType.MARK, user, 3, lambda eff: "If Black Coffin is used on this enemy, they will take 20 damage."))
                if target.has_effect(EffectType.MARK, "Black Coffin"):
                    user.progress_mission(1, 1)
                    target.add_effect(Effect(Ability("aizen2"), EffectType.DEF_NEGATE, user, 3, lambda eff: "This character cannot reduce damage or become invulnerable."))
        user.check_on_use()
        user.check_on_harm()

def exe_black_coffin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        invoke_order(user, 3)
        if user.primary_target.final_can_effect(user.check_bypass_effects()):
            if user.primary_target.has_effect(EffectType.MARK, "Shatter, Kyoka Suigetsu"):
                user.progress_mission(1, 1)
                user.progress_mission(4, 1)
                for enemy in enemyTeam:
                    if enemy != user.primary_target and enemy.hostile_target(user, user.check_bypass_effects()):
                        user.current_targets.append(enemy)

        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(Ability("aizen3"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                target.add_effect(Effect(Ability("aizen3"), EffectType.MARK, user, 3, lambda eff: "If Shatter, Kyoka Suigetsu is used on this character, all of their active cooldowns will be increased by 2."))
                target.add_effect(Effect(Ability("aizen3"), EffectType.MARK, user, 3, lambda eff: "If Overwhelming Power is used on this character, they will be unable to reduce damage or become invulnerable for 2 turns."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
                if target.has_effect(EffectType.MARK, "Overwhelming Power"):
                    user.progress_mission(1, 1)
                    base_damage = 20
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_effortless_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    invoke_order(user, 4)
    user.add_effect(Effect(Ability("aizen4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Aizen is invulnerable."))
    user.check_on_use()
#endregion
#region Akame Execution
def exe_red_eyed_killer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            user.progress_mission(4, 1)
            target.add_effect(Effect(Ability("akame1"), EffectType.MARK, user, 3, lambda eff: "Akame can use One Cut Killing on this character."))
    user.check_on_use()

def exe_one_cut_killing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) or (user.has_effect(EffectType.MARK, "Little War Horn") and target.final_can_effect("FULLBYPASS")):
                base_damage = 100
                user.deal_active_damage(base_damage, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 100 affliction damage.", mag = 100))
        user.check_on_use()
        user.check_on_harm()

def exe_little_war_horn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("akame3"), EffectType.MARK, user, 5, lambda eff: "Akame can use One Cut Killing on any target."))
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 5, lambda eff:"", mag = 1, system = True))
    if user.last_man_standing():
        user.add_effect(Effect("AkameMission3Tracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
    user.check_on_use()

def exe_rapid_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("akame4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Akame is invulnerable."))
    user.check_on_use()
#endregion
#region Astolfo Execution
def exe_casseur(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            target.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 2, lambda eff: "Astolfo will counter the first harmful Special or Mental ability used against this character. This effect is invisible until triggered.", invisible = True))
        user.check_on_help()
        user.check_on_use()

def exe_trap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 20
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
                target.add_effect(Effect(user.used_ability, EffectType.BOOST_NEGATE, user, 2, lambda eff: "This character cannot have their damage boosted over its base value."))
                if target.has_boosts():
                    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=1, print_mag=True), user)
                    user.progress_mission(2, 1)
        user.check_on_use()
        user.check_on_harm()
            

def exe_luna(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id == user.id:
                hostile_effects = [eff for eff in target.source.current_effects if eff.user.is_enemy() and not (eff.system or eff.eff_type == EffectType.SYSTEM)]
                if hostile_effects:
                    num = user.scene.d20.randint(0, len(hostile_effects) - 1)
                    target.full_remove_effect(hostile_effects[num].name, hostile_effects[num].user)
                    user.progress_mission(3, 1)
                    user.progress_mission(2, 1)
                    user.apply_stack_effect(Effect(Ability("astolfo2"), EffectType.STACK, user, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=1, print_mag=True), user)
            if target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.BOOST_NEGATE, user, 4, lambda eff: "This character cannot have their damage boosted over its base value."))
        user.check_on_use()
        user.check_on_help()
        user.check_on_harm()
        

                    

def exe_kosmos(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Astolfo is invulnerable."))
    user.check_on_use()

#endregion
#region Byakuya Execution

def exe_scatter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_power = 25
        helped = False
        harmed = False
        if user.has_effect(EffectType.TARGET_SWAP, "Bankai - Senbonzakura Kageyoshi"):
            user.progress_mission(3, 1)
        for target in user.current_targets:
            if target.id == user.id:
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} destructible defense.", mag = 25, print_mag=True))
                helped = True
            elif target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_active_damage(base_power, target, DamageType.PIERCING)
                harmed = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

def exe_sixrod(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    target.add_effect(Effect("ByakuyaMission1Marker", EffectType.SYSTEM, user, 3, lambda eff:"", system=True))
                    user.check_on_stun(target)
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Bakudou #61 - Six-Rod Light Restraint has been replaced by Hadou #2 - Byakurai.", mag=21))
        user.check_on_use()
        user.check_on_harm()

def exe_senbonzakura_kageyoshi(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 5, lambda eff: "Scatter, Senbonzakura will affect all enemy or allied targets.", mag = 14))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Bankai - Senbonzakura Kageyoshi has been replaced by White Imperial Sword.", mag = 32))
    user.check_on_use()

def exe_byakurai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    base_damage = 25
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                if target.has_effect(EffectType.SYSTEM, "ByakuyaMission1Marker"):
                    user.progress_mission(1, 1)
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
        user.remove_effect(user.get_effect_with_user(EffectType.ABILITY_SWAP, "Bakudou #61 - Six-Rod Light Restraint", user))
        user.check_on_use()
        user.check_on_harm()

def exe_imperial_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    base_damage = 30
    if not user.check_countered(playerTeam, enemyTeam):
        missing_health = 200 - user.source.hp
        boost_mag = (missing_health // 10) * 5
        mod_damage = base_damage + boost_mag
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(mod_damage, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_danku(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Byakuya is invulnerable."))
    user.check_on_use()

#endregion
#region Calamity Mary Execution
def exe_pistol(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)

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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Calamity Mary is using Quickdraw - Rifle. This effect will end if she is stunned. If this effect expires normally, Quickdraw - Rifle will be replaced by Quickdraw - Sniper."))


        user.check_on_use()
        user.check_on_harm()

def exe_sniper(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        for target in user.current_targets:
            base_damage = 55
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
            user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Calamity Mary is invulnerable."))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Chachamaru Execution
def exe_target_lock(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            user.progress_mission(1, 1)
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character can be targeted with Orbital Satellite Cannon."))
    user.check_on_use()

def exe_satellite_cannon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 35
            if target.final_can_effect("BYPASS"):
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
        user.check_on_harm()
        user.check_on_use()

def exe_active_combat_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            base_damage = 10
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 10 damage.", mag=10))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_DEST_DEF, user, 5, lambda eff: "This character will gain 15 points of destructible defense.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15, print_mag=True))
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Chachamaru cannot use Orbital Satellite Cannon."))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Chachamaru is using Active Combat Mode. This effect will end if she is stunned."))
        user.check_on_use()
        user.check_on_harm()

def exe_take_flight(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Chachamaru is invulnerable."))
    user.check_on_use()
#endregion
#region Chelsea Execution
def exe_mortal_wound(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                base_damage = 15
                if target.has_effect(EffectType.MARK, "Those Who Fight In The Shadows"):
                    user.add_effect(Effect("ChelseaMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
                    base_damage = base_damage * 3
                else:
                    if not user.has_effect(EffectType.SYSTEM, "ChelseaMission5Failure"):
                        user.add_effect(Effect("ChelseaMission5Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
                user.deal_active_damage(base_damage, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: f"This character will take {eff.mag} affliction damage.", mag = base_damage))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 280000, lambda eff: "This character will deal 5 less non-affliction damage.", mag=-5))
def exe_fight_in_shadows(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            target.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 2, lambda eff: "If this character receives a new helpful ability, the user will be countered, stunned for two turns, and Mortal Wound will have triple effect against them.", invisible=True))
    user.check_on_use()
    user.check_on_harm()

def exe_chelsea_smoke(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    harmed = False
    helped = False
    for target in user.current_targets:
        if target.id == user.id:
            if target.helpful_target(user):
                target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 10))
            helped = True
        if target.id != user.id:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                has_counter = list([eff for eff in target.source.current_effects if eff.eff_type == EffectType.COUNTER_RECEIVE and eff.user.id == target.id])
                logging.debug("Emergency Smoke detected %d allied counter effects on %s", len(has_counter), target.source.name)
                logging.debug("%s", target)
                if has_counter:
                    user.progress_mission(4, 1)
                    user.deal_active_damage(15, target, DamageType.AFFLICTION)
            harmed = True
    if helped:
        user.check_on_help()
    if harmed:
        user.check_on_harm()
    user.check_on_use()
        
def exe_gaia_evasion(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Chelsea is invulnerable."))
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
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=20, print_mag=True))
        user.check_on_use()
        user.check_on_harm()


def exe_mental_immolation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Chrome's destructible defense is not broken, this character will receive 20 damage and Chrome will remove one random energy from them."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15, print_mag=True))
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_illusory_world_destruction(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30, print_mag=True))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: "If this destructible defense is not destroyed, Mukuro will deal 25 damage to all enemies and stun them for one turn."))
    user.check_on_use()

def exe_mental_annihilation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Mukuro's destructible defense is not broken, this character will receive 35 damage that ignores invulnerability."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30, print_mag=True))
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
                    user.deal_active_damage(base_damage, target, DamageType.PIERCING)
                else:
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
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
                total_shatter = 0
                for eff in target.source.current_effects:
                    if eff.eff_type==EffectType.DEST_DEF:
                        total_shatter += eff.mag
                        eff.mag = 0
                        target.check_for_collapsing_dest_def(eff)
                user.progress_mission(4, total_shatter)
                if total_shatter > 0:
                    target.add_effect(Effect("GaeBolgPierceMarker", EffectType.SYSTEM, user, 1, lambda eff:"", system=True))
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
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
                target.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 2, lambda eff: "This character's ability costs are increased by 1 random.", mag=51))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "This effect will end if this character uses a new ability."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "This character can be targeted by Merciless Finish."))
            user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Illusory Disorientation has been replaced by Merciless Finish.", mag = 11))
        user.check_on_use()
        user.check_on_harm()

def exe_fortissimo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("FULLBYPASS"):
                base_damage = 25
                if target.is_ignoring() or target.check_invuln():
                    base_damage = 50
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_mental_radar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.COUNTER_IMMUNE, user, 3, lambda eff: "This character will ignore counter effects."))
        user.check_on_use()
        user.check_on_help()

def exe_cranberry_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Cranberry is invulnerable."))
    user.check_on_use()

def exe_merciless_finish(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 15 affliction damage.", mag=15))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Cranberry is using Merciless Finish. This effect will end if she is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Erza Execution
def exe_clear_heart_clothing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()
    if not user.has_effect(EffectType.SYSTEM, "ErzaMission5ClearHeart"):
        user.add_effect(Effect("ErzaMission5ClearHeart", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    if (user.has_effect(EffectType.SYSTEM, "ErzaMission5ClearHeart") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5HeavensWheel") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Nakagami") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Adamantine") and
        not user.has_effect(EffectType.SYSTEM, "ErzaMission5Tracker")):
        user.add_effect(Effect("ErzaMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Clear Heart Clothing."))
    user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 280000, lambda eff: "Erza cannot be stunned."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Clear Heart Clothing has been replaced by Titania's Rampage.", mag=11))
    user.check_on_use()

def exe_heavens_wheel_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()

    if not user.has_effect(EffectType.SYSTEM, "ErzaMission5HeavensWheel"):
        user.add_effect(Effect("ErzaMission5HeavensWheel", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    if (user.has_effect(EffectType.SYSTEM, "ErzaMission5ClearHeart") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5HeavensWheel") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Nakagami") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Adamantine") and
        not user.has_effect(EffectType.SYSTEM, "ErzaMission5Tracker")):
        user.add_effect(Effect("ErzaMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Heaven's Wheel Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.AFF_IMMUNE, user, 280000, lambda eff: "Erza will ignore affliction damage."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Heaven's Wheel Armor has been replaced by Circle Blade.", mag = 22))
    user.check_on_use()

def exe_nakagamis_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()

    if not user.has_effect(EffectType.SYSTEM, "ErzaMission5Nakagami"):
        user.add_effect(Effect("ErzaMission5Nakagami", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    if (user.has_effect(EffectType.SYSTEM, "ErzaMission5ClearHeart") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5HeavensWheel") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Nakagami") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Adamantine") and
        not user.has_effect(EffectType.SYSTEM, "ErzaMission5Tracker")):
        user.add_effect(Effect("ErzaMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Erza has equipped Nakagami's Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.ENERGY_GAIN, user, 5, lambda eff: "Erza will gain one random energy.", mag=51))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Nakagami's Armor has been replaced by Nakagami's Starlight.", mag = 33))
    user.check_on_use()


def exe_adamantine_armor(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.erza_requip()

    if not user.has_effect(EffectType.SYSTEM, "ErzaMission5Adamantine"):
        user.add_effect(Effect("ErzaMission5Adamantine", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    if (user.has_effect(EffectType.SYSTEM, "ErzaMission5ClearHeart") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5HeavensWheel") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Nakagami") and
        user.has_effect(EffectType.SYSTEM, "ErzaMission5Adamantine") and
        not user.has_effect(EffectType.SYSTEM, "ErzaMission5Tracker")):

        user.add_effect(Effect("ErzaMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Erza has equipped Adamantine Armor."))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "Erza has 15 points of damage reduction.", mag=15))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Adamantine Armor has been replaced by Adamantine Barrier.", mag = 44))

def exe_titanias_rampage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"Erza will deal {(eff.mag * 5) + 15} piercing damage to a random enemy.", mag = 1, print_mag=True))
    
    valid_targets: list["CharacterManager"] = []
    for enemy in enemyTeam:
        if enemy.final_can_effect(user.check_bypass_effects()) and not enemy.deflecting():
            valid_targets.append(enemy)
    if valid_targets:
        target = user.scene.d20.randint(0, len(valid_targets) - 1)
        user.deal_active_damage(15, valid_targets[target], DamageType.PIERCING)
        logging.debug("Rampage dealing 15 damage to %s", valid_targets[target].source.name)
    user.check_on_use()
    if valid_targets:
        user.check_on_harm()


def exe_circle_blade(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
        user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "Erza will deal 15 damage to all enemies.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_nakagamis_starlight(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(35, target, DamageType.NORMAL)
                target.source.change_energy_cont(-1)
                user.check_on_drain(target)
                user.progress_mission(3, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_adamantine_barrier(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
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
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 5, lambda eff: "Weiss Schnabel will target all enemies.", mag=31))
    user.check_on_use()
    user.check_on_harm()

def exe_weiss_schnabel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.has_effect(EffectType.COST_ADJUST, "Weiss Schnabel"):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(10, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will receive 10 damage.", mag=10))
        if user.current_targets:
            user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 5, lambda eff: "Weiss Schnabel will cost one fewer special energy and deal 15 piercing damage to its target.", mag = -321))
    else:
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.PIERCING)
    user.check_on_use()
    user.check_on_harm()            

def exe_esdeath_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Esdeath is invulnerable."))
    user.check_on_use()

def exe_mahapadma(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            if target != user:
                if target.id == user.id:
                    duration = 5
                else:
                    duration = 4
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, duration, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
            else:
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "When Mahapadma ends, Esdeath will be stunned for two turns."))
    if user.last_man_standing():
        user.add_effect(Effect("EsdeathMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
    user.check_on_use()
#endregion
#region Frankenstein Execution
def exe_bridal_smash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 20
                if user.has_effect(EffectType.CONT_UNIQUE, "Bridal Chest"):
                    user.progress_mission(1, 1)
                if user.has_effect(EffectType.STACK, "Galvanism"):
                    base_damage = base_damage + (user.get_effect(EffectType.STACK, "Galvanism").mag * 10)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_bridal_chest(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 20
                if user.has_effect(EffectType.STACK, "Galvanism"):
                    base_damage = base_damage + (user.get_effect(EffectType.STACK, "Galvanism").mag * 10)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: "Frankenstein will deal 20 damage to a random enemy target.", mag=20))
        user.check_on_use()
        user.check_on_harm()

def exe_blasted_tree(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            base_damage = user.source.hp
            if target.source.hp > 100:
                user.add_effect(Effect("FrankensteinMission5Tracker", EffectType.SYSTEM, user, 1, lambda eff:"", system=True))
            if user.has_effect(EffectType.STACK, "Galvanism"):
                    base_damage = base_damage + (user.get_effect(EffectType.STACK, "Galvanism").mag * 10)
            user.deal_active_damage(base_damage, target, DamageType.NORMAL)
    
    user.check_on_use()
    user.check_on_harm()

    user.source.hp = 0
    user.death_check(user)

        

def exe_galvanism(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 4, lambda eff: "Damaging Special abilities will instead heal Frankenstein.", invisible=True))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "If Frankenstein is healed by Galvanism, she will deal 10 additional damage with her abilities on the following turn.", invisible=True))
    
    user.check_on_use()
#endregion
#region Frenda Execution
def exe_close_combat_bombs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect():
                target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Detonate will deal {15 * eff.mag} damage to this character.", mag=1, print_mag=True), user)
                user.progress_mission(1, 1)
        user.check_on_use()

def exe_doll_trap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if not target.has_effect_with_user(EffectType.MARK, "Doll Trap", user):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "If an enemy damages this character, all stacks of Doll Trap will be transferred to them.", invisible=True))
        target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Detonate will deal {20 * eff.mag} damage to this character.", mag=1, invisible=True, print_mag=True), user)
        user.progress_mission(1, 1)
    user.check_on_use()

def exe_detonate(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        user.add_effect(Effect("FrendaMission2Tracker", EffectType.SYSTEM, user, 2, lambda eff:"", mag=0, system=True))
        total_bombs = 0
        total_dolls = 0
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 0
                if target.has_effect_with_user(EffectType.STACK, "Doll Trap", user):
                    base_damage += 20 * target.get_effect_with_user(EffectType.STACK, "Doll Trap", user).mag
                    total_dolls += target.get_effect_with_user(EffectType.STACK, "Doll Trap", user).mag
                if target.has_effect_with_user(EffectType.STACK, "Close Combat Bombs", user):
                    base_damage += 15 * target.get_effect_with_user(EffectType.STACK, "Close Combat Bombs", user).mag
                    total_bombs += target.get_effect_with_user(EffectType.STACK, "Close Combat Bombs", user).mag
                target.full_remove_effect("Doll Trap", user)
                target.full_remove_effect("Close Combat Bombs", user)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        if total_dolls >= 7 and total_bombs >= 2:
            user.progress_mission(4, 1)
            
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
                user.deal_active_damage(35, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_shadow_dragon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.ALL_DR, "Blacksteel Gajeel"):
        user.full_remove_effect("Blacksteel Gajeel", user)
    user.progress_mission(4, 1)
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 280000, lambda eff: "The first time each turn that Gajeel receives a harmful ability, he will ignore all hostile effects for the rest of the turn."))
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 280000, lambda eff: "", mag = 1, system=True))
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
                user.deal_active_damage(15, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_shadow_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_active_damage(25, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_blacksteel_gajeel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.UNIQUE, "Iron Shadow Dragon"):
        user.full_remove_effect("Iron Shadow Dragon", user)
        user.full_remove_effect("gajeel3", user)
    user.progress_mission(4, 1)
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "Gajeel has 15 points of damage reduction.", mag = 15))
    user.check_on_use()



#endregion
#region Gilgamesh Execution

def exe_gate_of_babylon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target == user:
                target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff:f"Gate of Babylon will deal {eff.mag * 15} additional damage.", mag=1, print_mag=True), user)
            else:
                if target.final_can_effect(user.check_bypass_effects()):
                    base_damage = 10
                    if user.has_effect(EffectType.STACK, "Gate of Babylon"):
                        base_damage += (user.get_effect(EffectType.STACK, "Gate of Babylon").mag * 15)
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                harmed = True
        user.check_on_use()
        if harmed:
            if user.has_effect(EffectType.STACK, "Gate of Babylon"):
                user.remove_effect(user.get_effect(EffectType.STACK, "Gate of Babylon"))
            user.check_on_harm()
            
def exe_enkidu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            if not target.source.uses_energy_mult([0, 1, 2]):
                user.progress_mission(5, 1)
            target.add_effect(Effect(user.used_ability, EffectType.COUNTER_USE, user, 2, lambda eff: f"The first harmful ability used by this character will be countered and they will be stunned for one turn.", invisible=True))
    user.check_on_use()
    user.check_on_harm()

def exe_enuma_elish(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(40, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.SPECIFIC_STUN, user, 4, lambda eff: "This character's Weapon skills are stunned.", mag=4))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_intercept(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: f"Gilgamesh is invulnerable."))
    user.check_on_use()

#endregion
#region Gokudera Execution

def advance_sistema_cai(sistema: Effect):
    sistema.alter_mag(1)
    if sistema.mag == 5:
        sistema.mag = 1
        if not sistema.user.has_effect(EffectType.SYSTEM, "GokuderaMission5Tracker"):
            sistema.user.add_effect(Effect("GokuderaMission5Tracker", EffectType.SYSTEM, sistema.user, 280000, lambda eff:"", mag=1, system=False))
        else:
            sistema.user.get_effect(EffectType.SYSTEM, "GokuderaMission5Tracker").alter_mag(1)
            if sistema.user.get_effect(EffectType.SYSTEM, "GokuderaMission5Tracker").mag >= 3:
                sistema.user.progress_mission(5, 1)
                sistema.user.source.mission5complete = True

def exe_sistema_cai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    stage = user.get_effect(EffectType.STACK, "Sistema C.A.I.").mag
    
    if not user.check_countered(playerTeam, enemyTeam):
        if stage == 1:
            for target in user.current_targets:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(10, target, DamageType.NORMAL)
            user.check_on_use()
            user.check_on_harm()
        elif stage == 2:
            for target in user.current_targets:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(10, target, DamageType.NORMAL)
                    if target == user.primary_target:
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        if target.meets_stun_check():
                            user.check_on_stun(target)
            user.check_on_use()
            user.check_on_harm()
        elif stage == 3:
            for target in user.current_targets:
                if target == user.primary_target:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_active_damage(20, target, DamageType.NORMAL)
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        if target.meets_stun_check():
                            user.check_on_stun(target)
                else:
                    if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                        user.deal_active_damage(10, target, DamageType.NORMAL)
            user.give_healing(15, user)
            user.check_on_use()
            user.check_on_harm()
        elif stage == 4:
            for target in user.current_targets:
                if target == "ally":
                    user.give_healing(25, target)
                else:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_active_damage(25, target, DamageType.NORMAL)
                        target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                        if target.meets_stun_check():
                            user.check_on_stun(target)
            
            user.check_on_use()
            user.check_on_harm()
            user.check_on_help()
        if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
            advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
            user.progress_mission(1, 1)
        else:
            if user.has_effect(EffectType.SYSTEM, "GokuderaMission4Tracker"):
                user.get_effect(EffectType.SYSTEM, "GokuderaMission4Tracker").alter_mag(1)
                if user.get_effect(EffectType.SYSTEM, "GokuderaMission4Tracker").mag >= 2:
                    user.progress_mission(4, 1)


def exe_vongola_ring(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    if not user.has_effect(EffectType.MARK, "Vongola Box Weapon - Vongola Bow"):
        advance_sistema_cai(user.get_effect(EffectType.STACK, "Sistema C.A.I."))
    user.check_on_use()

def exe_vongola_bow(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect("GokuderaMission4Tracker", EffectType.CONSECUTIVE_TRACKER, user, 5, lambda eff:"", mag = 0, system=True))
    user.add_effect(Effect("GokuderaMission4Tracker", EffectType.CONSECUTIVE_BUFFER, user, 2, lambda eff: "", system = True))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "The Sistema C.A.I. stage will not advance when Sistema C.A.I. is used."))
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 5, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=30, print_mag=True))
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
                user.deal_active_damage(20, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_handcuffs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(15, target, DamageType.NORMAL)
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
        user.progress_mission(5, 1)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
        user.check_on_use()
        user.check_on_harm()        


def exe_hammer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        user.progress_mission(5, 1)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
                    user.progress_mission(2, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.progress_mission(5, 1)
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Gray is invulnerable."))
    if not user.has_effect(EffectType.SYSTEM, "GrayMission3Tracker"):
        user.add_effect(Effect("GrayMission3Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", mag=1, system=True))
    else:
        user.get_effect(EffectType.SYSTEM, "GrayMission3Tracker").alter_mag(1)
    user.check_on_use()

def exe_unlimited(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        user.progress_mission(5, 1)
        for target in user.current_targets:
            if target.id == user.id:
                if target.helpful_target(user):
                    target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=5, print_mag=True))
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DEST_DEF, user, 280000, lambda eff: f"This character will gain 5 points of destructible defense.", mag=5))
                helped = True
            elif target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(5, target, DamageType.NORMAL)
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
    output = 0
    if gunha.has_effect(EffectType.STACK, "Guts"):
        if gunha.get_effect(EffectType.STACK, "Guts").mag >= max:
            gunha.get_effect(EffectType.STACK, "Guts").alter_mag(max * -1)
            if gunha.get_effect(EffectType.STACK, "Guts").mag < 3:
                gunha.source.main_abilities[2].target_type = Target.SINGLE
            if gunha.get_effect(EffectType.STACK, "Guts").mag == 0:
                gunha.remove_effect(gunha.get_effect(EffectType.STACK, "Guts"))
            output = max
        else:
            output = gunha.get_effect(EffectType.STACK, "Guts").mag
            gunha.remove_effect(gunha.get_effect(EffectType.STACK, "Guts"))
            gunha.source.main_abilities[2].target_type = Target.SINGLE

    if output >= 3:
        gunha.progress_mission(1, 1)
    return output


def exe_guts(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Guts"):
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Gunha has {eff.mag} Guts.", mag=3), user)
        if user.get_effect(EffectType.STACK, "Guts").mag > 2:
            user.source.main_abilities[2].target_type = Target.MULTI_ENEMY
        if user.get_effect(EffectType.STACK, "Guts").mag >= 10:
            user.add_effect(Effect("GunhaMission3Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
        user.give_healing(35, user)
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
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
                if charges == 5:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
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
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: f"This character will deal {-eff.mag} less damage.", mag=(suppression * -1)))
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
                    user.deal_active_damage(base_damage, target, DamageType.PIERCING)
            else:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Hinata Execution
def exe_twin_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    used = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.drain_energy(1, user)
                used = True
    else:
        user.source.first_countered = True
    user.source.second_swing = True
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.drain_energy(1, user)
                used = True
    user.source.second_swing = False
    user.source.first_countered = False
    if used:
        user.check_on_use()
        user.check_on_harm()

def exe_hinata_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):

    counterable = False
    for target in user.current_targets:
        if target in enemyTeam:
            counterable = True
    if counterable and not user.check_countered(playerTeam, enemyTeam):
        drained = False
        for target in user.current_targets:
            if target.id != user.id and target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                if user.has_effect(EffectType.MARK, "Byakugan") and not drained:
                    target.drain_energy(1, user)
                    drained = True
            elif target.id == user.id and target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: "This character has 10 points of damage reduction.", mag=10))
        if not user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Eight Trigrams - 64 Palms will deal 15 damage to all enemies."))
        else:
            user.get_effect(EffectType.MARK, "Eight Trigrams - 64 Palms").duration = 3
        user.check_on_use()
        user.check_on_harm()
    if not counterable:
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: "This character has 10 points of damage reduction.", mag=10))
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
                    user.deal_active_damage(40, target, DamageType.PIERCING)
                else:
                    user.deal_active_damage(40, target, DamageType.NORMAL)
                if target.check_invuln():
                    user.source.mission1progress += 1
        user.check_on_use()
        user.check_on_harm()

def exe_tensa_zangetsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 4, lambda eff: "Ichigo is invulnerable."))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Getsuga Tenshou deals piercing damage and ignores invulnerabilty."))
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 3, lambda eff: "Zangetsu Strike will target all enemies.", mag=31))
    user.source.change_energy_cont(1)
    user.check_on_use()

def exe_zangetsu_slash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        affected = 0
        for target in user.current_targets:
            base_damage = 20
            if user.has_effect(EffectType.STACK, "Zangetsu Strike") and user.can_boost():
                base_damage += (5 * user.get_effect(EffectType.STACK, "Zangetsu Strike").mag)
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                affected += 1
        if affected > 0:
            user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Zangetsu Strike will deal {5 * eff.mag} more damage.", mag = affected, print_mag = True), user)
            user.progress_mission(3, affected)
            if user.get_effect(EffectType.STACK, "Zangetsu Strike").mag >= 10:
                user.progress_mission(4, 1)
                user.source.mission4complete += 1
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
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1, print_mag=True), user)
                if not user.has_effect(EffectType.SYSTEM, "IchimaruMission4Tracker"):
                    user.add_effect(Effect("IchimaruMission4Tracker", EffectType.SYSTEM, user, 3, lambda eff:"", mag = 1, system = True))
                else:
                    user.get_effect(EffectType.SYSTEM, "IchimaruMission4Tracker").duration = 2
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_13_kilometer_swing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(25, target, DamageType.NORMAL)
                target.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1, print_mag=True), user)
        user.check_on_use()
        user.check_on_harm()

def exe_kamishini_no_yari(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                butou = False
                kilometer = False
                stacks = 0
                if target.has_effect(EffectType.STACK, "Butou Renjin"):
                    stacks += target.get_effect(EffectType.STACK, "Butou Renjin").mag
                    butou = True
                if target.has_effect(EffectType.STACK, "13 Kilometer Swing"):
                    stacks += target.get_effect(EffectType.STACK, "13 Kilometer Swing").mag
                    kilometer = True
                
                user.progress_mission(3, stacks)
                base_damage = 10 * stacks
                if target.has_effect_with_user(EffectType.CONT_UNIQUE, "Kill, Kamishini no Yari", user):
                    base_damage += target.get_effect(EffectType.CONT_UNIQUE, "Kill, Kamishini no Yari").mag * 10
                    target.get_effect(EffectType.CONT_UNIQUE, "Kill, Kamishini no Yari").waiting = True
                user.deal_active_damage(base_damage, target, DamageType.AFFLICTION)
                if target.has_effect_with_user(EffectType.CONT_UNIQUE, "Kill, Kamishini no Yari", user):
                    target.get_effect_with_user(EffectType.CONT_UNIQUE, "Kill, Kamishini no Yari", user).alter_mag(stacks)
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {eff.mag} affliction damage.", mag = base_damage, print_mag=True))
                if butou:
                    target.remove_effect(target.get_effect_with_user(EffectType.STACK, "Butou Renjin", user))
                if kilometer:
                    target.remove_effect(target.get_effect_with_user(EffectType.STACK, "13 Kilometer Swing", user))
                
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
                user.deal_active_damage(15, target, DamageType.NORMAL)
                user.deal_active_damage(10, target, DamageType.AFFLICTION)
        user.check_on_use()
        user.check_on_harm()

def exe_fog_of_london(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
            user.deal_active_damage(5, target, DamageType.AFFLICTION)
            target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 5, lambda eff: "This character will take 5 affliction damage.", mag=5))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda efF: "Jack can use Maria the Ripper."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Fog of London has been replaced by Streets of the Lost.", mag = 21))
    user.check_on_use()
    user.check_on_harm()

def exe_we_are_jack(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(30, target, DamageType.AFFLICTION)
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

                #region Itachi Mission 1 Handling
                if not target.has_effect(EffectType.SYSTEM, "ItachiMission1Handler"):
                    target.add_effect(Effect("ItachiMission1Handler", EffectType.SYSTEM, user, 280000, lambda eff: "", system = True))
                    if not user.source.mission1complete:
                        mission_completed = True
                        for enemy in enemyTeam:
                            if not enemy.has_effect(EffectType.SYSTEM, "ItachiMission1Handler"):
                                mission_completed = False
                        if mission_completed:
                            user.source.mission1complete = True
                            user.source.mission1progress += 1
                    
                #endregion

                user.deal_active_damage(10, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()


def exe_tsukuyomi(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "If this character is aided by an ally, this effect will end."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 6, lambda eff: "This character is stunned."))
                if target.meets_stun_check():

                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_susanoo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=45, print_mag=True))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "Itachi will take 10 affliction damage. If his health falls below 20 or Susano'o's destructible defense is destroyed, Susano'o will end.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 280000, lambda eff: "", mag = 1, system=True))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Amaterasu has been replaced by Totsuka Blade.", mag=11))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Tsukuyomi has been replaced by Yata Mirror.", mag=22))
    user.receive_system_aff_damage(10)
    user.check_on_use()

def exe_crow_genjutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: f"Itachi is invulnerable."))
    user.check_on_use()

def exe_totsuka_blade(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(35, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_yata_mirror(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.get_effect(EffectType.DEST_DEF, "Susano'o").alter_dest_def(20)
    user.receive_system_aff_damage(5)
    user.check_on_use()
#endregion
#region Jeanne Execution
def exe_flag_of_the_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff:f"This character has 10 points of damage reduction.", mag = 10))
                target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 10))
        user.check_on_use()
        user.check_on_help()            

def exe_luminosite(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                user.progress_mission(2, 1)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 4, lambda eff:"This character is invulnerable."))
        user.check_on_use()
        user.check_on_help()

def exe_la_pucelle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff:"La Pucelle - Draw has been replaced by Crimson Holy Maiden.", mag = 31))
    user.check_on_use()

def exe_crimson_holy_maiden(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(15, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff:f"This character will take 15 affliction damage.", mag=15))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 280000, lambda eff:"This character is stunned."))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "This character will take 35 affliction damage.", mag=35))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 280000, lambda eff: "Jeanne is invulnerable."))
        user.receive_eff_damage(35, user.get_effect(EffectType.CONT_AFF_DMG, "Crimson Holy Maiden"), DamageType.AFFLICTION)
        user.check_on_use()
        user.check_on_harm()

def exe_jeanne_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Jeanne is invulnerable."))
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
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
            user.check_on_use()
            user.check_on_harm()
    else:
        def_type = user.check_bypass_effects()

        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 5
                if target.final_can_effect(def_type) and not target.deflecting():
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 7, lambda eff:"This character will take 5 damage.", mag=5))
            
            if user.has_effect(EffectType.SYSTEM, "JiroMission5Tracker"):
                user.get_effect(EffectType.SYSTEM, "JiroMission5Tracker").duration = 7

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
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
            user.check_on_use()
            user.check_on_harm()
    else:
        def_type = user.check_bypass_effects()
        if not user.check_countered(playerTeam, enemyTeam):
            for target in user.current_targets:
                base_damage = 10
                if target.final_can_effect(def_type) and not target.deflecting():
                    user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 7, lambda eff:"This character will take 10 damage.", mag=10))
            
            if user.has_effect(EffectType.SYSTEM, "JiroMission5Tracker"):
                user.get_effect(EffectType.SYSTEM, "JiroMission5Tracker").duration = 7
            
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
                user.deal_active_damage(20, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "This character will take double damage from Raikiri."))
                if target.meets_stun_check():
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
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
                    user.deal_active_damage(20, target, DamageType.PIERCING)
                    if target.check_invuln():
                        user.source.mission3progress += 1
                        target.add_effect(Effect(user.used_ability, EffectType.ISOLATE, user, 2, lambda eff: "This character is isolated."))
            user.check_on_use()
            user.check_on_harm()

#endregion
#region Killua Execution
def exe_lightning_palm(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 20
                if not user.has_effect(EffectType.MARK, "Godspeed"):
                    target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 1, lambda eff:"If this character is damaged, the damager will become immune to stuns for a turn."))
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        if user.has_effect(EffectType.MARK, "Godspeed"):
            for ally in playerTeam:
                ally.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 3, lambda eff: "This character will ignore stun effects."))
        user.check_on_use()
        user.check_on_harm()

def exe_narukami(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 20
                if not user.has_effect(EffectType.MARK, "Godspeed"):
                    target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 1, lambda eff:"If this character is damaged, the damager will ignore counters for a turn."))
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        if user.has_effect(EffectType.MARK, "Godspeed"):
            for ally in playerTeam:
                ally.add_effect(Effect(user.used_ability, EffectType.COUNTER_IMMUNE, user, 3, lambda eff: "This character will ignore counter effects."))
        user.check_on_use()
        user.check_on_harm()

def exe_godspeed(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Lightning Palm and Narukami will activate their beneficial effects automatically."))
        user.add_effect(Effect(user.used_ability, EffectType.AFF_IMMUNE, user, 5, lambda eff: "Killua will ignore affliction damage."))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Godspeed has been replaced by Whirlwind Rush.", mag = 31))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "Killua will deal 5 more damage with all his abilities.", mag = 5))
        user.check_on_use()

def exe_whirlwind_rush(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 35
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 1, lambda eff:"If this character is damaged, the damager will become invulnerable for one turn."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_godspeed_withdrawal(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Killua is invulnerable."))
    user.check_on_use()
#endregion
#region Kuroko Execution

def kuroko_invoke_order(user: "CharacterManager", sequence: int):
    if user.has_effect(EffectType.SYSTEM, "KurokoMission5Tracker"):
        if user.get_effect(EffectType.SYSTEM, "KurokoMission5Tracker").mag == sequence:
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "KurokoMission5Tracker"))
        else:
            user.get_effect(EffectType.SYSTEM, "KurokoMission5Tracker").mag = sequence
            if user.has_effect(EffectType.SYSTEM, "KurokoMission5Counter"):
                user.get_effect(EffectType.SYSTEM, "KurokoMission5Counter").alter_mag(4)
                user.get_effect(EffectType.SYSTEM, "KurokoMission5Counter").duration = 3
                user.get_effect(EffectType.SYSTEM, "KurokoMission5Tracker").duration = 3
            else:
                user.add_effect(Effect("KurokoMission5Counter", EffectType.SYSTEM, user, 2, lambda eff:"", mag = 1, system=True))
            if user.get_effect(EffectType.SYSTEM, "KurokoMission5Counter").mag >= 3:
                user.progress_mission(5, 1)
                user.remove_effect(user.get_effect(EffectType.SYSTEM, "KurokoMission5Tracker"))
                user.remove_effect(user.get_effect(EffectType.SYSTEM, "KurokoMission5Counter"))
    else:
        user.add_effect(Effect("KurokoMission5Tracker", EffectType.SYSTEM, user, 3, lambda eff:"", mag = sequence, system=True))

def exe_teleporting_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        kuroko_invoke_order(user, 1)
        for target in user.current_targets:
            base_damage = 10
            if user.has_effect(EffectType.MARK, "Judgement Throw") and user.can_boost():
                base_damage = 25
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        if user.has_effect(EffectType.MARK, "Needle Pin"):
            user.used_ability.cooldown = 0
        user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Kuroko is invulnerable."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Needle Pin will ignore invulnerability and deal 15 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Judgement Throw will have double effect."))
        user.check_on_use()
        user.check_on_harm()

def exe_needle_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        kuroko_invoke_order(user, 2)
        if user.has_effect(EffectType.MARK, "Teleporting Strike"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                if user.has_effect(EffectType.MARK, "Teleporting Strike") and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.PIERCING)
                target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 3, lambda eff: "This character cannot reduce damage or become invulnerable."))
                if user.has_effect(EffectType.MARK, "Judgement Throw"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        user.progress_mission(2, 1)
                        user.check_on_stun(target)

        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Teleporting Strike will have no cooldown."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Judgement Throw will remove one random energy from its target."))
        user.check_on_use()
        user.check_on_harm()  

def exe_judgement_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        kuroko_invoke_order(user, 3)
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                if user.has_effect(EffectType.MARK, "Needle Pin"):
                    target.source.change_energy_cont(-1)
                    user.progress_mission(3, 1)
                    user.check_on_drain(target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: f"This character will deal {-eff.mag} less damage.", mag = -weaken))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Teleporting Strike will deal 15 more damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Needle Pin will stun its target for one turn."))
        user.check_on_use()
        user.check_on_harm()

def exe_kuroko_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    kuroko_invoke_order(user, 4)
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Kuroko is invulnerable."))
    user.check_on_use()
#endregion
#region Kurome Execution
def exe_mass_animation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 20
        if user.has_effect(EffectType.STACK, "Yatsufusa") and user.can_boost():
            base_damage += (10 * user.get_effect(EffectType.STACK, "Yatsufusa").mag)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_yatsufusa(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_damage = 15
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)

        user.check_on_use()
        user.check_on_harm()

def exe_doping_rampage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Kurome cannot be killed except by the affliction damage from this effect."))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "Kurome will take 30 affliction damage.", mag = 30))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 280000, lambda eff: "Yatsufusa will deal 20 bonus damage.", mag = 220))
    user.check_on_use()

def exe_impossible_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Kurome is invulnerable."))
    user.check_on_use()

#endregion
#region Lambo Execution
def exe_ten_year_bazooka(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.has_effect(EffectType.SYSTEM, "LamboMission1Failure"):
        user.add_effect(Effect("LamboMission1Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
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
            if target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(5, target, DamageType.NORMAL)
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 280000, lambda eff: "This character will take 5 damage.", mag=5))
                harmed = True
            elif target.id == user.id:
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 280000, lambda eff: "This character has 10 points of damage reduction.", mag=10))
                helped = True
        user.check_on_use()
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Lambo cannot use Summon Gyudon."))
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
                user.deal_active_damage(25, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_elettrico_cornata(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(35, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region La Pucelle Execution
def exe_knights_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_magic_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Knight's Sword deals {eff.mag * 20} bonus damage, costs {eff.mag} more random energy, and has its cooldown increased by {eff.mag}.", mag=1, print_mag=True), user)
    user.progress_mission(2, 1)
    user.check_on_use()

def exe_ideal_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect("BYPASS"):
            user.deal_active_damage(40, target, DamageType.NORMAL)
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
            if target.id == user.id:
                if target.helpful_target(user, user.check_bypass_effects()):
                    user.give_healing(20, target)
                helped = True
            elif target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_active_damage(20, target, DamageType.NORMAL)
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
                user.deal_active_damage(40, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_thunder_palace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff:"If this effect expires naturally, Laxus will deal 40 damage to the entire enemy team. If he is damaged by a new ability, this effect will end and the offending character will take damage equal to the damage of the ability they used."))
    user.check_on_use()

def exe_laxus_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Laxus is invulnerable."))
    user.check_on_use()
#endregion
#region Leone Execution
def exe_lionel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Leone can use her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 280000, lambda eff:"Leone will heal 10 health.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 280000, lambda eff: "Leone will heal 10 health when she damages an enemy or uses Instinctual Dodge."))
    user.give_healing(10, user)
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
                user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 5, lambda eff: "Leone will ignore stun effects."))
                user.add_effect(Effect(user.used_ability, EffectType.COUNTER_IMMUNE, user, 5, lambda eff: "Leone will ignore counter effects."))
        user.check_on_use()
        if harmed:
            user.check_on_harm()

def exe_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct") or not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if user.has_effect(EffectType.STUN_IMMUNE, "Beast Instinct") and target.is_countering():
                user.progress_mission(4, 1)
            if target.has_effect(EffectType.MARK, "Beast Instinct"):
                def_type = "BYPASS"
                base_damage = 55
            else:
                def_type = user.check_bypass_effects()
                base_damage = 35
            if target.final_can_effect(def_type):
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()
                

def exe_instinctual_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Leone is invulnerable."))
    user.give_healing(10, user)
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
            if target.source.current_hp < 25:
                user.progress_mission(5, 1)
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
        if not char.has_effect(EffectType.MARK, mark_name) and not char.source.dead:
            return False
    return True

def exe_crosstail_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        if not user.has_effect(EffectType.SYSTEM, "LubbockMission5Failure"):
            user.add_effect(Effect("LubbockMission5Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

        if all_marked(enemyTeam, "Cross-Tail Strike"):
            user.current_targets.clear()
            user.progress_mission(1, 1)
            for enemy in enemyTeam:
                if enemy.final_can_effect("BYPASS"):
                    enemy.full_remove_effect("Cross-Tail Strike", user)
                    user.deal_active_damage(20, enemy, DamageType.PIERCING)
            user.remove_effect(user.get_effect(EffectType.COST_ADJUST, "Cross-Tail Strike"))
        else:
            for target in user.current_targets:
                if not user.has_effect(EffectType.COST_ADJUST, "Cross-Tail Strike"):
                    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "Until Lubbock uses Cross-Tail Strike on a marked enemy, it costs one less weapon energy.", mag = -141))
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.NORMAL)
                    if target.has_effect(EffectType.MARK, "Cross-Tail Strike"):
                        user.remove_effect(user.get_effect(EffectType.COST_ADJUST, "Cross-Tail Strike"))
                    else:
                        target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character has been marked by Cross-Tail Strike."))
            
        user.check_on_use()
        user.check_on_harm()



def exe_wire_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):

        if not user.has_effect(EffectType.SYSTEM, "LubbockMission4Failure"):
            user.add_effect(Effect("LubbockMission4Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

        if all_marked(playerTeam, "Wire Shield"):
            user.current_targets.clear()
            user.progress_mission(2, 1)
            for player in playerTeam:
                if player.helpful_target(user, user.check_bypass_effects()):
                    player.remove_effect(player.get_effect(EffectType.MARK, "Wire Shield"))
                    player.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "This character is invulnerable."))
            user.remove_effect(user.get_effect(EffectType.COST_ADJUST, "Wire Shield"))
        else:
            for target in user.current_targets:
                if not user.has_effect(EffectType.COST_ADJUST, "Wire Shield"):
                    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "Until Lubbock uses Wire Shield on a marked ally, it costs one less weapon energy.", mag = -241))
       
                if target.helpful_target(user, user.check_bypass_effects()):
                    if target.has_effect(EffectType.DEST_DEF, "Wire Shield"):
                        target.get_effect(EffectType.DEST_DEF, "Wire Shield").alter_dest_def(15)
                    else:
                        target.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=15, print_mag=True))
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
                user.deal_active_damage(30, target, DamageType.PIERCING)
                if user.has_effect(EffectType.MARK, "Wire Shield"):
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will receive 15 affliction damage.", mag=15))
                if target.has_effect(EffectType.MARK, "Cross-Tail Strike"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_defensive_netting(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Lubbock is invulnerable."))
    user.check_on_use()
#endregion
#region Lucy Execution
def exe_aquarius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    help_duration = 2
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id == user.id:
                if target.helpful_target(user, user.check_bypass_effects()):
                    if user.has_effect(EffectType.MARK, "Gemini"):
                        help_duration = 4
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, help_duration, lambda eff: "This character has 10 points of damage reduction.", mag=10))
                helped = True
            elif target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.NORMAL)
                    if user.has_effect(EffectType.MARK, "Gemini"):
                        target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 10 damage.", mag=15))
                harmed = True
        user.check_on_use()
        if not user.has_effect(EffectType.CONSECUTIVE_TRACKER, "LucyMission4Tracker"):
            user.add_effect(Effect("LucyMission4Tracker", EffectType.CONSECUTIVE_TRACKER, user, 280000, lambda eff:"", mag = 1, system=True))
            user.add_effect(Effect("LucyMission4Tracker", EffectType.CONSECUTIVE_BUFFER, user, help_duration, lambda eff: "", system = True))
        elif user.get_effect(EffectType.CONSECUTIVE_TRACKER, "LucyMission4Tracker").mag == 3:
            user.progress_mission(4, 1)
            user.remove_effect(user.get_effect(EffectType.CONSECUTIVE_TRACKER, "LucyMission4Tracker"))
        else:
            user.get_effect(EffectType.CONSECUTIVE_TRACKER, "LucyMission4Tracker").alter_mag(1)
            if user.has_effect(EffectType.CONSECUTIVE_BUFFER, "LucyMission4Tracker"):
                user.remove_effect(user.get_effect(EffectType.CONSECUTIVE_BUFFER, "LucyMission4Tracker"))
            user.add_effect(Effect("LucyMission4Tracker", EffectType.CONSECUTIVE_BUFFER, user, help_duration, lambda eff: "", system=True))
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
                user.deal_active_damage(20, target, DamageType.NORMAL)
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
                user.deal_active_damage(20, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 20 damage.", mag=20))
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Midoriya Execution
def exe_smash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(45, target, DamageType.NORMAL)
                user.receive_system_aff_damage(20)
        user.check_on_use()
        user.check_on_harm()

def exe_air_force_gloves(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.COOLDOWN_MOD, user, 2, lambda eff: "This character's cooldowns have been increased by 1.", mag = 1))
                if not target.has_effect(EffectType.SYSTEM, "MidoriyaMission5Handler"):
                    target.add_effect(Effect("MidoriyaMission5Handler", EffectType.SYSTEM, user, 280000, lambda eff: "", system = True))
                    if not user.source.mission5complete:
                        mission_completed = True
                        for enemy in enemyTeam:
                            if not enemy.has_effect(EffectType.SYSTEM, "MidoriyaMission5Handler"):
                                mission_completed = False
                        if mission_completed:
                            user.source.mission5complete = True
                            user.progress_mission(5, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_shoot_style(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
        user.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 2, lambda eff: "Midoriya will counter the first harmful ability used on him.", invisible=True))
        user.check_on_use()
        user.check_on_harm()

def exe_enhanced_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Midoriya is invulnerable."))
    user.check_on_use()
#endregion
#region Minato Execution
def exe_flying_raijin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_active_damage(25, target, DamageType.PIERCING)
                if target.has_effect(EffectType.MARK, "Marked Kunai"):

                    #region  Minato Mission 4 Check

                    if not user.has_effect(EffectType.CONSECUTIVE_TRACKER, "MinatoMission4Tracker"):
                        user.add_effect(Effect("MinatoMission4Tracker", EffectType.CONSECUTIVE_TRACKER, user, 280000, lambda eff:"", mag = 1, system=True))
                        user.add_effect(Effect("MinatoMission4Tracker", EffectType.CONSECUTIVE_BUFFER, user, 2, lambda eff: "", system = True))
                    elif user.get_effect(EffectType.CONSECUTIVE_TRACKER, "MinatoMission4Tracker").mag == 2:
                        user.progress_mission(4, 1)
                        user.remove_effect(user.get_effect(EffectType.CONSECUTIVE_TRACKER, "MinatoMission4Tracker"))
                    else:
                        user.get_effect(EffectType.CONSECUTIVE_TRACKER, "MinatoMission4Tracker").alter_mag(1)
                        user.add_effect(Effect("MinatoMission4Tracker", EffectType.CONSECUTIVE_BUFFER, user, 2, lambda eff: "", system=True))

                    #endregion

                    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Minato is invulnerable."))
                    target.full_remove_effect("Marked Kunai", user)
                    user.used_ability.cooldown = 0
        user.check_on_use()
        user.check_on_harm()

def exe_marked_kunai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(10, target, DamageType.PIERCING)
                if not target.has_effect(EffectType.MARK, "Marked Kunai"):
                    target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "This character has been marked."))
                    #region Minato Mission 3 Check
                    user.source.mission3progress += 1
                    #endregion
        user.check_on_use()
        user.check_on_harm()

def exe_partial_shiki_fuujin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):

                target.add_effect(Effect(user.used_ability, EffectType.COOLDOWN_MOD, user, 280000, lambda eff: "This character's cooldowns have been increased by 1.", mag = 1))
                target.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: "This character's ability costs have been increased by one random.", mag = 51))

        #region Minato Mission 1 Check

        if user.source.hp < 20:
            user.source.mission1progress += 1

        #endregion

        user.check_on_use()
        user.check_on_harm()
        user.source.hp = 0
        user.death_check(user)

def exe_minato_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Minato is invulnerable."))
    user.check_on_use()
#endregion
#region Mine Execution
def exe_roman_artillery_pumpkin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Pumpkin Scouter"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            if target.final_can_effect(def_type):
                base_damage = 25
                if user.source.hp < 120 and user.can_boost():
                    base_damage = 35
                if user.has_effect(EffectType.MARK, "Pumpkin Scouter") and user.can_boost():
                    base_damage += 5
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_cutdown_shot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        user.add_effect(Effect("MineMission4Tracker", EffectType.SYSTEM, user, 2, lambda eff:"", mag=0, system=True))
        if user.has_effect(EffectType.MARK, "Pumpkin Scouter"):
            def_type = "BYPASS"
        else:
            def_type = user.check_bypass_effects()
        for target in user.current_targets:
            
            if target.final_can_effect(def_type):
                base_damage = 25
                if user.source.hp < 50 and user.can_boost():
                    base_damage = 50
                if user.has_effect(EffectType.MARK, "Pumpkin Scouter") and user.can_boost():
                    base_damage += 5
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                if user.source.hp < 100:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_pumpkin_scouter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Mine's abilities will ignore invulnerabilty and deal 5 additional damage."))
    user.check_on_use()

def exe_closerange_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mine is invulnerable."))
#endregion
#region Mirai Execution
def exe_blood_suppression_removal(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Mirai's abilities cause their target to receive 10 affliction damage for 2 turns."))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Blood Suppression Removal has been replaced by Blood Bullet.", mag = 11))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 5, lambda eff: "Mirai will take 10 affliction damage.", mag=10))
    user.receive_eff_damage(10, user.get_effect(EffectType.MARK, "Blood Suppression Removal"), DamageType.AFFLICTION)
    user.check_on_use()

def exe_blood_sword_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(30, target, DamageType.NORMAL)
                if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
                    user.deal_eff_damage(10, target, user.get_effect(EffectType.MARK, "Blood Suppression Removal"), DamageType.AFFLICTION)
                    target.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
        user.check_on_use()
        user.check_on_harm()

def exe_blood_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 20, print_mag=True))
    user.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: f"This character has {eff.mag} points of damage reduction.", mag = 20))
    if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
        user.receive_eff_damage(10, user.get_effect(EffectType.MARK, "Blood Suppression Removal"), DamageType.AFFLICTION)
        user.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
    user.check_on_use()
    

def exe_mirai_deflect(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mirai is invulnerable."))
    user.check_on_use()

def exe_blood_bullet(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(10, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
                if user.has_effect(EffectType.MARK, "Blood Suppression Removal"):
                    user.deal_eff_damage(10, target, user.get_effect(EffectType.MARK, "Blood Suppression Removal"), DamageType.AFFLICTION)
                    target.add_effect(Effect(Ability("mirai1"), EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag = 10))
        user.check_on_use()
        user.check_on_harm()

#endregion
#region Mirio Execution
def exe_permeation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that uses a new harmful effect on Mirio will be marked for Phantom Menace.", invisible=True))
    user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Mirio will ignore all harmful effects.", invisible=True))
    user.check_on_use()

def exe_phantom_menace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    used = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 20
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
        used = True
    
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Phantom Menace") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
    
    

    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS") and target.has_effect(EffectType.MARK, "Phantom Menace"):
                user.deal_active_damage(15, target, DamageType.PIERCING)
        mission3tracker = True
        for enemy in enemyTeam:
            if not enemy in user.current_targets:
                mission3tracker = False
        if mission3tracker:
            user.progress_mission(3, 1)
        used = True
    if used:
        user.check_on_use()
        user.check_on_harm()

def exe_protect_ally(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "Any enemy that uses a new harmful effect on this character will be marked for Phantom Menace.",invisible=True))
            target.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "This character will ignore all harmful effects.",invisible=True))
        user.check_on_use()
        user.check_on_help()
    

def exe_mirio_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Mirio is invulnerable."))
    user.check_on_use()
#endregion
#region Misaka Execution

def misaka_form_changed(user: "CharacterManager"):
    return (user.has_effect(EffectType.MARK, "Ultra Railgun") or user.has_effect(EffectType.CONT_DEST_DEF, "Iron Colossus") or user.has_effect(EffectType.PROF_SWAP, "Level-6 Shift"))

def misaka_reset_swaps(user: "CharacterManager"):
    new_effects = [eff for eff in user.source.current_effects if not (eff.eff_type == EffectType.ABILITY_SWAP and eff.user == user)]
    user.source.current_effects = new_effects

def exe_railgun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    damage = 20

    if user.has_effect(EffectType.STACK, "Overcharge"):
        charges = user.get_effect(EffectType.STACK, "Overcharge").mag
        damage += (charges * 5)

    if user.has_effect(EffectType.MARK, "Level-6 Shift"):
        damage -= 10

    if user.has_effect(EffectType.MARK, "Ultra Railgun"):
        damage = damage * 2
    
    for target in user.current_targets:
        if target.final_can_effect("BYPASS"):
            user.deal_active_damage(damage, target, DamageType.NORMAL)
            if user.has_effect(EffectType.MARK, "Level-6 Shift"):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: f"This character will take {eff.mag} damage.", mag=damage))
            if target.check_invuln():
                user.progress_mission(4, 1)
    if not misaka_form_changed(user):
        user.add_effect(Effect(Ability("misakaalt2"), EffectType.ABILITY_SWAP, user, 280000, lambda eff:"Railgun has been replaced by Ultra Railgun.", mag = 22))

    user.check_on_use()
    user.check_on_harm()

def exe_iron_sand(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    if not user.check_countered(playerTeam, enemyTeam):
        defense_value = 20

        if user.has_effect(EffectType.STACK, "Overcharge"):
            charges = user.get_effect(EffectType.STACK, "Overcharge").mag
            defense_value += (charges * 5)

        if user.has_effect(EffectType.MARK, "Level-6 Shift"):
            defense_value -= 10

        if user.has_effect(EffectType.MARK, "Ultra Railgun"):
            defense_value = defense_value * 2

        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.apply_dest_def_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=defense_value))
            if user.has_effect(EffectType.MARK, "Level-6 Shift"):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: f"This character will gain {eff.mag} points of destructible defense.", mag = defense_value))
        if not misaka_form_changed(user):
            user.add_effect(Effect(Ability("misakaalt1"), EffectType.ABILITY_SWAP, user, 280000, lambda eff:"Iron Sand has been replaced by Iron Colossus.", mag = 11))
     
        user.check_on_use()
        user.check_on_help()

def exe_overcharge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff:f"Iron Sand and Railgun will apply {eff.mag * 5} more destructible defense/damage.", mag = 1, print_mag=True), user)
    user.progress_mission(4, 1)
    if user.has_effect(EffectType.MARK, "Level-6 Shift"):
        user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: "Misaka will gain one stack of Overcharge."))
    if not misaka_form_changed(user):
            user.add_effect(Effect(Ability("misakaalt3"), EffectType.ABILITY_SWAP, user, 280000, lambda eff:"Overcharge has been replaced by Level-6 Shift", mag = 33))
    user.check_on_use()

def exe_electric_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Misaka is invulnerable."))
    user.check_on_use()

def exe_iron_colossus(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.CONT_DEST_DEF, user, 280000, lambda eff: f"Misaka will gain {eff.mag} points of destructible defense.", mag = 10))
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 280000, lambda eff: "Railgun will target all enemies.", mag = 21))
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 280000, lambda eff: "Iron Sand will target all enemies.", mag = 12))
    misaka_reset_swaps(user)
    user.check_on_use()


def exe_ultra_railgun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect("BYPASS"):
            user.deal_active_damage(50, target, DamageType.NORMAL)
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: f"Railgun and Iron Sand have double effect."))
    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: f"Railgun will cost one additional random energy.", mag = 251))
    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 280000, lambda eff: f"Iron Sand will cost one additional random energy.", mag = 151))
    misaka_reset_swaps(user)
    user.check_on_use()
    user.check_on_harm()


def exe_levelsix_shift(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 280000, lambda eff: f"Misaka is no longer controllable, and will use a random ability on a random valid target each turn.", mag = 1))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: "Railgun and Iron Sand apply 10 less damage/destructible defense."))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Railgun, Iron Sand, and Overcharge now last for 3 turns."))
    misaka_reset_swaps(user)
    user.check_on_use()
    user.check_on_harm()
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
#region Naruha Execution
def exe_bunny_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 15 damage.", mag=15))
                user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Naruha is using Bunny Assault. This effect will end if she is stunned. If this effect expires normally, Naruha will gain 20 points of destructible defense."))
        user.check_on_use()
        user.check_on_harm()

def exe_rampage_suit(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: f"Naruha is in her paper suit, enabling her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"Naruha has {eff.mag} points of destructible defense.", mag = 100, print_mag=True))
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_rabbit_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit") and user.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").mag > 0:
        user.get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").alter_dest_def(25)
        user.progress_mission(3, 25)
    user.check_on_use()

def exe_enraged_blow(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 40
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "Naruha will take double damage."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
                
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Natsu Execution
def exe_fire_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(25, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()

def exe_fire_dragons_iron_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                if target.has_effect(EffectType.CONT_AFF_DMG, "Fire Dragon's Roar") or target.has_effect(EffectType.CONT_UNIQUE, "Fire Dragon's Sword Horn"):
                    user.deal_active_damage(10, target, DamageType.AFFLICTION)
                    user.progress_mission(2, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_fire_dragons_sword_horn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(40, target, DamageType.NORMAL)
                if target.has_effect(EffectType.CONT_UNIQUE, "Fire Dragon's Sword Horn"):
                    target.get_effect(EffectType.CONT_UNIQUE, "Fire Dragon's Sword Horn").alter_mag(1)
                else:
                    sword_horn = Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {eff.mag * 5} affliction damage.", mag=1)
                    sword_horn.waiting = False
                    target.add_effect(sword_horn)
        user.check_on_use()
        user.check_on_harm()

def exe_natsu_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Natsu is invulnerable."))
    user.check_on_use()
#endregion
#region Neji Execution
def exe_neji_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(2, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 15, lambda eff: f"This character will take {2 * (2 ** eff.mag)} damage.", mag=1))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 15, lambda eff: "Chakra Point Strike can target this character."))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 15, lambda eff: "Neji is using Eight Trigrams - 128 Palms. This effect will end if Neji is stunned."))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 15, lambda eff: "Eight Trigrams - 128 Palms has been replaced by Chakra Point Strike.", mag=11))
        user.check_on_use()
        user.check_on_harm()

def exe_neji_mountain_crusher(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 25
                if target.check_invuln() and user.can_boost():
                    base_damage = 40
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_selfless_genius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
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
#region Nemurin Execution



def exe_nemurin_nap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Nemurin has entered the dream world, allowing the use of her abilities."))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: "Every turn Nemurin doesn't act, Nemurin gains one stack of Nemurin Nap. If Nemurin takes new, non-absorbed damage, she loses one stack.", mag = 1, print_mag=True))
    user.check_on_use()


def exe_nemurin_beam(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(25, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: "This character will deal 10 less damage.", mag = -10))
        user.add_effect(Effect("NemurinActivityMarker", EffectType.SYSTEM, user, 1, lambda eff: "", system=True))
        user.check_on_use()
        user.check_on_harm()

def exe_dream_manipulation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_HEAL, user, 5, lambda eff: "This character will heal 10 health.", mag = 10))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "This character will deal 10 more damage.", mag = 10))
                user.give_healing(10, target)
        user.add_effect(Effect("NemurinActivityMarker", EffectType.SYSTEM, user, 1, lambda eff: "", system=True))
        user.check_on_use()
        user.check_on_help()

def exe_dream_sovereignty(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Nemurin is invulnerable."))
    user.check_on_use()
#endregion
#region Orihime Execution
def one(user):
    return user.has_effect(EffectType.MARK, "Tsubaki!")

def two(user):
    return user.has_effect(EffectType.MARK, "Ayame! Shun'o!")

def three(user):
    return user.has_effect(EffectType.MARK, "Lily! Hinagiku! Baigon!")
   

def rename_i_reject(user: "CharacterManager"):
    def one():
        return user.has_effect(EffectType.MARK, "Tsubaki!")

    def two():
        return user.has_effect(EffectType.MARK, "Ayame! Shun'o!")
    
    def three():
        return user.has_effect(EffectType.MARK, "Lily! Hinagiku! Baigon!")
    
    if one() and two() and three():
        user.source.current_abilities[3].name = "Dance of the Heavenly Six"
        user.source.current_abilities[3].desc = "All allies heal 25 health and become invulnerable for one turn. All enemies take 25 damage."
    elif one() and two():
        user.source.current_abilities[3].name = "Three-God Empowering Shield"
        user.source.current_abilities[3].desc = "Target ally deals 5 more damage with all abilities, and will heal 10 health each time they damage an enemy with a new ability."
    elif two() and three():
        user.source.current_abilities[3].name = "Five-God Inviolate Shield"
        user.source.current_abilities[3].desc = "All allies gain 30 points of destructible defense, and will heal 10 health per turn. This effect ends on all allies once any of the destructible defense is fully depleted."
    elif one() and three():
        user.source.current_abilities[3].name = "Four-God Resisting Shield"
        user.source.current_abilities[3].desc = "Target ally gains 35 points of destructible defense. While active, any enemy that uses a new harmful ability on them will take 15 damage. This damage will not trigger on damage that breaks the destructible defense."
    elif three():
        user.source.current_abilities[3].name = "Three-God Linking Shield"
        user.source.current_abilities[3].desc = "Target ally gains 30 points of destructible defense for one turn."
    elif two():
        user.source.current_abilities[3].name = "Two-God Returning Shield"
        user.source.current_abilities[3].desc = "Target ally heals 20 health for two turns."
    elif one():
        user.source.current_abilities[3].name = "Lone-God Slicing Shield"
        user.source.current_abilities[3].desc = "All allies gain 30 points of destructible defense, and will heal 10 health per turn. This effect ends on all allies once any of the destructible defense is fully depleted."
    else:
        user.source.current_abilities[3].name = "I Reject!"
        user.source.current_abilities[3].desc = "Orihime activates her Shun Shun Rikka, with a composite effect depending on the flowers she has activated. This will end any active Shun Shun Rikka effect originating from a name she is currently calling out."

def exe_tsubaki(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared an offensive effect."))
    rename_i_reject(user)
    user.progress_mission(1,1)
    user.check_on_use()

def exe_ayame_shuno(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared a healing effect."))
    rename_i_reject(user)
    user.progress_mission(1, 1)
    user.check_on_use()

def exe_lily_hinagiku_baigon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Orihime has prepared a defensive effect."))
    rename_i_reject(user)
    user.progress_mission(1, 1)
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
        user.progress_mission(2, 1)
        for ally in playerTeam:
            if one():
                ally.full_remove_effect("Four-God Resisting Shield", user)
                ally.full_remove_effect("Three-God Empowering Shield", user)
            if two():
                ally.full_remove_effect("Two-God Returning Shield", user)
                ally.full_remove_effect("Three-God Empowering Shield", user)
                ally.full_remove_effect("Five-God Inviolate Shield", user)
            if three():
                ally.full_remove_effect("Three-God Linking Shield", user)
                ally.full_remove_effect("Four-God Resisting Shield", user)
                ally.full_remove_effect("Five-God Inviolate Shield", user)
        for enemy in enemyTeam:
            if one():
                enemy.full_remove_effect("Lone-God Slicing Shield", user)
        if one() and two() and three():
            user.progress_mission(5, 1)
        for target in user.current_targets:
            if one() and two() and three():

                if target.id != user.id:
                    if target.final_can_effect(user.check_bypass_effects()):
                        user.deal_active_damage(25, target, DamageType.NORMAL)
                    harmed = True
                if target.id == user.id:
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
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 30, print_mag=True))
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.CONT_HEAL, user, 280000, lambda eff: f"This character will heal 10 health.", mag=10))
                    user.give_healing(10, target)
                    target.add_effect(Effect(Ability("shunshunrikka2"), EffectType.UNIQUE, user, 280000, lambda eff: "This effect will end on all characters if this destructible defense is destroyed."))
                helped = True
            elif one() and three():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka3"), EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 35, print_mag=True))
                    target.add_effect(Effect(Ability("shunshunrikka3"), EffectType.UNIQUE, user, 280000, lambda eff: "While the destructible defense holds, this character will deal 15 damage to any enemy that uses a new harmful ability on them."))
                helped = True
            elif three():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka5"), EffectType.DEST_DEF, user, 2, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag = 30, print_mag=True))
                helped = True
            elif two():
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(Ability("shunshunrikka6"), EffectType.CONT_HEAL, user, 3, lambda eff: f"This character will heal 20 health.", mag=20))
                    user.give_healing(20, target)
                helped = True
            elif one():
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.NORMAL)
                    target.add_effect(Effect(Ability("shunshunrikka7"), EffectType.ALL_DR, user, 280000, lambda eff: f"This character will take 5 more damage from non-affliction abilities.", mag=-5))
                harmed = True
        user.check_on_use()
        if helped:
            user.check_on_help()
        if harmed:
            user.check_on_harm()

#endregion
#region Ripple Execution
def exe_perfect_accuracy(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.progress_mission(1, 1)
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "Shuriken Throw will always target this enemy, ignore their invulnerability, and deals 5 additional damage to them."))
        user.check_on_use()
        user.check_on_harm()

def exe_shuriken_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Perfect Accuracy") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
    if len(user.current_targets) == 3:
        user.progress_mission(2, 1)
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
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_countless_stars(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                base_damage = 5
                user.deal_active_damage(base_damage, target, DamageType.PIERCING)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_PIERCE_DMG, user, 5, lambda eff: "This character will take 5 piercing damage.", mag=5))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "Shuriken Throw deals 10 more damage.", mag = 210))
        user.check_on_use()
        user.check_on_harm()

def exe_ripple_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ripple is invulnerable."))
    user.check_on_use()
#endregion
#region Rukia Execution

def dance_step(user:"CharacterManager", step: int):
    if step == 1:
        if not user.has_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"):
            user.add_effect(Effect("RukiaMission3FirstStep", EffectType.SYSTEM, user, 280000, lambda eff: "", system = True))
        elif user.has_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"))
    elif step == 2:
        if user.has_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"))
            user.add_effect(Effect("RukiaMission3SecondStep", EffectType.SYSTEM, user, 280000, lambda eff: "", system = True))
        elif user.has_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"))
    elif step == 3:
        if user.has_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"))
        elif user.has_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"))
            user.progress_mission(3, 1)
    elif step == 4:
        if user.has_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3FirstStep"))
        if user.has_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"):
            user.remove_effect(user.get_effect(EffectType.SYSTEM, "RukiaMission3SecondStep"))

def exe_first_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        dance_step(user, 1)
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 25
                if target.check_invuln():
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
                        user.check_on_stun(target)
                        user.progress_mission(1, 1)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_second_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        dance_step(user, 2)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target == user.primary_target:
                    base_damage = 15
                else:
                    base_damage = 10
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_third_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    dance_step(user, 3)
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff:"The next time Rukia is countered, the countering enemy will take 30 damage and be stunned for one turn.", invisible=True))
    user.check_on_use()

def exe_rukia_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    dance_step(user, 4)
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff:"Rukia is invulnerable."))
    user.check_on_use()
#endregion
#region Ruler Execution
def exe_in_the_name_of_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 6, lambda eff: "This character is stunned."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "In The Name Of Ruler! will end if Ruler takes new damage."))
        user.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 5, lambda eff: "Ruler is stunned."))
        if user.has_effect(EffectType.DEST_DEF, "Minion - Minael and Yunael") and user.has_effect(EffectType.COUNTER_RECEIVE, "Minion - Tama"):
            user.progress_mission(4, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_minael_yunael(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        harmed = False
        for target in user.current_targets:
            if target.id != user.id:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.NORMAL)
                harmed = True
            else:
                if user.has_effect(EffectType.DEST_DEF, "Minion - Minael and Yunael"):
                    user.get_effect(EffectType.DEST_DEF, "Minion - Minael and Yunael").alter_dest_def(10)
                else:
                    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=10, print_mag=True))
        user.check_on_use()
        if harmed:
            user.check_on_harm()
                

def exe_tama(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for ally in playerTeam:
            ally.full_remove_effect("Minion - Tama", user)
        for target in user.current_targets:
            target.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 280000, lambda eff: "The first harmful ability used on this character will be countered and take 20 piercing damage.", invisible=True))
        user.check_on_use()

def exe_swim_swim(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ruler is invulnerable."))
    user.check_on_use()
#endregion
#region Ryohei Execution
def exe_maximum_cannon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
        if not user.has_effect(EffectType.MARK, "Vongola Headgear"):   
            if user.has_effect(EffectType.STACK, "Kangaryu"):
                user.full_remove_effect("Kangaryu", user)
            if user.has_effect(EffectType.STACK, "Maximum Cannon"):
                user.full_remove_effect("Maximum Cannon", user)
        user.check_on_use()
        user.check_on_harm()

def exe_kangaryu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                user.give_healing(15, target)
        if not user.has_effect(EffectType.MARK, "Vongola Headgear"):  
            if user.has_effect(EffectType.STACK, "Kangaryu"):
                user.full_remove_effect("Kangaryu", user)
            if user.has_effect(EffectType.STACK, "Maximum Cannon"):
                user.full_remove_effect("Maximum Cannon", user)
        user.check_on_use()
        user.check_on_harm()

def exe_vongola_headgear(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "Ryohei will ignore all random cost increases to Maximum Cannon and Kangaryu, and using them will not consume stacks of To The Extreme!"))
    user.check_on_use()

def exe_to_the_extreme(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 280000, lambda eff: "For every 30 unabsorbed damage Ryohei takes, he gains one stack of To The Extreme!"))
    user.check_on_use()
#endregion
#region Saber Execution
def exe_excalibur(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            if target.is_countering():
                user.progress_mission(2, 1)
            user.deal_active_damage(50, target, DamageType.PIERCING)
    user.check_on_use()
    user.check_on_harm()

def exe_wind_blade_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
            user.deal_active_damage(10, target, DamageType.NORMAL)
            target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 10 damage.", mag = 10))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Saber is using Wind Blade Combat."))
        user.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 5, lambda eff: "Saber cannot be stunned."))
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
                target.add_effect(Effect("Avalon", EffectType.MARK, user, 280000, lambda eff: "This character cannot be targeted with Avalon.", system = True))
        user.check_on_use()
        user.check_on_help()


def exe_saber_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda efF: "Saber is invulnerable."))
    user.check_on_use()
#endregion
#region Saitama Execution
def exe_one_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if not user.has_effect(EffectType.SYSTEM, "SaitamaMission4Tracker"):
            user.add_effect(Effect("SaitamaMission4Tracker", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(75, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_consecutive_normal_punches(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if not user.has_effect(EffectType.SYSTEM, "SaitamaMission4Failure"):
            user.add_effect(Effect("SaitamaMission4Failure", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
        
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if not target.has_effect(EffectType.SYSTEM, "SaitamaMission2Tracker"):
                    target.add_effect(Effect("SaitamaMission2Tracker", EffectType.SYSTEM, user, 1, lambda eff: "", mag = 0, system=True))
                else:
                    target.get_effect(EffectType.SYSTEM, "SaitamaMission2Tracker").duration = 1
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 15 damage.", mag = 15))
        user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Saitama is using Consecutive Normal Punches."))
        user.check_on_use()
        user.check_on_harm()

def exe_serious_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if not user.has_effect(EffectType.SYSTEM, "SaitamaMission4Failure"):
            user.add_effect(Effect("SaitamaMission4Failure", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
        
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 35 damage.", mag = 35, invisible=True))
        user.add_effect(Effect(user.used_ability, EffectType.IGNORE, user, 2, lambda eff: "Saitama is ignoring all hostile effects.", invisible=True))
        user.check_on_use()
        user.check_on_harm()

def exe_sideways_jumps(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.has_effect(EffectType.SYSTEM, "SaitamaMission4Failure"):
            user.add_effect(Effect("SaitamaMission4Failure", EffectType.SYSTEM, user, 280000, lambda eff: "", system=True))
        
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Saitama is invulnerable."))
    user.check_on_use()
#endregion
#region Seiryu Execution
def exe_body_mod_arm_gun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_raging_koro(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.PIERCING)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff:"This character will take 20 damage.", mag = 20))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Raging Koro has been replaced by Insatiable Justice.", mag = 22))
        user.check_on_use()
        user.check_on_harm()

def exe_berserker_howl(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 4, lambda eff:"This character will deal 10 less damage.", mag = -10))
        user.check_on_use()
        user.check_on_harm()

def exe_koro_defense(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Seryu is invulnerable."))
    user.check_on_use()

def exe_self_destruct(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for target in user.current_targets:
        if target.final_can_effect(user.check_bypass_effects()):
            user.deal_active_damage(30, target, DamageType.PIERCING)
            
    user.check_on_use()
    user.check_on_harm()
    user.source.hp = 0
    user.death_check(user)
    

def exe_insatiable_justice(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and target.source.hp < 60:
                target.source.hp = 0
                target.death_check(user)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Sheele Execution
def exe_extase(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        if target.final_can_effect("REGBYPASS"):
            base_damage = 35
            if target.get_dest_def_total() > 0:
                base_damage += 15
            if target.has_effect(EffectType.MARK, "Trump Card - Blinding Light"):
                base_damage += 10
            user.deal_active_damage(base_damage, target, DamageType.NORMAL)
    user.check_on_use()
    user.check_on_harm()

def exe_savior_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 25
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.cancel_control_effects()
        user.check_on_use()
        user.check_on_harm()


def exe_blinding_light(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                target.add_effect(Effect(user.used_ability, EffectType.DEF_NEGATE, user, 4, lambda eff: "This character cannot reduce damage or become invulnerable."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "This character will take 10 more damage from Extase - Bisector of Creation."))
                if target.meets_stun_check():
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_extase_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Sheele is invulnerable."))
    user.check_on_use()
#endregion
#region Shigaraki Execution
def exe_decaying_touch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target.has_effect(EffectType.CONT_UNIQUE, "Decaying Touch"):
                    target.get_effect(EffectType.CONT_UNIQUE, "Decaying Touch").alter_mag(1)
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {5 * (2 ** (eff.mag - 1))} affliction damage.", mag = 1, print_mag=True))
                    user.deal_active_damage(5, target, DamageType.AFFLICTION)
                if not target.has_effect(EffectType.CONSECUTIVE_TRACKER, "ShigarakiMission5Tracker"):
                        target.add_effect(Effect("ShigarakiMission5Tracker", EffectType.CONSECUTIVE_TRACKER, user, 280000, lambda eff:"", mag = 1, system=True))
                        target.add_effect(Effect("ShigarakiMission5Tracker", EffectType.CONSECUTIVE_BUFFER, user, 2, lambda eff: "", system = True))
                elif target.get_effect(EffectType.CONSECUTIVE_TRACKER, "ShigarakiMission5Tracker").mag == 2:
                    user.progress_mission(4, 1)
                    target.remove_effect(user.get_effect(EffectType.CONSECUTIVE_TRACKER, "ShigarakiMission5Tracker"))
                else:
                    target.get_effect(EffectType.CONSECUTIVE_TRACKER, "ShigarakiMission5Tracker").alter_mag(1)
                    target.add_effect(Effect("ShigarakiMission5Tracker", EffectType.CONSECUTIVE_BUFFER, user, 2, lambda eff: "", system=True))
        user.check_on_use()
        user.check_on_harm()


def exe_decaying_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target.has_effect(EffectType.CONT_UNIQUE, "Decaying Touch"):
                    target.get_effect(EffectType.CONT_UNIQUE, "Decaying Touch").alter_mag(1)
                else:
                    target.add_effect(Effect(Ability("shigaraki1"), EffectType.CONT_UNIQUE, user, 280000, lambda eff: f"This character will take {5 * (2 ** (eff.mag - 1))} affliction damage.", mag = 1, print_mag=True))
                    user.deal_active_damage(5, target, DamageType.AFFLICTION)
        user.check_on_use()
        user.check_on_harm()

def exe_destroy_what_you_love(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
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
#region Shikamaru Execution
def exe_shadow_bind_jutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Shadow Pin") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
            user.source.mission5progress += 1

    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Shadow Pin"):
                def_type = "BYPASS"
            else:
                def_type = user.check_bypass_effects()
            if target.final_can_effect(def_type):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 4, lambda eff: "This character is stunned."))
                if target.meets_stun_check:
                    user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_neck_bind(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for enemy in enemyTeam:
        if enemy.has_effect(EffectType.MARK, "Shadow Pin") and not (enemy in user.current_targets):
            user.current_targets.append(enemy)
            user.source.mission5progress += 1

    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.has_effect(EffectType.MARK, "Shadow Pin"):
                def_type = "BYPASS"
            else:
                def_type = user.check_bypass_effects()
            if target.final_can_effect(def_type) and not target.deflecting():
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 3, lambda eff: "This character will take 15 affliction damage.", mag = 15))
                user.deal_active_damage(15, target, DamageType.AFFLICTION)
        user.check_on_use()
        user.check_on_harm()

def exe_shadow_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "This character cannot target enemies."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Shadow Neck Bind and Shadow Bind Jutsu will affect this character in addition to their normal targets."))
                user.source.mission4progress += 1
        user.check_on_use()
        user.check_on_harm()

def exe_hide(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Shikamaru is invulnerable."))
    user.check_on_use()
#endregion
#region Shokuhou Execution

def mental_out_ability_switch(target: "CharacterManager") -> int:
    if target.source.name == "naruto":
        return 0
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
    if target.source.name == "kurome":
        return 0
    if target.source.name == "touka":
        return 2
    if target.source.name == "killua":
        return 0
    if target.source.name == "sheele":
        return 0
    if target.source.name == "byakuya":
        return 0
    if target.source.name == "frankenstein":
        return 0
    if target.source.name == "gilgamesh":
        return 1
    if target.source.name == "jeanne":
        return 0
    if target.source.name == "accelerator":
        return 0
    if target.source.name == "chelsea":
        return 2
    
def exe_mental_out(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):

                if not target.has_effect(EffectType.SYSTEM, "MisakiMission5Tracker"):
                    target.add_effect(Effect("MisakiMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
                else:
                    mission_complete = True
                    for enemy in enemyTeam:
                        if not enemy.has_effect(EffectType.SYSTEM, "MisakiMission5Tracker"):
                            mission_complete = False
                    if mission_complete:
                        user.add_effect(Effect("MisakiMission5Success", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))

                base_duration = 4
                if user.has_effect(EffectType.MARK, "Exterior"):
                    base_duration = 6
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, base_duration, lambda eff: "Shokuhou is controlling this character."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, base_duration, lambda eff: "This character is stunned."))
                user.add_effect(Effect(user.used_ability, EffectType.MARK, user, base_duration - 1, lambda eff: "Shokuhou is controlling a character, and can command them to act for her."))
                stolen_slot = mental_out_ability_switch(target)
                user.get_effect_with_user(EffectType.MARK, "Mental Out", user).alter_mag(stolen_slot)
                if stolen_slot > 3:
                    stolen_ability = target.source.alt_abilities[stolen_slot - 4]
                else:
                    stolen_ability = target.source.main_abilities[stolen_slot]
                user.source.alt_abilities[0] = Ability(stolen_ability.db_name)
                try:
                    user.alt_ability_sprites[0].surface = user.scene.get_scaled_surface(user.scene.scene_manager.surfaces[stolen_ability.db_name])
                    user.alt_ability_sprites[0].ability = user.source.alt_abilities[0]
                except AttributeError:
                    pass
                user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, base_duration - 1, lambda eff: f"Mental Out has been replaced by {stolen_ability.name}.", mag = 11))
                if target.meets_stun_check():
                    user.check_on_stun(target)

def exe_exterior(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.receive_system_aff_damage(40)
    if not user.has_effect(EffectType.SYSTEM, "MisakiMission4Tracker"):
        user.add_effect(Effect("MisakiMission4Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", system = True))
    else:
        user.remove_effect(user.get_effect(EffectType.SYSTEM, "MisakiMission4Tracker"))
        user.add_effect(Effect("MisakiMission4Success", EffectType.SYSTEM, user, 280000, lambda eff:"", system = True))
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 9, lambda eff: "Mental Out lasts 1 more turn."))
    user.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 9, lambda eff: "Mental Out costs 1 less mental energy.", mag = -131))
    user.check_on_use()

def exe_ally_mobilization(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.STUN_IMMUNE, user, 4, lambda eff: "This character will ignore stuns."))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 15 points of damage reduction.", mag=15))
        user.check_on_use()
        user.check_on_help()

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
    controlled_character.toggle_allegiance()
    stolen_ability.execute(controlled_character, playerTeam, enemyTeam)
    controlled_character.toggle_allegiance()
#endregion
#region Snow White Execution
def exe_enhanced_strength(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if not user.has_effect(EffectType.SYSTEM, "Enhanced Strength"):
            user.add_effect(Effect("SnowWhiteMission4Failure", EffectType.SYSTEM, user, 280000, lambda eff:"", system=True))
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(15, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_hear_distress(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = True
    for target in user.current_targets:
        if target.id == user.id:
            if target.helpful_target(user, "BYPASS"):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: "This character has 25 points of damage reduction.", mag=25, invisible=True))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 2, lambda eff: "This character will gain one random energy if they are affected by a new harmful ability.", invisible=True))
            helped = True
        elif target.id != user.id:
            if target.final_can_effect("BYPASS"):
                target.add_effect(Effect(user.used_ability, EffectType.COUNTER_USE, user, 2, lambda eff: "The first harmful ability used by this character will be countered, and they will lose one random energy.", invisible=True))
            harmed = True
    user.check_on_use()
    if harmed:
        user.check_on_harm()
    if helped:
        user.check_on_help()

def exe_rabbits_foot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam): 
        for target in user.current_targets:
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 2, lambda eff: "If this character dies, they will instead be set to 35 health.", invisible=True))
        user.check_on_use()
        user.check_on_help()

def exe_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Snow White is invulnerable."))
    user.check_on_use()
#endregion
#region SwimSwim Execution
def exe_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(25, target, DamageType.NORMAL)
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
#region Tatsumaki Execution
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
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: f"This character will take {eff.mag} damage.", mag=base_damage))
        user.check_on_use()
        user.check_on_harm()

def exe_arrest_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.STACK, "Gather Power"):
            stacks = user.get_effect(EffectType.STACK, "Gather Power").mag
        else:
            stacks = 0
        for target in user.current_targets:
            if target.helpful_target(user, user.check_bypass_effects()):
                base_dr = 10 + (5 * stacks)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 2, lambda eff: f"This character has {base_dr} points of damage reduction", mag = base_dr, invisible=True))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Arrest Assault has been replaced by Return Assault.", mag = 21, invisible=True))
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 3, lambda eff: f"Arrest Assault has received {eff.mag} abilities.", mag = 0, invisible=True, print_mag=True))
        user.check_on_use()
        user.check_on_help()

def exe_gather_power(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Rubble Barrage will deal {eff.mag * 5} more damage, Arrest Assault grants {eff.mag * 5} more damage reduction, and Gather Power has {eff.mag} less cooldown.", mag = 1, print_mag=True), user)
    user.progress_mission(1, 1)
    user.source.change_energy_cont(1)
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
        if stacks >= 3:
            user.progress_mission(4, 1)
        for target in user.current_targets:
            base_damage = 0
            if user.can_boost():
                base_damage += (stacks * 10)
            user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Todoroki Execution
def exe_half_cold(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 2, lambda eff: "This character will deal 10 less damage.", mag=-10))
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Todoroki's ability costs are increased by {eff.mag} random energy until he uses Flashfreeze Heatwave.", mag = 1, print_mag=True), user)
        user.check_on_use()
        user.check_on_harm()

def exe_half_hot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(30, target, DamageType.NORMAL)
        for ally in playerTeam:
            if user.has_effect(EffectType.STACK, "Quirk - Half-Hot"):
                base_ally_damage = 10 + (user.get_effect(EffectType.STACK, "Quirk - Half-Hot").mag * 10)
            else:
                base_ally_damage = 10
            if ally != user and ally.final_can_effect(user.check_bypass_effects()) and not ally.deflecting():
                user.deal_active_damage(base_ally_damage, ally, DamageType.NORMAL)
        user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Quirk - Half-Hot will deal {eff.mag * 10} more damage to Todoroki's allies until he uses Flashfreeze Heatwave.", mag = 1, print_mag=True), user)
        user.check_on_use()
        user.check_on_harm()

def exe_flashfreeze_heatwave(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    hot_stacks = 0
    cold_stacks = 0
    if not user.check_countered(playerTeam, enemyTeam):
        user.add_effect(Effect("TodorokiMission1Tracker", EffectType.SYSTEM, user, 2, lambda eff:"", mag=0, system=True))
        if user.has_effect(EffectType.STACK, "Quirk - Half-Hot"):
            hot_stacks = user.get_effect(EffectType.STACK, "Quirk - Half-Hot").mag
        if user.has_effect(EffectType.STACK, "Quirk - Half-Cold"):
            cold_stacks = user.get_effect(EffectType.STACK, "Quirk - Half-Cold").mag

        if hot_stacks and cold_stacks:
            user.progress_mission(5, 1)

        primary_damage = 10
        splash_damage = 5
        if user.can_boost():
            primary_damage += (10 * hot_stacks) + (10 * cold_stacks)
            splash_damage += (10 * hot_stacks)
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                if target == user.primary_target:
                    user.deal_active_damage(primary_damage, target, DamageType.NORMAL)
                else:
                    user.deal_active_damage(splash_damage, target, DamageType.NORMAL)
        user.full_remove_effect("Quirk - Half-Hot", user)
        user.full_remove_effect("Quirk - Half-Cold", user)
        user.check_on_use()
        user.check_on_harm()

def exe_ice_rampart(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Todoroki is invulnerable."))
    user.check_on_use()
#endregion
#region Tatsumi Execution
def exe_killing_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                base_damage = 25
                hurt = False
                stunned = False
                if target.source.hp < 100:
                    base_damage += 10
                    hurt = True
                if target.is_stunned():
                    base_damage += 10
                    stunned = True
                if hurt and stunned:
                    user.progress_mission(2, 1)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()

def exe_incursio(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 7, lambda eff: f"Tatsumi has {eff.mag} points of destructible defense.", mag=25, print_mag=True))
    user.add_effect(Effect(user.used_ability, EffectType.PROF_SWAP, user, 7, lambda eff: "", mag = 1, system=True))
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
                base_damage = 25 * multiplier
                if multiplier >= 4:
                    user.progress_mission(1, 1)
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "This character will take double damage from Neuntote."))
        user.check_on_use()

def exe_invisibility(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Tatsumi is invulnerable."))
    user.check_on_use()
#endregion
#region Toga Execution
def exe_thirsting_knife(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(10, target, DamageType.NORMAL)
                target.apply_stack_effect(Effect(Ability("toga3"), EffectType.STACK, user, 280000, lambda eff: f"Toga has drawn blood from this character {eff.mag} time(s).", mag = 2, print_mag=True), user)
                user.progress_mission(2, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_vacuum_syringe(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(10, target, DamageType.AFFLICTION)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 5, lambda eff: "This character will take 10 affliction damage.", mag=10))
                target.apply_stack_effect(Effect(Ability("toga3"), EffectType.STACK, user, 280000, lambda eff: f"Toga has drawn blood from this character {eff.mag} time(s).", mag = 1, print_mag=True), user)
                user.progress_mission(2, 1)
        user.check_on_use()
        user.check_on_harm()

def exe_transform(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    for target in user.current_targets:
        blood_stacks = target.get_effect(EffectType.STACK, "Quirk - Transform").mag
        target.remove_effect(target.get_effect(EffectType.STACK, "Quirk - Transform"))
        name = target.source.name
        user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, (1 + (2 * blood_stacks)), lambda eff: "Toga has transformed."))
        # user.add_effect(Effect("TogaTransformTarget", EffectType.SYSTEM, user, (1 + (2 * blood_stacks)), lambda eff: name, system=True))
        mission_complete = True
        
        if not user.has_effect(EffectType.SYSTEM, name):
            user.add_effect(Effect(name, EffectType.SYSTEM, user, 280000, lambda eff: name, system = True))
        
        for enemy in enemyTeam:
            if not user.has_effect(EffectType.SYSTEM, enemy.source.name):
                mission_complete = False

        if mission_complete:
            user.add_effect(Effect("TogaMission3Ready", EffectType.SYSTEM, user, 280000, lambda eff: "", system = True))

        user.toga_transform(target.source.name)
    user.check_on_use()

def exe_toga_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Toga is invulnerable."))
    user.check_on_use()
#endregion
#region Touka Execution
def exe_draw_stance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Nukiashi"):
        invis = True
    else:
        invis = False
    user.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 3, lambda eff: "The first harmful ability used on this character will be countered, and the countered enemy will receive 15 damage.", invisible=invis))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 3, lambda eff: "Draw Stance has been replaced by Raikiri.", mag=11, invisible=invis))
    user.check_on_use()

def exe_touka_raikiri(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(40, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()

def exe_nukiashi(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Draw Stance and Raiou are invisible.", invisible=True))
    user.check_on_use()

def exe_raiou(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        if user.has_effect(EffectType.MARK, "Nukiashi"):
            invis = True
        else:
            invis = False
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.COOLDOWN_MOD, user, 2, lambda eff:"This character's cooldowns have been increased by 2.", mag=2, invisible=invis))
        user.check_on_use()
        user.check_on_harm()

def exe_lightning_speed_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Touka is invulnerable."))
    user.check_on_use()
#endregion
#region Tsunayoshi Execution
def exe_xburner(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        user.add_effect(Effect("TsunaMission4Tracker", EffectType.SYSTEM, user, 2, lambda eff:"", mag=0, system=True))
        for target in user.current_targets:
            if target == user.primary_target:
                if target.final_can_effect(user.check_bypass_effects()):
                    user.deal_active_damage(25, target, DamageType.NORMAL)
            else:
                if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                    user.deal_active_damage(15, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_zero_point_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.COUNTER_RECEIVE, user, 2, lambda eff: "The first harmful ability used on Tsuna will be countered and the countered enemy will be stunned. X-Burner will deal 10 more damage for two turns after this effect is triggered.", invisible=True))
    user.check_on_use()

def exe_burning_axle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(35, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 1, lambda eff: ""))
        user.check_on_use()
        user.check_on_harm()

def exe_flare_burst(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Tsuna is invulnerable."))
    user.check_on_use()
#endregion
#region Uraraka Execution
def exe_zero_gravity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    helped = False
    harmed = False
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.id == user.id:
                if target.helpful_target(user, user.check_bypass_effects()):
                    target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 5, lambda eff: "This character will ignore invulnerability."))
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 6, lambda eff: "This character has 10 points of damage reduction.", mag = 10))
                helped = True
            if target.id != user.id: 
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
                user.deal_active_damage(15, target, DamageType.NORMAL)
                if target.has_effect(EffectType.DEF_NEGATE, "Quirk - Zero Gravity"):
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                    if target.meets_stun_check():
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
                user.deal_active_damage(20, target, DamageType.NORMAL)
                if target.has_effect(EffectType.DEF_NEGATE, "Quirk - Zero Gravity"):
                    target.source.change_energy_cont(-1)

                    user.progress_mission(3, 1)
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
#region Wendy Execution
def exe_troia(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        base_healing = 40
        multiplier = 0
        for eff in user.source.current_effects:
            if eff.name == "Troia":
                multiplier += 1
        
        if multiplier == 0:
            if not user.has_effect(EffectType.SYSTEM, "WendyMission5Tracker"):
                user.add_effect(Effect("WendyMission5Tracker", EffectType.SYSTEM, user, 280000, lambda eff:"", mag = 1, system=True))
            else:
                user.get_effect(EffectType.SYSTEM, "WendyMission5Tracker").alter_mag(1)
            if user.get_effect(EffectType.SYSTEM, "WendyMission5Tracker").mag >= 5:
                user.progress_mission(5, 1)
                user.source.mission5complete = True

        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 7, lambda eff: "Troia will have half effect."))
        
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
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "Targeting into Shredding Wedding from outside, or outside from within, will cause the targeter to take 20 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 6, lambda eff: "Targeting into Shredding Wedding from outside, or outside from within, will cause the targeter to take 20 piercing damage."))
        user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Shredding Wedding has been replaced by Piercing Winds.", mag=21))
        user.check_on_use()
        user.check_on_harm()


def exe_sky_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
   if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(20, target, DamageType.NORMAL)
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
                user.deal_active_damage(25, target, DamageType.PIERCING)
        user.check_on_use()
        user.check_on_harm()
#endregion
#region Yamamoto Execution
def exe_shinotsuku_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_active_damage(30, target, DamageType.NORMAL)
                if target.has_effect(EffectType.ALL_BOOST, "Shinotsuku Ame"):
                    target.get_effect(EffectType.ALL_BOOST, "Shinotsuku Ame").duration = 6
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 6, lambda eff: "This character will deal 10 less damage.", mag=-10))
        user.apply_stack_effect(Effect(Ability("yamamoto3"), EffectType.STACK, user, 280000, lambda eff: f"Yamamoto has {eff.mag} stack(s) of Asari Ugetsu.", mag = 1, print_mag=True), user)
        if user.get_effect(EffectType.STACK, "Asari Ugetsu").mag >= 10:
            user.progress_mission(3, 1)
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
                beccatas = [eff for eff in target.source.current_effects if eff.name == "Beccata di Rondine"]
                if len(beccatas) >= 2:
                    user.progress_mission(4, 1)
                base_damage = 20
                if target.check_damage_drain() >= 10 and user.can_boost():
                    base_damage = 30
                user.deal_active_damage(base_damage, target, DamageType.NORMAL)
        user.check_on_use()
        user.check_on_harm()

def exe_beccata_di_rondine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered(playerTeam, enemyTeam):
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_active_damage(5, target, DamageType.NORMAL)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 5, lambda eff: "This character will take 5 damage.", mag=5))
                target.add_effect(Effect(user.used_ability, EffectType.ALL_BOOST, user, 5, lambda eff: "This character will deal 5 less damage.", mag=-5))
        if user.has_effect(EffectType.CONT_USE, "Beccata di Rondine"):
            user.get_effect(EffectType.CONT_USE, "Beccata di Rondine").duration = 5
        else:
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 5, lambda eff: "Yamamoto is using Beccata di Rondine. This effect will end if he is stunned."))
        user.check_on_use()
        user.check_on_harm()
#endregion

#endregion

ability_info_db = {
    "naruto1": [
        "Rasengan",
        "Naruto deals 25 damage to target enemy and stuns them for one turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_rasengan, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "naruto2": [
        "Shadow Clones",
        "For three turns, Naruto will ignore counter and reflect abilities. During this time, he gains 10 points of damage reduction and Rasengan is replaced by Odama Rasengan.",
        [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF"), exe_shadow_clones, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "naruto3": [
        "Sage Mode",
        "For two turns, Naruto will ignore stun effects. During this time, any enemy that drains energy from him will take 20 affliction damage and Rasengan is replaced by Senpou - Rasenrengan. If activated while Shadow Clones is active, Naruto will become invulnerable for one turn, and Odama Rasengan will be replaced by Rasenshuriken.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_sage_mode, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "naruto4": [
        "Substitution", "Naruto becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_substitution, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "narutoalt1": [
        "Odama Rasengan",
        "Naruto deals 35 damage to one enemy and 25 damage to the others. The primary target will be stunned for one turn.",
        [0, 1, 0, 0, 1, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_odama_rasengan, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "narutoalt2": [
        "Senpou - Rasenrengan",
        "Naruto deals 50 damage to one enemy and stuns them for 2 turns.",
        [0, 1, 1, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_rasenrengan, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "narutoalt3": [
        "Rasenshuriken",
        "Naruto deals 35 damage to all enemies and stuns them for one turn.", [0, 1, 1, 0, 1, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_rasenshuriken, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "accelerator1": ["Vector Scatter", "Accelerator deals 20 damage to target enemy and stuns them for one turn.", [0, 0, 1, 0, 0, 1], Target.SINGLE, default_target("HOSTILE"), exe_vector_scatter, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STUN]],
    "accelerator2": ["Plasma Bomb", "Accelerator deals 15 damage to all enemies for 3 turns. During this time, only stun effects can be applied to Accelerator.", [0, 0, 2, 0, 1, 5], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_plasma_bomb, [AbilityType.ACTION, AbilityType.ENERGY]],
    "accelerator3": ["Vector Reflection", "For one turn, Accelerator will ignore all harmful effects. Any enemy that targets him with a new harmful ability will be targeted by Vector Scatter. This ability is invisible.", [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("SELF"), exe_vector_reflection, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "accelerator4": ["Vector Immunity", "Accelerator becomes invulnerable for one turn.", [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_vector_immunity, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "aizen1": [
        "Shatter, Kyoka Suigetsu",
        "Target enemy has their ability costs increased by one random and are marked by Kyoka Suigetsu for 1 turn. If the enemy is marked with Black Coffin, "
        +
        "all their currently active cooldowns are increased by 2. If the enemy is marked by Overwhelming Power, Aizen's abilities will cost one less random energy on the following turn.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_shatter, [AbilityType.INSTANT, AbilityType.MENTAL]
    ],
    "aizen2": [
        "Overwhelming Power",
        "Aizen deals 25 damage to target enemy and marks them with Overwhelming Power for one turn. If the enemy is marked with Black Coffin,"
        +
        " that enemy will be unable to reduce damage or become invulnerable for 2 turns. If that enemy is marked with Shatter, Kyoka Suigetsu, Overwhelming Power deals 20 bonus damage to them.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_overwhelming_power, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "aizen3": [
        "Black Coffin",
        "Target enemy is stunned and marked with Black Coffin for 1 turn. If the enemy is marked with Overwhelming Power, they will also take 20 damage. If the"
        +
        " enemy is marked with Shatter, Kyoka Suigetsu, then Black Coffin also affects their allies.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_black_coffin, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "aizen4": [
        "Effortless Guard", "Aizen becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_effortless_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "akame1": [
        "Red-Eyed Killer",
        "Akame marks an enemy for 1 turn. During this time, she can use One-Cut Killing on the target.",
        [0, 0, 1, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_red_eyed_killer, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC]
    ],
    "akame2": [
        "One Cut Killing",
        "Akame deals 100 affliction damage to one enemy for two turns. Can only be used on a target marked with Red-Eyed Killer.",
        [0, 0, 0, 2, 1, 1], Target.SINGLE, target_one_cut_killing, exe_one_cut_killing, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "akame3": [
        "Little War Horn",
        "For two turns, Akame can use One Cut Killing on any target, regardless of their effects.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF"), exe_little_war_horn, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "akame4": [
        "Rapid Deflection", "Akame becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rapid_deflection, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "astolfo1": [
        "Casseur de Logistille",
        "Astolfo targets himself or another ally for one turn. During this time, if they are targeted by a hostile Energy or Mental ability, that ability"
        +
        " will be countered and the user will be stunned and isolated for 1 turn. This ability is invisible until triggered.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HELPFUL"), exe_casseur, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "astolfo2": [
        "Trap of Argalia - Down With A Touch!",
        "Astolfo deals 20 piercing damage to target enemy. For one turn, they cannot have their damage boosted above its default value. If the target's damage is currently boosted, Trap of Argalia will permanently "
        + "deal 5 additional damage.", [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_trap, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "astolfo3": [
        "La Black Luna",
        "Astolfo removes one hostile effect from every member of his team, and for 2 turns, no enemy can have their damage boosted above its default value. For every hostile effect removed, Trap of Argalia will permanently"
        + " deal 5 additional damage.", [0, 1, 0, 0, 1, 2], Target.ALL_TARGET,
        default_target("ALL"), exe_luna, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "astolfo4": [
        "Akhilleus Kosmos", "Astolfo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kosmos, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "byakuya1": ["Scatter, Senbonzakura", "Byakuya deals 25 piercing damage to target enemy or gives target ally 25 points of destructible defense for one turn. During Bankai - Senbonzakura Kageyoshi, this ability will target all enemies or allies.",
                 [0,0,0,1,1,0], Target.SINGLE, default_target("ALL"), exe_scatter, [AbilityType.ENERGY, AbilityType.INSTANT]
    ],
    "byakuya2": ["Bakudou #61 - Six-Rod Light Restraint", "Byakuya stuns target enemy for one turn. After being used, this ability is replaced by Hadou #2 - Byakurai", [0, 1, 0, 0, 0, 2], Target.SINGLE, default_target("HOSTILE"), exe_sixrod],
    "byakuya3": ["Bankai - Senbonzakura Kageyoshi", "For the next 2 turns, Scatter, Senbonzakura will affect all enemies or allies when it is used and this ability will be replaced by White Imperial Sword.", 
                [0, 0, 0, 1, 1, 3], Target.SINGLE, default_target("SELF"), exe_senbonzakura_kageyoshi, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "byakuya4": ["Bakudou #81 - Danku", "Byakuya becomes invulnerable for one turn.", [0,0,0,0,1,4], Target.SINGLE, default_target("SELF"), exe_danku, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "byakuyaalt1": ["Hadou #2 - Byakurai", "Byakuya deals 25 piercing damage to one enemy.", [0,1,0,0,0,0], Target.SINGLE, default_target("HOSTILE"), exe_byakurai],
    "byakuyaalt2": ["White Imperial Sword", "Byakuya deals 30 piercing damage to one enemy. This damage is increased by 5 for every 10 health Byakuya is missing.", [0,1,0,1,0,1], Target.SINGLE, default_target("HOSTILE"), exe_imperial_sword],
    "cmary1": [
        "Quickdraw - Pistol",
        "Calamity Mary deals 15 damage to target enemy. This ability will become Quickdraw - Rifle after being used.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_pistol, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "cmary2": [
        "Hidden Mine",
        "Traps one enemy for two turns. During this time, if that enemy used a new ability, they will take 20 piercing damage and this effect will end.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_mine, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "cmary3": [
        "Grenade Toss",
        "Calamity Mary deals 20 damage to all enemy targets. This ability deals 20 more damage to enemies affected by Hidden Mine.",
        [0, 0, 0, 1, 1, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_grenade_toss, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "cmary4": [
        "Rifle Guard", "Calamity Mary becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rifle_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "cmaryalt1": [
        "Quickdraw - Rifle",
        "Calamity Mary deals 15 damage to target enemy for 2 turns. This ability will become Quickdraw - Sniper after it ends.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE", lockout=(EffectType.CONT_USE, "Quickdraw - Rifle")), exe_rifle, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "cmaryalt2": [
        "Quickdraw - Sniper",
        "Calamity Mary deals 55 piercing damage to one enemy and becomes invulnerable for one turn.",
        [0, 0, 0, 2, 1, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_sniper, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "chachamaru1": [
        "Target Lock",
        "Chachamaru marks a single target for Orbital Satellite Cannon.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", protection=(EffectType.MARK, "Target Lock")), exe_target_lock, [AbilityType.INSTANT, AbilityType.STRATEGIC]
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
        default_target("HOSTILE"), exe_active_combat_mode, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "chachamaru4": [
        "Take Flight", "Chachamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_take_flight, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "chelsea1": ["Mortal Wound", "Target enemy takes 15 affliction damage each turn until they die. During this time, they deal 5 less non-affliction damage. This ability deals triple damage if used on an enemy affected by Those Who Fight In The Shadows, and cannot be used on an enemy already affected by it.",
        [0, 0, 1, 0, 1, 0], Target.SINGLE, default_target("HOSTILE", protection=(EffectType.CONT_AFF_DMG, "Mortal Wound")), exe_mortal_wound, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]],
    "chelsea2": ["Those Who Fight In The Shadows", "For one turn, the first enemy to use a helpful ability on target enemy will be countered and stunned for two turns. During this time, Mortal Wound will deal triple damage to them. This effect is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE, default_target("HOSTILE"), exe_fight_in_shadows, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "chelsea3": ["Emergency Smoke", "All allies gain 10 points of destructible defense for one turn, and any enemy with a helpful counter effect active on them will take 15 affliction damage. This ability cannot be countered.", [0, 0, 0, 0, 1, 1], Target.ALL_TARGET, default_target("ALL"), exe_chelsea_smoke, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "chelsea4": ["Gaia Foundation Evasion", "Chelsea becomes invulnerable for one turn.", [0,0,0,0,1,4], Target.SINGLE, default_target("SELF"), exe_gaia_evasion, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "chrome1": [
        "You Are Needed",
        "Chrome accepts Mukuro's offer to bond their souls, enabling the user of her abilities. If Chrome ends a turn below 80 health, she transforms into Rokudou Mukuro.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", protection=(EffectType.MARK, "You Are Needed")), exe_you_are_needed, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "chrome2": [
        "Illusory Breakdown",
        "Chrome targets one enemy and gains 20 points of destructible defense for one turn. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 25 damage to the targeted enemy and stun them for one turn.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed"), exe_illusory_breakdown, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.UNIQUE, AbilityType.STUN]
    ],
    "chrome3": [
        "Mental Immolation",
        "Chrome targets one enemy and gains 15 points of destructible defense. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 20 damage to the targeted enemy and remove one random energy from them.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed"), exe_mental_immolation, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.UNIQUE]
    ],
    "chrome4": [
        "Mental Substitution",
        "Chrome becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="You Are Needed"), exe_mental_substitution, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "chromealt1": [
        "Trident Combat",
        "Mukuro deals 25 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_trident_combat, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "chromealt2": [
        "Illusory World Destruction",
        "Mukuro gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        + "he will deal 25 damage to all enemies and stun them for one turn.",
        [0, 0, 1, 0, 2, 2], Target.SINGLE,
        default_target("SELF"), exe_illusory_world_destruction, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.UNIQUE, AbilityType.STUN]
    ],
    "chromealt3": [
        "Mental Annihilation",
        "Mukuro targets one enemy and gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        +
        "he will deal 35 piercing damage to the targeted enemy. This damage ignores invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_mental_annihilation, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.UNIQUE]
    ],
    "chromealt4": [
        "Trident Deflection", "Mukuro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_trident_deflection, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "chu1": [
        "Relentless Assault",
        "Chu deals 15 damage to one enemy for three turns. If that enemy has less"
        +
        " than 15 points of damage reduction, this damage is considered piercing.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_relentless_assault, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "chu2": [
        "Flashing Deflection",
        "Chu gains 15 points of damage reduction for 3 turns. If he would be affected by a move that"
        +
        " deals less than 15 points of damage, he will fully ignore that move instead.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_flashing_deflection, [AbilityType.ACTION, AbilityType.PHYSICAL, AbilityType.STRATEGIC]
    ],
    "chu3": [
        "Gae Bolg",
        "Chu removes all destructible defense from target enemy, then deals 40 piercing damage"
        + " to them. This ability ignores invulnerability.",
        [2, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_gae_bolg, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "chu4": [
        "Chu Block", "Chu becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_chu_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "cranberry1": [
        "Illusory Disorientation",
        "For 1 turns, one enemy has their ability costs increased by 1 random and this ability is replaced by Merciless Finish.",
        [0, 1, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_illusory_disorientation, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC]
    ],
    "cranberry2": [
        "Fortissimo",
        "Cranberry deals 25 damage to all enemies, ignoring invulnerability. This ability cannot be ignored and invulnerable or ignoring enemies take double damage from it.",
        [0, 2, 0, 0, 0, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS"), exe_fortissimo, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "cranberry3": [
        "Mental Radar",
        "For 2 turns, Cranberry's team will ignore counter effects.",
        [0, 0, 1, 0, 1, 4], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_mental_radar, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC]
    ],
    "cranberry4": [
        "Cranberry Block", "Cranberry becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_cranberry_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "cranberryalt1": [
        "Merciless Finish",
        "Cranberry stuns target enemy for 2 turns, and deals 15 affliction damage to them each turn. Only usable on a target currently affected by Illusory Disorientation.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_merciless_finish, [AbilityType.ACTION, AbilityType.PHYSICAL, AbilityType.AFFLICTION, AbilityType.STUN]
    ],
    "erza1": [
        "Clear Heart Clothing",
        "Until Erza requips another armor set, she cannot be stunned and Clear Heart Clothing is replaced by Titania's Rampage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_clear_heart_clothing, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "erza2": [
        "Heaven's Wheel Armor",
        "Until Erza requips another armor set, she will ignore all affliction damage and Heaven's Wheel Armor is replaced by Circle Blade.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_heavens_wheel_armor, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "erza3": [
        "Nakagami's Armor",
        "For the next two turns, Erza gains 1 additional random energy per turn and Nakagami's Armor is replaced by Nakagami's Starlight.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_nakagamis_armor, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "erza4": [
        "Adamantine Armor",
        "Until Erza requips another armor set, she gains 15 damage reduction and Adamantine Armor is replaced by Adamantine Barrier.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF"), exe_adamantine_armor, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "erzaalt1": [
        "Titania's Rampage",
        "Until Erza is killed or requips another armor set, she deals 15 piercing damage to a random enemy. Each turn that this ability"
        +
        " remains active, it deals 5 more damage. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        target_titanias_rampage, exe_titanias_rampage, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "erzaalt2": [
        "Circle Blade",
        "Erza deals 20 damage to one enemy. On the following turn, all enemies take 15 damage, ignoring invulnerability.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_circle_blade, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "erzaalt3": [
        "Nakagami's Starlight",
        "Erza deals 35 damage to one enemy and removes 1 random energy from them.",
        [0, 1, 0, 1, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_nakagamis_starlight, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "erzaalt4": [
        "Adamantine Barrier",
        "Both of Erza's allies become invulnerable for one turn.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_adamantine_barrier, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STRATEGIC]
    ],
    "esdeath1": [
        "Demon's Extract",
        "Esdeath calls forth the power of her Teigu, enabling the user of her abilities for 5 turns. During this time, this ability changes to Mahapadma, "
        + "and Esdeath cannot be countered.", [0, 1, 0, 0, 0,
                                               4], Target.SINGLE,
        default_target("SELF"), exe_demons_extract, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "esdeath2": [
        "Frozen Castle",
        "For the next two turns, no enemy can target any of Esdeath's allies. Esdeath's allies cannot target Esdeath or enemies affected by Frozen Castle. During this time, "
        + "Weiss Schnabel will affect all enemies.", [0, 2, 0, 0, 0,
                                                      7], Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Demon's Extract"), exe_frozen_castle, [AbilityType.ACTION, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "esdeath3": [
        "Weiss Schnabel",
        "Deals 10 damage to target enemy for 3 turns. While active, Weiss Schnabel costs one fewer special energy and deals 15 piercing damage to target enemy.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", prep_req="Demon's Extract"), exe_weiss_schnabel, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "esdeath4": [
        "Esdeath Guard",
        "Esdeath becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_esdeath_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "esdeathalt1": [
        "Mahapadma",
        "Esdeath stuns every living character except for her for 2 turns. At the end of those turns, Esdeath is stunned for 2 turns.",
        [0, 2, 0, 0, 1, 8], Target.ALL_TARGET,
        default_target("ALL"), exe_mahapadma, [AbilityType.INSTANT, AbilityType.STUN, AbilityType.STRATEGIC]
    ],
    "frankenstein1": ["Bridal Smash", "Frankenstein deals 20 damage to target enemy.", [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_bridal_smash, [AbilityType.INSTANT, AbilityType.PHYSICAL]],
    "frankenstein2": ["Bridal Chest", "Frankenstein deals 20 damage to all enemies. During the following two turns, she will deal 20 damage to a random enemy.", [1, 1, 0, 0, 0, 3],
                      Target.MULTI_ENEMY, default_target("HOSTILE"), exe_bridal_chest, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]],
    "frankenstein3": ["Blasted Tree", "Frankenstein self-destructs, dealing her remaining health in piercing damage to target enemy. This ability cannot be countered or reflected, cannot be used while Frankenstein is at full health, and will kill her upon use.",
                      [0, 1, 0, 0, 2, 0], Target.SINGLE, target_blasted_tree, exe_blasted_tree, [AbilityType.INSTANT, AbilityType.ENERGY]],
    "frankenstein4": ["Galvanism", "For 2 turns, Frankenstein ignores Special damage and instead heals for that amount. Whenever Frankenstein is healed this way, she deals 10 additional damage with all her abilities on the following turn. This effect is invisible.",
                      [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_galvanism, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "frenda2": [
        "Close Combat Bombs",
        "Frenda hurls a handful of bombs at an enemy, permanently marking them with a stack of Close Combat Bombs. If Detonate is used, "
        +
        "the marked enemy will take 15 damage per stack of Close Combat Bombs.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_close_combat_bombs, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "frenda1": [
        "Doll Trap",
        "Frenda traps an ally or herself, permanently marking them with a Doll Trap. During this time, if any enemy damages the marked ally, all stacks of Doll Trap on that ally are transferred to"
        +
        " the damaging enemy. If Detonate is used, characters marked with Doll Trap receive 20 damage per stack of Doll Trap on them. Doll Trap is invisible until transferred.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_doll_trap, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "frenda3": [
        "Detonate",
        "Frenda consumes all her stacks of Close Combat Bombs and Doll Trap from all characters. This ability ignores invulnerability.",
        [0, 0, 0, 0, 2, 0], Target.ALL_TARGET, target_detonate, exe_detonate, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "frenda4": [
        "Frenda Dodge", "Frenda becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_frenda_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "gajeel1": [
        "Iron Dragon's Roar", "Gajeel deals 35 piercing damage to one enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_iron_dragon_roar, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "gajeel2": [
        "Iron Dragon's Club", "Gajeel deals 20 piercing damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_iron_dragon_club, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "gajeel3": [
        "Iron Shadow Dragon",
        "If Gajeel is targeted with a new harmful ability, he will ignore all further hostile effects that turn. This changes Gajeel's abilities to their special versions.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_iron_shadow_dragon, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "gajeel4": [
        "Gajeel Block", "Gajeel becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gajeel_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "gajeelalt1": [
        "Iron Shadow Dragon's Roar",
        "Gajeel deals 15 damage to all enemies, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS"), exe_iron_shadow_dragon_roar, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "gajeelalt2": [
        "Iron Shadow Dragon's Club",
        "Gajeel deals 20 damage to one enemy, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_iron_shadow_dragon_club, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "gajeelalt3": [
        "Blacksteel Gajeel",
        "Gajeel permanently gains 15 damage reduction. This changes Gajeel's abilities back to their physical versions.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_blacksteel_gajeel, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "gilgamesh1": ["Gate of Babylon", "If used on Gilgamesh, adds one stack of Gate of Babylon. If used on an enemy, deals 10 damage to that enemy plus 15 additional damage for every stack of Gate of Babylon on Gilgamesh. Removes all stacks of Gate of Babylon on use.",
                    [0, 0, 0, 0, 0, 0], Target.SINGLE, target_gate_of_babylon, exe_gate_of_babylon, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]],
    "gilgamesh2": ["Enkidu, Chains of Heaven", "If target enemy uses a harmful ability on the following turn, that ability is countered and the countered enemy is stunned for one turn. During this time, any active abilities or effects caused by that character do not deal damage or healing.",
                    [0,0,0,1,0,3], Target.SINGLE, default_target("HOSTILE"), exe_enkidu, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "gilgamesh3": ["Enuma Elish", "Deals 40 damage to one enemy and stuns their Weapon abilities for one turn.",
                    [0, 0, 0, 2, 0, 3], Target.SINGLE, default_target("HOSTILE"), exe_enuma_elish, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]],
    "gilgamesh4": ["Gate of Babylon - Interception", "Gilgamesh becomes invulnerable for one turn.",
                    [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_intercept, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "gokudera1": [
        "Sistema C.A.I.",
        "Advances the C.A.I. Stage by 1. All effects are cumulative except for Stage 4."
        +
        " Stage 1: Deals 10 damage to all enemies.\nStage 2: Stuns target enemy for one turn.\nStage 3: Deals 10 damage to one enemy and heals Gokudera for 15 health.\nStage 4: Deals 25 damage to all enemies and stuns them for 1 turn. Gokudera's team heals for 20 health. Resets the C.A.I. stage to 1.",
        [0, 0, 0, 1, 1, 0], Target.ALL_TARGET, target_sistema_CAI, exe_sistema_cai, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "gokudera2": [
        "Vongola Skull Rings", "Moves the C.A.I. stage forward by one.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("SELF"), exe_vongola_ring, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "gokudera3": [
        "Vongola Box Weapon - Vongola Bow",
        "Gokudera gains 30 points of destructible defense for 2 turns. During this time, the C.A.I. stage will not advance.",
        [0, 1, 0, 1, 0, 5], Target.SINGLE,
        default_target("SELF"), exe_vongola_bow, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "gokudera4": [
        "Gokudera Block", "Gokudera becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gokudera_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "hibari1": [
        "Bite You To Death", "Hibari deals 20 damage to target enemy.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_bite_you_to_death, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "hibari2": [
        "Alaudi's Handcuffs",
        "Hibari stuns one enemy for 2 turns. During this time, they take 15 damage per turn and Hibari cannot use Porcospino Nuvola.",
        [0, 0, 0, 1, 1, 5], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Porcospino Nuvola")), exe_handcuffs, [AbilityType.ACTION, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "hibari3": [
        "Porcospino Nuvola",
        "For 2 turns, any enemy that uses a new harmful ability will take 10 damage. During this time, Hibari cannot use Alaudi's Handcuffs.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Alaudi's Handcuffs")), exe_porcospino, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "hibari4": [
        "Tonfa Block", "Hibari becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_tonfa_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "gray1": [
        "Ice, Make...",
        "Gray prepares to use his ice magic. On the following turn, all of his abilities are enabled and Ice, Make... becomes Ice, Make Unlimited.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_ice_make, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "gray2": [
        "Ice, Make Freeze Lancer",
        "Gray deals 15 damage to all enemies for 2 turns.", [0, 1, 0, 0, 1, 2],
        Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Ice, Make..."), exe_freeze_lancer, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "gray3": [
        "Ice, Make Hammer",
        "Gray deals 20 damage to one enemy and stuns them for 1 turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="Ice, Make..."), exe_hammer, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "gray4": [
        "Ice, Make Shield", "Gray becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF", prep_req="Ice, Make..."), exe_shield, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "grayalt1": [
        "Ice, Make Unlimited",
        "Gray deals 5 damage to all enemies and grants all allies 5 destructible defense every turn.",
        [0, 1, 0, 0, 2, 0], Target.ALL_TARGET,
        default_target("ALL", prep_req="Ice, Make...", lockout=(EffectType.MARK, "Ice, Make Unlimited")), exe_unlimited, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "sogiita1": [
        "Super Awesome Punch",
        "Gunha does 35 piercing damage to target enemy. Using this ability consumes up to 5 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, Super Awesome Punch deals 10 additional damage. If Gunha consumes 5 stacks, Super Awesome Punch will "
        + "stun its target for 1 turn.", [1, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Guts"), exe_super_awesome_punch, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "sogiita2": [
        "Overwhelming Suppression",
        "Gunha reduces the damage dealt by all enemies by 5 for 1 turn. Using this ability consumes up to 3 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, then the damage reduction is increased by 5. If Gunha consumes 3 stacks, then all affected enemies cannot reduce"
        + " damage or become invulnerable for 2 turns.", [0, 0, 1, 0, 0, 0
                                                         ], Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Guts"), exe_overwhelming_suppression, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC]
    ],
    "sogiita3": [
        "Hyper Eccentric Ultra Great Giga Extreme Hyper Again Awesome Punch",
        "Gunha does 20 damage to target enemy. Using this ability consumes up to "
        +
        "3 stacks of Guts from Gunha. If Gunha consumes at least 2 stacks, this ability deals 5 extra damage and becomes piercing. If Gunha consumes 3 stacks, this ability"
        +
        " will target all enemies.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", prep_req="Guts"), exe_hyper_eccentric_punch, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "sogiita4": [
        "Guts",
        "Gunha permanently activates Guts, enabling his other abilities and granting him 5 stacks of Guts. After the initial use, Gunha can activate "
        +
        "Guts again to grant himself 3 stacks of Guts and heal for 35 health.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF"), exe_guts, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "hinata1": [
        "Gentle Step - Twin Lion Fists",
        "Hinata deals 20 damage to one enemy, then deals 20 damage to the same enemy. The second instance of damage will occur even if this ability is "
        + "countered or reflected.", [1, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_twin_lion_fist, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "hinata2": [
        "Eight Trigrams - 64 Palms",
        "Hinata gives her entire team 10 points of damage reduction for 1 turn. If used on consecutive turns, this ability will also deal 15 damage to the enemy team.",
        [1, 0, 0, 0, 0, 0], Target.ALL_TARGET, target_eight_trigrams, exe_hinata_trigrams, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "hinata3": [
        "Byakugan",
        "For 3 turns, Hinata removes one energy from one of her targets whenever she deals damage.",
        [0, 1, 0, 0, 0, 3], Target.SINGLE, 
        default_target("SELF"), exe_hinata_byakugan, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "hinata4": [
        "Gentle Fist Block", "Hinata becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_gentle_fist_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ichigo1": [
        "Getsuga Tenshou",
        "Ichigo deals"
        +
        " 40 damage to one enemy. If used on the turn after Tensa Zangetsu, it will "
        + "ignore invulnerability and deal piercing damage.",
        [0, 0, 0, 1, 2, 1], Target.SINGLE, target_getsuga_tenshou, exe_getsuga_tenshou
    ],
    "ichigo2": [
        "Tensa Zangetsu",
        "Ichigo gains one random energy and is invulnerable for two turns." +
        " The turn after this ability " +
        "is used, Getsuga Tenshou and Zangetsu Strike are improved.",
        [1, 0, 0, 1, 0, 6], Target.SINGLE,
        default_target("SELF"), exe_tensa_zangetsu, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "ichigo3": [
        "Zangetsu Strike",
        "Ichigo deals 20 damage to one enemy and permanently "
        +
        "increases Zangetsu Strike's damage by 5. If used on the turn after "
        +
        "Tensa Zangetsu, it will target all enemies and permanently increase Zangetsu Strike's "
        + "damage by 5 per enemy struck.", [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_zangetsu_slash, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "ichigo4": [
        "Zangetsu Block", "Ichigo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_zangetsu_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ichimaru1": [
        "Butou Renjin",
        "Ichimaru deals 15 damage to one enemy for two turns, adding a stack of Kamishini no Yari to the target each turn when it damages them.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_butou_renjin, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "ichimaru2": [
        "13 Kilometer Swing",
        "Ichimaru deals 25 damage to all enemies and adds a stack of Kamishini no Yari to each enemy damaged.",
        [0, 0, 0, 1, 2, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_13_kilometer_swing, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "ichimaru3": [
        "Kill, Kamishini no Yari",
        "Ichimaru consumes all stacks of Kamishini no Yari, dealing 10 affliction damage to each enemy for the rest of the game for each stack of consumed from them. This effect ignores invulnerability.",
        [0, 0, 0, 2, 0, 2], Target.MULTI_ENEMY,
        target_kill_shinso, exe_kamishini_no_yari, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "ichimaru4": [
        "Shinso Parry", "Ichimaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_shinso_parry, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "jack1": [
        "Maria the Ripper",
        "Jack deals 15 damage and 10 affliction damage to one enemy. Can only target enemies affected by Fog of London or Streets of the Lost.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", prep_req = "Fog of London"), exe_maria_the_ripper, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "jack2": [
        "Fog of London",
        "Jack deals 5 affliction damage to all enemies for 3 turns. During this time, Fog of London is replaced by Streets of the Lost. This ability cannot be countered.",
        [0, 0, 1, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_fog_of_london, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.AFFLICTION]
    ],
    "jack3": [
        "We Are Jack",
        "Jack deals 30 affliction damage to an enemy affected by Streets of the Lost.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Streets of the Lost"), exe_we_are_jack, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.AFFLICTION]
    ],
    "jack4": [
        "Smokescreen Defense", "Jack becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_smokescreen_defense, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "jackalt1": [
        "Streets of the Lost",
        "For 3 turns, target enemy is isolated and can only target Jack. During this time, We Are Jack is usable.",
        [0, 0, 1, 0, 1, 5], Target.SINGLE,
        default_target("HOSTILE"), exe_streets_of_the_lost, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "jeanne1": ["Flag of the Ruler", "For one turn, Jeanne's allies gain 10 points of damage reduction and 10 points of destructible defense.",
                [0, 0, 0, 1, 0, 1], Target.MULTI_ALLY, default_target("SELFLESS"), exe_flag_of_the_ruler, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "jeanne2": ["Luminosite Eternelle", "Jeanne makes her entire team invulnerable for two turns.",
                [0, 0, 0, 2, 1, 6], Target.MULTI_ALLY, default_target("HELPFUL"), exe_luminosite, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "jeanne3": ["La Pucelle - Draw", "Jeanne draws her sword, preparing to give her life. On the following turn, this ability is replaced with Crimson Holy Maiden.",
                [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("SELF"), exe_la_pucelle, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "jeanne4": ["Jeanne Dodge", "Jeanne becomes invulnerable for one turn.", [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_jeanne_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]],
    "jeannealt1": ["Crimson Holy Maiden", "Jeanne stuns herself and becomes permanently invulnerable. Each turn, she suffers 35 affliction damage and deals 15 affliction damage to all enemies.",
                    [0, 0, 0, 2, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_crimson_holy_maiden, [AbilityType.ACTION, AbilityType.AFFLICTION, AbilityType.UNIQUE]],
    "itachi1": [
        "Amaterasu",
        "Itachi deals 10 affliction damage to one enemy for the rest of the game. This effect does not stack.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.CONT_AFF_DMG, "Amaterasu")), exe_amaterasu, [AbilityType.INSTANT, AbilityType.AFFLICTION]
    ],
    "itachi2": [
        "Tsukuyomi",
        "Itachi stuns one target for 3 turns. This effect will end early if an ally uses a skill on them.",
        [0, 0, 2, 0, 0, 4], Target.SINGLE,
        default_target("HOSTILE"), exe_tsukuyomi, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STUN]
    ],
    "itachi3": [
        "Susano'o",
        "Itachi gains 45 destructible defense, and takes 10 affliction damage each turn. During this time, Amaterasu is replaced by Totsuka Blade and Tsukuyomi is replaced by"
        +
        " Yata Mirror. If Itachi falls below 50 health or he loses all his destructible defense, Susano'o will end.",
        [0, 2, 0, 0, 0, 6], Target.SINGLE,
        default_target("SELF"), exe_susanoo, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "itachi4": [
        "Crow Genjutsu", "Itachi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_crow_genjutsu, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "itachialt1": [
        "Totsuka Blade",
        "Itachi deals 35 damage to one enemy and stuns them for one turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_totsuka_blade, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "itachialt2": [
        "Yata Mirror",
        "Itachi's Susano'o regains 20 destructible defense and Itachi loses 5 health.",
        [0, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("SELF"), exe_yata_mirror, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "jiro1": [
        "Counter-Balance",
        "For one turn, any enemy that stuns Jiro or her allies will lose one energy, and any enemy that drains energy from Jiro or her allies will be stunned for one turn. This effect is invisible.",
        [0, 1, 0, 0, 0, 2], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_counter_balance, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "jiro2": [
        "Heartbeat Distortion",
        "Jiro deals 5 damage to the enemy team for 4 turns. During this time, Heartbeat Distortion cannot be used and Heartbeat Surround will cost one less random energy and deal 20 damage to a single enemy. This ability"
        +
        " ignores invulnerability against enemies affected by Heartbeat Surround.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, target_heartbeat_distortion, exe_heartbeat_distortion, [AbilityType.ACTION, AbilityType.ENERGY, AbilityType.UNIQUE]
    ],
    "jiro3": [
        "Heartbeat Surround",
        "Jiro deals 10 damage to one enemy for 4 turns. During this time, Heartbeat Surround cannot be used and Heartbeat Distortion will cost one less random energy and deal 15 damage to all enemies. This ability ignores invulnerability "
        + "against enemies affected by Heartbeat Distortion.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE, target_heartbeat_surround, exe_heartbeat_surround, [AbilityType.ACTION, AbilityType.ENERGY, AbilityType.UNIQUE]
    ],
    "jiro4": [
        "Early Detection", "Jiro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_early_detection, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "kakashi1": [
        "Copy Ninja Kakashi",
        "For one turn, Kakashi will reflect the first hostile ability that targets him. This ability is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF"), exe_copy_ninja, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "kakashi2": [
        "Summon - Nin-dogs",
        "Target enemy takes 20 damage and is stunned for one turn. During this time, they take double damage from Raikiri.",
        [0, 1, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_nindogs, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "kakashi3": [
        "Raikiri", "Kakashi deals 40 piercing damage to target enemy.",
        [0, 2, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_raikiri, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "kakashi4": [
        "Kamui",
        "Kakashi targets one enemy or himself, ignoring invulnerability. If used on himself, Kakashi will ignore all harmful effects for one turn. If used on an enemy, this ability will deal"
        +
        " 20 piercing damage to them. If they are invulnerable, they will become isolated for one turn.",
        [0, 1, 0, 0, 0, 4], Target.SINGLE, target_kamui, exe_kamui, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.UNIQUE]
    ],
    "killua1":[
        "Lightning Palm",
        "Killua deals 20 damage to one enemy. If an ally deals damage to them during this turn, that ally will become immune to stun effects for one turn.",
        [1,0,0,0,0,0], Target.SINGLE, default_target("HOSTILE"), exe_lightning_palm, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "killua2":[
        "Narukami",
        "Killua deals 20 damage to one enemy. If an ally deals damage to them during this turn, that ally will ignore counter effects for one turn.",
        [0,1,0,0,0,0], Target.SINGLE, default_target("HOSTILE"), exe_narukami, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "killua3":[
        "Godspeed",
        "For three turns, Killua will ignore affliction damage. During this time Godspeed is replaced by Whirlwind Rush, and Lightning Palm and Narukami will deal 5 additional damage and apply their triggered effects immediately to Killua's entire team.",
        [1,1,0,0,0,6], Target.SINGLE, default_target("SELF"), exe_godspeed, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "killua4":[
        "Godspeed Withdrawal",
        "Killua becomes invulnerable for one turn.",
        [0,0,0,0,1,4], Target.SINGLE, default_target("SELF"), exe_godspeed_withdrawal, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "killuaalt1":[
        "Whirlwind Rush",
        "Killua deals 35 damage to one enemy and stuns them for one turn. If an ally deals damage to them during this turn, that ally will become invulnerable for one turn.",
        [1,1,0,0,0,3], Target.SINGLE, default_target("HOSTILE"), exe_whirlwind_rush, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "kuroko2": [
        "Teleporting Strike",
        "Kuroko deals 10 damage to one enemy and becomes invulnerable for one turn. If used on the turn after "
        +
        "Needle Pin, this ability will have no cooldown. If used on the turn after Judgement Throw, this ability will deal 15 extra damage.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_teleporting_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "kuroko3": [
        "Needle Pin",
        "One enemy becomes unable to reduce damage or become invulnerable for two turns. If used on the turn after Teleporting Strike, "
        +
        "this ability ignores invulnerability and deals 15 piercing damage to its target. If used on the turn after Judgement Throw, this ability will stun its target for one turn.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_needle_pin, exe_needle_pin, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "kuroko1": [
        "Judgement Throw",
        "Kuroko deals 15 damage to one enemy and reduces their damage dealt by 10 for one turn. If used on the turn"
        +
        " after Teleporting Strike, this ability will have double effect. If used on the turn after Needle Pin, this ability will remove one energy from its target.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_judgement_throw, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "kuroko4": [
        "Kuroko Dodge", "Kuroko is invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kuroko_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "kurome1":[
        "Mass Animation", "Kurome deals 20 damage to all enemies.", [0,0,0,0,2,1], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_mass_animation, [AbilityType.INSTANT, AbilityType.PHYSICAL]],
    "kurome2":[
        "Yatsufusa", "Kurome deals 15 piercing damage to one enemy or one ally other than herself. If this ability kills an enemy, Mass Animation will permanently deal 10 more damage. If this ability kills an ally, " +
        "at the start of Kurome's next turn, that ally will be resurrected with 40 health. After being resurrected, that ally cannot reduce damage or become invulnerable and their abilities will cost one additional random energy.",
        [0,0,0,1,0,0], Target.SINGLE, target_yatsufusa, exe_yatsufusa, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "kurome3":
    [
        "Doping Rampage", "Yatsufusa will deal 20 bonus piercing damage permanently. During this time, Kurome will take 30 affliction damage at the end of each of her turns, and can only be killed by this damage. This effect does not damage her on the turn in which she uses it.",
        [0,0,0,0,2,0], Target.SINGLE, default_target("SELF", lockout="Doping Rampage"), exe_doping_rampage, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]],
    "kurome4":
    [
        "Impossible Dodge", "Kurome is invulnerable for 1 turn.", [0,0,0,0,1,4], Target.SINGLE, default_target("SELF"), exe_impossible_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
        ],
    "lambo1": 
    [
        "Ten-Year Bazooka",
        "Lambo switches places with himself ten years in the future. The first time this is used, Summon Gyudon"
        +
        " will be replaced by Thunder, Set, Charge! for the next three turns. If used again, Thunder, Set, Charge! will be replaced by Elettrico Cornata for the next two turns. If used again, Lambo will return to his normal state.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_ten_year_bazooka, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "lambo2": [
        "Conductivity",
        "For two turns, Lambo's allies receive 20 points of damage reduction. If they receive damaging abilities during this time, "
        + "Lambo will take 10 affliction damage.", [0, 0, 0, 0, 1, 2], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_conductivity, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "lambo3": [
        "Summon Gyudon",
        "Lambo's team gains 10 points of damage reduction permanently. During this time, the enemy team receives 5 points of damage each turn. This skill will end if "
        + "Ten-Year Bazooka is used.", [0, 0, 0, 1, 2, 4], Target.ALL_TARGET,
        target_summon_gyudon, exe_summon_gyudon, [AbilityType.ACTION, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "lambo4": [
        "Lampow's Shield", "Lambo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_lampows_shield, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "lamboalt1": [
        "Thunder, Set, Charge!", "Lambo deals 25 damage to one enemy.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_thunder_set_charge, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "lamboalt2": [
        "Elettrico Cornata", "Lambo deals 35 damage to all enemies.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_elettrico_cornata, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "pucelle1": [
        "Knight's Sword", "La Pucelle deals 20 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_knights_sword, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "pucelle2": [
        "Magic Sword",
        "La Pucelle commands her sword to grow, permanently increasing its damage by 20, its cost by 1 random, and its cooldown by 1.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_magic_sword, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "pucelle3": [
        "Ideal Strike",
        "La Pucelle deals 40 piercing damage to one enemy. This ability ignores invulnerability, cannot be countered, and can only be used if La Pucelle is below 50 health.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE, target_ideal_strike, exe_ideal_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "pucelle4": [
        "Knight's Guard", "La Pucelle becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_knights_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "laxus1": [
        "Fairy Law",
        "Laxus deals 20 damage to all enemies and restores 20 health to all allies.",
        [0, 0, 0, 0, 3, 5], Target.ALL_TARGET,
        default_target("ALL"), exe_fairy_law, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "laxus2": [
        "Lightning Dragon's Roar",
        "Laxus deals 40 damage to one enemy and stuns them for one turn. When the stun wears off, the target receives 10 more damage for 1 turn.",
        [0, 2, 0, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_lightning_dragons_roar, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "laxus3": [
        "Thunder Palace",
        "After 2 turns, Laxus deals 40 damage to the entire enemy team. Dealing damage to Laxus during these two turns will cancel this effect,"
        +
        " dealing damage equal to the original damage of the move that damaged him to the user.",
        [0, 1, 0, 0, 2, 4], Target.SINGLE,
        default_target("SELF"), exe_thunder_palace, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "laxus4": [
        "Laxus Block", "Laxus becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_laxus_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "leone1": [
        "King of Beasts Transformation - Lionel",
        "Leone activates her Teigu, permanently allowing the use of her other moves and causing her to heal 10 health per turn."
        +
        " This healing is increased by 10 at the end of a turn in which she did damage to an enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "King of Beasts Transformation - Lionel")), exe_lionel, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "leone2": [
        "Beast Instinct",
        "Leone targets herself or an enemy for 3 turns. If used on an enemy, Lion Fist will ignore invulnerability and deal 20 additional damage to them. If"
        +
        " used on Leone, she will ignore counters and stuns for the duration.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, target_beast_instinct, exe_beast_instinct, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "leone3": [
        "Lion Fist",
        "Leone deals 35 damage to target enemy. If this ability kills an enemy while Leone is affected by Beast Instinct, Beast Instinct's duration will refresh. "
        +
        "If this ability kills an enemy that is affected by Beast Instinct, Leone will heal for 20 health.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        target_lion_fist, exe_lion_fist, [AbilityType.INSTANT, AbilityType.PHYSICAL] 
    ],
    "leone4": [
        "Instinctual Dodge",
        "Leone becomes invulnerable for one turn. Using this ability counts as a damaging ability for triggering King of Beasts Transformation - Lionel's healing.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="King of Beasts Transformation - Lionel"), exe_instinctual_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "levy1": [
        "Solid Script - Fire",
        "Levy marks all enemies for one turn. During this time, if they use a new ability, they will take 10 affliction damage. When this ability"
        + " ends, all affected enemies take 10 affliction damage.",
        [0, 0, 1, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_solidscript_fire, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.AFFLICTION]
    ],
    "levy2": [
        "Solid Script - Silent",
        "For two turns, all characters become isolated. This ability cannot be countered or ignored and ignores invulnerability.",
        [0, 0, 1, 0, 2, 3], Target.ALL_TARGET,
        default_target("ALL", def_type="BYPASS"), exe_solidscript_silent, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "levy3": [
        "Solid Script - Mask",
        "For two turns, target ally will ignore all stuns and affliction damage.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("HELPFUL"), exe_solidscript_mask, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "levy4": [
        "Solid Script - Guard", "Levy becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_solidscript_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "raba1": [
        "Cross-Tail Strike",
        "Lubbock deals 15 damage to one target and marks them with Cross-Tail Strike. Until Lubbock uses this ability on an enemy already marked with Cross-Tail Strike, this ability will cost no energy. "
        +
        "If this ability targets a marked enemy and all living enemies are marked, this ability will deal 20 piercing damage to all marked enemies, ignoring invulnerability. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_crosstail_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "raba2": [
        "Wire Shield",
        "Target ally gains 15 permanent destructible defense and is marked with Wire Shield. Until Lubbock uses this ability on an ally already targeted with Wire Shield, this ability will costs no energy. "
        +
        "If this ability targets an ally marked with Wire Shield and all living allies are marked, all marked allies become invulnerable for one turn. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_wire_shield, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "raba3": [
        "Heartseeker Thrust",
        "Lubbock deals 30 piercing damage to one target. If Lubbock is marked by Wire Shield, the damaged enemy will receive 15 affliction damage on the following turn. If the target is marked by Cross-Tail Strike, "
        + "the target will become stunned for one turn.", [0, 0, 0, 1, 1,
                                                           1], Target.SINGLE,
        default_target("HOSTILE"), exe_heartseeker_thrust, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "raba4": [
        "Defensive Netting", "Lubbock becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_defensive_netting, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "lucy1": [
        "Aquarius",
        "Lucy deals 15 damage to all enemies and grants her team 10 points of damage reduction.",
        [0, 0, 0, 1, 1, 1], Target.ALL_TARGET,
        default_target("ALL"), exe_aquarius, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "lucy2": [
        "Gemini",
        "For the next three turns, Lucy's abilities will stay active for one extra turn. During this time, this ability is replaced by Urano Metria.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF"), exe_gemini, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "lucy3": [
        "Capricorn", "Lucy deals 20 damage to one enemy.", [0, 0, 0, 1, 0, 0],
        Target.SINGLE,
        default_target("HOSTILE"), exe_capricorn, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "lucy4": [
        "Leo", "Lucy becomes invulnerable for one turn.", [0, 0, 0, 0, 1, 4],
        Target.SINGLE,
        default_target("SELF"), exe_leo, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "lucyalt1": [
        "Urano Metria", "Lucy deals 20 damage to all enemies.",
        [0, 0, 1, 1, 0, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_urano_metria, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "midoriya1": [
        "SMASH!",
        "Midoriya deals 45 damage to one enemy and 20 affliction damage to himself.", [1, 0, 0, 0, 2, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_smash, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "midoriya2": [
        "Air Force Gloves",
        "Midoriya deals 15 damage to one enemy and"
        + " increases the cooldown of any move they use by one for one turn.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_air_force_gloves, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "midoriya3": [
        "One For All - Shoot Style",
        "Midoriya deals 20 damage to all enemies. For 1 turn,"
        + " Midoriya will counter the first ability used on him. This effect is invisible.",
        [1, 0, 0, 0, 1, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_shoot_style, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "midoriya4": [
        "Enhanced Leap", "Midoriya becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_enhanced_leap, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "minato1": [
        "Flying Raijin",
        "Minato deals 25 piercing damage that ignores invulnerability to one enemy. If used on a target marked with Marked Kunai, Minato becomes invulnerable for "
        +
        "one turn and the cooldown on Flying Raijin is reduced to 0. This effect consumes Marked Kunai's mark.",
        [0, 1, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_flying_raijin, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "minato2": [
        "Marked Kunai",
        "Minato deals 10 piercing damage to one enemy and permanently marks them.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_marked_kunai, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "minato3": [
        "Partial Shiki Fuujin",
        "Minato permanently increases the cooldowns and random cost of target enemy by one. After using this skill, Minato dies.",
        [0, 0, 0, 0, 3, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_partial_shiki_fuujin, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "minato4": [
        "Minato Parry", "Minato becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_minato_parry, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "mine1": [
        "Roman Artillery - Pumpkin",
        "Mine deals 25 damage to one enemy. If Mine is below 120 health, this ability deals 10 more damage. If Mine is below 60 health, this ability "
        + "costs one less weapon energy.", [0, 0, 0, 1, 1, 0], Target.SINGLE, target_pumpkin, exe_roman_artillery_pumpkin, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "mine2": [
        "Cut-Down Shot",
        "Deals 25 damage to all enemies. If Mine is below 100 health, this ability will stun all targets hit for 1 turn. If Mine is below 50 health, this ability deals double damage and the damage it deals "
        + "is piercing.", [0, 0, 0, 1, 2, 3], Target.MULTI_ENEMY, target_cutdown_shot, exe_cutdown_shot, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "mine3": [
        "Pumpkin Scouter",
        "For the next two turns, all of Mine's abilities will ignore invulnerability and deal 5 additional damage.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_pumpkin_scouter, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "mine4": [
        "Close-Range Deflection", "Mine becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_closerange_deflection, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "mirai1": [
        "Blood Suppression Removal",
        "For 3 turns, Mirai's abilities will cause their target to receive 10 affliction damage for 2 turns. During this time, this ability is replaced with Blood Bullet and Mirai receives 10 affliction damage per turn.",
        [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF"), exe_blood_suppression_removal, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.AFFLICTION, AbilityType.UNIQUE]
    ],
    "mirai2": [
        "Blood Sword Combat", "Mirai deals 30 damage to target enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_blood_sword_combat, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "mirai3": [
        "Blood Shield",
        "Mirai gains 20 points of destructible defense and 20 points of damage reduction for one turn.",
        [0, 1, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF"), exe_blood_shield, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "mirai4": [
        "Mirai Deflect", "Mirai becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_mirai_deflect, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "miraialt1": [
        "Blood Bullet",
        "Mirai deals 10 affliction damage to target enemy for 2 turns.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_blood_bullet, [AbilityType.INSTANT, AbilityType.AFFLICTION]
    ],
    "mirio1": [
        "Quirk - Permeation",
        "For one turn, Mirio will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF"), exe_permeation, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "mirio2": [
        "Phantom Menace",
        "Mirio deals 20 piercing damage to one enemy. This ability ignores invulnerability, and deals 15 piercing damage to any enemy marked by Phantom Menace.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", def_type="BYPASS"), exe_phantom_menace, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "mirio3": [
        "Protect Ally",
        "For one turn, target ally will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELFLESS"), exe_protect_ally, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "mirio4": [
        "Mirio Dodge", "Mirio becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_mirio_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misaka2": [
        "Railgun",
        "Misaka deals 20 damage to one enemy. This ability ignores invulnerability and cannot be countered or reflected. After being used, this ability will be replaced by Ultra Railgun.",
        [0, 0, 1, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_railgun, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "misaka1": [
        "Iron Sand",
        "Misaka grants one ally 20 points of destructible defense for one turn. After being used, this ability will be replaced by Iron Colossus.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_iron_sand, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misaka3": [
        "Overcharge",
        "Misaka permanently gains one stack of Overcharge. For each stack she has, Railgun deals 5 additional damage and Iron Sand grants 5 additional destructible defense.", [0, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("SELF"), exe_overcharge, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "misaka4": [
        "Electric Deflection", "Misaka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_electric_deflection, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misakaalt1":[
        "Iron Colossus", "Misaka permanently gains 10 destructible defense per turn. For the rest of the game, Iron Sand and Railgun affect all valid targets. Using this ability will reset all her abilities to their original forms and prevent her from switching for the rest of the game.",
        [0, 1, 1, 0, 0, 0],
        Target.SINGLE, default_target("SELF"), exe_iron_colossus, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "misakaalt2":[
        "Ultra Railgun", "Misaka deals 50 damage to target enemy. This ability ignores invulnerability and cannot be countered or reflected. For the rest of the game, Misaka's abilities cost one additional random energy and have their effects doubled. Using this ability will reset all her abilities to their original forms and prevent her from switching for the rest of the game.",
        [0, 1, 1, 0, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_ultra_railgun, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.UNIQUE]
    ],
    "misakaalt3":[
        "Level-6 Shift", "For the rest of the game, Misaka will be uncontrollable and will use one of her abilities on a random valid target each round. During this time, she will deal 10 less damage, apply 10 less destructible defense, but all her effects will last for 3 turns. Using this ability will reset all her abilities to their original forms and prevent her from switching for the rest of the game.",
        [0, 1, 1, 0, 0, 0], Target.SINGLE, default_target("SELF"), exe_levelsix_shift, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
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
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit"), exe_bunny_assault, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "naruha2": [
        "Perfect Paper - Rampage Suit",
        "Naru permanently gains 100 points of destructible defense. After being used, Naru can use Bunny Assault and this ability is replaced by Enraged Blow.",
        [0, 0, 0, 0, 2, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.UNIQUE, "Perfect Paper - Rampage Suit")), exe_rampage_suit, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "naruha3": [
        "Perfect Paper - Piercing Umbrella",
        "Naru deals 15 damage to target enemy. If Naru has destructible defense remaining on Perfect Paper - Rampage Suit, this ability will deal 10 bonus damage.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_piercing_umbrella, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "naruha4": [
        "Rabbit Guard",
        "Perfect Paper - Rampage Suit gains 25 points of destructible defense. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="Perfect Paper - Rampage Suit"), exe_rabbit_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "naruhaalt1": [
        "Enraged Blow",
        "Naru deals 40 damage to one enemy and stuns them for a turn. During the following turn, Naru takes double damage. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [1, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit"), exe_enraged_blow, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "natsu1": [
        "Fire Dragon's Roar",
        "Natsu deals 25 damage to one enemy. The following turn, they take 10 affliction damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_roar, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.AFFLICTION]
    ],
    "natsu2": [
        "Fire Dragon's Iron Fist",
        "Natsu deals 15 damage to one enemy. If they are currently affected by one of Natsu's affliction damage-over-time"
        + " effects, they take 10 affliction damage.", [0, 1, 0, 0, 0,
                                                        0], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_iron_fist, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "natsu3": [
        "Fire Dragon's Sword Horn",
        "Natsu deals 40 damage to one enemy. For the rest of the game, that enemy"
        + " takes 5 affliction damage per turn.", [1, 1, 0, 0, 1,
                                                   3], Target.SINGLE,
        default_target("HOSTILE"), exe_fire_dragons_sword_horn, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "natsu4": [
        "Natsu Dodge", "Natsu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_natsu_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "neji1": [
        "Eight Trigrams - 128 Palms",
        "Neji deals 2 damage to target enemy for seven turns. The damage this ability deals doubles each turn. While active, this ability is replaced by "
        +
        "Chakra Point Strike, which removes one random energy from the target if they take damage from Eight Trigrams - 128 Palms this turn.",
        [1, 0, 0, 0, 1, 8], Target.SINGLE,
        default_target("HOSTILE"), exe_neji_trigrams, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "neji2": [
        "Eight Trigrams - Mountain Crusher",
        "Neji deals 25 damage to target enemy, ignoring invulnerability. If used on an invulnerable target, this ability will deal 15 additional damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_neji_mountain_crusher, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "neji3": [
        "Selfless Genius",
        "If a target ally would die this turn, they instead take no damage and deal 10 additional damage on the following turn. If this ability is triggered, Neji dies. This skill is invisible until "
        + "triggered and the death cannot be prevented.", [0, 0, 0, 0, 2,
                                                           3], Target.SINGLE,
        default_target("SELFLESS"), exe_selfless_genius, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "neji4": [
        "Eight Trigrams - Revolving Heaven",
        "Neji becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                    4], Target.SINGLE,
        default_target("SELF"), exe_revolving_heaven, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "nejialt1": [
        "Chakra Point Strike",
        "If target enemy takes damage from Eight Trigrams - 128 Palms this turn, they will lose 1 random energy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Eight Trigrams - 128 Palms"), exe_chakra_point_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.DRAIN]
    ],
    "nemu1": [
        "Nemurin Nap",
        "Nemurin heads for the dream world, enabling the use of her other abilities. " + 
        "Every turn that she does not take new damage or use an ability, her sleep grows one stage deeper. While dozing, Nemu can use her abilities. While fully asleep, Nemurin Beam and Dream Manipulation cost one less random energy. While deeply asleep, Nemurin Beam and Dream Manipulation become area-of-effect. When Nemurin takes new, non-absorbed damage, she loses one stage of sleep depth.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Nemurin Nap")), exe_nemurin_nap, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "nemu2": [
        "Nemurin Beam",
        "Nemurin deals 25 damage to target enemy and reduces the damage they deal by 10 for one turn.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", prep_req = "Nemurin Nap"), exe_nemurin_beam, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "nemu3": [
        "Dream Manipulation",
        "For 3 turns, target ally deals 10 additional damage and heals 10 health per turn. Cannot be used on Nemurin.",
        [0, 0, 1, 0, 1, 2], Target.SINGLE,
        default_target("SELFLESS", prep_req = "Nemurin Nap"), exe_dream_manipulation, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC]
    ],
    "nemu4": [
        "Dreamland Sovereignty", "Nemurin becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req = "Nemurin Nap"), exe_dream_sovereignty, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "orihime1": [
        "Tsubaki!",
        "Orihime prepares the Shun Shun Rikka with an offensive effect.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Tsubaki!")), exe_tsubaki, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "orihime2": [
        "Ayame! Shun'o!",
        "Orihime prepares the Shun Shun Rikka with a healing effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Ayame! Shun'o!")), exe_ayame_shuno, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "orihime3": [
        "Lily! Hinagiku! Baigon!",
        "Orihime prepares the Shun Shun Rikka with a defensive effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF",
                       lockout=(EffectType.MARK, "Lily! Hinagiku! Baigon!")), exe_lily_hinagiku_baigon, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "orihime4": [
        "I Reject!",
        "Orihime activates her Shun Shun Rikka, with a composite effect depending on the flowers she has activated. This will end any active Shun Shun Rikka effect originating from a name she is currently calling out.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, target_shun_shun_rikka, exe_i_reject, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STRATEGIC]
    ],
    "shunshunrikka1": [
        "Dance of the Heavenly Six",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "shunshunrikka2": [
        "Five-God Inviolate Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shunshunrikka3": [
        "Four-God Resisting Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shunshunrikka4": [
        "Three-God Empowering Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shunshunrikka5": [
        "Three-God Linking Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shunshunrikka6": [
        "Two-God Returning Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shunshunrikka7": [
        "Lone-God Slicing Shield",
        "",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "ripple1": [
        "Perfect Accuracy",
        "Targets one enemy with Ripple's perfect accuracy. For the rest of the game, Shuriken Throw will target that enemy in addition to any other targets, ignoring invulnerability and dealing 5 additional damage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.MARK, "Perfect Accuracy")), exe_perfect_accuracy, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ripple2": [
        "Shuriken Throw", "Ripple deals 15 piercing damage to target enemy.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_shuriken_throw, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "ripple3": [
        "Night of Countless Stars",
        "Ripple deals 5 piercing damage to all enemies for three turns. During this time, Shuriken Throw deals 10 additional damage.",
        [0, 0, 0, 1, 1, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_countless_stars, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "ripple4": [
        "Ripple Block", "Ripple becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_ripple_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "rukia1": [
        "First Dance - Tsukishiro",
        "Rukia deals 25 damage to one enemy, ignoring invulnerability. If that enemy is invulnerable, they are stunned for one turn.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS"), exe_first_dance, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STUN]
    ],
    "rukia2": [
        "Second Dance - Hakuren",
        "Rukia deals 15 damage to one enemy and 10 damage to all others.",
        [0, 1, 0, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_second_dance, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "rukia3": [
        "Third Dance - Shirafune",
        "The next time Rukia is countered, the countering enemy receives 30 damage and is stunned for one turn. This effect is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF"), exe_third_dance, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "rukia4": [
        "Rukia Parry", "Rukia becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_rukia_parry, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ruler1": [
        "In The Name Of Ruler!",
        "Ruler stuns one enemy and herself for 3 turns. This skill cannot be used while active and will end if Ruler receives new damage.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "In The Name Of Ruler!")), exe_in_the_name_of_ruler, [AbilityType.ACTION, AbilityType.MENTAL, AbilityType.STUN, AbilityType.UNIQUE]
    ],
    "ruler2": [
        "Minion - Minael and Yunael",
        "Deals 15 damage to target enemy or gives 10 destructible defense to Ruler.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, target_minion_minael_yunael, exe_minael_yunael, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "ruler3": [
        "Minion - Tama",
        "The next time target ally receives a new harmful ability, that ability is countered and its user takes 20 piercing damage. This effect can only be active on one target at a time.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HELPFUL"), exe_tama, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "ruler4": [
        "Minion - Swim Swim", "Ruler becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_swim_swim, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ryohei1": [
        "Maximum Cannon", "Ryohei deals 20 damage to a single target.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_maximum_cannon, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "ryohei2": [
        "Kangaryu", "Ryohei heals target ally for 15 health.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HELPFUL"), exe_kangaryu, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "ryohei3": [
        "Vongola Headgear",
        "For the next 2 turns, Ryohei will ignore all random cost increases to Maximum Cannon and Kangaryu, and using them will not consume stacks of To The Extreme!",
        [0, 0, 0, 0, 2, 4], Target.SINGLE,
        default_target("SELF"), exe_vongola_headgear, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "ryohei4": [
        "To The Extreme!",
        "For the rest of the game, whenever Ryohei takes 30 damage, he will gain one stack of To The Extreme! For each stack of To The Extreme! on him, Maximum Cannon will deal 15 more damage and cost one more random"
        +
        " energy, and Kangaryu will restore 20 more health and cost one more random energy. Using either ability will reset all stacks of To The Extreme!",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "To The Extreme!")), exe_to_the_extreme, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "saber1": [
        "Excalibur",
        "Saber deals 50 piercing damage to one enemy. This ability cannot be countered.",
        [1, 0, 0, 1, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_excalibur, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "saber2": [
        "Wind Blade Combat",
        "Saber deals 10 damage to one enemy for three turns. During this time, Saber"
        + " cannot be stunned. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_wind_blade_combat, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "saber3": [
        "Avalon",
        "One ally permanently heals 10 health per turn. This ability can only affect one ally at a time.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL", protection=(EffectType.MARK, "Avalon")), exe_avalon, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "saber4": [
        "Saber Parry", "Saber becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_saber_parry, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "saitama1": [
        "One Punch", "Saitama deals 75 piercing damage to one enemy.",
        [2, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_one_punch, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "saitama2": [
        "Consecutive Normal Punches",
        "Saitama deals 15 damage to one enemy for 3 turns.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_consecutive_normal_punches, [AbilityType.ACTION, AbilityType.PHYSICAL]
    ],
    "saitama3": [
        "Serious Series - Serious Punch",
        "On the following turn Saitama deals 35 damage to target enemy. During this time, Saitama will ignore all effects.",
        [1, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("HOSTILE"), exe_serious_punch, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "saitama4": [
        "Serious Series - Serious Sideways Jumps",
        "Saitama becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                       4], Target.SINGLE,
        default_target("SELF"), exe_sideways_jumps, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "seryu1": [
        "Body Modification - Arm Gun",
        "Seryu deals 20 damage to one enemy. Becomes Body Modification - Self Destruct if Seryu falls below 50 health.",
        [0, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_body_mod_arm_gun, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "seryu2": [
        "Raging Koro",
        "Koro deals 20 damage to one enemy for two turns. Becomes Insatiable Justice while active.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE"), exe_raging_koro, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "seryu3": [
        "Berserker Howl",
        "Koro deals 15 damage to all enemies and lowers the damage they deal by 10 for 2 turns.",
        [0, 0, 0, 0, 3, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_berserker_howl, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "seryu4": [
        "Koro Defense", "Seryu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_koro_defense, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "seryualt1": [
        "Body Modification - Self Destruct",
        "Seryu deals 30 damage to all enemies. After using this ability, Seryu dies. Effects that prevent death cannot prevent Seryu from dying. This ability cannot be countered.",
        [0, 0, 0, 0, 2, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_self_destruct, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "seryualt2": [
        "Insatiable Justice",
        "Koro instantly kills one enemy that is below 60 health. Effects that prevent death cannot prevent this ability.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE, target_insatiable_justice, exe_insatiable_justice, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "sheele1": [
        "Extase - Bisector of Creation",
        "Sheele deals 35 damage to one enemy. This ability cannot be countered, reflected, or ignored, and deals 15 more damage if the target has destructible defense.",
        [0,0,0,1,1,0], Target.SINGLE, default_target("HOSTILE"), exe_extase, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "sheele2": [
        "Savior Strike",
        "Sheele deals 25 damage to one enemy. If that enemy is using an Action ability, that ability is ended as though that character were stunned.",
        [0,0,0,1,1,0], Target.SINGLE, default_target("HOSTILE"), exe_savior_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "sheele3": [
        "Trump Card - Blinding Light",
        "Target enemy is stunned for two turns. During this time, they cannot reduce damage or become invulnerable and Extase - Bisector of Creation will deal 10 additional damage to them.",
        [0,0,1,1,0,5], Target.SINGLE, default_target("HOSTILE"), exe_blinding_light, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STUN]
    ],
    "sheele4": [
        "Extase Block",
        "Sheele becomes invulnerable for one turn.",
        [0,0,0,0,1,4], Target.SINGLE, default_target("SELF"), exe_extase_block, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shigaraki1": [
        "Decaying Touch",
        "Shigaraki deals 5 affliction damage to target enemy for the rest of the game. This damage is doubled each time Decaying Touch is applied.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_decaying_touch, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "shigaraki2": [
        "Decaying Breakthrough",
        "Shigaraki applies a stack of Decaying Touch to all enemies.",
        [1, 0, 0, 0, 2, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_decaying_breakthrough, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "shigaraki3": [
        "Destroy What You Hate, Destroy What You Love",
        "Shigaraki's allies deal 10 more damage for 2 turns. During this time they take 5 more damage from all effects and cannot reduce damage or become invulnerable.",
        [0, 0, 1, 0, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_destroy_what_you_love, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shigaraki4": [
        "Kurogiri Escape", "Shigaraki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_kurogiri_escape, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "shikamaru1": [
        "Shadow Bind Jutsu",
        "Shikamaru stuns one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 4], Target.SINGLE, default_target("HOSTILE"), exe_shadow_bind_jutsu, [AbilityType.ACTION, AbilityType.MENTAL, AbilityType.STUN]
    ],
    "shikamaru2": [
        "Shadow Neck Bind",
        "Shikamaru deals 15 affliction damage to one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_shadow_neck_bind, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.AFFLICTION]
    ],
    "shikamaru3": [
        "Shadow Pin",
        "For one turn, target enemy cannot target enemies.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE,
        default_target("HOSTILE"), exe_shadow_pin, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "shikamaru4": [
        "Shikamaru Hide", "Shikamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_hide, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misaki1": [
        "Mental Out",
        "Shokuhou stuns target enemy for 2 turns. During this time, Mental Out is replaced by one of their abilities, and Shokuhou can use that ability as though she were the stunned enemy. All negative effects applied to Misaki as a result of this ability's use are applied to the stunned enemy instead.",
        [0, 0, 2, 0, 0, 3], Target.SINGLE,
        target_mental_out, exe_mental_out, [AbilityType.ACTION, AbilityType.MENTAL, AbilityType.STUN, AbilityType.UNIQUE]
    ],
    "misaki2": [
        "Exterior",
        "Shokuhou takes 40 affliction damage. For the next 4 turns, Mental Out costs 1 less mental energy and lasts 1 more turn.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF"), exe_exterior, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "misaki3": [
        "Ally Mobilization",
        "For 2 turns, both of Shokuhou's allies will ignore stuns and gain 15 damage reduction.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ALLY,
        default_target("SELFLESS"), exe_ally_mobilization, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misaki4": [
        "Loyal Guard",
        "Shokuhou becomes invulnerable for 1 turn. This ability is only usable if Shokuhou has a living ally.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE, target_loyal_guard, exe_loyal_guard, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "misakialt1": [
        "Mental Out - Order",
        "Placeholder ability to be replaced by a controlled enemy's ability.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, target_mental_out_order, exe_mental_out_order, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "snowwhite1": [
        "Enhanced Strength", "Snow White deals 15 damage to one enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE"), exe_enhanced_strength, [AbilityType.INSTANT, AbilityType.PHYSICAL]
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
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("ALL", def_type="BYPASS"), exe_hear_distress, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "snowwhite3": [
        "Lucky Rabbit's Foot",
        "Snow White targets an ally other than herself. For 1 turn, if that ally dies, they instead"
        + " return to 35 health. This healing cannot be prevented.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELFLESS"), exe_rabbits_foot, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "snowwhite4": [
        "Leap", "Snow White becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_leap, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "swimswim1": [
        "Ruler", "Swim Swim deals 25 damage to target enemy.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_ruler, exe_ruler, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "swimswim2": [
        "Dive",
        "Swim Swim ignores all hostile effects for one turn. The following turn, her abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("SELF"), exe_dive, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "swimswim3": [
        "Vitality Pills",
        ("For 3 turns, Swim Swim gains 10 points of damage reduction and her"
        " abilities will deal 10 more damage."),
        [0, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("SELF"), exe_vitality_pills, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "swimswim4": [
        "Water Body", "Swim Swim becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF"), exe_water_body, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "tatsumaki1": [
        "Rubble Barrage",
        "Tatsumaki deals 10 damage to all enemies for two turns.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE"), exe_rubble_barrage, [AbilityType.INSTANT, AbilityType.MENTAL]
    ],
    "tatsumaki2": [
        "Arrest Assault",
        ("Tatsumaki's team gains 10 points of damage reduction for one turn."
        " This effect is invisible. After being used, this ability is replaced "
        "by Return Assault for one turn."), [0, 0, 1, 0, 0,
                                              3], Target.MULTI_ALLY,
        default_target("HELPFUL"), exe_arrest_assault, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "tatsumaki3": [
        "Gather Power",
        "Tatsumaki gains one random energy and one stack of Gather Power. For each stack of Gather Power on her, Rubble Barrage"
        +
        " deals 5 more damage, Arrest Assault grants 5 more damage reduction, and Gather Power has one less cooldown.",
        [0, 0, 1, 0, 0, 4], Target.SINGLE, default_target("SELF"), exe_gather_power, [AbilityType.INSTANT, AbilityType.MENTAL, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "tatsumaki4": [
        "Psionic Barrier", "Tatsumaki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_psionic_barrier, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "tatsumakialt1": [
        "Return Assault",
        "Tatsumaki deals 0 damage to all enemies. This ability deals 10 more damage for every damaging ability Tatsumaki's team received on the previous turn.",
        [0, 0, 1, 0, 1, 2], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_return_assault, [AbilityType.INSTANT, AbilityType.MENTAL]
    ],
    "todoroki1": [
        "Quirk - Half-Cold",
        "Deals 20 damage to all enemies and lowers their damage dealt by 10 for one turn. Increases the cost of all of Todoroki's abilities by one random energy until he uses Flashfreeze Heatwave.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_half_cold, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "todoroki2": [
        "Quirk - Half-Hot",
        "Deals 30 damage to one enemy and 10 damage to Todoroki's allies. The damage dealt to Todoroki's allies is permanently increased by 10 with each use until he uses Flashfreeze Heatwave.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_half_hot, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.UNIQUE]
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
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_ice_rampart, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "tatsumi1": [
        "Killing Strike",
        "Tatsumi deals 25 damage to one enemy. If that enemy is stunned or below half"
        + " health, they take 10 more damage. Both damage boosts can occur.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_killing_strike, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "tatsumi2": [
        "Incursio",
        "For four turns, Tatsumi gains 25 points of destructible defense and "
        + "Neuntote becomes usable.", [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_incursio, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "tatsumi3": [
        "Neuntote",
        "Tatsumi deals 25 damage to target enemy. For two turns, that enemy receives double"
        + " damage from Neuntote. This effect stacks.", [0, 0, 0, 1, 1,
                                                         0], Target.SINGLE, default_target("HOSTILE", prep_req="Incursio"), exe_neuntote, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "tatsumi4": [
        "Invisibility", "Tatsumi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_invisibility, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "toga1": [
        "Thirsting Knife",
        "Toga deals 10 damage to one enemy and applies two stacks of Quirk - Transform to them.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, default_target("HOSTILE"), exe_thirsting_knife, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "toga2": [
        "Vacuum Syringe",
        "Toga deals 10 affliction damage to one enemy for 3 turns. Each turn, she applies a stack of Quirk - Transform to them.", [0, 0, 0, 0, 2, 1], Target.SINGLE, default_target("HOSTILE"), exe_vacuum_syringe, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.AFFLICTION]
    ],
    "toga3": [
        "Quirk - Transform",
        "Toga consumes all stacks of Quirk - Transform on one enemy, turning into a copy of them"
        + " for one turn per stack consumed. This effect ignores invulnerability.", [0, 0, 0, 0, 1,
                                                5], Target.SINGLE, target_transform, exe_transform, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "toga4": [
        "Toga Dodge", "Toga becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_toga_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "touka1":[
        "Draw Stance",
        "Touka enters Draw Stance for one turn and this ability is replaced by Raikiri. During this time, she will counter the first harmful ability to target her and deal 15 damage to the countered enemy, and this effect will end.",
        [0,0,0,0,0,2],
        Target.SINGLE, default_target("SELF"), exe_draw_stance, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    
    ],
    "touka2":[
        "Nukiashi",
        "For the next 3 turns, Draw Stance and Raikou are invisible. This effect is invisible.",
        [0,0,1,0,0,4],
        Target.SINGLE, default_target("SELF"), exe_nukiashi, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "touka3":[
        "Raikou",
        "Touka deals 20 damage to one enemy. For one turn, any ability they use has its cooldown increased by 2.",
        [0,1,0,0,0,0],
        Target.SINGLE, default_target("HOSTILE"), exe_raiou, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "touka4":[
        "Lightning Speed Dodge",
        "Touka becomes invulnerable for one turn.",
        [0,0,0,0,1,4],
        Target.SINGLE, default_target("SELF"), exe_lightning_speed_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "toukaalt1":[
        "Raikiri",
        "Touka deals 40 piercing damage to one enemy.",
        [0,0,0,1,1,0],
        Target.SINGLE, default_target("HOSTILE"), exe_touka_raikiri, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "tsunayoshi1": [
        "X-Burner",
        "Tsuna deals 25 damage to one enemy and 15 damage to all others.",
        [0, 1, 0, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_xburner, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "tsunayoshi2": [
        "Zero Point Breakthrough",
        "For one turn, the first harmful ability used on Tsuna" +
        " will be countered, and the countered enemy will be stunned for two turns. If this successfully"
        +
        " counters an ability, Tsuna will deal 10 additional damage with X-Burner for two turns.",
        [0, 0, 0, 0, 2, 4], Target.SINGLE, default_target("SELF"), exe_zero_point_breakthrough, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "tsunayoshi3": [
        "Burning Axle",
        "Tsuna deals 35 damage to one enemy. For one turn, if that enemy takes new"
        + " damage, they are stunned for one turn and take 15 damage.",
        [0, 1, 0, 1, 1, 3], Target.SINGLE, default_target("HOSTILE"), exe_burning_axle, [AbilityType.INSTANT, AbilityType.PHYSICAL, AbilityType.STUN]
    ],
    "tsunayoshi4": [
        "Flare Burst", "Tsuna becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_flare_burst, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "uraraka1": [
        "Quirk - Zero Gravity",
        "Uraraka targets one enemy or one ally for 3 turns. If used on an enemy, that enemy will take 10 more non-affliction damage from all sources and be unable to reduce damage"
        +
        " or become invulnerable. If used on an ally, that ally will gain 10 points of damage reduction and their abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("ALL"), exe_zero_gravity, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "uraraka2": [
        "Meteor Storm",
        "Uraraka deals 15 damage to all enemies. If a damaged enemy is currently targeted by Zero Gravity, that enemy will be stunned for one turn. If an ally is currently targeted by "
        +
        "Zero Gravity, they will deal 5 more damage with abilities this turn.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_meteor_storm, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "uraraka3": [
        "Comet Home Run",
        "Uraraka deals 20 damage to one enemy. If the damaged enemy is currently targeted by Zero Gravity, that enemy will lose one random energy. If an ally is currently targeted by "
        + "Zero Gravity, they will become invulnerable for one turn.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_comet_home_run, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "uraraka4": [
        "Gunhead Martial Arts", "Uraraka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_float, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "wendy3": [
        "Troia",
        "Wendy heals target ally for 40 health. For 3 turns, this ability will have 50% effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HELPFUL"), exe_troia, [AbilityType.INSTANT, AbilityType.ENERGY, AbilityType.STRATEGIC]
    ],
    "wendy2": [
        "Shredding Wedding",
        "For three turns, Wendy and target enemy will take 20 piercing damage when they attempt to target anyone that isn't each other. During this time, any other characters that attempt to target either will take 20 piercing damage and Shredding Wedding becomes Piercing Winds.",
        [0, 2, 0, 0, 0, 5], Target.SINGLE, default_target("HOSTILE"), exe_shredding_wedding, [AbilityType.ACTION, AbilityType.ENERGY, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "wendy1": [
        "Sky Dragon's Roar",
        "Deals 20 damage to all enemies and heals Wendy for 15 health.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_sky_dragons_roar, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "wendy4": [
        "Wendy Dodge", "Wendy becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_wendy_dodge, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "wendyalt1": [
        "Piercing Winds",
        "Wendy deals 25 piercing damage to the enemy affected by Shredding Wedding.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", mark_req="Shredding Wedding"), exe_piercing_winds, [AbilityType.INSTANT, AbilityType.ENERGY]
    ],
    "yamamoto1": [
        "Shinotsuku Ame",
        "Yamamoto deals 30 damage to one enemy and reduces the damage they deal by 10 for three turns. Grants Yamamoto"
        +
        " one stack of Asari Ugetsu. Using this ability on an enemy already affected by it will refresh the effect.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE, default_target("HOSTILE"), exe_shinotsuku_ame, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "yamamoto2": [
        "Utsuhi Ame",
        "On the following turn, Yamamoto will deal 20 damage to target enemy and grant himself one stack of"
        + " Asari Ugetsu. If that enemy uses a new ability " +
        "during this time, Yamamoto deals 40 damage to them and grants himself 3 stacks of Asari Ugetsu instead.",
        [0, 0, 0, 1, 0, 2], Target.SINGLE, default_target("HOSTILE"), exe_utsuhi_ame, [AbilityType.ACTION, AbilityType.PHYSICAL, AbilityType.UNIQUE]
    ],
    "yamamoto3": [
        "Asari Ugetsu",
        "Consumes all stacks of Asari Ugetsu on use, and remains active for one turn plus one per stack consumed. While active, replaces Shinotsuku Ame with Scontro di Rondine and "
        +
        "Utsuhi Ame with Beccata di Rondine, and Yamamoto gains 20 points of damage reduction.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE, default_target("SELF", lockout=(EffectType.ALL_DR, "Asari Ugetsu")), exe_asari_ugetsu, [AbilityType.INSTANT, AbilityType.STRATEGIC, AbilityType.UNIQUE]
    ],
    "yamamoto4": [
        "Sakamaku Ame", "Yamamoto becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF"), exe_sakamaku_ame, [AbilityType.INSTANT, AbilityType.STRATEGIC]
    ],
    "yamamotoalt1": [
        "Scontro di Rondine",
        "Yamamoto deals 20 damage to one enemy. If that enemy's damage is being reduced by at least 10, this ability deals 10 bonus damage.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE"), exe_scontro_di_rondine, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    "yamamotoalt2": [
        "Beccata di Rondine",
        "Yamamoto deals 5 damage to all enemies and reduces their damage dealt by 5 for 3 turns.",
        [0, 0, 0, 1, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE"), exe_beccata_di_rondine, [AbilityType.INSTANT, AbilityType.PHYSICAL]
    ],
    #"" : ["", "", [], Target.],
}
