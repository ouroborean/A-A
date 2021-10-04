import enum

@enum.unique
class Energy(enum.IntEnum):
    PHYSICAL = 0
    SPECIAL = 1
    MENTAL = 2
    WEAPON = 3
    RANDOM = 4