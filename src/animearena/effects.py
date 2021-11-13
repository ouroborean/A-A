import enum
import typing

import sdl2
import sdl2.ext


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
    COUNTER = 29
    REFLECT = 30
    CONT_AFF_DMG = 31
    PASSIVE = 32
    COST_ADJUST = 33
    ENERGY_GAIN = 34
    ABILITY_SWAP = 35
    CONT_USE = 36
    DEF_NEGATE = 37
    TARGET_SWAP = 38
    STACK = 39
    ISOLATE = 40
    PROF_SWAP = 41
    IGNORE = 42
    CONT_PIERCE_DMG = 43
    BOOST_NEGATE = 44
    AFF_IMMUNE = 45
    INVIS_END = 46
    COUNTER_IMMUNE = 47


class Effect:
    eff_type: EffectType
    mag: int
    duration: int
    source: "Ability"
    user: "CharacterManager"
    eff_img: sdl2.SDL_Surface
    name: str
    waiting: bool
    user_id: int
    invisible: bool
    system: bool

    def __init__(self,
                 source: "Ability",
                 eff_type: EffectType,
                 user: "CharacterManager",
                 duration: int,
                 desc,
                 mag: int = 0,
                 invisible=False,
                 system=False):
        self.eff_type = eff_type
        self.mag = mag
        self.duration = duration
        self.name = source.name
        self.db_name = source.db_name
        self.source = source
        self.user = user
        self.user_id = self.user.id
        self.desc = desc
        self.lambda_string = self.get_desc()
        self.eff_img = source.image
        self.waiting = True
        self.invisible = invisible
        self.system = system

    def get_desc(self) -> str:
        return self.desc(self)

    def tick_duration(self):
        self.duration -= 1

    def alter_mag(self, mod: int):
        self.mag = self.mag + mod

    def alter_dest_def(self, mod: int):
        self.mag += mod
        if self.mag < 0:
            self.mag = 0

    def check_waiting(self) -> bool:
        if self.waiting:
            self.waiting = False
            return False
        return True
