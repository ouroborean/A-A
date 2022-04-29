
from typing import Callable, Tuple, Optional

from numpy import greater
from animearena import ability, mission
from animearena.character import Character
from animearena.effects import Effect, EffectType
from typing import TYPE_CHECKING
from collections import namedtuple

if TYPE_CHECKING:
    from animearena.battle_scene import BattleScene
    from animearena.character_manager import CharacterManager

EffectRequirement = namedtuple("effect_requirement", ["eff_type", "name"])

class WinMission:
    
    mission_num: int
    mission_increment: int
    eff_req: Optional[EffectRequirement]
    eff_req_reversed: bool
    mag_req: int
    
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, mag_req: int = 0):
        self.mission_num = mission_num
        self.mission_increment = mission_increment
        self.eff_req = eff_req
        self.eff_req_reversed = eff_req_reversed
        self.mag_req = mag_req
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.eff_type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.eff_type, self.eff_req.name).mag < self.mag_req:
                return False
        return True
    
    def complete_mission(self, character: "CharacterManager"):
        character.progress_mission(self.mission_num, self.mission_increment)

class ProtectionMission(WinMission):
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        for ally in character.player_team:
            if ally.source.hp == 100 and ally.char_id != character.char_id:
                return True
        return False

class HighestDamageMission(WinMission):
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        return character.scene.saber_is_the_strongest_servant(character)

class LastManStandingMission(WinMission):
    
    health_threshold: int
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, mag_req: int = 0, health_threshold: int = 101):
        super().__init__(mission_num, mission_increment, eff_req, eff_req_reversed, mag_req)
        self.health_threshold = health_threshold
        
    def conditions_met(self, character: "CharacterManager") -> bool:
        for ally in character.player_team:
            if not ally.source.dead:
                return False
            if character.source.hp >= self.health_threshold:
                return False
        return True
    
class SpecificMagMission(WinMission):
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.eff_type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.eff_type, self.eff_req.name).mag != self.mag_req:
                return False
        return True

class FullHealthMission(WinMission):
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        if character.source.hp >= 100:
            return True
        return False

class ExclusionMission(WinMission):
    
    def __init__(self, mission_num: int, mission_increment: int, eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, mag_req: int = 0, excluded_effect: Optional[EffectRequirement] = None):
        super().__init__(mission_num, mission_increment, eff_req, eff_req_reversed, mag_req)
        self.excluded_effect = excluded_effect
    
    def conditions_met(self, character: "CharacterManager") -> bool:
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.eff_type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.eff_type, self.eff_req.name).mag < self.mag_req:
                return False
        if character.has_effect(self.excluded_effect.eff_type, self.excluded_effect.name):
            return False
        return True
    
class NoDeathMission(WinMission):
    def conditions_met(self, character: "CharacterManager") -> bool:
        for ally in character.player_team:
            if ally.source.dead:
                return False
        return True

class AbilityDamageMission:
    
    mission_num: int
    eff_req: Optional[EffectRequirement]
    eff_req_reversed: bool
    mag_req: int
    ability_req: str
    target_eff_req: Optional[EffectRequirement]
    target_eff_req_reversed: bool
    target_mag_req: int
    handoff: bool
    user_handoff: bool
    
    def __init__(self, mission_num: int, ability_req: str = "", eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_eff_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, mag_req: int = 0, target_mag_req: int = 0, handoff: bool = False, user_handoff: bool = True):
        self.mission_num = mission_num
        self.eff_req = eff_req
        self.eff_req_reversed = eff_req_reversed
        self.mag_req = mag_req
        self.ability_req = ability_req
        self.target_eff_req = target_eff_req
        self.target_eff_req_reversed = target_eff_req_reversed
        self.target_mag_req = target_mag_req
        self.handoff = handoff
        self.user_handoff = user_handoff
        
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        output = True
        if self.eff_req:
            effect_requirement_met = (character.has_effect(self.eff_req.eff_type, self.eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.eff_req.eff_type, self.eff_req.name).mag < self.mag_req or (self.ability_req and source != self.ability_req):
                output = False
        if self.target_eff_req:
            target_effect_requirement_met = (target.has_effect(self.target_eff_req.eff_type, self.target_eff_req.name) != self.target_eff_req_reversed)
            if not target_effect_requirement_met or target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).mag < self.target_mag_req:
                output = False
        return output
    
    def complete_mission(self, character: "CharacterManager", target: "CharacterManager", damage: int):
        if self.handoff:
            if self.user_handoff:
                affected = character.get_effect(self.eff_req.eff_type, self.eff_req.name).user
            else:
                affected = target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name)
        else:
            affected = character
        
        affected.progress_mission(self.mission_num, damage)

class AbilityAllyDamageMission(AbilityDamageMission):
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        if not target.id == character.id:
            return False
        return super().conditions_met(character, target, source)

class KillingBlowMission:
    
    mission_num: int
    user_eff_req: Optional[EffectRequirement]
    eff_req_reversed: bool
    target_eff_req: Optional[EffectRequirement]
    target_eff_req_reversed: bool
    mag_req: int
    target_mag_req: int
    ability_req: str
    once: bool
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, once: bool = False):
        self.mission_num = mission_num
        self.user_eff_req = user_eff_req
        self.eff_req_reversed = eff_req_reversed
        self.target_eff_req = target_effect_req
        self.target_eff_req_reversed = target_eff_req_reversed
        self.target_mag_req = target_mag_req
        self.mag_req = user_mag_req
        self.ability_req = ability_req
        self.once = once
        
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        output = True
        if self.user_eff_req:
            effect_requirement_met = (character.has_effect(self.user_eff_req.eff_type, self.user_eff_req.name) != self.eff_req_reversed)
            if not effect_requirement_met or character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).mag < self.mag_req or (self.ability_req and source != self.ability_req):
                output = False
        if self.target_eff_req:
            target_effect_requirement_met = (target.has_effect(self.target_eff_req.eff_type, self.target_eff_req.name) != self.target_eff_req_reversed)
            if not target_effect_requirement_met or target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).mag < self.target_mag_req:
                output = False
        return output
    
    def complete_mission(self, character: "CharacterManager", target: "CharacterManager"):
        character.progress_mission(self.mission_num, 1, self.once)

class KillingBlowHealthThresholdMission(KillingBlowMission):
    
    health_threshold_inclusive: int
    greater_than_threshold: bool
    
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, threshold: int = 200, greater_than: bool = True, once: bool = False):
        super().__init__(mission_num, ability_req, user_eff_req, eff_req_reversed, target_effect_req, target_eff_req_reversed, user_mag_req, target_mag_req, once)
        self.health_threshold_inclusive = threshold
        self.greater_than_threshold = greater_than
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        output = True
        if self.greater_than_threshold:
            if character.source.hp < self.health_threshold_inclusive:
                output = False
        else:
            if character.source.hp >= self.health_threshold_inclusive:
                output = False
        if output:
            return super().conditions_met(character, target, source)
        return output

class KillingBlowHandoffMission(KillingBlowMission):
    
    user_eff_handoff: bool
    required_handoff: bool
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, user_eff_handoff: bool = True, required_handoff: bool = False, once: bool = False):
        super().__init__(mission_num, ability_req, user_eff_req, eff_req_reversed, target_effect_req, target_eff_req_reversed, user_mag_req, target_mag_req, once)
        self.user_eff_handoff = user_eff_handoff
        self.required_handoff = required_handoff
        
    def complete_mission(self, character: "CharacterManager", target: "CharacterManager"):
        if self.user_eff_handoff:
            if not self.required_handoff or character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).user != character:
                character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).user.progress_mission(self.mission_num, 1, self.once)
        else:
            if not self.required_handoff or target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).user != character:
                target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).user.progress_mission(self.mission_num, 1, self.once)

class KillingBlowTwinLionMission(KillingBlowMission):
    
    def complete_mission(self, character: "CharacterManager", target: "CharacterManager"):
        if character.source.second_swing:
            character.progress_mission(2, 1)
        if character.source.second_swing and character.source.first_countered:
            character.progress_mission(3, 1)

class KillingBlowSharinganMission(KillingBlowMission):
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        return character.scene.sharingan_reflecting
    
    def complete_mission(self, character: "CharacterManager", target: "CharacterManager"):
        character.scene.sharingan_reflector.progress_mission(self.mission_num, 1, self.once)

class KillingBlowMultiEffectMission(KillingBlowMission):
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_reqs: list[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_reqs: list[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, once: bool = False):
        self.mission_num = mission_num
        self.user_eff_reqs = user_eff_reqs
        self.eff_req_reversed = eff_req_reversed
        self.target_eff_reqs = target_effect_reqs
        self.target_eff_req_reversed = target_eff_req_reversed
        self.target_mag_req = target_mag_req
        self.mag_req = user_mag_req
        self.ability_req = ability_req
        self.once = once
        
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        output = True
        if self.user_eff_reqs:
            for req in self.user_eff_reqs:
                effect_requirement_met = (character.has_effect(req.eff_type, req.name) != self.eff_req_reversed)
                if not effect_requirement_met or character.get_effect(req.eff_type, req.name).mag < self.mag_req or (self.ability_req and source != self.ability_req):
                    output = False
        if self.target_eff_reqs:
            for req in self.target_eff_reqs:
                target_effect_requirement_met = (target.has_effect(self.target_eff_req.eff_type, self.target_eff_req.name) != self.target_eff_req_reversed)
                if not target_effect_requirement_met or target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).mag < self.target_mag_req:
                    output = False
        return output    

class KillingBlowTargetStateMission(KillingBlowMission):
    
    state_checks: list[Callable]
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, once: bool = False, states: list[Callable] = []):
        super().__init__(mission_num, ability_req, user_eff_req, eff_req_reversed, target_effect_req, target_eff_req_reversed, user_mag_req, target_mag_req, once)
        self.state_checks = states
        
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        for state in self.state_checks:
            if not state(target):
                return False
        return super().conditions_met(character, target, source)

class KillingBlowEffectDurationMission(KillingBlowMission):
    
    def __init__(self, mission_num: int, ability_req: str = "", user_eff_req: Optional[EffectRequirement] = None, eff_req_reversed: bool = False, target_effect_req: Optional[EffectRequirement] = None, target_eff_req_reversed: bool = False, user_mag_req: int = 0, target_mag_req: int = 0, once: bool = False, duration: int = 1, target_duration: bool = True, greater_than: bool = True):
        super().__init__(mission_num, ability_req, user_eff_req, eff_req_reversed, target_effect_req, target_eff_req_reversed, user_mag_req, target_mag_req, once)
        self.duration = duration
        self.target_duration = target_duration
        self.greater_than = greater_than
        
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        
        if self.target_duration:
            if target.has_effect(self.target_eff_req.eff_type, self.target_eff_req.name):
                if self.greater_than:
                    if target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).duration <= self.duration:
                        return False
                else:
                    if target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).duration > self.duration:
                        return False
        else:
            if character.has_effect(self.user_eff_req.eff_type, self.user_eff_req.name):
                if self.greater_than:
                    if character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).duration <= self.duration:
                        return False
                else:
                    if character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).duration > self.duration:
                        return False
        
        return super().conditions_met(character, target, source)

class KillingBlowTrigger:
    
    mission_name: str
    mission_effect_duration: int
    ability_req: str
    user_states: list[Callable]
    target_states: list[Callable]
    user_eff_req: Optional[EffectRequirement]
    user_eff_reversed: bool
    target_eff_req: Optional[EffectRequirement]
    target_eff_reversed: bool
    user_mag: int
    target_mag: int
    handoff: bool
    user_handoff: bool
    
    def __init__(self, mission_name: str, mission_effect_duration: int, user_effect_target: bool = True, ability_req: str = "", user_states: list[Callable] = [], target_states: list[Callable] = [], user_eff_req: Optional[EffectRequirement] = None, user_eff_reversed: bool = False, user_mag: int = 0, target_eff_req: Optional[EffectRequirement] = None, target_eff_reversed: bool = False, target_mag: int = 0, handoff: bool = False, user_handoff: bool = False):
        self.mission_name = mission_name
        self.mission_effect_duration = mission_effect_duration
        self.ability_req = ability_req
        self.user_states = user_states
        self.target_states = target_states
        self.user_eff_req = user_eff_req
        self.user_eff_reversed = user_eff_reversed
        self.user_mag = user_mag
        self.target_eff_req = target_eff_req
        self.target_eff_reversed = target_eff_reversed
        self.target_mag = target_mag
        self.user_effect_target = user_effect_target
        self.handoff = handoff
        self.user_handoff = user_handoff
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        output = True
        if self.user_eff_req:
            effect_requirement_met = (character.has_effect(self.user_eff_req.eff_type, self.user_eff_req.name) != self.user_eff_reversed)
            if not effect_requirement_met or character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).mag < self.user_mag or (self.ability_req and source != self.ability_req) or not all([state(character) for state in self.user_states]):
                output = False
        if self.target_eff_req:
            target_effect_requirement_met = (target.has_effect(self.target_eff_req.eff_type, self.target_eff_req.name) != self.target_eff_reversed)
            if not target_effect_requirement_met or target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name).mag < self.target_mag or (self.ability_req and source != self.ability_req) or not all([state(target) for state in self.user_states]):
                output = False
        return output
    
    def trigger(self, character: "CharacterManager", target: "CharacterManager"):
        if self.handoff:
            if self.user_handoff:
                affected = character.get_effect(self.user_eff_req.eff_type, self.user_eff_req.name).user
                user = affected
            else:
                affected = target.get_effect(self.target_eff_req.eff_type, self.target_eff_req.name)
                user = affected
        else:
            if self.user_effect_target:
                affected = character
                user = character
            else:
                affected = target
                user = character
        if affected.has_effect(EffectType.SYSTEM, self.mission_name):
            affected.get_effect(EffectType.SYSTEM, self.mission_name).alter_mag(1)
        else:
            affected.add_effect(Effect(self.mission_name, EffectType.SYSTEM, user, self.mission_effect_duration, lambda eff:"", mag=1, system=True))

class KillingBlowExclusiveTrigger(KillingBlowTrigger):
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        if self.user_effect_target:
            relevant_manager = character
        else:
            relevant_manager = target
            
        if relevant_manager.has_effect(EffectType.SYSTEM, self.mission_name):
            return False
        
        return super().conditions_met(character, target, source)

class KillingBlowSelfTrigger(KillingBlowTrigger):
    
    def conditions_met(self, character: "CharacterManager", target: "CharacterManager", source: str) -> bool:
        if not character == target:
            return False
        return super().conditions_met(character, target, source)

def invuln(target: "CharacterManager") -> bool:
    return target.check_invuln()

def ignoring(target: "CharacterManager") -> bool:
    return target.is_ignoring()

def countering(target: "CharacterManager") -> bool:
    return target.is_countering()

def last_man_standing(target: "CharacterManager") -> bool:
    return not any([(manager != target and not manager.source.dead) for manager in target.player_team])
    
class MissionHandler:
    
    @classmethod
    def handle_win_mission(self, character: "CharacterManager"):
        try:
            for mission in win_mission_handler[character.source.name]:
                if mission.conditions_met(character):
                    mission.complete_mission(character)
        except KeyError:
            pass
                
    @classmethod
    def handle_loss_mission(self, character: "CharacterManager"):
        try:
            for mission in loss_mission_handler[character.source.name]:
                if mission.conditions_met(character):
                    mission.complete_mission(character)
        except KeyError:
            pass
    
    @classmethod  
    def handle_ability_damage_mission(self, character: "CharacterManager", target: "CharacterManager", damage: int, source_name: str):
        try:
            for mission in ability_damage_mission_handler[character.source.name]:
                if mission.conditions_met(character, target, source_name):
                    mission.complete_mission(character, target, damage)
        except KeyError:
            pass
    
    @classmethod
    def handle_killing_blow_mission(self, character: "CharacterManager", target: "CharacterManager", source_name: str):
        try:
            for mission in killing_blow_mission_handler[character.source.name]:
                if mission.conditions_met(character, target, source_name):
                    mission.complete_mission(character, target)
        except KeyError:
            pass

class TriggerHandler:
    
    @classmethod
    def handle_killing_blow_trigger(self, character: "CharacterManager", target: "CharacterManager", source_name: str):
        try:
            for trigger in killing_blow_trigger_handler[character.source.name]:
                if trigger.conditions_met(character, target, source_name):
                    trigger.trigger(character, target)
        except KeyError:
            pass

killing_blow_trigger_handler: dict[str, list[KillingBlowTrigger]] = {
    "all": [KillingBlowTrigger("ShigarakiMission3Tracker", 280000, target_eff_req=EffectRequirement(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"), handoff=True, user_handoff=False)],
    "shikamaru": [KillingBlowTrigger("ShikamaruMission2Tracker", 1, ability_req="Shadow Neck Bind")],
    "ichimaru": [KillingBlowTrigger("IchimaruMission5Tracker", 280000, user_states=[last_man_standing,])],
    "shigaraki": [KillingBlowTrigger("ShigarakiMission4Tracker", 280000, user_eff_req=EffectRequirement(EffectType.ALL_BOOST, "Destroy What You Hate, Destroy What You Love"), handoff=True, user_handoff=True)],
    "uraraka": [KillingBlowExclusiveTrigger("UrarakaMission5Tracker", 280000, user_effect_target=False)],
    "todoroki": [KillingBlowTrigger("TodorokiMission1Tracker", 1, ability_req="Flashfreeze Heatwave")],
    "natsu": [KillingBlowTrigger("NatsuMission4Tracker", 280000)],
    "gajeel": [KillingBlowExclusiveTrigger("GajeelMission1ShadowTracker", 280000, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Iron Shadow Dragon")), KillingBlowExclusiveTrigger("GajeelMission1IronTracker", 280000, user_eff_req=EffectRequirement(EffectType.ALL_DR, "Blacksteel Gajeel"))],
    "frenda": [KillingBlowTrigger("FrendaMission2Tracker", 1, ability_req="Detonate")],
    "tsunayoshi": [KillingBlowTrigger("TsunaMission4Tracker", 1, ability_req="X-Burner")],
    "chrome": [KillingBlowTrigger("ChromeMission5Marker", 280000, user_effect_target=False, user_eff_req=EffectRequirement(EffectType.PROF_SWAP, "You Are Needed"), target_eff_req=EffectRequirement(EffectType.SYSTEM, "ChromeMission5Marker"), target_eff_reversed=True),
               KillingBlowTrigger("ChromeMission5Tracker", 280000, target_eff_req=EffectRequirement(EffectType.SYSTEM, "ChromeMission5Marker"), target_eff_reversed=True)],
    "tatsumi": [KillingBlowTrigger("TatsumiMission5Marker", 280000, user_effect_target=False, target_eff_req=EffectRequirement(EffectType.SYSTEM, "TatsumiMission5Marker"), target_eff_reversed=True),
               KillingBlowTrigger("TatsumiMission5Tracker", 280000, target_eff_req=EffectRequirement(EffectType.SYSTEM, "TatsumiMission5Marker"), target_eff_reversed=True)],
    "akame": [KillingBlowTrigger("AkameMission5Marker", 280000, user_effect_target=False, target_eff_req=EffectRequirement(EffectType.SYSTEM, "AkameMission5Marker"), target_eff_reversed=True),
               KillingBlowTrigger("AkameMission5Tracker", 280000, target_eff_req=EffectRequirement(EffectType.SYSTEM, "AkameMission5Marker"), target_eff_reversed=True)],
    "mine": [KillingBlowTrigger("MineMission4Tracker", 1)],
    "ripple": [KillingBlowTrigger("RippleMission5Tracker", 1)],
    "pucelle": [KillingBlowTrigger("PucelleMission5Tracker", 1, ability_req="Ideal Strike", user_states=[last_man_standing,])],
    "chachamaru": [KillingBlowTrigger("ChachamaruMission4Tracker", 1, ability_req="Orbital Satellite Cannon")],
    "saitama": [KillingBlowTrigger("SaitamaMission5Marker", 280000, user_effect_target=False, target_eff_req=EffectRequirement(EffectType.SYSTEM, "SaitamaMission5Marker"), target_eff_reversed=True),
               KillingBlowTrigger("SaitamaMission5Tracker", 280000, target_eff_req=EffectRequirement(EffectType.SYSTEM, "SaitamaMission5Marker"), target_eff_reversed=True)],
    "jeanne": [KillingBlowSelfTrigger("JeanneMission5Tracker", 280000, ability_req="Crimson Holy Maiden")],
    "frankenstein": [KillingBlowTrigger("FrankensteinMission2Counter", 280000, ability_req="Bridal Chest")],
    
}
      
killing_blow_mission_handler: dict[str, list[KillingBlowMission]] = {
    "all": [KillingBlowHandoffMission(1, user_eff_req=EffectRequirement(EffectType.ALL_DR, "Flag of the Ruler")),
            KillingBlowHandoffMission(3, target_effect_req=EffectRequirement(EffectType.ALL_STUN, "Shadow Bind Jutsu"), user_eff_handoff=False, required_handoff=True),
            KillingBlowSharinganMission(1),
            KillingBlowHandoffMission(1, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Quirk - Zero Gravity")),
            KillingBlowHandoffMission(2, target_effect_req=EffectRequirement(EffectType.ALL_DR, "Quirk - Zero Gravity"), user_eff_handoff=False),
            KillingBlowHandoffMission(4, user_eff_req=EffectRequirement(EffectType.ALL_INVULN, "Adamantine Barrier"), required_handoff=True),
            KillingBlowHandoffMission(2, target_effect_req=EffectRequirement(EffectType.ISOLATE, "Solid Script - Silent"), user_eff_handoff=False),
            KillingBlowHandoffMission(3, user_eff_req=EffectRequirement(EffectType.AFF_IMMUNE, "Solid Script - Mask")),
            KillingBlowHandoffMission(4, target_effect_req=EffectRequirement(EffectType.DEF_NEGATE, "Overwhelming Suppression"), user_eff_handoff=False),
            KillingBlowHandoffMission(1, user_eff_req=EffectRequirement(EffectType.ALL_STUN, "Mental Out")),
            KillingBlowHandoffMission(3, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Yatsufusa")),
            KillingBlowHandoffMission(5, target_effect_req=EffectRequirement(EffectType.ALL_STUN, "In The Name Of Ruler!"), user_eff_handoff=False),
            KillingBlowHandoffMission(3, user_eff_req=EffectRequirement(EffectType.ALL_BOOST, "Dream Manipulation")),
            
            ],
    "chelsea": [KillingBlowMission(3, "Mortal Wound")],
    "accelerator": [KillingBlowMission(4, "Plasma Bomb"), KillingBlowHealthThresholdMission(1)],
    "gilgamesh": [KillingBlowMission(1, "Gate of Babylon"), KillingBlowHealthThresholdMission(3), KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.SYSTEM, "GilgameshMission4Tracker"))],
    "frankenstein": [KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.STACK, "Galvanism")), KillingBlowMission(5, "Blasted Tree", EffectRequirement(EffectType.SYSTEM, "FrankensteinMission5Tracker")), KillingBlowMission(2, "Bridal Chest", user_eff_req=EffectRequirement(EffectType.SYSTEM, "FrankensteinMission2Counter"), user_mag_req=3), KillingBlowMission(1, "Bridal Smash", user_eff_req=EffectRequirement(EffectType.CONT_UNIQUE, "Bridal Chest"))],
    "naruto": [KillingBlowMission(3, user_eff_req=EffectRequirement(EffectType.ALL_INVULN, "Sage Mode")), KillingBlowMission(2, user_eff_req=EffectRequirement(EffectType.ALL_DR, "Shadow Cloens")), KillingBlowMission(4, "Rasenshuriken")],
    "itachi": [KillingBlowMission(3, user_eff_req=EffectRequirement(EffectType.DEST_DEF, "Susano'o"))],
    "minato": [KillingBlowMission(2, "Flying Raijin")],
    "neji": [KillingBlowTargetStateMission(1, "Eight Trigrams - Mountain Crusher", states=[invuln,])],
    "hinata": [KillingBlowTwinLionMission(1, "Gentle Step - Twin Lion Fists")],
    "shikamaru": [KillingBlowMission(2, "Shadow Neck Bind", EffectRequirement(EffectType.SYSTEM, "ShikamaruMission2Tracker"), user_mag_req=2)],
    "kakashi": [KillingBlowMission(2, "Raikiri", target_effect_req=EffectRequirement(EffectType.ALL_STUN, "Summon - Nin-dogs")), KillingBlowMission(4, target_effect_req=EffectRequirement(EffectType.SYSTEM, "KakashiMission4Tracker"), target_eff_req_reversed=True)],
    "ichigo": [KillingBlowMission(2, user_eff_req=EffectRequirement(EffectType.ALL_INVULN, "Tensa Zangetsu")), KillingBlowHealthThresholdMission(5, threshold=30, greater_than=False)],
    "ichimaru": [KillingBlowMission(1, "Kill, Kamishini no Yari")],
    "aizen": [KillingBlowMission(3, "Overwhelming Power")],
    "midoriya": [KillingBlowMission(4, "One For All - Shoot Style")],
    "mirio": [KillingBlowMission(5, "Phantom Menace")],
    "toga": [KillingBlowMission(5, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Quirk - Transform"), eff_req_reversed=True), KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Quirk - Transform"))],
    "shigaraki": [KillingBlowMission(2)],
    "jiro": [KillingBlowMission(4, target_effect_req=EffectRequirement(EffectType.SYSTEM, "JiroMission4Tracker")), KillingBlowMission(3, ability_req = "Heartbeat Distortion", user_eff_req=EffectRequirement(EffectType.UNIQUE, "Heartbeat Surround")), KillingBlowMission(3, ability_req = "Heartbeat Surround", user_eff_req=EffectRequirement(EffectType.UNIQUE, "Heartbeat Distortion"))],
    "natsu": [KillingBlowMission(3)],
    "gajeel": [KillingBlowMultiEffectMission(1, user_eff_reqs=[EffectRequirement(EffectType.SYSTEM, "GajeelMission1ShadowTracker"), EffectRequirement(EffectType.SYSTEM, "GajeelMission1IronTracker")], once=True)],
    "wendy": [KillingBlowMission(2, target_effect_req=EffectRequirement(EffectType.MARK, "Shredding Wedding"))],
    "erza": [KillingBlowMission(1, "Titania's Rampage")],
    "jack": [KillingBlowMission(2, target_effect_req=EffectRequirement(EffectType.MARK, "Streets of the Lost")), KillingBlowMission(4, "Maria the Ripper"), KillingBlowMission(1, user_eff_req=EffectRequirement(EffectType.SYSTEM, "JackMission1Failure"), eff_req_reversed=True)],
    "chu": [KillingBlowMission(3, ability_req="Gae Bolg", target_effect_req=EffectRequirement(EffectType.SYSTEM, "GaeBolgPierceMarker")), KillingBlowEffectDurationMission(5, "Relentless Assault", target_effect_req=EffectRequirement(EffectType.CONT_UNIQUE, "Relentless Assault"), greater_than = False)],
    "astolfo": [KillingBlowMission(3, ability_req="Trap of Argalia - Down With A Touch!"), KillingBlowMission(5, target_effect_req=EffectRequirement(EffectType.BOOST_NEGATE, "La Black Luna"))],
    "misaka": [KillingBlowMission(2, ability_req="Railgun"), KillingBlowMission(2, ability_req="Ultra Railgun")],
    "kuroko": [KillingBlowMission(4, ability_req="Teleporting Strike")],
    "gunha": [KillingBlowMission(2, ability_req="Super Awesome Punch")],
    "frenda": [KillingBlowMission(3, ability_req="Detonate")],
    "naruha": [KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.MARK, "Perfect Paper - Rampage Suit")), KillingBlowMission(5, ability_req="Enraged Blow")],
    "yamamoto": [KillingBlowMission(2, ability_req="Shinotsuku Ame")],
    "gokudera": [KillingBlowMission(3, ability_req="Sistema C.A.I.", user_eff_req=EffectRequirement(EffectType.MARK, "Vongola Box Weapon"))],
    "ryohei": [KillingBlowMission(1, ability_req="Maximum Cannon")],
    "chrome": [KillingBlowMission(4)],
    "tatsumi": [KillingBlowMission(5)],
    "mine": [KillingBlowTargetStateMission(1, user_eff_req=EffectRequirement(EffectType.MARK, "Pumpkin Scouter"), states=[invuln,]), KillingBlowHealthThresholdMission(2, ability_req="Roman Artillery Pumpkin", threshold=30, greater_than=False), KillingBlowHealthThresholdMission(3, ability_req="Cut-Down Shot", threshold=25, greater_than=False)],
    "akame": [KillingBlowMission(2), KillingBlowMission(1, user_eff_req=EffectRequirement(EffectType.MARK, "Little War Horn"))],
    "leone": [KillingBlowMission(2), KillingBlowMission(3, target_effect_req=EffectRequirement(EffectType.MARK, "Beast Instinct"))],
    "lubbock": [KillingBlowMission(3, ability_req="Heartseeker Thrust")],
    "sheele": [KillingBlowMission(1), KillingBlowTargetStateMission(2, states=[ignoring, countering]), KillingBlowMission(5, target_effect_req=EffectRequirement(EffectType.ALL_STUN, "Trump Card - Blinding Light"))],
    "seryu": [KillingBlowHandoffMission(2, ability_req="Insatiable Justice"), KillingBlowMission(3, ability_req="Body Modification - Arm Gun", target_effect_req=EffectRequirement(EffectType.ALL_BOOST, "Berserker Howl")), KillingBlowMission(5, ability_req="Body Modification - Self Destruct"), KillingBlowMultiEffectMission(4, target_effect_reqs=[EffectRequirement(EffectType.SYSTEM, "SeryuKoroTracker"), EffectRequirement(EffectType.SYSTEM, "SeryuArmGunTracker")])],
    "kurome": [KillingBlowMission(2, ability_req="Mass Animation", user_eff_req=EffectRequirement(EffectType.STACK, "Yatsufusa")), KillingBlowMission(5, user_eff_req=EffectRequirement(EffectType.MARK, "Doping Rampage"))],
    "esdeath": [KillingBlowMission(1, target_effect_req=EffectRequirement(EffectType.MARK, "Frozen Castle")), KillingBlowMission(4, target_effect_req=EffectRequirement(EffectType.ALL_STUN, "Mahapadma"))],
    "ripple": [KillingBlowMission(3, target_effect_req=EffectRequirement(EffectType.CONT_PIERCE_DMG, "Night of Countless Stars")), KillingBlowTargetStateMission(4, states=[invuln,])],
    "cmary": [KillingBlowMission(2, ability_req="Grenade Toss", target_effect_req=EffectRequirement(EffectType.UNIQUE, "Hidden Mine")), KillingBlowMission(3, "Quickdraw - Pistol"), KillingBlowMission(3, "Quickdraw - Rifle"), KillingBlowMission(3, "Quickdraw - Sniper")],
    "cranberry": [KillingBlowMission(2, "Merciless Finish")],
    "swimswim": [KillingBlowMission(1, user_eff_req=EffectRequirement(EffectType.UNIQUE, "Dive")), KillingBlowMission(2, user_eff_req=EffectRequirement(EffectType.ALL_BOOST, "Vitality Pill"))],
    "pucelle": [KillingBlowMission(1, "Ideal Strike"), KillingBlowMission(3, "Knight's Sword")],
    "chachamaru": [KillingBlowMission(3, "Orbital Satellite Cannon")],
    "saitama": [KillingBlowMission(1, "One Punch")],
    "tatsumaki": [KillingBlowMission(3, "Return Assault"), KillingBlowMission(5, "Rubble Barrage")],
    "mirai": [KillingBlowMission(2, user_eff_req=EffectRequirement(EffectType.MARK, "Blood Suppression Removal")), KillingBlowHandoffMission(4, "Blood Sword Combat")],
    "touka": [KillingBlowMission(3, "Raikiri"), KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.MARK, "Nukiashi"))],
    "killua": [KillingBlowMission(4, user_eff_req=EffectRequirement(EffectType.MARK, "Godspeed"))],
    "byakuya": [KillingBlowHealthThresholdMission(4), KillingBlowHealthThresholdMission(5, ability_req="White Imperial Sword", threshold=41, greater_than=False)],
    "lucy": [KillingBlowMission(3, user_eff_req=EffectRequirement(EffectType.MARK, "Gemini"))]
}
                
ability_damage_mission_handler: dict[str, list[AbilityDamageMission]] = {
    "hinata": [AbilityDamageMission(5, "Eight Trigrams - 64 Palms")],
    "shikamaru": [AbilityDamageMission(1, "Shadow Neck Bind")],
    "neji": [AbilityDamageMission(3, "Eight Trigrams - 128 Palms")],
    "rukia": [AbilityDamageMission(2, "Second Dance - Hakuren")],
    "midoriya": [AbilityDamageMission(1, "SMASH!"), AbilityDamageMission(2, "One For All - Shoot Style")],
    "uraraka": [AbilityDamageMission(4, eff_req=EffectRequirement(EffectType.ALL_BOOST, "Meteor Storm"), handoff=True)],
    
    
}
        
loss_mission_handler: dict[str, list[WinMission]] = {
    "saber": [HighestDamageMission(4, 1)],
    "mine": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "SaberDamageTracker"), mag_req=225)],
    "leone": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "LeoneMission5Tracker"), mag_req=200)],
}

        
win_mission_handler: dict[str, list[WinMission]] = {
    "itachi": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "ItachiMission4Tracker")),],
    "aizen": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "AizenMission5Tracker")),],
    "toga": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "TogaMission3Ready")), WinMission(5, 1, EffectRequirement(EffectType.UNIQUE, "Quirk - Transform"), eff_req_reversed=True), WinMission(4, 1, EffectRequirement(EffectType.UNIQUE, "Quirk - Transform"))],
    "shigaraki": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "ShigarakiMission3Tracker")), WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "ShigarakiMission4Tracker"), mag_req=3)],
    "uraraka": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "UrarakaMission5Tracker"), eff_req_reversed=True)],
    "todoroki": [WinMission(1, 1, EffectRequirement(EffectType.SYSTEM, "TodorokiMission1Tracker"), mag_req=3)],
    "jiro": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "JiroMission5Tracker"))],
    "mirio": [ProtectionMission(4, 1)],
    "saber": [HighestDamageMission(3, 1)],
    "natsu": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "NatsuMission3Tracker"), mag_req=3)],
    "gray": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "GrayMission3Tracker"), mag_req=4), WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "GrayMission4TrackerSuccess"))],
    "lucy": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "LucyMission5Failure"), eff_req_reversed=True)],
    "jack": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "JackMission5Success"))],
    "erza": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "ErzaMission5Tracker"))],
    "gunha": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "GunhaMission3Tracker"))],
    "misaki": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "MisakiMission4Success")), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "MisakiMission5Success"))],
    "frenda": [WinMission(2, 1, EffectRequirement(EffectType.SYSTEM, "FrendaMission2Tracker"), mag_req=3), LastManStandingMission(5, 1, health_threshold = 25)],
    "naruha": [WinMission(1, 1, EffectRequirement(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"), eff_req_reversed=True), WinMission(2, 1, EffectRequirement(EffectType.UNIQUE, "Perfect Paper - Rampage Suit"))],
    "lambo": [WinMission(1, 1, EffectRequirement(EffectType.SYSTEM, "LamboMission1Failure"), eff_req_reversed=True), SpecificMagMission(2, 1, EffectRequirement(EffectType.PROF_SWAP, "Ten-Year Bazooka"), mag_req = 1), SpecificMagMission(3, 1, EffectRequirement(EffectType.PROF_SWAP, "Ten-Year Bazooka"), mag_req = 2)],
    "chrome": [WinMission(1, 1, EffectRequirement(EffectType.PROF_SWAP, "You Are Needed"), eff_req_reversed=True), WinMission(2, 1, EffectRequirement(EffectType.PROF_SWAP, "You Are Needed")), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "ChromeMission5Tracker"), mag_req=3)],
    "tatsumi": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "TatsumiMission5Tracker"), mag_req=3)],
    "mine": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "MineMission4Tracker"), mag_req=3), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "SaberDamageTracker"), mag_req=225)],
    "tsunayoshi": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "TsunaMission4Tracker"), mag_req=3)],
    "akame": [WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "AkameMission3Tracker")), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "AkameMission5Tracker"), mag_req=3)],
    "leone": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "LeoneMission5Tracker"), mag_req=200)],
    "lubbock": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "LubbockMission4Failure"), eff_req_reversed=True), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "LubbockMission5Failure"), eff_req_reversed=True)],
    "esdeath": [WinMission(2, 1), WinMission(3, 1, EffectRequirement(EffectType.SYSTEM, "EsdeathMission3Failure"), eff_req_reversed=True), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "EsdeathMission5Tracker"))],
    "snowwhite": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "SnowWhiteMission4Failure"), eff_req_reversed=True)],
    "ripple": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "RippleMission5Tracker"), mag_req=3)],
    "nemurin": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "NemurinMission5Failure"), eff_req_reversed=True)],
    "swimswim": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "SwimSwimMission5Tracker"), mag_req=5)],
    "pucelle": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "PucelleMission5Tracker"))],
    "chachamaru": [WinMission(4, 1, EffectRequirement(EffectType.SYSTEM, "ChachamaruMission4Tracker"), mag_req=3)],
    "saitama": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "SaitamaMission5Tracker"), mag_req=3), ExclusionMission(4, 1, EffectRequirement(EffectType.SYSTEM, "SaitamaMission4Tracker"), excluded_effect=EffectRequirement(EffectType.SYSTEM, "SaitamaMission4Failure"))],
    "touka": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "ToukaMission5Failure"), eff_req_reversed=True)],
    "swimswim": [LastManStandingMission(3, 1)],
    "misaka": [WinMission(1, 1, EffectRequirement(EffectType.MARK, "Ultra Railgun")), LastManStandingMission(5, 1, EffectRequirement(EffectType.MARK, "Level-6 Shift"))],
    "gilgamesh": [FullHealthMission(2, 1)],
    "jeanne": [NoDeathMission(4, 1), WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "JeanneMission5Tracker"))],
    "accelerator": [WinMission(5, 1, EffectRequirement(EffectType.SYSTEM, "AcceleratorMission5Tracker")), ExclusionMission(2, 1, EffectRequirement(EffectType.SYSTEM, "AcceleratorMission2Tracker"), excluded_effect=EffectRequirement(EffectType.SYSTEM, "AcceleratorMission2Failure"))],
    "chelsea": [FullHealthMission(1, 1), ExclusionMission(5, 1, EffectRequirement(EffectType.SYSTEM, "ChelseaMission5Tracker"), excluded_effect=EffectRequirement(EffectType.SYSTEM, "ChelseaMission5Failure"))]
}