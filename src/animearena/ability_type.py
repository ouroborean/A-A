import enum

@enum.unique
class AbilityType(enum.IntEnum):
    INSTANT = 0
    ACTION = 1
    PHYSICAL = 2
    ENERGY = 3
    MENTAL = 4
    STRATEGIC = 5
    AFFLICTION = 6
    STUN = 7
    DRAIN = 8
    UNIQUE = 9
    INVISIBLE = 10