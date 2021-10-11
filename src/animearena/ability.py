from operator import add
from random import randint
import PIL
from PIL import Image
from pathlib import Path
import sdl2
import sdl2.ext
import enum
import copy

from animearena.effects import EffectType, Effect

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
            self.image = Image.open(RESOURCES / (name + ".png"))
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

    if not user.has_effect(EffectType.MARK, "Heartbeat Distortion"):
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

    if not user.has_effect(EffectType.MARK, "Heartbeat Surround"):
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
        if (enemy.has_effect(EffectType.MARK, "Thirsting Knife") and enemy.get_effect(EffectType.MARK, "Thirsting Knife").user == user) or (enemy.has_effect(EffectType.MARK, "Vacuum Syringe") and enemy.get_effect(EffectType.MARK, "Vacuum Syringe").user == user):
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():

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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(Ability("akame1"), EffectType.MARK, user, 3, lambda eff: "Akame can use One Cut Killing on this character."))
    user.check_on_use()

def exe_one_cut_killing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():

        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
            user.add_effect(Effect(Ability("cmaryalt1"), EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Quickdraw - Pistol has been replaced by Quickdraw - Rifle.", mag=11))
        user.check_on_use()
        user.check_on_harm()

def exe_mine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 4, lambda eff: "If this character uses a new ability, they will take 20 piercing damage and this effect will end."))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 4, lambda eff: "Grenade Toss will deal 20 additional damage to this character."))
        user.check_on_use()
        user.check_on_harm()

def exe_grenade_toss(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():

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
    if not user.check_countered():

        for target in user.current_targets:
            base_damage = 15
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(base_damage, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
            user.add_effect(Effect(user.used_ability, EffectType.CONT_USE, user, 3, lambda eff: "Calamity Mary is using Quickdraw - Rifle. This effect will end if she is stunned. If this effect expires normally, Quickdraw - Rifle will be replaced by Quickdraw - Sniper."))


        user.check_on_use()
        user.check_on_harm()

def exe_sniper(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():

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
    if not user.check_countered():
        for target in user.current_targets:
            base_damage = 35
            if target.final_can_effect("BYPASS"):
                user.deal_pierce_damage(base_damage, target)
        user.check_on_harm()
        user.check_on_use()

def exe_active_combat_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "If Chrome's destructible defense is not broken, this character will receive 25 damage and be stunned for one turn."))
                user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 3, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=20))
        user.check_on_use()
        user.check_on_harm()


def exe_mental_immolation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.COST_ADJUST, user, 6, lambda eff: "This character's ability costs are increased by 1 random.", mag=51))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "This effect will end if this character uses a new ability."))
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "This character can be targeted by Merciless Finish."))
            user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Illusory Disorientation has been replaced by Merciless Finish.", mag = 11))
        user.check_on_use()
        user.check_on_harm()

def exe_fortissimo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
        if target.helpful_target(user, ):
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "This character will ignore counter effects."))
    user.check_on_use()
    user.check_on_help()

def exe_cranberry_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Cranberry is invulnerable."))
    user.check_on_use()

def exe_merciless_finish(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    user.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 280000, lambda eff: "Erza will ignore affliction damage."))
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "Erza will deal 15 damage to all enemies.", mag=15))
        user.check_on_use()
        user.check_on_harm()

def exe_nakagamis_starlight(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_pierce_damage(35, target)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_iron_shadow_dragon_club(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(20, target)
        user.check_on_use()
        user.check_on_harm()

def exe_handcuffs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_DMG, user, 3, lambda eff: "This character will take 15 damage.", mag=15))
        user.check_on_use()
        user.check_on_harm()        


def exe_hammer(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
    if not user.check_countered():
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
#region Hinata Execution (Tests)
def exe_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                if user.has_effect(EffectType.MARK, "Byakugan"):
                    target.source.energy_contribution -= 1
                    user.check_on_drain(target)
        user.check_on_use()
        user.check_on_harm()

def exe_hinata_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    counterable = False
    for target in user.current_targets:
        if target.id > 2:
            counterable = True
    if counterable and not user.check_countered():
        drained = False
        for target in user.current_targets:
            if target.id > 2 and target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_damage(15, target)
                if user.has_effect(EffectType.MARK, "Byakugan") and not drained:
                    target.source.energy_contribution -= 1
                    drained = True
                    user.check_on_drain(target)
            elif target.id < 3 and target.helpful_target():
                target.add_effect(Effect(user.used_ability, EffectType.ALL_DR, user, 4, lambda eff: "This character has 10 points of damage reduction.", mag=10))
        if not user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
            user.add_effect(Effect(user.used_ability, EffectType.MARK, user, 3, lambda eff: "Eight Trigrams - 64 Palms will deal 15 damage to all enemies."))
        else:
            user.get_effect(EffectType.MARK, "Eight Trigrams - 64 Palms").duration = 3
        user.check_on_use()
        user.check_on_harm()
    else:
        for target in user.current_targets:
            if target.helpful_target():
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
#region Ichigo Execution (Tests)
def exe_getsuga_tenshou(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if user.has_effect(EffectType.MARK, "Tensa Zangetsu"):
        def_type = "BYPASS"
        dmg_pierce = True
    else:
        def_type = user.check_bypass_effects()
        dmg_pierce = False
    if not user.check_countered():
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
    user.add_effect(Effect(user.used_ability, EffectType.TARGET_SWAP, user, 3, lambda eff: "Zangetsu Slash will target all enemies.", mag=31))
    user.source.energy_contribution += 1
    user.check_on_use()

def exe_zangetsu_slash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            base_damage = 20
            if user.has_effect(EffectType.STACK, "Zangetsu Slash") and user.can_boost():
                base_damage += (5 * user.get_effect(EffectType.STACK, "Zangetsu Slash").mag)
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(base_damage, user)
            user.apply_stack_effect(Effect(user.used_ability, EffectType.STACK, user, 280000, lambda eff: f"Zangetsu Slash will deal {5 * eff.mag} more damage.", mag = 1))
        user.check_on_use()
        user.check_on_harm()

def exe_zangetsu_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ichigo is invulnerable."))
    user.check_on_use()
#endregion
#region Ichimaru Execution (Tests)
def exe_butou_renjin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(15, target)
                target.apply_stack_effect(Effect(Ability("ichimaru3"), EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1), user)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_UNIQUE, user, 3, lambda eff: "This character will take 15 damage."))
        user.check_on_use()
        user.check_on_harm()

def exe_13_kilometer_swing(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(25, target)
                target.apply_stack_effect(Effect(Ability("ichimaru3"), EffectType.STACK, user, 280000, lambda eff: f"This character will take {10 * eff.mag} affliction damage from Kill, Kamishini no Yari.", mag=1), user)
        user.check_on_use()
        user.check_on_harm()

def exe_kamishini_no_yari(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect("BYPASS"):
                base_damage = 10 * target.get_effect_with_user(EffectType.STACK, "Kill, Kamishini no Yari", user).mag
                user.deal_aff_damage(base_damage, target)
                if target.has_effect_with_user(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari", user):
                    target.get_effect_with_user(EffectType.CONT_AFF_DMG, "Kill, Kamishini no Yari", user).mag += base_damage
                else:
                    target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: f"This character will take {eff.mag} affliction damage.", mag = base_damage))
        user.check_on_use()
        user.check_on_harm()

def exe_shinso_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Ichimaru is invulnerable."))
    user.check_on_use()

#endregion
#region Jack Execution (Tests)
def exe_maria_the_ripper(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
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
            target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "This character can be targeted by Maria the Ripper."))
            target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 5, lambda eff: "This character will take 5 affliction damage.", mag=5))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 5, lambda eff: "Fog of London has been replaced by Streets of the Lost.", mag = 22))
    user.check_on_use()
    user.check_on_harm()

def exe_we_are_jack(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_aff_damage(30, target)
        user.check_on_use()
        user.check_on_harm()

def exe_smokescreen_defense(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 2, lambda eff: "Jack is invulnerable."))
    user.check_on_use()

def exe_streets_of_the_lost(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.MARK, user, 5, lambda eff: "This character can be targeted by Maria the Ripper and We Are Jack."))
                target.add_effect(Effect(user.used_ability, EffectType.ISOLATE, user, 6, lambda eff: "This character is isolated."))
                target.add_effect(Effect(user.used_ability, EffectType.UNIQUE, user, 6, lambda eff: "This character can only target Jack."))
    user.check_on_use()
    user.check_on_harm()
#endregion
#region Itachi Execution (Tests)
def exe_amaterasu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()) and not target.deflecting():
                user.deal_aff_damage(10, target)
                target.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "This character will take 10 affliction damage.", mag=10))
        user.check_on_use()
        user.check_on_harm()


def exe_tsukuyomi(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 6, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_susanoo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.DEST_DEF, user, 280000, lambda eff: f"This character has {eff.mag} points of destructible defense.", mag=45))
    user.add_effect(Effect(user.used_ability, EffectType.CONT_AFF_DMG, user, 280000, lambda eff: "Itachi will take 10 affliction damage. If his health falls below 20, Susano'o will end.", mag=10))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Amaterasu has been replaced by Totsuka Blade.", mag=11))
    user.add_effect(Effect(user.used_ability, EffectType.ABILITY_SWAP, user, 280000, lambda eff: "Tsukuyomi has been replaced by Yata Mirror.", mag=22))
    user.receive_eff_aff_damage(10)
    user.check_on_use()

def exe_crow_genjutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(user.used_ability, EffectType.ALL_INVULN, user, 280000, lambda eff: f"Itachi is invulnerable."))
    user.check_on_use()

def exe_totsuka_blade(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        for target in user.current_targets:
            if target.final_can_effect(user.check_bypass_effects()):
                user.deal_damage(35, target)
                target.add_effect(Effect(user.used_ability, EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
        user.check_on_use()
        user.check_on_harm()

def exe_yata_mirror(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.get_effect(EffectType.DEST_DEF, "Susano'o").alter_dest_def(20)
    user.receive_eff_aff_damage(5)
    user.check_on_use()
#endregion
#region Jiro Execution (Incomplete)
def exe_counter_balance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    


def exe_heartbeat_distortion(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_heartbeat_surround(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_early_detection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Kakashi Execution (Incomplete)
def exe_copy_ninja(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_nindogs(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_raikiri(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_kamui(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Kuroko Execution (Incomplete)
def exe_teleporting_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_needle_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_judgement_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_kuroko_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Lambo Execution (Incomplete)
def exe_ten_year_bazooka(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_conductivity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_summon_gyudon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_lampows_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_thunder_set_charge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_elettrico_cornata(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region La Pucelle Execution (Incomplete)
def exe_knights_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_magic_sword(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_ideal_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_knights_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Laxus Execution (Incomplete)
def exe_fairy_law(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_lightning_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_thunder_palace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_laxus_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Leone Execution (Incomplete)
def exe_lionel(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_beast_instinct(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_lion_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_instinctual_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Levy Execution (Incomplete)
def exe_solidscript_fire(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_solidscript_silent(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_solidscript_mask(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_solidscript_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Raba Execution (Incomplete)
def exe_crosstail_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_wire_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_heartseeker_thrust(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_defensive_netting(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Lucy Execution (Incomplete)
def exe_aquarius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_gemini(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_capricorn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_leo(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_urano_metria(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Midoriya Execution (Incomplete)
def exe_smash(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_air_force_gloves(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_shoot_style(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_enhanced_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Minato Execution (Incomplete)
def exe_flying_raijin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_marked_kunai(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_partial_shiki_fuujin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_minato_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Mine Execution (Incomplete)
def exe_roman_artillery_pumpkin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_cutdown_shot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_pumpkin_scouter(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_closerange_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Mirai Execution (Incomplete)
def exe_blood_suppression_removal(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_blood_sword_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_blood_shield(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_mirai_deflect(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_blood_bullet(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Mirio Execution (Incomplete)
def exe_permeation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_phantom_menace(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_protect_ally(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_mirio_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Misaka Execution (Incomplete)
def exe_railgun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_iron_sand(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_electric_rage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_electric_deflection(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
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
#region Naruha Execution (Incomplete)
def exe_bunny_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_rampage_suit(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_piercing_umbrella(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_rabbit_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_enraged_blow(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Natsu Execution (Incomplete)
def exe_fire_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_fire_dragons_iron_fist(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_fire_dragons_sword_horn(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_natsu_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Neji Execution (Incomplete)
def exe_neji_trigrams(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_neji_mountain_crusher(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_selfless_genius(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_revolving_heaven(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_chakra_point_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Nemurin Execution (Incomplete)
def exe_nemurin_nap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_nemurin_beam(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_dream_manipulation(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_dream_sovereignty(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Orihime Execution (Incomplete)
def exe_tsubaki(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_ayame_shuno(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_lily_hinagiku_baigon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_i_reject(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Ripple Execution (Incomplete)
def exe_perfect_accuracy(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_shuriken_throw(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_countless_stars(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_ripple_block(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Rukia Execution (Incomplete)
def exe_first_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_second_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_third_dance(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_rukia_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Ruler Execution (Incomplete)
def exe_in_the_name_of_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_minael_yunael(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_tama(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_swim_swim(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Ryohei Execution (Incomplete)
def exe_maximum_cannon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_kangaryu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_vongola_headgear(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_to_the_extreme(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Saber Execution (Incomplete)
def exe_excalibur(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_wind_blade_combat(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_avalon(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_saber_parry(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Saitama Execution (Incomplete)
def exe_one_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_consecutive_normal_punches(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_serious_punch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_sideways_jumps(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Seiryu Execution (Incomplete)
def exe_body_mod_arm_gun(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_raging_koro(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_berserker_howl(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_koro_defense(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_self_destruct(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_insatiable_justice(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Shigaraki Execution (Incomplete)
def exe_decaying_touch(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_decaying_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_destroy_what_you_love(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_kurogiri_escape(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Shikamaru Execution (Incomplete)
def exe_shadow_bind_jutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_shadow_neck_bind(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_shadow_pin(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_hide(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Shokuhou Execution (Incomplete)
def exe_mental_out(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_exterior(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_ally_mobilization(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
def exe_loyal_guard(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Snow White Execution (Incomplete)
def exe_enhanced_strength(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_hear_distress(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_rabbits_foot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
def exe_leap(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region SwimSwim Execution (Incomplete)
def exe_ruler(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_dive(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_vitality_pills(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_water_body(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Tatsumaki Execution (Incomplete)
def exe_rubble_barrage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_arrest_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_gather_power(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_psionic_barrier(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_return_assault(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Todoroki Execution (Incomplete)
def exe_half_cold(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_half_hot(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_flashfreeze_heatwave(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_ice_rampart(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Tatsumi Execution (Incomplete)
def exe_killing_strike(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_incursio(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_neuntote(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_invisibility(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Toga Execution (Incomplete)
def exe_thirsting_knife(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_vacuum_syringe(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_transform(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_toga_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Tsunayoshi Execution (Incomplete)
def exe_xburner(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_zero_point_breakthrough(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_burning_axle(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_flare_burst(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Uraraka Execution (Incomplete)
def exe_zero_gravity(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_meteor_storm(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_comet_home_run(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_float(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Wendy Execution (Incomplete)
def exe_troia(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_shredding_wedding(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_sky_dragons_roar(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_wendy_dodge(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_piercing_winds(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
#endregion
#region Yamamoto Execution (Incomplete)
def exe_shinotsuku_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_utsuhi_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_asari_ugetsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_sakamaku_ame(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_scontro_di_rondine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass

def exe_beccata_di_rondine(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    pass
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
        default_target("HOSTILE")
    ],
    "hinata2": [
        "Eight Trigrams - 64 Palms",
        "Hinata gives her entire team 10 points of damage reduction for 2 turns. If used again within 2 turns, this ability will also deal 15 damage to the enemy team.",
        [1, 0, 0, 0, 0, 0], Target.MULTI_ALLY, target_eight_trigrams
    ],
    "hinata3": [
        "Byakugan",
        "For 3 turns, Hinata removes one energy from one of her targets whenever she deals damage.",
        [0, 1, 0, 0, 0, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "hinata4": [
        "Gentle Fist Block", "Hinata becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "ichigo1": [
        "Getsuga Tenshou",
        "Ichigo fires a wave of energy from the edge of his zanpakutou, dealing"
        +
        " 40 damage to one enemy. If used on the turn after Tensa Zangetsu, it will "
        + "ignore invulnerability and deal piercing damage.",
        [0, 0, 0, 1, 2, 1], Target.SINGLE, target_getsuga_tenshou
    ],
    "ichigo2": [
        "Tensa Zangetsu",
        "Ichigo activates his zanpakutou's true strength, gaining enhanced combat abilities and speed. "
        + "Ichigo gains one random energy and is invulnerable for two turns." +
        " The turn after this ability " +
        "is used, Getsuga Tenshou and Zangetsu Strike are improved.",
        [1, 0, 0, 1, 0, 6], Target.SINGLE,
        default_target("SELF")
    ],
    "ichigo3": [
        "Zangetsu Strike",
        "Ichigo slashes one enemy with Zangetsu, dealing 20 damage to them and permanently "
        +
        "increasing Zangetsu Strike's damage by 5. If used on the turn after "
        +
        "Tensa Zangetsu, it will target all enemies and permanently increase Zangetsu Strike's "
        + "damage by 5 per enemy struck.", [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "ichigo4": [
        "Zangetsu Block", "Ichigo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
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
        [1, 0, 0, 0, 0, 0], Target.SINGLE, target_maria_the_ripper
    ],
    "jack2": [
        "Fog of London",
        "Jack deals 5 affliction damage to all enemies for 3 turns. During this time, Fog of London is replaced by Streets of the Lost. This ability cannot be countered.",
        [0, 0, 1, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "jack3": [
        "We Are Jack",
        "Jack deals 30 affliction damage to an enemy affected by Streets of the Lost.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Streets of the Lost")
    ],
    "jack4": [
        "Smokescreen Defense", "Jack becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "jackalt1": [
        "Streets of the Lost",
        "For 3 turns, target enemy is isolated and can only target Jack. During this time, We Are Jack is usable.",
        [0, 0, 1, 0, 1, 5], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "itachi1": [
        "Amaterasu",
        "Itachi deals 10 affliction damage to one enemy for the rest of the game. This effect does not stack.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.CONT_AFF_DMG, "Amaterasu"))
    ],
    "itachi2": [
        "Tsukuyomi",
        "Itachi stuns one target for 3 turns. This effect will end early if an ally uses a skill on them.",
        [0, 0, 2, 0, 0, 4], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "itachi3": [
        "Susano'o",
        "Itachi gains 45 destructible defense, and takes 10 affliction damage each turn. During this time, Amaterasu is replaced by Totsuka Blade and Tsukuyomi is replaced by"
        +
        " Yata Mirror. If Itachi falls below 20 health or he loses all his destructible defense, Susano'o will end.",
        [0, 2, 0, 0, 0, 6], Target.SINGLE,
        default_target("SELF")
    ],
    "itachi4": [
        "Crow Genjutsu", "Itachi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "itachialt1": [
        "Totsuka Blade",
        "Itachi deals 35 damage to one enemy and stuns them for one turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "itachialt2": [
        "Yata Mirror",
        "Itachi's Susano'o regains 20 destructible defense and Itachi loses 5 health.",
        [0, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("SELF")
    ],
    "jiro1": [
        "Counter-Balance",
        "For one turn, any enemy that stuns Jiro or her allies will lose one energy, and any enemy that drains energy from Jiro or her allies will be stunned for one turn. This effect is invisible.",
        [0, 1, 0, 0, 0, 2], Target.MULTI_ALLY,
        default_target("HELPFUL")
    ],
    "jiro2": [
        "Heartbeat Distortion",
        "Jiro deals 5 damage to the enemy team for 4 turns. During this time, Heartbeat Distortion cannot be used and Heartbeat Surround will cost one less random energy and deal 20 damage to a single enemy. This ability"
        +
        " ignores invulnerability against enemies affected by Heartbeat Surround.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, target_heartbeat_distortion
    ],
    "jiro3": [
        "Heartbeat Surround",
        "Jiro deals 10 damage to one enemy for 4 turns. During this time, Heartbeat Surround cannot be used and Heartbeat Distortion will cost one less random energy and deal 15 damage to all enemies. This ability ignores invulnerability "
        + "against enemies affected by Heartbeat Distortion.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE, target_heartbeat_surround
    ],
    "jiro4": [
        "Early Detection", "Jiro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "kakashi1": [
        "Copy Ninja Kakashi",
        "For one turn, Kakashi will reflect the first hostile ability that targets him. This ability is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "kakashi2": [
        "Summon - Nin-dogs",
        "Target enemy takes 20 damage and is stunned for one turn. During this time, they take double damage from Raikiri.",
        [0, 1, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "kakashi3": [
        "Raikiri", "Kakashi deals 40 piercing damage to target enemy.",
        [0, 2, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "kakashi4": [
        "Kamui",
        "Kakashi targets one enemy or himself, ignoring invulnerability. If used on himself, Kakashi will ignore all harmful effects for one turn. If used on an enemy, this ability will deal"
        +
        " 20 piercing damage to them. If they are invulnerable, they will become isolated for one turn.",
        [0, 1, 0, 0, 0, 4], Target.SINGLE, target_kamui
    ],
    "kuroko2": [
        "Teleporting Strike",
        "Kuroko deals 10 damage to one enemy and becomes invulnerable for one turn. If used on the turn after "
        +
        "Needle Pin, this ability will have no cooldown. If used on the turn after Judgement Throw, this ability will deal 15 extra damage.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "kuroko3": [
        "Needle Pin",
        "One enemy becomes unable to reduce damage or become invulnerable for two turns. If used on the turn after Teleporting Strike, "
        +
        "this ability ignores invulnerability and deals 15 piercing damage to its target. If used on the turn after Judgement Throw, this ability will stun its target for one turn.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_needle_pin
    ],
    "kuroko1": [
        "Judgement Throw",
        "Kuroko deals 15 damage to one enemy and reduces their damage dealt by 10 for one turn. If used on the turn"
        +
        " after Teleporting Strike, this ability will have double effect. If used on the turn after Needle Pin, this ability will remove one energy from its target.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "kuroko4": [
        "Kuroko Dodge", "Kuroko is invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "lambo1": [
        "Ten-Year Bazooka",
        "Lambo switches places with himself ten years in the future. The first time this is used, Conductivity"
        +
        " will be replaced by Thunder, Set, Charge! for three turns. If used again, Thunder, Set, Charge! will be replaced by Elettrico Cornata for two turns.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "lambo2": [
        "Conductivity",
        "For two turns, Lambo's allies receive 20 points of damage reduction. If they receive damaging abilities during this time, "
        + "Lambo will take 10 damage.", [0, 0, 0, 0, 1, 2], Target.MULTI_ALLY,
        default_target("HELPFUL")
    ],
    "lambo3": [
        "Summon Gyudon",
        "Lambo's team gains 10 points of damage reduction permanently. During this time, the enemy team receives 5 points of damage each turn. This skill will end if "
        + "Ten-Year Bazooka is used.", [0, 0, 0, 1, 2, 4], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "lambo4": [
        "Lampow's Shield", "Lambo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "lamboalt1": [
        "Thunder, Set, Charge!", "Lambo deals 25 damage to one enemy.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "lamboalt2": [
        "Elettrico Cornata", "Lambo deals 35 damage to all enemies.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "pucelle1": [
        "Knight's Sword", "La Pucelle deals 20 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "pucelle2": [
        "Magic Sword",
        "La Pucelle commands her sword to grow, permanently increasing its damage by 20, its cost by 1 random, and its cooldown by 1.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "pucelle3": [
        "Ideal Strike",
        "La Pucelle deals 40 piercing damage to one enemy. This ability ignores invulnerability, cannot be countered, and can only be used if La Pucelle is below 50 health.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE, target_ideal_strike
    ],
    "pucelle4": [
        "Knight's Guard", "La Pucelle becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "laxus1": [
        "Fairy Law",
        "Laxus deals 20 damage to all enemies and restores 20 health to all allies.",
        [0, 0, 0, 0, 3, 5], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "laxus2": [
        "Lightning Dragon's Roar",
        "Laxus deals 40 damage to one enemy and stuns them for one turn. When the stun wears off, the target receives 10 more damage for 1 turn.",
        [0, 2, 0, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "laxus3": [
        "Thunder Palace",
        "After 2 turns, Laxus deals 40 damage to the entire enemy team. Dealing damage to Laxus during these two turns will cancel this effect,"
        +
        " dealing damage equal to the original damage of the move that damaged him to the user.",
        [0, 1, 0, 0, 2, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "laxus4": [
        "Laxus Block", "Laxus becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "leone1": [
        "King of Beasts Transformation - Lionel",
        "Leone activates her Teigu, permanently allowing the use of her other moves and causing her to heal 10 health per turn."
        +
        " This healing is increased by 10 at the end of a turn in which she did damage to an enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "leone2": [
        "Beast Instinct",
        "Leone targets herself or an enemy for 3 turns. If used on an enemy, Lion Fist will ignore invulnerability and deal 20 additional damage to them. If"
        +
        " used on Leone, she will ignore counters and stuns for the duration.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, target_beast_instinct
    ],
    "leone3": [
        "Lion Fist",
        "Leone deals 35 damage to target enemy. If this ability kills an enemy while Leone is affected by Beast Instinct, Beast Instinct's duration will refresh. "
        +
        "If this ability kills an enemy that is affected by Beast Instinct, Leone will heal for 20 health.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE",
                       prep_req="King of Beasts Transformation - Lionel")
    ],
    "leone4": [
        "Instinctual Dodge",
        "Leone becomes invulnerable for one turn. Using this ability counts as a damaging ability for triggering King of Beasts Transformation - Lionel's healing.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "levy1": [
        "Solid Script - Fire",
        "Levy marks all enemies for one turn. During this time, if they use a new ability, they will take 10 affliction damage. When this ability"
        + " ends, all affected enemies take 10 affliction damage.",
        [0, 0, 1, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "levy2": [
        "Solid Script - Silent",
        "For two turns, all characters become isolated. This ability cannot be countered or ignored and ignores invulnerability.",
        [0, 0, 1, 0, 2, 3], Target.ALL_TARGET,
        default_target("ALL", def_type="BYPASS")
    ],
    "levy3": [
        "Solid Script - Mask",
        "For two turns, target ally will ignore all stuns and affliction damage.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "levy4": [
        "Solid Script - Guard", "Levy becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "raba1": [
        "Cross-Tail Strike",
        "Lubbock deals 15 damage to one target and marks them with Cross-Tail Strike. Until Lubbock uses this ability on an enemy already marked with Cross-Tail Strike, this ability will cost no energy. "
        +
        "If this ability targets a marked enemy and all living enemies are marked, this ability will deal 15 piercing damage to all marked enemies, ignoring invulnerability. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "raba2": [
        "Wire Shield",
        "Target ally gains 15 permanent destructible defense and is marked with Wire Shield. Until Lubbock uses this ability on an ally already targeted with Wire Shield, this ability will costs no energy. "
        +
        "If this ability targets an enemy marked with Wire Shield and all living allies are marked, all marked allies become invulnerable for one turn. This effect consumes all active marks.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "raba3": [
        "Heartseeker Thrust",
        "Lubbock deals 30 piercing damage to one target. If Lubbock is marked by Wire Shield, the damaged enemy will receive 15 affliction damage on the following turn. If the target is marked by Cross-Tail Strike, "
        + "the target will become stunned for one turn.", [0, 0, 0, 1, 1,
                                                           1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "raba4": [
        "Defensive Netting", "Lubbock becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "lucy1": [
        "Aquarius",
        "Lucy deals 15 damage to all enemies and grants her team 10 points of damage reduction.",
        [0, 0, 0, 1, 1, 2], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "lucy2": [
        "Gemini",
        "For three turns, Lucy's abilities will stay active for one extra turn. During this time, this ability is replaced by Urano Metria.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "lucy3": [
        "Capricorn", "Lucy deals 20 damage to one enemy.", [0, 0, 0, 1, 0, 0],
        Target.SINGLE,
        default_target("HOSTILE")
    ],
    "lucy4": [
        "Leo", "Lucy becomes invulnerable for one turn.", [0, 0, 0, 0, 1, 4],
        Target.SINGLE,
        default_target("SELF")
    ],
    "lucyalt1": [
        "Urano Metria", "Lucy deals 20 damage to all enemies.",
        [0, 1, 0, 1, 0, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "midoriya1": [
        "SMASH!",
        "Midoriya unleashes the full power of his quirk, dealing 45 damage to one enemy. The backlash"
        +
        " from unleashing One For All's strength deals 20 affliction damage to Midoriya and stuns him for"
        + " one turn.", [1, 0, 0, 0, 2, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "midoriya2": [
        "Air Force Gloves",
        "Midoriya fires a compressed ball of air with a flick, dealing 15 damage to one enemy and"
        + " increasing the cooldown of any move they use by one for one turn.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "midoriya3": [
        "One For All - Shoot Style",
        "Midoriya unleashes his own style of One For All, dealing 20 damage to all enemies. For 1 turn,"
        + " Midoriya will counter the first ability used on him.",
        [1, 0, 0, 0, 1, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "midoriya4": [
        "Enhanced Leap", "Midoriya becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "minato1": [
        "Flying Raijin",
        "Minato deals 35 piercing damage that ignores invulnerability to one enemy. If used on a target marked with Marked Kunai, Minato becomes invulnerable for "
        +
        "one turn and the cooldown on Flying Raijin is reset. This effect consumes Marked Kunai's mark.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "minato2": [
        "Marked Kunai",
        "Minato deals 10 piercing damage to one enemy and permanently marks them.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "minato3": [
        "Partial Shiki Fuujin",
        "Minato permanently increases the cooldowns and random cost of target enemy by one. After using this skill, Minato dies.",
        [0, 0, 0, 0, 3, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "minato4": [
        "Minato Parry", "Minato becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "mine1": [
        "Roman Artillery - Pumpkin",
        "Mine deals 25 damage to one enemy. If Mine is below 60 health, this ability deals 10 more damage. If Mine is below 30 health, this ability"
        + "costs one less weapon energy.", [0, 0, 0, 1, 1, 0], Target.SINGLE, target_pumpkin
    ],
    "mine2": [
        "Cut-Down Shot",
        "Deals 25 damage to all enemies. If Mine is below 50 health, this ability will stun all targets hit for 1 turn. If Mine is below 25 health, this ability deals double damage and the damage it deals "
        + "is piercing.", [0, 0, 0, 1, 2, 3], Target.MULTI_ENEMY, target_cutdown_shot
    ],
    "mine3": [
        "Pumpkin Scouter",
        "For the next two turns, all of Mine's abilities will ignore invulnerability and deal 5 additional damage.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "mine4": [
        "Close-Range Deflection", "Mine becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "mirai1": [
        "Blood Suppression Removal",
        "For 3 turns, Mirai's abilities will cause their target to receive 10 affliction damage for 2 turns. During this time, this ability is replaced with Blood Bullet and Mirai receives 10 affliction damage per turn.",
        [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "mirai2": [
        "Blood Sword Combat", "Mirai deals 30 damage to target enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "mirai3": [
        "Blood Shield",
        "Mirai gains 20 points of destructible defense and 20 points of damage reduction for one turn.",
        [0, 1, 0, 0, 1, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "mirai4": [
        "Mirai Deflect", "Mirai becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "miraialt1": [
        "Blood Bullet",
        "Mirai deals 10 affliction damage to target enemy for 2 turns.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "mirio1": [
        "Quirk - Permeation",
        "For one turn, Mirio will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF")
    ],
    "mirio2": [
        "Phantom Menace",
        "Mirio deals 20 piercing damage to one enemy. This ability ignores invulnerability, always damages marked targets, and deals 15 bonus damage to them.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", def_type="BYPASS")
    ],
    "mirio3": [
        "Protect Ally",
        "For one turn, target ally will ignore all new harmful effects. Any enemy that attempts to apply a new harmful effect during this time will be marked for Phantom Menace "
        + "for one turn.", [0, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "mirio4": [
        "Mirio Dodge", "Mirio becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "misaka1": [
        "Railgun",
        "Misaka deals 45 damage to one enemy. This ability ignores invulnerability and cannot be countered or reflected.",
        [0, 1, 1, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "misaka2": [
        "Iron Sand",
        "Misaka targets an ally or an enemy. If used on an ally, that ally gains 20 points of destructible defense"
        +
        " for one turn and this ability goes on cooldown for one turn. If used on an enemy, it deals 20 damage to them.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("ALL")
    ],
    "misaka3": [
        "Electric Rage",
        "For 2 turns, Misaka will gain one special energy whenever she takes new damage. She cannot"
        + " be killed while this ability is active.", [0, 0, 1, 0, 0,
                                                       6], Target.SINGLE,
        default_target("SELF")
    ],
    "misaka4": [
        "Electric Deflection", "Misaka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
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
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit")
    ],
    "naruha2": [
        "Perfect Paper - Rampage Suit",
        "Naru permanently gains 70 points of destructible defense. After being used, Naru can use Bunny Assault and this ability is replaced by Enraged Blow.",
        [0, 0, 0, 0, 2, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "naruha3": [
        "Perfect Paper - Piercing Umbrella",
        "Naru deals 15 damage to target enemy. If Naru has destructible defense remaining on Perfect Paper - Rampage Suit, this ability will deal 10 bonus damage.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "naruha4": [
        "Rabbit Guard",
        "Perfect Paper - Rampage Suit gains 25 points of destructible defense. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF", prep_req="Perfect Paper - Rampage Suit")
    ],
    "naruhaalt1": [
        "Enraged Blow",
        "Naru deals 40 damage to one enemy and stuns them for a turn. During the following turn, Naru takes double damage. This ability can only be used while Perfect Paper - Rampage Suit has destructible defense.",
        [1, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE", prep_req="Perfect Paper - Rampage Suit")
    ],
    "natsu1": [
        "Fire Dragon's Roar",
        "Natsu deals 25 damage to one enemy. The following turn, they take 10 affliction damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "natsu2": [
        "Fire Dragon's Iron Fist",
        "Natsu deals 15 damage to one enemy. If they are currently affected by one of Natsu's affliction damage-over-time"
        + " effects, they take 10 affliction damage.", [0, 1, 0, 0, 0,
                                                        0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "natsu3": [
        "Fire Dragon's Sword Horn",
        "Natsu deals 40 damage to one enemy. For the rest of the game, that enemy"
        + " takes 5 affliction damage per turn.", [1, 1, 0, 0, 1,
                                                   3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "natsu4": [
        "Natsu Dodge", "Natsu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "neji1": [
        "Eight Trigrams - 128 Palms",
        "Neji deals 2 damage to target enemy for seven turns. The damage this ability deals doubles each turn. While active, this ability is replaced by "
        +
        "Chakra Point Strike, which removes one random energy from the target if they take damage from Eight Trigrams - 128 Palms this turn.",
        [1, 0, 0, 0, 1, 8], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "neji2": [
        "Eight Trigrams - Mountain Crusher",
        "Neji deals 25 damage to target enemy, ignoring invulnerability. If used on an invulnerable target, this ability will deal 15 additional damage.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "neji3": [
        "Selfless Genius",
        "If a target ally would die this turn, they instead take no damage and deal 10 additional damage on the following turn. If this ability is triggered, Neji dies. This skill is invisible until "
        + "triggered and the death cannot be prevented.", [0, 0, 0, 0, 2,
                                                           3], Target.SINGLE,
        default_target("SELFLESS")
    ],
    "neji4": [
        "Eight Trigrams - Revolving Heaven",
        "Neji becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                    4], Target.SINGLE,
        default_target("SELF")
    ],
    "nejialt1": [
        "Chakra Point Strike",
        "If target enemy took unabsorbed damage from Eight Trigrams - 128 Palms this turn, they will lose 1 random energy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", mark_req="Eight Trigrams - 128 Palms")
    ],
    "nemu1": [
        "Nemurin Nap",
        "Nemurin heads for the dream world, enabling the use of her other abilities. Every turn, her sleep grows one stage deeper. While dozing, Nemurin heals "
        +
        "10 health per turn. While fully asleep, Nemurin Beam and Dream Manipulation cost one less random energy. While deeply asleep, Nemurin Beam and Dream Manipulation become area-of-effect. When Nemurin takes non-absorbed damage, she loses one stage of sleep depth.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF")
    ],
    "nemu2": [
        "Nemurin Beam",
        "Nemurin deals 25 damage to target enemy and reduces the damage they deal by 10 for one turn.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "nemu3": [
        "Dream Manipulation",
        "For 3 turns, target ally deals 10 additional damage and heals 10 health per turn. Cannot be used on Nemurin.",
        [0, 0, 1, 0, 1, 2], Target.SINGLE,
        default_target("SELFLESS")
    ],
    "nemu4": [
        "Dreamland Sovereignty", "Nemurin becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "orihime1": [
        "Tsubaki!",
        "Orihime prepares the Shun Shun Rikka with an offensive effect. Calling Tsubaki will end any ongoing offensive effect.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Tsubaki!"))
    ],
    "orihime2": [
        "Ayame! Shun'o!",
        "Orihime prepares the Shun Shun Rikka with a healing effect. Calling Ayame and Shun'o will end any ongoing healing effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF", lockout=(EffectType.MARK, "Ayame! Shun'o!"))
    ],
    "orihime3": [
        "Lily! Hinagiku! Baigon!",
        "Orihime prepares the Shun Shun Rikka with a defensive effect. Calling Lily, Hinagiku, and Baigon will end any ongoing defensive effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF",
                       lockout=(EffectType.MARK, "Lily! Hinagiku! Baigon!"))
    ],
    "orihime4": [
        "I Reject!",
        "Orihime activates her Shun Shun Rikka, with a composite effect depending on the flowers she has activated. Current effect: None.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE, target_shun_shun_rikka
    ],
    "ripple1": [
        "Perfect Accuracy",
        "Targets one enemy with Ripple's perfect accuracy. For the rest of the game, Shuriken Throw will target that enemy in addition to any other targets, ignoring invulnerability and dealing 5 additional damage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE",
                       protection=(EffectType.MARK, "Perfect Accuracy"))
    ],
    "ripple2": [
        "Shuriken Throw", "Ripple deals 15 piercing damage to target enemy.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE")
    ],
    "ripple3": [
        "Night of Countless Stars",
        "Ripple deals 5 damage to all enemies for three turns. During this time, Shuriken Throw deals 10 additional damage.",
        [0, 0, 0, 1, 1, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "ripple4": [
        "Ripple Block", "Ripple becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "rukia1": [
        "First Dance - Tsukishiro",
        "Rukia deals 25 damage to one enemy, ignoring invulnerability. If that enemy is invulnerable, they are stunned for one turn.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "rukia2": [
        "Second Dance - Hakuren",
        "Rukia deals 15 damage to one enemy and 10 damage to all others.",
        [0, 1, 0, 0, 0, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "rukia3": [
        "Third Dance - Shirafune",
        "The next time Rukia is countered, the countering enemy receives 30 damage and is stunned for one turn. This effect is invisible until triggered.",
        [0, 0, 1, 0, 0, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "rukia4": [
        "Rukia Parry", "Rukia becomes invulnerable for a turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "ruler1": [
        "In The Name Of Ruler!",
        "Ruler stuns one enemy and herself for 3 turns. This skill cannot be used while active and will end if Ruler is damaged.",
        [0, 1, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "In The Name Of Ruler!"))
    ],
    "ruler2": [
        "Minion - Minael and Yunael",
        "Deals 15 damage to target enemy or gives 10 destructible defense to Ruler.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, target_minion_minael_yunael
    ],
    "ruler3": [
        "Minion - Tama",
        "The next time target ally receives a new harmful ability, that ability is countered and its user takes 20 piercing damage. This effect can only be active on one target at a time.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "ruler4": [
        "Minion - Swim Swim", "Ruler becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "ryohei1": [
        "Maximum Cannon", "Ryohei deals 20 damage to a single target.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "ryohei2": [
        "Kangaryu", "Ryohei heals target ally for 15 health.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "ryohei3": [
        "Vongola Headgear",
        "For 3 turns, Ryohei will ignore all random cost increases to Maximum Cannon and Kangaryu, and using them will not consume stacks of To The Extreme!",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "ryohei4": [
        "To The Extreme!",
        "For the rest of the game, whenever Ryohei takes 20 damage, he will gain one stack of To The Extreme! For each stack of To The Extreme! on him, Maximum Cannon will deal 15 more damage and cost one more random"
        +
        " energy, and Kangaryu will restore 20 more health and cost one more random energy. Using either ability will reset all stacks of To The Extreme!",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "saber1": [
        "Excalibur",
        "Saber deals 50 piercing damage to one enemy. This ability cannot be countered.",
        [0, 1, 0, 1, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "saber2": [
        "Wind Blade Combat",
        "Saber deals 10 damage to one enemy for three turns. During this time, Saber"
        + " cannot be stunned. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "saber3": [
        "Avalon",
        "One ally permanently heals 10 health per turn. This ability can only affect one ally at a time.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HELPFUL", protection=(EffectType.MARK, "Avalon"))
    ],
    "saber4": [
        "Saber Parry", "Saber becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "saitama1": [
        "One Punch", "Saitama deals 75 piercing damage to one enemy.",
        [2, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "saitama2": [
        "Consecutive Normal Punches",
        "Saitama deals 15 damage to one enemy for 3 turns.",
        [1, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "saitama3": [
        "Serious Series - Serious Punch",
        "On the following turn Saitama deals 35 damage to target enemy. During this time, Saitama will ignore all effects.",
        [1, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "saitama4": [
        "Serious Series - Serious Sideways Jumps",
        "Saitama becomes invulnerable for one turn.", [0, 0, 0, 0, 1,
                                                       4], Target.SINGLE,
        default_target("SELF")
    ],
    "seiryu1": [
        "Body Modification - Arm Gun",
        "Seiryu deals 20 damage to one enemy. Becomes Body Modification - Self Destruct if Seiryu falls below 30 health.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "seiryu2": [
        "Raging Koro",
        "Koro deals 20 damage to one enemy for two turns. Becomes Insatiable Justice while active.",
        [0, 0, 0, 0, 2, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "seiryu3": [
        "Berserker Howl",
        "Koro deals 15 damage to all enemies and lowers the damage they deal by 10 for 2 turns.",
        [0, 0, 0, 0, 3, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "seiryu4": [
        "Koro Defense", "Seiryu becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "seiryualt1": [
        "Body Modification - Self Destruct",
        "Seiryu deals 30 damage to all enemies. After using this ability, Seiryu dies. Effects that prevent death cannot prevent Seiryu from dying. This ability cannot be countered.",
        [0, 0, 0, 0, 2, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "seiryualt2": [
        "Insatiable Justice",
        "Koro instantly kills one enemy that is below 30 health. Effects that prevent death cannot prevent this ability.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE, target_insatiable_justice
    ],
    "shigaraki1": [
        "Decaying Touch",
        "Shigaraki deals 5 affliction damage to target enemy for the rest of the game. This damage is doubled each time Decaying Touch is applied.",
        [1, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "shigaraki2": [
        "Decaying Breakthrough",
        "Shigaraki applies a stack of Decaying Touch to all enemies.",
        [1, 0, 0, 0, 2, 4], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "shigaraki3": [
        "Destroy What You Hate, Destroy What You Love",
        "Shigaraki's allies deal 10 more damage for 2 turns. During this time they take 5 more damage from all effects and cannot reduce damage or become invulnerable.",
        [0, 0, 1, 0, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS")
    ],
    "shigaraki4": [
        "Kurogiri Escape", "Shigaraki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "shikamaru1": [
        "Shadow Bind Jutsu",
        "Shikamaru stuns one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 4], Target.SINGLE, default_target("HOSTILE")
    ],
    "shikamaru2": [
        "Shadow Neck Bind",
        "Shikamaru deals 15 damage to one enemy for 2 turns. This ability will also affect any enemy affected by Shadow Pin, ignoring invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "shikamaru3": [
        "Shadow Pin",
        "Shikamaru stuns one enemy's hostile abilities for one turn.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "shikamaru4": [
        "Shikamaru Hide", "Shikamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "misaki1": [
        "Mental Out",
        "Shokuhou stuns target enemy for 2 turns. During this time, Mental Out is replaced by one of their abilities, and Shokuhou can use that ability as though she were the stunned enemy. All negative effects applied to Misaki as a result of this ability's use are applied to the stunned enemy instead.",
        [0, 0, 2, 0, 0, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "misaki2": [
        "Exterior",
        "Shokuhou takes 25 affliction damage. For the next 4 turns, Mental Out costs 1 less mental energy and lasts 1 more turn.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF")
    ],
    "misaki3": [
        "Ally Mobilization",
        "For the next 2 turns, both of Shokuhou's allies will ignore stuns and gain 15 damage reduction.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ALLY,
        default_target("SELFLESS")
    ],
    "misaki4": [
        "Loyal Guard",
        "Shokuhou becomes invulnerable for 1 turn. This ability is only usable if Shokuhou has a living ally.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE, target_loyal_guard
    ],
    "snowwhite1": [
        "Enhanced Strength", "Snow White deals 15 damage to one enemy.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "snowwhite2": [
        "Hear Distress",
        "Snow White targets an ally or an enemy for 1 turn. If used on an ally, that ally will "
        +
        "gain 25 points of damage reduction and will gain one random energy if a new move is used on them. If used on an"
        +
        " enemy, that enemy will have their first new harmful ability countered, and they will lose one random energy. This"
        +
        " skill is invisible until triggered and ignores invulnerability and isolation.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE,
        default_target("ALL", def_type="BYPASS")
    ],
    "snowwhite3": [
        "Lucky Rabbit's Foot",
        "Snow White targets an ally other than herself. For 1 turn, if that ally dies, they instead"
        + " return to 35 health. This healing cannot be prevented.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELFLESS")
    ],
    "snowwhite4": [
        "Leap", "Snow White becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "swimswim1": [
        "Ruler", "Swim Swim deals 25 damage to target enemy.",
        [0, 0, 0, 1, 0, 1], Target.SINGLE, target_ruler
    ],
    "swimswim2": [
        "Dive",
        "Swim Swim ignores all hostile effects for one turn. The following turn, her abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("SELF")
    ],
    "swimswim3": [
        "Vitality Pills",
        ("For 3 turns, Swim Swim gains 10 points of damage reduction and her"
        " abilities will deal 10 more damage."),
        [0, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("SELF")
    ],
    "swimswim4": [
        "Water Body", "Swim Swim becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "tatsumaki1": [
        "Rubble Barrage",
        "Tatsumaki deals 10 damage to all enemies for two turns.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "tatsumaki2": [
        "Arrest Assault",
        ("Tatsumaki's team gains 10 points of damage reduction for one turn."
        " This effect is invisible. After being used, this ability is replaced "
        "by Return Assault for one turn."), [0, 0, 1, 0, 0,
                                              3], Target.MULTI_ALLY,
        default_target("HELPFUL")
    ],
    "tatsumaki3": [
        "Gather Power",
        "Tatsumaki gains one random energy and one stack of Gather Power. For each stack of Gather Power on her, Rubble Barrage"
        +
        " deals 5 more damage, Arrest Assault grants 5 more damage reduction, and Gather Power has one less cooldown.",
        [0, 0, 1, 0, 0, 4], Target.SINGLE, default_target("SELF")
    ],
    "tatsumaki4": [
        "Psionic Barrier", "Tatsumaki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "tatsumakialt1": [
        "Return Assault",
        "Tatsumaki deals 0 damage to all enemies. This ability deals 20 more damage for every damaging ability Tatsumaki's team received on the previous turn.",
        [0, 0, 1, 0, 1, 2], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "todoroki1": [
        "Quirk - Half-Cold",
        "Deals 20 damage to all enemies and lowers their damage dealt by 10 for one turn. Increases the cost of all of Todoroki's abilities by one random energy until he uses Quirk - Half-Hot or Flashfreeze Heatwave.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "todoroki2": [
        "Quirk - Half-Hot",
        "Deals 30 damage to one enemy and 10 damage to Todoroki's allies. The damage dealt to Todoroki's allies is permanently increased by 10 with each use.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "todoroki3": [
        "Flashfreeze Heatwave",
        "Deals 10 damage to target enemy and 5 damage to all other enemies. The damage to the primary target is increased by 10 for each stack of Quirk - Half-Hot on Todoroki, and the "
        +
        "damage to all targets is increased by 10 for each stack of Quirk - Half-Cold on Todoroki. Consumes all stacks of Quirk - Half-Hot and Quirk - Half-Cold.",
        [0, 2, 0, 0, 0, 2], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "todoroki4": [
        "Ice Rampart", "Todoroki becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "tatsumi1": [
        "Killing Strike",
        "Tatsumi deals 25 damage to one enemy. If that enemy is stunned or below half"
        + " health, they take 10 more damage. Both damage boosts can occur.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "tatsumi2": [
        "Incursio",
        "For four turns, Tatsumi gains 25 points of destructible defense and "
        + "Neuntote becomes usable.", [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "tatsumi3": [
        "Neuntote",
        "Tatsumi deals 15 damage to target enemy. For two turns, that enemy receives double"
        + " damage from Neuntote. This effect stacks.", [0, 0, 0, 1, 1,
                                                         0], Target.SINGLE, default_target("HOSTILE", prep_req="Incursio")
    ],
    "tatsumi4": [
        "Invisibility", "Tatsumi becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "toga1": [
        "Thirsting Knife",
        "Toga deals 10 damage to one enemy and applies a stack of Thirsting Knife to them.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE, default_target("HOSTILE")
    ],
    "toga2": [
        "Vacuum Syringe",
        "Toga deals 10 affliction damage to one enemy for 2 turns. Each turn, she applies a stack of Vacuum"
        + " Syringe to them.", [0, 0, 0, 0, 2, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "toga3": [
        "Quirk - Transform",
        "Toga consumes all stacks of Thirsting Knife and Vacuum Syringe on one enemy, turning into a copy of them"
        + " for one turn per stack consumed. This effect ignores invulnerability.", [0, 0, 0, 0, 1,
                                                5], Target.SINGLE, target_transform
    ],
    "toga4": [
        "Toga Dodge", "Toga becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "tsunayoshi1": [
        "X-Burner",
        "Tsuna deals 25 damage to one enemy and 10 damage to all others.",
        [0, 1, 0, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "tsunayoshi2": [
        "Zero Point Breakthrough",
        "For one turn, the first harmful ability used on Tsuna" +
        " will be countered, and the countered enemy will be stunned for two turns. If this successfully"
        +
        " counters an ability, Tsuna will deal 10 additional damage with X-Burner for two turns.",
        [0, 0, 0, 0, 2, 4], Target.SINGLE, default_target("SELF")
    ],
    "tsunayoshi3": [
        "Burning Axle",
        "Tsuna deals 35 damage to one enemy. For one turn, if that enemy takes new"
        + " damage, they are stunned for one turn and take 15 damage.",
        [0, 1, 0, 1, 1, 3], Target.SINGLE, default_target("HOSTILE")
    ],
    "tsunayoshi4": [
        "Flare Burst", "Tsuna becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "uraraka1": [
        "Quirk - Zero Gravity",
        "Uraraka targets one enemy or one ally for 3 turns. If used on an enemy, that enemy will take 10 more damage from all sources and be unable to reduce damage"
        +
        " or become invulnerable. If used on an ally, that ally will gain 10 points of damage reduction and their abilities will ignore invulnerability.",
        [0, 0, 1, 0, 0, 2], Target.SINGLE, default_target("ALL")
    ],
    "uraraka2": [
        "Meteor Storm",
        "Uraraka deals 15 damage to all enemies. If a damaged enemy is currently targeted by Zero Gravity, that enemy will be stunned for one turn. If an ally is currently targeted by "
        +
        "Zero Gravity, they will deal 5 more damage with abilities this turn.",
        [0, 0, 1, 0, 1, 1], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "uraraka3": [
        "Comet Home Run",
        "Uraraka deals 20 damage to one enemy. If the damaged enemy is currently targeted by Zero Gravity, that enemy will lose one random energy. If an ally is currently targeted by "
        + "Zero Gravity, they will become invulnerable for one turn.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "uraraka4": [
        "Float", "Uraraka becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "wendy1": [
        "Troia",
        "Wendy heals target ally for 40 health. For 3 turns, this ability will have 50% effect.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HELPFUL")
    ],
    "wendy2": [
        "Shredding Wedding",
        "For three turns, Wendy and target enemy will take 20 piercing damage when they attempt to target anyone that isn't each other. During this time, any other characters that attempt to target either will take 20 piercing damage and Shredding Wedding becomes Piercing Winds.",
        [0, 2, 0, 0, 0, 5], Target.SINGLE, default_target("HOSTILE")
    ],
    "wendy3": [
        "Sky Dragon's Roar",
        "Deals 20 damage to all enemies and heals Wendy for 15 health.",
        [0, 1, 0, 0, 1, 0], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    "wendy4": [
        "Wendy Dodge", "Wendy becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "wendyalt1": [
        "Piercing Winds",
        "Wendy deals 25 piercing damage to the enemy affected by Shredding Wedding.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE", mark_req="Shredding Wedding")
    ],
    "yamamoto1": [
        "Shinotsuku Ame",
        "Yamamoto deals 30 damage to one enemy and reduces the damage they deal by 10 for three turns. Grants Yamamoto"
        +
        " one stack of Rain Flames. Using this ability on an enemy already affected by it will refresh the effect.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "yamamoto2": [
        "Utsuhi Ame",
        "On the following turn, Yamamoto will deal 20 damage to target enemy and grant himself one stack of"
        + " Rain Flames. If that enemy uses a new ability " +
        "during this time, Yamamoto deals 40 damage to them and grants himself 3 stacks of Rain Flames instead.",
        [0, 0, 0, 1, 0, 2], Target.SINGLE, default_target("HOSTILE")
    ],
    "yamamoto3": [
        "Asari Ugetsu",
        "Consumes one stack of Rain Flames per turn. While active, replaces Shinotsuku Ame with Scontro di Rondine and "
        +
        "Utsuhi Ame with Beccata di Rondine, and Yamamoto gains 20 points of damage reduction.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE, default_target("SELF", lockout=(EffectType.MARK, "Asari Ugetsu"))
    ],
    "yamamoto4": [
        "Sakamaku Ame", "Yamamoto becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE, default_target("SELF")
    ],
    "yamamotoalt1": [
        "Scontro di Rondine",
        "Yamamoto deals 20 damage to one enemy. If that enemy's damage is being reduced by at least 10, this ability deals 10 bonus damage.",
        [0, 0, 0, 1, 0, 0], Target.SINGLE, default_target("HOSTILE")
    ],
    "yamamotoalt2": [
        "Beccata di Rondine",
        "Yamamoto deals 5 damage to all enemies and reduces their damage dealt by 5 for 3 turns.",
        [0, 0, 0, 1, 0, 0], Target.MULTI_ENEMY, default_target("HOSTILE")
    ],
    #"" : ["", "", [], Target.],
}
