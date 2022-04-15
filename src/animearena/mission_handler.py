
from typing import Tuple
from animearena.character_manager import CharacterManager
from animearena.effects import Effect, EffectType
from typing import TYPE_CHECKING
from collections import namedtuple

if TYPE_CHECKING:
    from animearena.battle_scene import BattleScene

effect_requirement = namedtuple("effect_requirement", ["type", "name"])

class Mission:
    
    mission_num: int
    mission_increment: int
    eff_req: effect_requirement
    eff_req_reversed: bool
    mag_req: int
    
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: effect_requirement = None, eff_req_reversed: bool = False, mag_req: int = 0):
        self.mission_num = mission_num
        self.mission_increment = mission_increment
        self.eff_req = eff_req
        self.eff_req_reversed = eff_req_reversed
        self.mag_req = mag_req
    
    def conditions_met(self, character: CharacterManager) -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.type, self.eff_req.name).mag < self.mag_req:
                return False
        return True
    
    def complete_mission(self, character: CharacterManager):
        character.progress_mission(self.mission_num, self.mission_increment)

class ProtectionMission(Mission):
    
    def conditions_met(self, character: CharacterManager) -> bool:
        for ally in character.player_team:
            if ally.source.hp == 100 and ally.char_id != character.char_id:
                return True
        return False

class HighestDamageMission(Mission):
    
    def conditions_met(self, character: CharacterManager) -> bool:
        return character.scene.saber_is_the_strongest_servant(character)

class LastManStandingMission(Mission):
    
    health_threshold: int
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: effect_requirement = None, eff_req_reversed: bool = False, mag_req: int = 0, health_threshold: int = 101):
        super().__init__(mission_num, mission_increment, eff_req, eff_req_reversed, mag_req)
        self.health_threshold = health_threshold
        
    def conditions_met(self, character: CharacterManager) -> bool:
        for ally in character.player_team:
            if not ally.source.dead:
                return False
            if character.source.hp >= self.health_threshold:
                return False
        return True
    
class SpecificMagMission(Mission):
    
    def conditions_met(self, character: CharacterManager) -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.type, self.eff_req.name).mag != self.mag_req:
                return False
        return True

class FullHealthMission(Mission):
    
    def conditions_met(self, character: CharacterManager) -> bool:
        if character.source.hp >= 100:
            return True
        return False

class ExclusionMission(Mission):
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: effect_requirement = None, eff_req_reversed: bool = False, mag_req: int = 0, excluded_effect: effect_requirement = None):
        super().__init__(mission_num, mission_increment, eff_req, eff_req_reversed, mag_req)
        self.excluded_effect = excluded_effect
    
    def conditions_met(self, character: CharacterManager) -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.type, self.eff_req.name).mag < self.mag_req:
                return False
        if character.has_effect(self.excluded_effect.type, self.excluded_effect.name):
            return False
        return True
    
class NoDeathMission(Mission):
    def conditions_met(self, character: CharacterManager) -> bool:
        for ally in character.player_team:
            if ally.source.dead:
                return False
        return True

class AbilityDamageMission:
    
    mission_num: int
    eff_req: effect_requirement
    eff_req_reversed: bool
    mag_req: int
    ability_req: str
    
    
    def __init__(self, mission_num: int, ability_req: str = "", eff_req: effect_requirement = None, eff_req_reversed: bool = False, mag_req: int = 0):
        self.mission_num = mission_num
        self.eff_req = eff_req
        self.eff_req_reversed = eff_req_reversed
        self.mag_req = mag_req
        self.ability_req = ability_req
        
    def conditions_met(self, character: CharacterManager) -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.type, self.eff_req.name).mag < self.mag_req or (self.ability_req and character.used_ability.name != self.ability_req):
                return False
        return True
    
    def complete_mission(self, character: CharacterManager, damage: int):
        character.progress_mission(self.mission_num, damage)

class MissionHandler:
    
    @classmethod
    def handle_win_mission(self, character: CharacterManager):
        
        for mission in win_mission_handler[character.source.name]:
            if mission.conditions_met(character):
                mission.complete_mission(character)
                
    @classmethod
    def handle_loss_mission(self, character: CharacterManager):
        for mission in loss_mission_handler[character.source.name]:
            if mission.conditions_met(character):
                mission.complete_mission(character)
    
    @classmethod  
    def handle_ability_damage_mission(self, character: CharacterManager, damage: int):
        for mission in ability_damage_mission_handler[character.source.name]:
            if mission.conditions_met(character):
                mission.complete_mission(character, damage)
                
ability_damage_mission_handler: dict[str, list[AbilityDamageMission]] = {
    "hinata": [AbilityDamageMission(5, "Eight Trigrams - 64 Palms")]
}
        
loss_mission_handler: dict[str, list[Mission]] = {
    "saber": [HighestDamageMission(4, 1)],
    "mine": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "SaberDamageTracker"), mag_req=225)],
    "leone": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "LeoneMission5Tracker"), mag_req=200)],
}

        
win_mission_handler: dict[str, list[Mission]] = {
    "itachi": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "ItachiMission4Tracker")),],
    "aizen": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "AizenMission5Tracker")),],
    "toga": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "TogaMission3Ready")), Mission(5, 1, effect_requirement(EffectType.UNIQUE, "Quirk - Transform"), eff_req_reversed=True), Mission(4, 1, effect_requirement(EffectType.UNIQUE, "Quirk - Transform"))],
    "shigaraki": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "ShigarakiMission3Tracker")), Mission(4, 1, effect_requirement(EffectType.SYSTEM, "ShigarakiMission4Tracker"), mag_req=3)],
    "uraraka": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "UrarakaMission5Tracker"), eff_req_reversed=True)],
    "todoroki": [Mission(1, 1, effect_requirement(EffectType.SYSTEM, "TodorokiMission1Tracker"), mag_req=3)],
    "jiro": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "JiroMission5Tracker"))],
    "mirio": [ProtectionMission(4, 1)],
    "saber": [HighestDamageMission(3, 1)],
    "natsu": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "NatsuMission3TrackerSuccess"))],
    "gray": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "GrayMission3Tracker"), mag_req=4), Mission(4, 1, effect_requirement(EffectType.SYSTEM, "GrayMission4TrackerSuccess"))],
    "lucy": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "LucyMission5Failure"), eff_req_reversed=True)],
    "jack": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "JackMission5Success"))],
    "erza": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "ErzaMission5Tracker"))],
    "gunha": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "GunhaMission3Tracker"))],
    "misaki": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "MisakiMission4Success")), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "MisakiMission5Success"))],
    "frenda": [Mission(2, 1, effect_requirement(EffectType.SYSTEM, "FrendaMission2Tracker"), mag_req=3), LastManStandingMission(5, 1, health_threshold = 25)],
    "naruha": [Mission(1, 1, effect_requirement(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"), eff_req_reversed=True), Mission(2, 1, effect_requirement(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"))],
    "lambo": [Mission(1, 1, effect_requirement(EffectType.SYSTEM, "LamboMission1Failure"), eff_req_reversed=True), SpecificMagMission(2, 1, effect_requirement(EffectType.PROF_SWAP, "Ten-Year Bazooka"), mag_req = 1), SpecificMagMission(3, 1, effect_requirement(EffectType.PROF_SWAP, "Ten-Year Bazooka"), mag_req = 2)],
    "chrome": [Mission(1, 1, effect_requirement(EffectType.PROF_SWAP, "You Are Needed"), eff_req_reversed=True), Mission(2, 1, effect_requirement(EffectType.PROF_SWAP, "You Are Needed")), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "ChromeMission5Tracker"), mag_req=3)],
    "tatsumi": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "TatsumiMission5Tracker"), mag_req=3)],
    "mine": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "MineMission4Tracker"), mag_req=3), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "SaberDamageTracker"), mag_req=225)],
    "tsunayoshi": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "TsunaMission4Tracker"), mag_req=3)],
    "akame": [Mission(3, 1, effect_requirement(EffectType.SYSTEM, "AkameMission3Tracker")), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "AkameMission5Tracker"), mag_req=3)],
    "leone": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "LeoneMission5Tracker"), mag_req=200)],
    "lubbock": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "LubbockMission4Failure"), eff_req_reversed=True), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "LubbockMission5Failure"), eff_req_reversed=True)],
    "esdeath": [Mission(2, 1), Mission(3, 1, effect_requirement(EffectType.SYSTEM, "EsdeathMission3Failure"), eff_req_reversed=True), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "EsdeathMission5Tracker"))],
    "snowwhite": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "SnowWhiteMission4Failure"), eff_req_reversed=True)],
    "ripple": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "RippleMission5Tracker"), mag_req=3)],
    "nemurin": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "NemurinMission5Failure"), eff_req_reversed=True)],
    "swimswim": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "SwimSwimMission5Tracker"), mag_req=5)],
    "pucelle": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "PucelleMission5Tracker"))],
    "chachamaru": [Mission(4, 1, effect_requirement(EffectType.SYSTEM, "ChachamaruMission4Tracker"), mag_req=3)],
    "saitama": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "SaitamaMission5Tracker"), mag_req=3), ExclusionMission(4, 1, effect_requirement(EffectType.SYSTEM, "SaitamaMission4Tracker"), excluded_effect=effect_requirement(EffectType.SYSTEM, "SaitamaMission4Failure"))],
    "touka": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "ToukaMission5Failure"), eff_req_reversed=True)],
    "swimswim": [LastManStandingMission(3, 1)],
    "misaka": [Mission(1, 1, effect_requirement(EffectType.MARK, "Ultra Railgun")), LastManStandingMission(5, 1, effect_requirement(EffectType.MARK, "Level-6 Shift"))],
    "gilgamesh": [FullHealthMission(2, 1)],
    "jeanne": [NoDeathMission(4, 1), Mission(5, 1, effect_requirement(EffectType.SYSTEM, "JeanneMission5Tracker"))],
    "accelerator": [Mission(5, 1, effect_requirement(EffectType.SYSTEM, "AcceleratorMission5Tracker")), ExclusionMission(2, 1, effect_requirement(EffectType.SYSTEM, "AcceleratorMission2Tracker"), excluded_effect=effect_requirement(EffectType.SYSTEM, "AcceleratorMission2Failure"))],
    "chelsea": [FullHealthMission(1, 1), ExclusionMission(5, 1, effect_requirement(EffectType.SYSTEM, "ChelseaMission5Tracker"), excluded_effect=effect_requirement(EffectType.SYSTEM, "ChelseaMission5Failure"))]
}