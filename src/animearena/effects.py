import enum
import typing

from typing import Union, Tuple

import sdl2
import sdl2.ext

from animearena.ability_type import AbilityType

if typing.TYPE_CHECKING:
    from animearena.character_manager import CharacterManager
    from animearena.ability import Ability


@enum.unique
class EffectType(enum.IntEnum):
    UNIQUE = 0
    ALL_BOOST = 1
    PHYS_BOOST = 2
    MAG_BOOST = 3
    MELEE_BOOST = 4
    RANGED_BOOST = 5
    ALL_DR = 6
    PHYS_DR = 7
    MAG_DR = 8
    MELEE_DR = 9
    RANGED_DR = 10
    DEST_DEF = 11
    ALL_STUN = 12
    PHYS_STUN = 13
    MAG_STUN = 14
    MELEE_STUN = 15
    RANGED_STUN = 16
    ALL_INVULN = 17
    PHYS_INVULN = 18
    MAG_INVULN = 19
    MELEE_INVULN = 20
    RANGED_INVULN = 21
    STUN_IMMUNE = 22
    CONT_DMG = 23
    CONT_HEAL = 24
    CONT_DEST_DEF = 25
    CONT_UNIQUE = 26
    MARK = 27
    COOLDOWN_MOD = 28
    COUNTER_RECEIVE = 29
    REFLECT = 30
    CONT_AFF_DMG = 31
    PASSIVE = 32
    COST_ADJUST = 33 # mag = (naive ability index, 0 for all)(naive energy index)(true quantity of adjustment)
    ENERGY_GAIN = 34
    ABILITY_SWAP = 35 # mag = (naive ability index)(naive replacement index)
    CONT_USE = 36
    DEF_NEGATE = 37
    TARGET_SWAP = 38 # mag = (naive ability index)(true targeting type)
    STACK = 39
    ISOLATE = 40
    PROF_SWAP = 41
    IGNORE = 42
    CONT_PIERCE_DMG = 43
    BOOST_NEGATE = 44
    AFF_IMMUNE = 45
    INVIS_END = 46
    COUNTER_IMMUNE = 47
    SYSTEM = 48
    CONSECUTIVE_TRACKER = 49
    CONSECUTIVE_BUFFER = 50
    SPECIFIC_STUN = 51
    COUNTER_USE = 52


class Effect:
    eff_type: EffectType
    mag: int
    duration: int
    source: Union["Ability", str]
    user: "CharacterManager"
    eff_img: sdl2.SDL_Surface
    name: str
    waiting: bool
    user_id: int
    invisible: bool
    system: bool
    removing: bool
    instant: bool
    action: bool
    unique: bool
    affliction: bool
    print_mag: bool

    def __init__(self,
                 source: Union["Ability", str],
                 eff_type: EffectType,
                 user: "CharacterManager",
                 duration: int,
                 desc,
                 mag: int = 0,
                 invisible=False,
                 system=False,
                 print_mag=False):
        self.eff_type = eff_type
        self.mag = mag
        self.duration = duration
        self.action = False
        self.instant = False
        self.unique = False
        self.print_mag = print_mag
        if type(source) == str:
            self.name = source
            self.db_name = source
        else:
            self.name = source.name
            self.db_name = source.db_name
            self.source = source
            self.eff_img = source.image
            
            if AbilityType.ACTION in source.types:
                self.action = True
            elif AbilityType.INSTANT in source.types:
                self.instant = True
            if AbilityType.UNIQUE in source.types:
                self.unique = True
            
        self.user = user
        self.user_id = self.user.id
        self.desc = desc
        self.lambda_string = self.get_desc()
        self.waiting = True
        self.invisible = invisible
        self.system = system
        self.removing = False
        

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Tuple):
            return (self.eff_type == __o[0] and self.name == __o[1])
        if isinstance(__o, Effect):
            return (self.eff_type == __o.eff_type and self.name == __o.name)

    def __str__(self) -> str:
        return self.name + "(" + self.eff_type.name + ") <User: " + self.user.id + " " + self.user.source.name + ">"

    def get_desc(self) -> str:
        return self.desc(self)

    def tick_duration(self):
        self.duration -= 1

    def alter_mag(self, mod: int, max: int = 0):
        self.mag = self.mag + mod
        if max and self.mag > max:
            self.mag = max

    def alter_dest_def(self, mod: int):
        self.mag += mod
        if self.mag < 0:
            self.mag = 0

    def check_waiting(self) -> bool:
        if self.waiting:
            self.waiting = False
            return False
        return True



