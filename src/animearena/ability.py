from operator import add
import PIL
from PIL import Image
from pathlib import Path
import sdl2
import sdl2.ext
import enum

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
    types = list[str]
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
        return True

    def modify_ability_cost(self, energy_type: Energy, mod: int):
        self.cost[energy_type] = max(self.cost[energy_type] + mod, 0)
        
    def reset_costs(self):
        for k in self.cost.keys():
            self.cost[k] = self._base_cost[k]

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
                if enemy.hostile_target(def_type) and (
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
                if ally.helpful_target(def_type) and (
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
                if ally != user and ally.helpful_target(def_type) and (
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
            if enemy.hostile_target(targeting) and enemy.has_effect(EffectType.MARK, "Red Eyed Killer"):
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
        if ally.hostile_target(targeting) and ((ally.has_effect(EffectType.MARK, "Doll Trap") and ally.get_effect(EffectType.MARK, "Doll Trap").user == user) or ((ally.has_effect(EffectType.MARK, "Close Combat Bombs")) and (ally.get_effect(EffectType.MARK, "Close Combat Bombs").user == user))):
            if not fake_targeting:
                ally.set_targeted()
            total_targets += 1
    for enemy in enemyTeam:
        if enemy.hostile_target(targeting) and ((enemy.has_effect(EffectType.MARK, "Doll Trap") and enemy.get_effect(EffectType.MARK, "Doll Trap").user == user) or ((enemy.has_effect(EffectType.MARK, "Close Combat Bombs")) and (enemy.get_effect(EffectType.MARK, "Close Combat Bombs").user == user))):
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
            if ally.helpful_target(targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    for enemy in enemyTeam:
        if enemy.hostile_target(targeting):
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
        if ally.helpful_target(targeting):
            if not fake_targeting:
                ally.set_targeted()
            total_targets += 1
    if user.has_effect(EffectType.MARK, "Eight Trigrams - 64 Palms"):
        for enemy in enemyTeam:
            if enemy.hostile_target(targeting):
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
        if enemy.hostile_target(targeting):
            if not fake_targeting:
                enemy.set_targeted()
            total_targets += 1
    return total_targets 

def target_maria_the_ripper(user: "CharacterManager",
              playerTeam: list["CharacterManager"],
              enemyTeam: list["CharacterManager"],
              fake_targeting: bool = False) -> int:
    total_targets = 0
    targeting = user.check_bypass_effects()
    for enemy in enemyTeam:
        if enemy.hostile_target(targeting) and ((enemy.has_effect(EffectType.MARK, "Fog of London") or enemy.has_effect(EffectType.MARK, "Streets of the Lost"))):
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
            if enemy.hostile_target(targeting):
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
            if enemy.hostile_target(targeting):
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
        if enemy.hostile_target("BYPASS"):
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
        if enemy.hostile_target(targeting):
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
            if enemy.hostile_target("BYPASS"):
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
            if enemy.hostile_target(targeting):
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
        if enemy.hostile_target(targeting):
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
        if enemy.hostile_target(targeting):
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
            if enemy.hostile_target(targeting):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
        for ally in playerTeam:
            if ally.helpful_target(targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    elif (one() and three()) or (one() and two()) or (two() and three()) or (two()) or (three()):
        for ally in playerTeam:
            if ally.helpful_target(targeting):
                if not fake_targeting:
                    ally.set_targeted()
                total_targets += 1
    elif one():
        for enemy in enemyTeam:
            if enemy.hostile_target(targeting):
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
        if enemy.hostile_target(targeting):
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
        if enemy.hostile_target("BYPASS") and enemy.source.hp < 30:
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
        if enemy.hostile_target(targeting):
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
            if enemy.hostile_target("BYPASS"):
                if not fake_targeting:
                    enemy.set_targeted()
                total_targets += 1
    return total_targets
#endregion
#endregion


#region Execution
#(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
def exe_rasengan(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        base_damage = 25
        stun_duration = 2
        if user.has_effect(EffectType.MARK, "Sage Mode"):
            base_damage = 50
            stun_duration = 4
        for target in user.current_targets:
            user.deal_damage(base_damage, target)
            target.add_effect(Effect(Ability("naruto2"), EffectType.ALL_STUN, user, stun_duration, lambda eff: "This character is stunned."))
            user.check_on_stun(target)
        user.check_on_use()

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
            user.deal_damage(base_damage, target)
        user.check_on_use()

def exe_substitution(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.add_effect(Effect(Ability("naruto4"), EffectType.ALL_INVULN, user, 2, lambda eff: "Naruto is invulnerable."))
    user.check_on_use()

def exe_sage_mode(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    user.full_remove_effect("Shadow Clones")
    user.scene.player_display.team.energy_pool[Energy.SPECIAL] += 1
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.ALL_INVULN, user, 3, lambda eff: "Naruto is invulnerable."))
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.ABILITY_SWAP, user, 3, lambda eff: "Uzumaki Barrage has been replaced by Toad Taijutsu.", mag=33))
    user.add_effect(Effect(Ability("narutoalt1"), EffectType.MARK, user, 3, lambda eff: "Rasengan stun duration and damage are doubled."))
    user.check_on_use()

def exe_uzumaki_barrage(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        base_damage = 15
        for target in user.current_targets:
            user.deal_damage(base_damage, target)
            if user.has_effect(EffectType.MARK, "Uzumaki Barrage"):
                target.add_effect(Effect(Ability("narutoalt2"), EffectType.ALL_STUN, user, 2, lambda eff: "This character is stunned."))
                user.check_on_stun(target)
            user.add_effect(Effect(Ability("narutoalt2"), EffectType.MARK, user, 3, lambda eff: "Uzumaki Barrage will stun its target for one turn."))
        user.check_on_use()

def exe_toad_taijutsu(user: "CharacterManager", playerTeam: list["CharacterManager"], enemyTeam: list["CharacterManager"]):
    if not user.check_countered():
        base_damage = 35
        for target in user.current_targets:
            user.deal_damage(base_damage, target)
            target.add_effect(Effect(Ability("narutoalt3"), EffectType.COST_ADJUST, user, 4, lambda eff: "This character's ability costs have been increased by 2 random energy.", mag=52))
        user.check_on_use()
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
        default_target("HOSTILE")
    ],
    "aizen2": [
        "Overwhelming Power",
        "Aizen deals 25 damage to target enemy and marks them with Overwhelming Power for one turn. If the enemy is marked with Black Coffin,"
        +
        " that enemy will be unable to reduce damage or become invulnerable for 2 turns. If that enemy is marked with Shatter, Kyoka Suigetsu, Overwhelming Power deals 20 bonus damage to them.",
        [1, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "aizen3": [
        "Black Coffin",
        "Target enemy is stunned and marked with Black Coffin for 1 turn. If the enemy is marked with Overwhelming Power, they will also take 20 damage. If the"
        +
        " enemy is marked with Shatter, Kyoka Suigetsu, then Black Coffin also affects their allies.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE, default_target("HOSTILE")
    ],
    "aizen4": [
        "Effortless Guard", "Aizen becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "akame1": [
        "Red-Eyed Killer",
        "Akame marks an enemy for 1 turn. During this time, she can use One-Cut Killing on the target.",
        [0, 0, 1, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "akame2": [
        "One Cut Killing",
        "Akame instantly kills a target marked with Red-Eyed Killer.",
        [0, 0, 0, 2, 1, 1], Target.SINGLE, target_one_cut_killing
    ],
    "akame3": [
        "Little War Horn",
        "For two turns, Akame can use One Cut Killing on any target, regardless of their effects.",
        [0, 0, 0, 0, 2, 5], Target.SINGLE,
        default_target("SELF")
    ],
    "akame4": [
        "Rapid Deflection", "Akame becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "astolfo1": [
        "Casseur de Logistille",
        "Astolfo targets himself or another ally for one turn. During this time, if they are targeted by a hostile Special or Mental ability, that ability"
        +
        " will be countered and the user will be stunned and isolated for 1 turn. This ability is invisible until triggered.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "astolfo2": [
        "Trap of Argalia - Down With A Touch!",
        "Astolfo deals 20 piercing damage to target enemy. For one turn, they cannot have their damage boosted above its default value. If the target's damage is currently boosted, Trap of Argalia will permanently "
        + "deal 5 additional damage.", [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "astolfo3": [
        "La Black Luna",
        "Astolfo removes one hostile effect from every member of his team, and for 2 turns, no enemy can have their damage boosted above its default value. For every hostile effect removed, Trap of Argalia will permanently"
        + " deal 5 additional damage.", [0, 1, 0, 0, 1, 2], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "astolfo4": [
        "Akhilleus Kosmos", "Astolfo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "cmary1": [
        "Quickdraw - Pistol",
        "Calamity Mary deals 15 damage to target enemy. This ability will become Quickdraw - Rifle after being used.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "cmary2": [
        "Hidden Mine",
        "Traps one enemy for two turns. During this time, if that enemy used a new ability, they will take 20 piercing damage and this effect will end.",
        [0, 0, 0, 1, 0, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "cmary3": [
        "Grenade Toss",
        "Calamity Mary deals 20 damage to all enemy targets. This ability deals 20 more damage to enemies affected by Hidden Mine.",
        [0, 0, 0, 1, 1, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "cmary4": [
        "Rifle Guard", "Calamity Mary becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "cmaryalt1": [
        "Quickdraw - Rifle",
        "Calamity Mary deals 15 damage to target enemy for 2 turns. This ability will become Quickdraw - Sniper after it ends.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "cmaryalt2": [
        "Quickdraw - Sniper",
        "Calamity Mary deals 55 piercing damage to one enemy and becomes invulnerable for one turn.",
        [0, 0, 0, 2, 1, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "chachamaru1": [
        "Target Lock",
        "Chachamaru marks a single target for Orbital Satellite Cannon.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", protection=(EffectType.MARK, "Target Lock"))
    ],
    "chachamaru2": [
        "Orbital Satellite Cannon",
        "Deals 35 piercing damage that ignores invulnerability to all targets marked by Target Lock.",
        [0, 0, 0, 0, 3, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE",
                       def_type="BYPASS",
                       mark_req="Target Lock",
                       lockout=(EffectType.MARK, "Active Combat Mode"))
    ],
    "chachamaru3": [
        "Active Combat Mode",
        "Chachamaru gains 15 points of destructible defense each turn and deals 10 damage to one enemy for 3 turns. During this time, she cannot use"
        + " Orbital Satellite Cannon.", [0, 0, 0, 0, 2, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "chachamaru4": [
        "Take Flight", "Chachamaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "chrome1": [
        "You Are Needed",
        "Chrome accepts Mukuro's offer to bond their souls, enabling the user of her abilities. If Chrome ends a turn below 40 health, she transforms into Rokudou Mukuro.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF", protection=(EffectType.MARK, "You Are Needed"))
    ],
    "chrome2": [
        "Illusory Breakdown",
        "Illusory Breakdown: Chrome targets one enemy and gains 20 points of destructible defense for one turn. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 25 damage to the targeted enemy and stun them for one turn.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed")
    ],
    "chrome3": [
        "Mental Immolation",
        "Mental Immolation: Chrome targets one enemy and gains 15 points of destructible defense. If she still has any of this destructible defense on her next turn, "
        +
        "she will deal 20 damage to the targeted enemy and remove one random energy from them.",
        [0, 0, 1, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="You Are Needed")
    ],
    "chrome4": [
        "Mental Substitution",
        "Mental Substitution: Chrome becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "chromealt1": [
        "Trident Combat",
        "Trident Combat: Mukuro deals 25 damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "chromealt2": [
        "Illusory World Destruction",
        "Illusory World Destruction: Mukuro gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        + "he will deal 25 damage to all enemies and stun them for one turn.",
        [0, 0, 1, 0, 2, 2], Target.SINGLE,
        default_target("SELF")
    ],
    "chromealt3": [
        "Mental Annihilation",
        "Mental Annihilation: Mukuro targets one enemy and gains 30 points of destructible defense. If he still has any of this destructible defense on his next turn, "
        +
        "he will deal 35 piercing damage to the targeted enemy. This damage ignores invulnerability.",
        [0, 0, 1, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "chromealt4": [
        "Trident Deflection", "Mukuro becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "chu1": [
        "Relentless Assault",
        "Chu deals 15 damage to one enemy for three turns. If that enemy has less"
        +
        " than 15 points of damage reduction, this damage is considered piercing.",
        [1, 0, 0, 0, 1, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "chu2": [
        "Flashing Deflection",
        "Chu gains 15 points of damage reduction for 3 turns. If he would be affected by a move that"
        +
        " deals less than 15 points of damage, he will fully ignore that move instead.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("SELF")
    ],
    "chu3": [
        "Gae Bolg",
        "Chu removes all destructible defense from target enemy, then deals 40 piercing damage"
        + " to them. This ability ignores invulnerability.",
        [2, 0, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "chu4": [
        "Chu Block", "Chu becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "cranberry1": [
        "Illusory Disorientation",
        "For 3 turns, one enemy has their ability costs increased by 1 random and this ability is replaced by Merciless Finish. This effect is removed on ability use.",
        [0, 1, 0, 0, 1, 3], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "cranberry2": [
        "Fortissimo",
        "Cranberry deals 25 damage to all enemies, ignoring invulnerability. This ability cannot be ignored and deals double damage to enemies that are invulnerable or ignoring.",
        [0, 2, 0, 0, 0, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "cranberry3": [
        "Mental Radar",
        "For 2 turns, Cranberry's team will ignore counter effects.",
        [0, 0, 1, 0, 1, 4], Target.MULTI_ALLY,
        default_target("HELPFUL")
    ],
    "cranberry4": [
        "Cranberry Block", "Cranberry becomes invulnerable for 1 turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "cranberryalt1": [
        "Merciless Finish",
        "Cranberry stuns target enemy for 2 turns, and deals 15 affliction damage to them each turn. Only usable on a target currently affected by Illusory Disorientation.",
        [1, 0, 0, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE", mark_req="Illusory Disorientation")
    ],
    "erza1": [
        "Clear Heart Clothing",
        "Until Erza requips another armor set, she cannot be stunned and Clear Heart Clothing is replaced by Titania's Rampage.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "erza2": [
        "Heaven's Wheel Armor",
        "Until Erza requips another armor set, she will ignore all affliction damage and Heaven's Wheel Armor is replaced by Circle Blade.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "erza3": [
        "Nakagami's Armor",
        "Until Erza requips another armor set, she gains 1 additional random energy per turn and Nakagami's Armor is replaced by Nakagami's Starlight.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "erza4": [
        "Adamantine Armor",
        "Until Erza requips another armor set, she gains 15 damage reduction and Adamantine Armor is replaced by Adamantine Barrier.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "erzaalt1": [
        "Titania's Rampage",
        "Until Erza is killed or requips another armor set, she deals 15 piercing damage to a random enemy. Each turn that this ability"
        +
        " remains active, it deals 5 more damage. This ability cannot be countered.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "erzaalt2": [
        "Circle Blade",
        "Erza deals 20 damage to one enemy. On the following turn, all enemies take 15 damage, ignoring invulnerability.",
        [0, 0, 0, 1, 1, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "erzaalt3": [
        "Nakagami's Starlight",
        "Erza deals 35 damage to one enemy and removes 1 random energy from them.",
        [0, 1, 0, 1, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "erzaalt4": [
        "Adamantine Barrier",
        "Both of Erza's allies become invulnerable for one turn.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ALLY,
        default_target("SELFLESS")
    ],
    "esdeath1": [
        "Demon's Extract",
        "Esdeath calls forth the power of her Teigu, enabling the user of her abilities for 5 turns. During this time, this ability changes to Mahapadma, "
        + "and Esdeath cannot be countered.", [0, 1, 0, 0, 0,
                                               4], Target.SINGLE,
        default_target("SELF")
    ],
    "esdeath2": [
        "Frozen Castle",
        "For the next two turns, no enemy can target any of Esdeath's allies. Esdeath's allies cannot target enemies affected by Frozen Castle. During this time, "
        + "Weiss Schnabel will affect all enemies.", [0, 2, 0, 0, 0,
                                                      7], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "esdeath3": [
        "Weiss Schnabel",
        "Deals 10 damage to target enemy for 3 turns. While active, Weiss Schnabel costs one fewer special energy and deals 15 piercing damage to target enemy.",
        [0, 1, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE", prep_req="Demon's Extract")
    ],
    "esdeath4": [
        "Esdeath Guard",
        "Esdeath Guard: Esdeath becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "esdeathalt1": [
        "Mahapadma",
        "Mahapadma: Esdeath stuns every living character except for her for 2 turns. At the end of those turns, Esdeath is stunned for 2 turns.",
        [0, 2, 0, 0, 1, 8], Target.ALL_TARGET,
        default_target("ALL")
    ],
    "frenda1": [
        "Close Combat Bombs",
        "Frenda hurls a handful of bombs at an enemy, marking them with a stack of Close Combat Bombs for 3 turns. If Detonate is used, "
        +
        "the marked enemy will take 15 damage per stack of Close Combat Bombs.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "frenda2": [
        "Doll Trap",
        "Frenda traps an ally or herself, permanently marking them with a Doll Trap. During this time, if any enemy damages the marked ally, all stacks of Doll Trap on that ally are transferred to"
        +
        " the damaging enemy. If Detonate is used, characters marked with Doll Trap receive 20 damage per stack of Doll Trap on them. Doll Trap is invisible until transferred.",
        [0, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HELPFUL")
    ],
    "frenda3": [
        "Detonate",
        "Frenda consumes all her stacks of Close Combat Bombs and Doll Trap from all characters. This ability ignores invulnerability.",
        [0, 0, 0, 0, 2, 0], Target.ALL_TARGET, target_detonate
    ],
    "frenda4": [
        "Frenda Dodge", "Frenda becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "gajeel1": [
        "Iron Dragon's Roar", "Gajeel deals 35 piercing damage to one enemy.",
        [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "gajeel2": [
        "Iron Dragon's Club", "Gajeel deals 20 piercing damage to one enemy.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "gajeel3": [
        "Iron Shadow Dragon",
        "If Gajeel is targeted with a new harmful ability, he will ignore all further hostile effects that turn. This changes Gajeel's abilities to their special versions.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "gajeel4": [
        "Gajeel Block", "Gajeel becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "gajeelalt1": [
        "Iron Shadow Dragon's Roar",
        "Gajeel deals 15 damage to all enemies, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "gajeelalt2": [
        "Iron Shadow Dragon's Club",
        "Gajeel deals 20 damage to one enemy, ignoring invulnerability.",
        [0, 1, 0, 0, 0, 0], Target.SINGLE,
        default_target("HOSTILE", def_type="BYPASS")
    ],
    "gajeelalt3": [
        "Blacksteel Gajeel",
        "Gajeel permanently gains 15 damage reduction. This changes Gajeel's abilities back to their physical versions.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "gokudera1": [
        "Sistema C.A.I.",
        "Gokudera causes an effect based on the CAI stage, and moves the stage forward one. All effects are cumulative except for Stage 4."
        +
        " Stage 1: Deals 10 damage to all enemies.\nStage 2: Stuns target enemy for one turn.\nStage 3: Deals 10 damage to one enemy and heals Gokudera for 15 health.\nStage 4: Deals 25 damage to all enemies and stuns them for 1 turn. This heals Gokudera's entire team for 20 health. Resets the C.A.I. stage to 1.",
        [0, 0, 0, 1, 1, 0], Target.ALL_TARGET, target_sistema_CAI
    ],
    "gokudera2": [
        "Vongola Skull Rings", "Moves the C.A.I. stage forward by one.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("SELF")
    ],
    "gokudera3": [
        "Vongola Box Weapon, Vongola Bow",
        "Gokudera gains 30 points of destructible defense for 2 turns. During this time, the C.A.I. stage will not advance.",
        [0, 1, 0, 1, 0, 5], Target.SINGLE,
        default_target("SELF")
    ],
    "gokudera4": [
        "Gokudera Block", "Gokudera becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "hibari1": [
        "Bite You To Death", "Hibari deals 20 damage to target enemy.",
        [0, 0, 0, 0, 0, 1], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "hibari2": [
        "Alaudi's Handcuffs",
        "Hibari stuns one enemy for 2 turns. During this time, they take 10 damage per turn and Hibari cannot use Porcospino Nuvola.",
        [0, 1, 0, 1, 0, 5], Target.SINGLE,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Porcospino Nuvola"))
    ],
    "hibari3": [
        "Porcospino Nuvola",
        "For 2 turns, any enemy that uses a new harmful ability will take 10 damage. During this time, Hibari cannot use Alaudi's Handcuffs.",
        [0, 0, 0, 1, 0, 3], Target.MULTI_ENEMY,
        default_target("HOSTILE",
                       lockout=(EffectType.MARK, "Alaudi's Handcuffs"))
    ],
    "hibari4": [
        "Tonfa Block", "Hibari becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "gray1": [
        "Ice, Make...",
        "Gray prepares to use his ice magic. On the following turn, all of his abilities are enabled and Ice, Make... becomes Ice, Make Unlimited.",
        [0, 0, 0, 0, 0, 0], Target.SINGLE,
        default_target("SELF")
    ],
    "gray2": [
        "Ice, Make Freeze Lancer",
        "Gray deals 15 damage to all enemies for 2 turns.", [0, 1, 0, 0, 1, 2],
        Target.MULTI_ENEMY,
        default_target("HOSTILE", prep_req="Ice, Make...")
    ],
    "gray3": [
        "Ice, Make Hammer",
        "Gray deals 20 damage to one enemy and stuns them for 1 turn.",
        [0, 1, 0, 0, 1, 1], Target.SINGLE,
        default_target("HOSTILE", prep_req="Ice, Make...")
    ],
    "gray4": [
        "Ice, Make Shield", "Gray becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF", prep_req="Ice, Make...")
    ],
    "grayalt1": [
        "Ice, Make Unlimited",
        "Gray deals 5 damage to all enemies and grants all allies 5 destructible defense. This will continue to occur on any turn in which Gray is not under the effect of Ice, Make... and is not stunned.",
        [0, 1, 0, 0, 2, 0], Target.ALL_TARGET,
        default_target("ALL", lockout=(EffectType.MARK, "Ice, Make Unlimited"))
    ],
    "sogiita1": [
        "Super Awesome Punch",
        "Gunha does 35 piercing damage to target enemy. Using this ability consumes up to 5 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, Super Awesome Punch deals 10 additional damage. If Gunha consumes 5 stacks, Super Awesome Punch will "
        + "stun its target for 1 turn.", [1, 0, 1, 0, 0, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "sogiita2": [
        "Overwhelming Suppression",
        "Gunha reduces the damage dealt by all enemies by 5 for 1 turn. Using this ability consumes up to 3 stacks of Guts from Gunha. "
        +
        "If Gunha consumes at least 2 stacks, then the damage reduction is increased by 5. If Gunha consumes 3 stacks, then all affected enemies cannot reduce"
        + " damage or become invulnerable for 1 turn.", [0, 0, 1, 0, 0, 0
                                                         ], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "sogiita3": [
        "Hyper Eccentric Ultra Great Giga Extreme Hyper Again Awesome Punch",
        "Gunha does 20 damage to target enemy. Using this ability consumes up to "
        +
        "3 stacks of Guts from Gunha. If Gunha consumes at least 2 stacks, this ability deals 5 extra damage and becomes piercing. If Gunha consumes 3 stacks, this ability"
        +
        " will deal 25 piercing damage to all other enemies, ignoring invulnerability.",
        [1, 0, 0, 0, 0, 0], Target.SINGLE, default_target("HOSTILE")
    ],
    "sogiita4": [
        "Guts",
        "Gunha permanently activates Guts, enabling his other abilities and granting him 5 stacks of Guts. After the initial use, Gunha can activate "
        +
        "Guts again to grant himself 2 stacks of Guts and heal for 25 health.",
        [0, 0, 0, 0, 1, 2], Target.SINGLE,
        default_target("SELF")
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
        + "damage by 15.", [1, 0, 0, 0, 1, 0], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "ichigo4": [
        "Zangetsu Block", "Ichigo becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
    ],
    "ichimaru1": [
        "Butou Renjin",
        "Ichimaru deals 15 damage to one enemy for two turns, adding a stack of Shinso to the target each turn when it damages them.",
        [0, 0, 0, 1, 1, 2], Target.SINGLE,
        default_target("HOSTILE")
    ],
    "ichimaru2": [
        "13 Kilometer Swing",
        "Ichimaru deals 25 damage to all enemies and adds a stack of Shinso to each enemy damaged.",
        [0, 0, 0, 1, 2, 1], Target.MULTI_ENEMY,
        default_target("HOSTILE")
    ],
    "ichimaru3": [
        "Kill, Kamishini no Yari",
        "Ichimaru consumes all stacks of Shinso, dealing 10 affliction damage to each enemy for the rest of the game for each stack of Shinso consumed from them. This effect ignores invulnerability.",
        [0, 0, 0, 2, 0, 2], Target.MULTI_ENEMY,
        default_target("HOSTILE", def_type="BYPASS", mark_req="Shinso")
    ],
    "ichimaru4": [
        "Shinso Parry", "Ichimaru becomes invulnerable for one turn.",
        [0, 0, 0, 0, 1, 4], Target.SINGLE,
        default_target("SELF")
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
        "Itachi gains 45 destructible defense, and loses 10 health at the end of each turn. During this time, Amaterasu is replaced by Totsuka Blade and Tsukuyomi is replaced by"
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
        "Partial Shiki Fuukin",
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
