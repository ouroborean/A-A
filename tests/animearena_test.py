from pickle import PUT

from animearena import battle_scene, character_select_scene
from animearena.ability import Ability, ability_info_db, Target
from animearena.energy import Energy
from animearena.scene_manager import SceneManager
from animearena.character import Character, character_db
from animearena.effects import Effect, EffectType
from animearena import engine

import pytest
import sdl2
import sdl2dll
import sdl2.ext

from animearena.battle_scene import BattleScene, make_battle_scene, CharacterManager

scene_manager = SceneManager()
uiprocessor = sdl2.ext.UIProcessor()
resources_path = "resources"

def do_targeting(scene: BattleScene, targeter: CharacterManager, primary_target: CharacterManager):
    scene.acting_character = targeter
    scene.selected_ability = targeter.used_ability
    scene.apply_targeting(primary_target)

def do_enemy_targeting(scene: BattleScene, targeter: CharacterManager, primary_target: CharacterManager):
    scene.acting_character = targeter
    scene.selected_ability = targeter.used_ability
    enemy_apply_targeting(scene, primary_target)

def tick_one_turn(scene: BattleScene):
    scene.resolve_ticking_ability()
    scene.tick_effect_duration()
    scene.tick_effect_duration()

def enemy_apply_targeting(scene: BattleScene, primary_target: CharacterManager):
        if scene.selected_ability.target_type == Target.SINGLE:
            scene.acting_character.add_current_target(primary_target)
            primary_target.add_received_ability(scene.selected_ability)
        elif scene.selected_ability.target_type == Target.MULTI_ALLY:
            scene.selected_ability.primary_target = primary_target
            for manager in scene.enemy_display.team.character_managers:
                if manager.targeted:
                    scene.acting_character.add_current_target(manager)
                    manager.add_received_ability(scene.selected_ability)
        elif scene.selected_ability.target_type == Target.MULTI_ENEMY:
            scene.selected_ability.primary_target = primary_target
            for manager in scene.player_display.team.character_managers:
                if manager.targeted:
                    scene.acting_character.add_current_target(manager)
                    manager.add_received_ability(scene.selected_ability)
        elif scene.selected_ability.target_type == Target.ALL_TARGET:
            scene.selected_ability.primary_target = primary_target
            for manager in scene.player_display.team.character_managers:
                if manager.targeted:
                    scene.acting_character.add_current_target(manager)
                    manager.add_received_ability(scene.selected_ability)
            for manager in scene.enemy_display.team.character_managers:
                if manager.targeted:
                    scene.acting_character.add_current_target(manager)
                    manager.add_received_ability(scene.selected_ability)
        scene.reset_targeting()
        scene.acting_character.primary_target = primary_target
        scene.selected_ability.user = scene.acting_character
        scene.acting_character.used_ability = scene.selected_ability
        scene.selected_ability = None
        scene.acting_character.acted = True

def ally_use_ability_with_response(scene: BattleScene, targeter: CharacterManager, primary_target: CharacterManager, ability: Ability):
    targeter.used_ability = ability
    targeter.used_ability.target(targeter, scene.player_display.team.character_managers, scene.enemy_display.team.character_managers)
    do_targeting(scene, targeter, primary_target)
    targeter.used_ability.execute(targeter, scene.player_display.team.character_managers, scene.enemy_display.team.character_managers)
    targeter.current_targets.clear()
    scene.resolve_ticking_ability()
    scene.tick_effect_duration()

def ally_use_ability(scene: BattleScene, targeter: CharacterManager, primary_target: CharacterManager, ability: Ability):
    targeter.used_ability = ability
    targeter.used_ability.target(targeter, scene.player_display.team.character_managers, scene.enemy_display.team.character_managers)
    do_targeting(scene, targeter, primary_target)
    targeter.used_ability.execute(targeter, scene.player_display.team.character_managers, scene.enemy_display.team.character_managers)
    targeter.current_targets.clear()
    tick_one_turn(scene)

def enemy_use_ability(scene: BattleScene, targeter: CharacterManager, primary_target: CharacterManager, ability: Ability):
    targeter.used_ability = ability
    targeter.used_ability.target(targeter, scene.enemy_display.team.character_managers, scene.player_display.team.character_managers)
    do_enemy_targeting(scene, targeter, primary_target)
    targeter.used_ability.execute(targeter, scene.enemy_display.team.character_managers, scene.player_display.team.character_managers)
    targeter.current_targets.clear()

@pytest.fixture
def test_scene() -> engine.Scene:
    return make_battle_scene(scene_manager)

@pytest.fixture
def naruto_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("naruto"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("snowwhite"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def aizen_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("aizen"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("snowwhite"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def akame_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("akame"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("snowwhite"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def astolfo_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("astolfo"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("naruto"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def cmary_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("cmary"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("naruto"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def chachamaru_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("chachamaru"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("naruto"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene    

@pytest.fixture
def chrome_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("chrome"), Character("toga"), Character("nemu")]
    enemy_team = [Character("ruler"), Character("naruto"), Character("mirio")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def chu_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("chu"), Character("toga"), Character("nemu")]
    enemy_team = [Character("chrome"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def cranberry_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("cranberry"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def erza_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("erza"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def frenda_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("frenda"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def esdeath_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("esdeath"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def gajeel_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("naruto"), Character("toga"), Character("nemu")]
    enemy_team = [Character("gajeel"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def gokudera_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("gokudera"), Character("toga"), Character("nemu")]
    enemy_team = [Character("gajeel"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def hibari_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("hibari"), Character("toga"), Character("nemu")]
    enemy_team = [Character("gajeel"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def gray_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("gray"), Character("toga"), Character("nemu")]
    enemy_team = [Character("gajeel"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def gunha_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("sogiita"), Character("toga"), Character("nemu")]
    enemy_team = [Character("gajeel"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def hinata_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("hinata"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("chu")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def ichigo_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("ichigo"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("cmary")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def ichimaru_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("ichimaru"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("cmary")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def jack_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("jack"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("cmary")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def itachi_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("itachi"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("itachi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def jiro_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("jiro"), Character("toga"), Character("nemu")]
    enemy_team = [Character("hinata"), Character("naruto"), Character("itachi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def kakashi_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("kakashi"), Character("toga"), Character("nemu")]
    enemy_team = [Character("hinata"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def kuroko_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("kuroko"), Character("toga"), Character("nemu")]
    enemy_team = [Character("hinata"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def lambo_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("lambo"), Character("toga"), Character("nemu")]
    enemy_team = [Character("hinata"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def lapucelle_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("pucelle"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def laxus_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("laxus"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def leone_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("leone"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("kakashi")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def levy_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("levy"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("toga")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene


@pytest.fixture
def lubbock_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("raba"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("toga")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene

@pytest.fixture
def lucy_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("lucy"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("toga")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene


@pytest.fixture
def midoriya_test_scene(test_scene: BattleScene) -> engine.Scene:
    ally_team = [Character("midoriya"), Character("toga"), Character("nemu")]
    enemy_team = [Character("astolfo"), Character("naruto"), Character("toga")]
    test_scene.setup_scene(ally_team, enemy_team)
    return test_scene




def test_detail_unpack():
    details_package = ["Justice Kick", "Shiro deals 20 damage to target enemy. If they damaged one of Shiro's allies the previous turn, this ability deals double damage.", [1,0,0,0,0,1], Target.SINGLE]

    test_ability = Ability()

    test_ability.unpack_details(details_package)

    assert test_ability.name == "Justice Kick"
    assert test_ability.cost[Energy.PHYSICAL] == 1

def test_shadow_clones(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers
    shadow_clones = naruto.source.current_abilities[0]
    rasengan = naruto.source.current_abilities[1]
    
    shadow_clones.execute(naruto, e_team, p_team)

    assert len(naruto.source.current_effects) == 4

    naruto.update_ability()

    assert naruto.source.current_abilities[0].name == "Sage Mode"
    assert naruto.source.current_abilities[2].name == "Uzumaki Barrage"
    assert naruto.source.current_abilities[1].target_type == Target.MULTI_ENEMY

    rasengan.target(naruto, p_team, e_team)
    naruto_test_scene.selected_ability = rasengan
    naruto_test_scene.acting_character = naruto
    naruto_test_scene.apply_targeting(e_team[0])

    assert len(naruto.current_targets) == 3
    naruto.used_ability = rasengan
    rasengan.execute(naruto, p_team, e_team)

    for enemy in e_team:
        assert enemy.source.hp == 75
        assert enemy.is_stunned()

def test_sage_mode(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers

    Ability("narutoalt1").execute(naruto, e_team, p_team)

    assert len(naruto.source.current_effects) == 3
    
    naruto.update_ability()

    assert naruto.source.current_abilities[2].name == "Toad Taijutsu"
    assert naruto.check_invuln()

def test_uzumaki_barrage(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers
    uzumaki_barrage = naruto.source.alt_abilities[1]
    naruto.current_targets.append(e_team[0])
    naruto.used_ability = uzumaki_barrage
    uzumaki_barrage.execute(naruto, e_team, p_team)

    assert e_team[0].source.hp == 85
    assert e_team[0].is_stunned() == False
    assert naruto.has_effect(EffectType.MARK, "Uzumaki Barrage")

    uzumaki_barrage.execute(naruto, e_team, p_team)

    assert e_team[0].source.hp == 70
    assert e_team[0].is_stunned() == True
    assert naruto.has_effect(EffectType.MARK, "Uzumaki Barrage")

def test_toad_taijutsu(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers
    toad_taijutsu = naruto.source.alt_abilities[2]
    fucking_ruler = e_team[0]
    naruto.current_targets.append(fucking_ruler)
    naruto.used_ability = toad_taijutsu
    toad_taijutsu.execute(naruto, p_team, e_team)

    assert len(fucking_ruler.source.current_effects) == 1
    assert fucking_ruler.source.hp == 65
    fucking_ruler.refresh_character(True)
    assert fucking_ruler.source.main_abilities[0].total_cost == 3

def test_sage_mode_rasengan(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers
    rasengan = naruto.source.main_abilities[1]
    sage_mode = naruto.source.alt_abilities[0]
    fucking_ruler = e_team[0]

    naruto.current_targets.append(naruto)
    sage_mode.execute(naruto, p_team, e_team)
    naruto.current_targets.clear()
    
    naruto.used_ability = rasengan
    naruto.current_targets.append(fucking_ruler)
    rasengan.execute(naruto, p_team, e_team)

    assert fucking_ruler.source.hp == 50
    assert fucking_ruler.get_effect(EffectType.ALL_STUN, "Rasengan").duration == 4

def test_aizen_mark_application(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    shatter = aizen.source.current_abilities[0]
    power = aizen.source.current_abilities[1]
    coffin = aizen.source.current_abilities[2]

    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)
    shatter.execute(aizen, pteam, eteam)
    aizen.used_ability = power
    power.execute(aizen, pteam, eteam)

    coffin.execute(aizen, pteam, eteam)

    assert fucking_ruler.has_effect(EffectType.MARK, "Shatter, Kyoka Suigetsu")
    assert fucking_ruler.has_effect(EffectType.MARK, "Overwhelming Power")
    assert fucking_ruler.has_effect(EffectType.MARK, "Black Coffin")
    
def test_shatter(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    shatter = aizen.source.current_abilities[0]
    fucking_ruler = eteam[0]

    aizen.current_targets.append(fucking_ruler)
    shatter.execute(aizen, pteam, eteam)
    fucking_ruler.adjust_ability_costs()
    assert fucking_ruler.source.current_abilities[0].total_cost == 2

def test_shatter_on_power(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    shatter = aizen.source.current_abilities[0]
    power = aizen.source.current_abilities[1]
    fucking_ruler = eteam[0]
    aizen.used_ability = power
    aizen.current_targets.append(fucking_ruler)
    power.execute(aizen, pteam, eteam)

    fucking_ruler.refresh_character(True)

    assert fucking_ruler.has_effect(EffectType.MARK, "Overwhelming Power")

    shatter.execute(aizen, pteam, eteam)

    aizen.adjust_ability_costs()

    assert aizen.source.current_abilities[0].total_cost == 1

def test_shatter_on_coffin(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    shatter = aizen.source.current_abilities[0]
    coffin = aizen.source.current_abilities[2]
    fucking_ruler = eteam[0]
    
    fucking_ruler.source.current_abilities[0].cooldown_remaining = 3
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)

    coffin.execute(aizen, pteam, eteam)

    fucking_ruler.refresh_character(True)

    shatter.execute(aizen, pteam, eteam)

    assert fucking_ruler.source.current_abilities[0].cooldown_remaining == 5
    assert fucking_ruler.source.current_abilities[1].cooldown_remaining == 0

def test_power(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    power = aizen.source.current_abilities[1]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)
    aizen.used_ability=power
    power.execute(aizen, pteam, eteam)

    assert fucking_ruler.source.hp == 75

def test_power_on_shatter(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    power = aizen.source.current_abilities[1]
    shatter = aizen.source.current_abilities[0]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)

    shatter.execute(aizen, pteam, eteam)
    aizen.used_ability=power
    power.execute(aizen, pteam, eteam)

    assert fucking_ruler.source.hp == 55

def test_power_on_coffin(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    power = aizen.source.current_abilities[1]
    coffin = aizen.source.current_abilities[2]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)

    coffin.execute(aizen, pteam, eteam)
    aizen.used_ability=power
    power.execute(aizen, pteam, eteam)

    assert fucking_ruler.has_effect(EffectType.DEF_NEGATE, "Overwhelming Power")

def test_coffin(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    coffin = aizen.source.current_abilities[2]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)

    coffin.execute(aizen, pteam, eteam)

    assert fucking_ruler.is_stunned()

def test_coffin_on_power(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    power = aizen.source.current_abilities[1]
    coffin = aizen.source.current_abilities[2]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)
    aizen.used_ability=power
    power.execute(aizen, pteam, eteam)
    aizen.used_ability=coffin
    coffin.execute(aizen, pteam, eteam)

    assert fucking_ruler.source.hp == 55

def test_coffin_on_shatter(aizen_test_scene: BattleScene):
    aizen = aizen_test_scene.player_display.team.character_managers[0]
    eteam = aizen_test_scene.enemy_display.team.character_managers
    pteam = aizen_test_scene.player_display.team.character_managers
    coffin = aizen.source.current_abilities[2]
    shatter = aizen.source.current_abilities[0]
    fucking_ruler = eteam[0]
    aizen.primary_target = fucking_ruler
    aizen.current_targets.append(fucking_ruler)

    shatter.execute(aizen, pteam, eteam)

    coffin.execute(aizen, pteam, eteam)

    for enemy in eteam:
        assert enemy.is_stunned()
        assert enemy.has_effect(EffectType.MARK, "Black Coffin")

def test_red_eye_mark(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    fucking_ruler = eteam[0]
    akame.primary_target = fucking_ruler
    akame.current_targets.append(fucking_ruler)
    red_eyes = akame.source.current_abilities[0]
    
    red_eyes.execute(akame, pteam, eteam)

    assert fucking_ruler.has_effect(EffectType.MARK, "Red-Eyed Killer")

def test_one_cut(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    fucking_ruler = eteam[0]
    akame.primary_target = fucking_ruler
    akame.current_targets.append(fucking_ruler)
    one_cut = akame.source.current_abilities[1]
    akame.used_ability = one_cut
    one_cut.execute(akame, pteam, eteam)

    assert fucking_ruler.source.dead

def test_little_war_horn_markless(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    fucking_ruler = eteam[0]
    
    akame.current_targets.append(akame)
    one_cut = akame.source.current_abilities[1]
    little_war_horn = akame.source.current_abilities[2]

    little_war_horn.execute(akame, pteam, eteam)

    akame.current_targets.clear()
    
    assert one_cut.target(akame, pteam, eteam, True) == 3

def test_little_war_horn_bypass(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    fucking_ruler = eteam[0]
    
    akame.current_targets.append(akame)
    one_cut = akame.source.current_abilities[1]
    little_war_horn = akame.source.current_abilities[2]

    little_war_horn.execute(akame, pteam, eteam)

    akame.current_targets.clear()

    for enemy in eteam:
        enemy.source.invulnerable = True
    
    assert one_cut.target(akame, pteam, eteam, True) == 3

def test_one_cut_default_markless(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    one_cut = akame.source.current_abilities[1]

    akame.current_targets.clear()

    assert one_cut.target(akame, pteam, eteam, True) == 0

def test_one_cut_default_mark(akame_test_scene: BattleScene):
    akame = akame_test_scene.player_display.team.character_managers[0]
    eteam = akame_test_scene.enemy_display.team.character_managers
    pteam = akame_test_scene.player_display.team.character_managers
    one_cut = akame.source.current_abilities[1]
    red_eye = akame.source.current_abilities[0]
    akame.current_targets.append(eteam[0])
    red_eye.execute(akame, pteam, eteam)

    akame.current_targets.clear()

    assert one_cut.target(akame, pteam, eteam, True) == 1

def test_trap_of_argalia(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    trap = astolfo.source.current_abilities[1]
    fucking_ruler = eteam[0]
    astolfo.used_ability = trap
    astolfo.current_targets.append(fucking_ruler)
    trap.execute(astolfo, pteam, eteam)

    assert fucking_ruler.source.hp == 80

def test_trap_boost_gain(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    trap = astolfo.source.current_abilities[1]
    fucking_ruler = eteam[0]
    astolfo.used_ability = trap
    astolfo.current_targets.append(fucking_ruler)

    fucking_ruler.add_effect(Effect(Ability("ruler1"), EffectType.ALL_BOOST, fucking_ruler, 100, lambda eff:"", 30))

    trap.execute(astolfo, pteam, eteam)
    assert astolfo.has_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!")

def test_trap_boost_halt(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    trap = astolfo.source.current_abilities[1]
    fucking_ruler = eteam[0]
    astolfo.used_ability = trap
    astolfo.current_targets.append(fucking_ruler)
    fucking_ruler.add_effect(Effect(Ability("ruler1"), EffectType.ALL_BOOST, fucking_ruler, 100, lambda eff:"", 30))
    fucking_ruler.used_ability = trap
    trap.execute(astolfo, pteam, eteam)
    naruto = CharacterManager(Character("naruto"), astolfo_test_scene)
    naruto.id = 69
    astolfo.current_targets.clear()
    astolfo.current_targets.append(naruto)
    trap.execute(astolfo, pteam, eteam)
    naruto.current_targets.append(naruto)
    naruto.source.alt_abilities[0].execute(naruto, pteam, eteam)
    naruto.current_targets.clear()

    naruto.current_targets.append(fucking_ruler)
    naruto.used_ability = naruto.source.main_abilities[1]
    naruto.used_ability.execute(naruto, pteam, eteam)

    assert fucking_ruler.get_boosts(0) == 0
    assert fucking_ruler.source.hp == 55

def test_trap_stack_boost(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    trap = astolfo.source.current_abilities[1]
    fucking_ruler = eteam[0]
    astolfo.used_ability = trap
    astolfo.current_targets.append(fucking_ruler)
    astolfo.apply_stack_effect(Effect(trap, EffectType.STACK, astolfo, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=5), astolfo)

    trap.execute(astolfo, pteam, eteam)

    assert fucking_ruler.source.hp == 55

def test_effect_removal(naruto_test_scene: BattleScene):
    naruto = naruto_test_scene.player_display.team.character_managers[0]
    e_team = naruto_test_scene.enemy_display.team.character_managers
    p_team = naruto_test_scene.player_display.team.character_managers
    shadow_clones = naruto.source.current_abilities[0]
    
    shadow_clones.execute(naruto, e_team, p_team)
    naruto.full_remove_effect("Shadow Clones", naruto)
    assert len(naruto.source.current_effects) == 0

def test_luna_cleanse(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    luna = astolfo.source.current_abilities[2]
    naruto = eteam[1]
    for p in pteam:
        astolfo.current_targets.append(p)
    astolfo.used_ability = luna
    rasengan = naruto.source.current_abilities[1]
    naruto.used_ability = rasengan
    naruto.current_targets.append(pteam[1])

    rasengan.execute(naruto, pteam, eteam)

    assert len(pteam[1].source.current_effects) == 1

    luna.execute(astolfo, pteam, eteam)

    assert len(pteam[1].source.current_effects) == 0

    assert astolfo.has_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!")

def test_luna_boost_halt(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    luna = astolfo.source.current_abilities[2]
    fucking_ruler = eteam[0]
    astolfo.used_ability = luna
    naruto = CharacterManager(Character("naruto"), astolfo_test_scene)
    astolfo.current_targets.append(naruto)
    
    naruto.id = 69
    luna.execute(astolfo, pteam, eteam)

    
    naruto.current_targets.append(naruto)
    naruto.source.alt_abilities[0].execute(naruto, pteam, eteam)
    naruto.current_targets.clear()
    
    

    naruto.current_targets.append(fucking_ruler)
    naruto.used_ability = naruto.source.main_abilities[1]
    naruto.used_ability.execute(naruto, pteam, eteam)

    assert fucking_ruler.source.hp == 75

def test_cmary_pistol(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers

    pistol = cmary.source.current_abilities[0]
    fucking_ruler = eteam[0]
    cmary.used_ability = pistol
    cmary.current_targets.append(fucking_ruler)

    pistol.execute(cmary, pteam, eteam)

    cmary.update_ability()
    
    assert fucking_ruler.source.hp == 85
    assert cmary.source.current_abilities[0].name == "Quickdraw - Rifle"

def test_cmary_rifle(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers

    rifle = cmary.source.alt_abilities[0]
    fucking_ruler = eteam[0]
    cmary.used_ability = rifle
    cmary.current_targets.append(fucking_ruler)

    rifle.execute(cmary, pteam, eteam)

    assert fucking_ruler.source.hp == 85
    assert fucking_ruler.has_effect(EffectType.CONT_DMG, "Quickdraw - Rifle")

    cmary_test_scene.resolve_ticking_ability()
    cmary_test_scene.tick_effect_duration()
    cmary_test_scene.tick_effect_duration()
    cmary_test_scene.resolve_ticking_ability()
    cmary_test_scene.tick_effect_duration()

    cmary.update_ability()

    assert fucking_ruler.source.hp == 70
    assert len(cmary.source.current_effects) == 1
    assert cmary.source.current_abilities[0].name == "Quickdraw - Sniper"

def test_hidden_mine(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers

    mine = cmary.source.main_abilities[1]
    naruto = eteam[1]
    cmary.used_ability = mine
    cmary.current_targets.append(naruto)

    mine.execute(cmary, pteam, eteam)

    assert naruto.has_effect(EffectType.MARK, "Hidden Mine")
    
    smack = naruto.source.main_abilities[2]
    naruto.used_ability = smack
    naruto.current_targets.append(cmary)

    smack.execute(naruto, eteam, pteam)

    assert cmary.source.hp == 70
    assert naruto.source.hp == 80

def test_hidden_mine_on_invuln(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers

    mine = cmary.source.main_abilities[1]
    naruto = eteam[1]
    cmary.used_ability = mine
    cmary.current_targets.append(naruto)

    mine.execute(cmary, pteam, eteam)

    assert naruto.has_effect(EffectType.MARK, "Hidden Mine")
    
    sub = naruto.source.main_abilities[3]
    naruto.used_ability = sub
    naruto.current_targets.append(cmary)

    sub.execute(naruto, eteam, pteam)

    assert naruto.source.hp == 100

def test_grenade_toss(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers
    grenade_toss = cmary.source.main_abilities[2]
    mine = cmary.source.main_abilities[1]
    naruto = eteam[1]
    cmary.used_ability = mine
    cmary.current_targets.append(naruto)
    
    mine.execute(cmary, pteam, eteam)
    cmary.current_targets.clear()
    for enemy in eteam:
        cmary.current_targets.append(enemy)

    cmary.used_ability = grenade_toss
    grenade_toss.execute(cmary, pteam, eteam)

    assert eteam[0].source.hp == 80
    assert eteam[1].source.hp == 60
    assert eteam[2].source.hp == 80

def test_sniper_rifle(cmary_test_scene: BattleScene):
    cmary = cmary_test_scene.player_display.team.character_managers[0]
    eteam = cmary_test_scene.enemy_display.team.character_managers
    pteam = cmary_test_scene.player_display.team.character_managers

    sniper = cmary.source.alt_abilities[1]
    naruto = eteam[1]
    cmary.used_ability = sniper
    cmary.current_targets.append(naruto)

    sniper.execute(cmary, pteam, eteam)

    assert cmary.check_invuln()
    assert naruto.source.hp == 45

def test_target_lock(chachamaru_test_scene: BattleScene):
    chacha = chachamaru_test_scene.player_display.team.character_managers[0]
    eteam = chachamaru_test_scene.enemy_display.team.character_managers
    pteam = chachamaru_test_scene.player_display.team.character_managers
    lock = chacha.source.current_abilities[0]
    cannon = chacha.source.current_abilities[1]
    combat_mode = chacha.source.current_abilities[2]
    chacha.used_ability = lock
    ruler = eteam[0]
    chacha.current_targets.append(ruler)
    lock.execute(chacha, pteam, eteam)
    chacha.current_targets.clear()

    assert cannon.target(chacha, pteam, eteam, True) == 1

def test_satellite_cannon(chachamaru_test_scene: BattleScene):
    chacha = chachamaru_test_scene.player_display.team.character_managers[0]
    eteam = chachamaru_test_scene.enemy_display.team.character_managers
    pteam = chachamaru_test_scene.player_display.team.character_managers
    ruler = eteam[0]
    lock = chacha.source.current_abilities[0]
    cannon = chacha.source.current_abilities[1]
    combat_mode = chacha.source.current_abilities[2]
    chacha.current_targets.append(ruler)
    chacha.used_ability = cannon
    cannon.execute(chacha, pteam, eteam)

    assert ruler.source.hp == 65

def test_combat_mode(chachamaru_test_scene: BattleScene):
    chacha = chachamaru_test_scene.player_display.team.character_managers[0]
    eteam = chachamaru_test_scene.enemy_display.team.character_managers
    pteam = chachamaru_test_scene.player_display.team.character_managers
    ruler = eteam[0]
    naruto = eteam[1]
    lock = chacha.source.current_abilities[0]
    cannon = chacha.source.current_abilities[1]
    combat_mode = chacha.source.current_abilities[2]
    chacha.current_targets.append(ruler)
    chacha.used_ability = combat_mode
    combat_mode.execute(chacha, pteam, eteam)
    naruto.current_targets.append(chacha)
    naruto.used_ability = naruto.source.current_abilities[2]

    naruto.used_ability.execute(naruto, eteam, pteam)

    assert ruler.source.hp == 90
    assert chacha.source.hp == 85

    chachamaru_test_scene.resolve_ticking_ability()
    chachamaru_test_scene.resolve_ticking_ability()
    chachamaru_test_scene.resolve_ticking_ability()

    assert ruler.source.hp == 70
    
    naruto.used_ability.execute(naruto, eteam, pteam)

    assert chacha.source.hp == 85

def test_you_are_needed(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    ruler = eteam[0]

    assert breakdown.target(chrome, pteam, eteam, True) == 0
    assert immolation.target(chrome, pteam, eteam, True) == 0
    chrome.current_targets.append(chrome)

    chrome.used_ability = needed
    needed.execute(chrome, pteam, eteam)

    assert chrome.has_effect(EffectType.MARK, "You Are Needed")

def test_breakdown(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]
    
    naruto.current_targets.append(chrome)
    naruto.used_ability = naruto.source.main_abilities[1]

    chrome.used_ability = breakdown

    chrome.current_targets.append(naruto)

    chrome.used_ability.execute(chrome, pteam, eteam)

    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 75
    assert naruto.is_stunned()

    assert len(chrome.source.current_effects) == 0

    chrome.used_ability.execute(chrome, pteam, eteam)
    naruto.used_ability.execute(naruto, pteam, eteam)

    assert chrome.source.hp == 95
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 75

def test_immolation(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]
    
    naruto.current_targets.append(chrome)
    naruto.used_ability = naruto.source.main_abilities[1]

    chrome.used_ability = immolation

    chrome.current_targets.append(naruto)

    chrome.used_ability.execute(chrome, pteam, eteam)

    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 80
    assert naruto.source.energy_contribution == 0

    assert len(chrome.source.current_effects) == 0

    chrome.used_ability.execute(chrome, pteam, eteam)
    naruto.used_ability.execute(naruto, pteam, eteam)

    assert chrome.source.hp == 90
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 80

def test_you_are_needed_swap(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]

    chrome.used_ability = needed
    needed.execute(chrome, pteam, eteam)

    chrome.source.hp = 50
    
    naruto.used_ability = naruto.source.current_abilities[2]
    naruto.current_targets.append(chrome)
    naruto.used_ability.execute(naruto, eteam, pteam)

    chrome.check_profile_swaps()
    chrome.update_ability()

    assert chrome.source.current_abilities[0].name == "Trident Combat"
    assert chrome.source.current_abilities[1].name == "Illusory World Destruction"
    assert chrome.source.current_abilities[2].name == "Mental Annihilation"
    assert chrome.source.current_abilities[3].name == "Trident Deflection"
    assert chrome.source.profile_image == chrome.source.altprof1

def test_world_destruction(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]

    chrome.used_ability = world_destruction

    chrome.used_ability.execute(chrome, pteam, eteam)

    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    for enemy in eteam:
        assert enemy.source.hp == 75
        assert enemy.is_stunned()

def test_world_destruction_fail(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]

    chrome.used_ability = world_destruction

    chrome.used_ability.execute(chrome, pteam, eteam)

    naruto.used_ability = naruto.source.current_abilities[2]
    naruto.current_targets.append(chrome)
    naruto.used_ability.execute(naruto, pteam, eteam)


    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    for enemy in eteam:
        assert enemy.source.hp == 100
        assert not enemy.is_stunned()

def test_annihilation(chrome_test_scene: BattleScene):
    chrome = chrome_test_scene.player_display.team.character_managers[0]
    eteam = chrome_test_scene.enemy_display.team.character_managers
    pteam = chrome_test_scene.player_display.team.character_managers
    needed = chrome.source.main_abilities[0]
    breakdown = chrome.source.main_abilities[1]
    immolation = chrome.source.main_abilities[2]
    trident = chrome.source.alt_abilities[0]
    world_destruction = chrome.source.alt_abilities[1]
    annihilation = chrome.source.alt_abilities[2]
    naruto = eteam[1]
    
    naruto.current_targets.append(chrome)
    naruto.used_ability = naruto.source.main_abilities[2]

    chrome.used_ability = annihilation

    chrome.current_targets.append(naruto)

    chrome.used_ability.execute(chrome, pteam, eteam)

    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 65

    assert len(chrome.source.current_effects) == 0

    chrome.used_ability.execute(chrome, pteam, eteam)
    naruto.used_ability.execute(naruto, pteam, eteam)

    assert chrome.source.hp == 100
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()
    chrome_test_scene.tick_effect_duration()

    assert naruto.source.hp == 65

def test_relentless_assault(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    naruto = eteam[1]
    chrome = eteam[0]
    chu2 = eteam[2]

    chu.current_targets.append(naruto)
    chu.used_ability = assault

    assault.execute(chu, pteam, eteam)

    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()
    

    assert naruto.source.hp == 55

def test_relentless_assault_pierce(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    naruto = eteam[1]

    chu.current_targets.append(naruto)
    chu.used_ability = assault

    naruto.add_effect(Effect(Ability("naruto1"), EffectType.ALL_DR, naruto, 10, lambda eff: "", mag=10))

    assault.execute(chu, pteam, eteam)

    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()

    assert naruto.source.hp == 55

def test_relentless_assault_nonpierce(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    naruto = eteam[1]

    chu.current_targets.append(naruto)
    chu.used_ability = assault

    naruto.add_effect(Effect(Ability("naruto1"), EffectType.ALL_DR, naruto, 10, lambda eff: "", mag=15))

    assault.execute(chu, pteam, eteam)

    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()
    chu_test_scene.resolve_ticking_ability()

    assert naruto.source.hp == 100

def test_deflect_negation(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    naruto = eteam[1]

    chu.used_ability = deflect
    deflect.execute(chu, pteam, eteam)

    naruto.used_ability = naruto.source.alt_abilities[1]
    naruto.current_targets.append(chu)

    naruto.used_ability.execute(naruto, eteam, pteam)
    naruto.used_ability.execute(naruto, eteam, pteam)

    assert chu.source.hp == 100
    assert chu.is_stunned() == False
    assert naruto.has_effect(EffectType.MARK, "Uzumaki Barrage")

def test_deflect_negation_failure(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    naruto = eteam[1]

    chu.used_ability = deflect
    deflect.execute(chu, pteam, eteam)

    naruto.used_ability = naruto.source.main_abilities[1]
    naruto.current_targets.append(chu)

    naruto.used_ability.execute(naruto, eteam, pteam)

    assert chu.source.hp == 90
    assert chu.is_stunned() == True

def test_gae_bolg_defense_shatter(chu_test_scene: BattleScene):
    chu = chu_test_scene.player_display.team.character_managers[0]
    eteam = chu_test_scene.enemy_display.team.character_managers
    pteam = chu_test_scene.player_display.team.character_managers
    assault = chu.source.current_abilities[0]
    deflect = chu.source.current_abilities[1]
    gae_bolg = chu.source.current_abilities[2]
    block = chu.source.current_abilities[3]
    chrome = eteam[0]
    chrome.used_ability = chrome.source.main_abilities[1]
    chrome.current_targets.append(chu)

    chu.used_ability = gae_bolg
    chu.current_targets.append(chrome)

    chrome.used_ability.execute(chrome, eteam, pteam)

    assert chrome.has_effect(EffectType.DEST_DEF, "Illusory Breakdown")

    chu.used_ability.execute(chu, pteam, eteam)

    assert chrome.source.hp == 60
    assert len(chu.source.current_effects) == 0

def test_illusory_disorientation_effect(cranberry_test_scene: BattleScene):
    cranberry = cranberry_test_scene.player_display.team.character_managers[0]
    eteam = cranberry_test_scene.enemy_display.team.character_managers
    pteam = cranberry_test_scene.player_display.team.character_managers
    disorient = cranberry.source.main_abilities[0]
    fortissimo = cranberry.source.main_abilities[1]
    radar = cranberry.source.main_abilities[2]
    finish = cranberry.source.alt_abilities[0]
    astolfo = eteam[0]
    cranberry.current_targets.append(astolfo)
    cranberry.used_ability = disorient
    disorient.execute(cranberry, pteam, eteam)

    astolfo.adjust_ability_costs()

    assert astolfo.source.current_abilities[0].total_cost == 2

    astolfo.current_targets.append(astolfo)
    astolfo.used_ability = astolfo.source.current_abilities[0]
    astolfo.used_ability.execute(astolfo, eteam, pteam)

    astolfo.adjust_ability_costs()

    assert astolfo.source.current_abilities[0].total_cost == 1

def test_illusory_disorientation_swap(cranberry_test_scene: BattleScene):
    cranberry = cranberry_test_scene.player_display.team.character_managers[0]
    eteam = cranberry_test_scene.enemy_display.team.character_managers
    pteam = cranberry_test_scene.player_display.team.character_managers
    disorient = cranberry.source.main_abilities[0]
    fortissimo = cranberry.source.main_abilities[1]
    radar = cranberry.source.main_abilities[2]
    finish = cranberry.source.alt_abilities[0]
    astolfo = eteam[0]
    cranberry.current_targets.append(astolfo)
    cranberry.used_ability = disorient
    disorient.execute(cranberry, pteam, eteam)

    cranberry.update_ability()

    assert cranberry.source.current_abilities[0].name == "Merciless Finish"

def test_merciless_finish_targeting(cranberry_test_scene: BattleScene):
    cranberry = cranberry_test_scene.player_display.team.character_managers[0]
    eteam = cranberry_test_scene.enemy_display.team.character_managers
    pteam = cranberry_test_scene.player_display.team.character_managers
    disorient = cranberry.source.main_abilities[0]
    fortissimo = cranberry.source.main_abilities[1]
    radar = cranberry.source.main_abilities[2]
    finish = cranberry.source.alt_abilities[0]
    astolfo = eteam[0]
    
    assert finish.target(cranberry, pteam, eteam, True) == 0

    cranberry.used_ability = disorient
    cranberry.current_targets.append(astolfo)
    cranberry.used_ability.execute(cranberry, pteam, eteam)

    assert finish.target(cranberry, pteam, eteam, True) == 1

def test_mental_radar(cranberry_test_scene: BattleScene):
    cranberry = cranberry_test_scene.player_display.team.character_managers[0]
    eteam = cranberry_test_scene.enemy_display.team.character_managers
    pteam = cranberry_test_scene.player_display.team.character_managers
    disorient = cranberry.source.main_abilities[0]
    fortissimo = cranberry.source.main_abilities[1]
    radar = cranberry.source.main_abilities[2]
    finish = cranberry.source.alt_abilities[0]
    astolfo = eteam[0]

    cranberry.used_ability = radar
    cranberry.current_targets.append(cranberry)
    cranberry.used_ability.execute(cranberry, pteam, eteam)
    cranberry.current_targets.clear()

    astolfo.used_ability = astolfo.source.main_abilities[0]
    astolfo.current_targets.append(astolfo)
    cranberry.current_targets.append(astolfo)
    cranberry.used_ability = fortissimo

    astolfo.used_ability.execute(astolfo, eteam, pteam)

    cranberry.used_ability.execute(cranberry, pteam, eteam)

    assert astolfo.source.hp == 75

def test_fortissimo_double(cranberry_test_scene: BattleScene):
    cranberry = cranberry_test_scene.player_display.team.character_managers[0]
    eteam = cranberry_test_scene.enemy_display.team.character_managers
    pteam = cranberry_test_scene.player_display.team.character_managers
    disorient = cranberry.source.main_abilities[0]
    fortissimo = cranberry.source.main_abilities[1]
    radar = cranberry.source.main_abilities[2]
    finish = cranberry.source.alt_abilities[0]
    astolfo = eteam[0]

    cranberry.used_ability = fortissimo
    cranberry.current_targets.append(astolfo)

    astolfo.used_ability = astolfo.source.main_abilities[3]
    astolfo.source.main_abilities[3].execute(astolfo, eteam, pteam)

    cranberry.used_ability.execute(cranberry, pteam, eteam)

    assert astolfo.source.hp == 50

def test_requip(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]
    erza.used_ability = clearheart
    clearheart.execute(erza, pteam, eteam)
    erza.check_ability_swaps()
    assert erza.source.current_abilities[0].name == "Titania's Rampage"
    
    erza.used_ability = heavenswheel
    erza.used_ability.execute(erza, pteam, eteam)
    erza.check_ability_swaps()
    assert erza.source.current_abilities[1].name == "Circle Blade"
    assert erza.source.current_abilities[0].name == "Clear Heart Clothing"

def test_clearheart_stun_immunity(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]
    erza.used_ability = clearheart
    erza.used_ability.execute(erza, pteam, eteam)

    naruto.used_ability = naruto.source.current_abilities[1]
    naruto.current_targets.append(erza)
    naruto.used_ability.execute(naruto, eteam, pteam)

    assert not erza.is_stunned()

def test_rampage(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]

    erza.used_ability = rampage
    erza.used_ability.execute(erza, pteam, eteam)

    erza_test_scene.resolve_ticking_ability()
    erza_test_scene.resolve_ticking_ability()
    erza_test_scene.resolve_ticking_ability()

    total_damage = 0
    for enemy in eteam:
        total_damage = total_damage + (100 - enemy.source.hp)

    assert total_damage == 60
    
def test_circle_blade(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]

    erza.used_ability = circleblade
    erza.current_targets.append(astolfo)
    erza.used_ability.execute(erza, pteam, eteam)

    assert astolfo.source.hp == 80

    erza_test_scene.resolve_ticking_ability()
    erza_test_scene.resolve_ticking_ability()

    assert astolfo.source.hp == 65
    assert naruto.source.hp == 85

def test_nakagamis_starlight(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]

    erza.used_ability = starlight
    erza.current_targets.append(naruto)
    erza.used_ability.execute(erza, pteam, eteam)

    assert naruto.source.hp == 65
    assert naruto.source.energy_contribution == 0

def test_adamantine_barrier(erza_test_scene: BattleScene):
    erza = erza_test_scene.player_display.team.character_managers[0]
    eteam = erza_test_scene.enemy_display.team.character_managers
    pteam = erza_test_scene.player_display.team.character_managers
    clearheart = erza.source.main_abilities[0]
    heavenswheel = erza.source.main_abilities[1]
    nakagami = erza.source.main_abilities[2]
    adamantine = erza.source.main_abilities[3]
    rampage = erza.source.alt_abilities[0]
    circleblade = erza.source.alt_abilities[1]
    starlight = erza.source.alt_abilities[2]
    barrier = erza.source.alt_abilities[3]
    astolfo = eteam[0]
    naruto = eteam[1]

    erza.used_ability = barrier
    erza.current_targets.append(pteam[1])
    erza.current_targets.append(pteam[2])

    erza.used_ability.execute(erza, pteam, eteam)

    assert pteam[1].check_invuln()
    assert pteam[2].check_invuln()

def test_demons_extract(esdeath_test_scene: BattleScene):
    esdeath = esdeath_test_scene.player_display.team.character_managers[0]
    eteam = esdeath_test_scene.enemy_display.team.character_managers
    pteam = esdeath_test_scene.player_display.team.character_managers
    extract = esdeath.source.main_abilities[0]
    castle = esdeath.source.main_abilities[1]
    schnabel = esdeath.source.main_abilities[2]
    mahapadma = esdeath.source.alt_abilities[0]
    astolfo = eteam[0]
    naruto = eteam[1]

    assert schnabel.target(esdeath, pteam, eteam, True) == 0

    esdeath.used_ability = extract
    extract.execute(esdeath, pteam, eteam)

    assert schnabel.target(esdeath, pteam, eteam, True) == 3
    esdeath.check_ability_swaps()
    assert esdeath.source.current_abilities[0].name == "Mahapadma"

def test_frozen_castle(esdeath_test_scene: BattleScene):
    esdeath = esdeath_test_scene.player_display.team.character_managers[0]
    eteam = esdeath_test_scene.enemy_display.team.character_managers
    pteam = esdeath_test_scene.player_display.team.character_managers
    extract = esdeath.source.main_abilities[0]
    castle = esdeath.source.main_abilities[1]
    schnabel = esdeath.source.main_abilities[2]
    mahapadma = esdeath.source.alt_abilities[0]
    astolfo = eteam[0]
    naruto = eteam[1]

    for e in eteam:
        esdeath.current_targets.append(e)
    
    esdeath.used_ability = castle
    esdeath.used_ability.execute(esdeath, pteam, eteam)

    for e in eteam:
        assert len(e.source.current_effects) == 1

    assert not esdeath.has_effect(EffectType.MARK, "Frozen Castle")
    assert esdeath.has_effect(EffectType.UNIQUE, "Frozen Castle")

    naruto.used_ability = naruto.source.current_abilities[1]
    assert naruto.used_ability.target(naruto, eteam, pteam, True) == 1

def test_weiss_schnabel_reuse(esdeath_test_scene: BattleScene):
    esdeath = esdeath_test_scene.player_display.team.character_managers[0]
    eteam = esdeath_test_scene.enemy_display.team.character_managers
    pteam = esdeath_test_scene.player_display.team.character_managers
    extract = esdeath.source.main_abilities[0]
    castle = esdeath.source.main_abilities[1]
    schnabel = esdeath.source.main_abilities[2]
    mahapadma = esdeath.source.alt_abilities[0]
    astolfo = eteam[0]
    naruto = eteam[1]
    esdeath.used_ability = schnabel
    esdeath.current_targets.append(astolfo)

    esdeath.used_ability.execute(esdeath, pteam, eteam)

    assert astolfo.source.hp == 90

    esdeath_test_scene.resolve_ticking_ability()
    esdeath_test_scene.resolve_ticking_ability()

    esdeath.adjust_ability_costs()

    assert esdeath.used_ability.total_cost == 1

    esdeath.used_ability.execute(esdeath, pteam, eteam)

    assert astolfo.source.hp == 65

def test_frozen_castle_schnabel(esdeath_test_scene: BattleScene):
    esdeath = esdeath_test_scene.player_display.team.character_managers[0]
    eteam = esdeath_test_scene.enemy_display.team.character_managers
    pteam = esdeath_test_scene.player_display.team.character_managers
    extract = esdeath.source.main_abilities[0]
    castle = esdeath.source.main_abilities[1]
    schnabel = esdeath.source.main_abilities[2]
    mahapadma = esdeath.source.alt_abilities[0]
    astolfo = eteam[0]
    naruto = eteam[1]

    for e in eteam:
        esdeath.current_targets.append(e)
    
    esdeath.used_ability = castle
    esdeath.used_ability.execute(esdeath, pteam, eteam)

    esdeath.used_ability = schnabel
    esdeath.used_ability.execute(esdeath, pteam, eteam)

    esdeath_test_scene.resolve_ticking_ability()

    esdeath.used_ability.execute(esdeath, pteam, eteam)

    esdeath_test_scene.resolve_ticking_ability()

    esdeath.used_ability.execute(esdeath, pteam, eteam)

    esdeath_test_scene.resolve_ticking_ability()
    
    for e in eteam:
        assert e.source.hp == 40

def test_close_combat_bombs(frenda_test_scene: BattleScene):
    frenda = frenda_test_scene.player_display.team.character_managers[0]
    eteam = frenda_test_scene.enemy_display.team.character_managers
    pteam = frenda_test_scene.player_display.team.character_managers
    bombs = frenda.source.current_abilities[0]
    dolltrap = frenda.source.current_abilities[1]
    detonate = frenda.source.current_abilities[2]
    astolfo = eteam[0]
    naruto = eteam[1]

    assert detonate.target(frenda, pteam, eteam, True) == 0

    frenda.used_ability = bombs
    frenda.current_targets.append(astolfo)

    frenda.used_ability.execute(frenda, pteam, eteam)

    assert detonate.target(frenda, pteam, eteam, True) == 1

    frenda.used_ability = detonate
    
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert astolfo.source.hp == 85

def test_doll_trap(frenda_test_scene: BattleScene):
    frenda = frenda_test_scene.player_display.team.character_managers[0]
    eteam = frenda_test_scene.enemy_display.team.character_managers
    pteam = frenda_test_scene.player_display.team.character_managers
    bombs = frenda.source.current_abilities[0]
    dolltrap = frenda.source.current_abilities[1]
    detonate = frenda.source.current_abilities[2]
    astolfo = eteam[0]
    naruto = eteam[1]

    frenda.current_targets.append(astolfo)
    frenda.used_ability = dolltrap
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert len(astolfo.source.current_effects) == 2

    frenda.used_ability = detonate
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert astolfo.source.hp == 20

def test_doll_trap_transfer(frenda_test_scene: BattleScene):
    frenda = frenda_test_scene.player_display.team.character_managers[0]
    eteam = frenda_test_scene.enemy_display.team.character_managers
    pteam = frenda_test_scene.player_display.team.character_managers
    bombs = frenda.source.current_abilities[0]
    dolltrap = frenda.source.current_abilities[1]
    detonate = frenda.source.current_abilities[2]
    astolfo = eteam[0]
    naruto = eteam[1]
    toga = pteam[1]
    frenda.current_targets.append(toga)
    frenda.used_ability = dolltrap
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert toga.get_effect(EffectType.STACK, "Doll Trap").mag == 4

    naruto.used_ability = naruto.source.main_abilities[2]
    naruto.current_targets.append(toga)
    naruto.used_ability.execute(naruto, eteam, pteam)

    assert len(toga.source.current_effects) == 0
    frenda.current_targets.clear()
    frenda.current_targets.append(naruto)
    frenda.used_ability = detonate
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert naruto.source.hp == 20

def test_multi_explosive_detonation(frenda_test_scene: BattleScene):
    frenda = frenda_test_scene.player_display.team.character_managers[0]
    eteam = frenda_test_scene.enemy_display.team.character_managers
    pteam = frenda_test_scene.player_display.team.character_managers
    bombs = frenda.source.current_abilities[0]
    dolltrap = frenda.source.current_abilities[1]
    detonate = frenda.source.current_abilities[2]
    astolfo = eteam[0]
    naruto = eteam[1]
    toga = pteam[1]
    frenda.current_targets.append(astolfo)
    frenda.used_ability = bombs
    frenda.used_ability.execute(frenda, pteam, eteam)
    frenda.used_ability = dolltrap
    frenda.used_ability.execute(frenda, pteam, eteam)
    
    frenda.current_targets.append(toga)
    frenda.used_ability.execute(frenda, pteam, eteam)

    frenda.used_ability = detonate
    frenda.used_ability.execute(frenda, pteam, eteam)

    assert astolfo.source.hp == 45

    assert toga.source.hp == 80

def test_shadow_swap(gajeel_test_scene: BattleScene):
    gajeel = gajeel_test_scene.enemy_display.team.character_managers[0]
    pteam = gajeel_test_scene.player_display.team.character_managers
    eteam = gajeel_test_scene.enemy_display.team.character_managers
    astolfo = eteam[0]
    naruto = eteam[1]
    shadowdragon = gajeel.source.main_abilities[2]
    blacksteel = gajeel.source.alt_abilities[2]
    gajeel.used_ability = shadowdragon
    gajeel.used_ability.execute(gajeel, pteam, eteam)

    gajeel.check_ability_swaps()

    assert gajeel.source.current_abilities[0].name == "Iron Shadow Dragon's Roar"

def test_shadow_ignore(gajeel_test_scene: BattleScene):
    pteam = gajeel_test_scene.player_display.team.character_managers
    eteam = gajeel_test_scene.enemy_display.team.character_managers
    gajeel = eteam[0]
    naruto = pteam[0]
    shadowdragon = gajeel.source.main_abilities[2]
    blacksteel = gajeel.source.alt_abilities[2]
    gajeel.used_ability = shadowdragon
    gajeel.used_ability.execute(gajeel, pteam, eteam)

    naruto.used_ability = naruto.source.current_abilities[2]
    naruto.current_targets.append(gajeel)
    naruto.used_ability.execute(naruto, eteam, pteam)
    naruto.used_ability.execute(naruto, eteam, pteam)
    naruto.used_ability.execute(naruto, eteam, pteam)

    assert gajeel.source.hp == 70

def test_sistema_cai_stages(gokudera_test_scene: BattleScene):
    pteam = gokudera_test_scene.player_display.team.character_managers
    eteam = gokudera_test_scene.enemy_display.team.character_managers
    gokudera = pteam[0]
    gajeel = eteam[0]
    sistema = gokudera.source.main_abilities[0]
    skullring = gokudera.source.main_abilities[1]
    skullbow = gokudera.source.main_abilities[2]
    
    gokudera.add_effect(Effect(Ability("gokudera1"), EffectType.STACK, gokudera, 280000, lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.", mag=1))

    gokudera.used_ability = sistema
    gokudera.current_targets.append(eteam[0])
    gokudera.current_targets.append(eteam[1])
    gokudera.current_targets.append(eteam[2])
    gokudera.used_ability.execute(gokudera, pteam, eteam)

    assert eteam[0].source.hp == 90
    assert gokudera.get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 2

    gokudera.primary_target = eteam[1]

    gokudera.used_ability.execute(gokudera, pteam, eteam)

    assert eteam[0].source.hp == 80
    assert eteam[1].source.hp == 80
    assert eteam[1].is_stunned()

    gokudera.source.hp = 65

    gokudera.used_ability.execute(gokudera, pteam, eteam)
    assert eteam[0].source.hp == 70
    assert eteam[1].source.hp == 60
    assert eteam[1].is_stunned()
    assert gokudera.source.hp == 80

    gokudera.current_targets.append(pteam[0])
    gokudera.current_targets.append(pteam[1])
    gokudera.current_targets.append(pteam[2])

    gokudera.used_ability.execute(gokudera, pteam, eteam)

    assert eteam[0].source.hp == 45
    assert eteam[1].source.hp == 35
    assert eteam[0].is_stunned()
    assert gokudera.source.hp == 100

def test_vongola_bow_stage_halt(gokudera_test_scene: BattleScene):
    pteam = gokudera_test_scene.player_display.team.character_managers
    eteam = gokudera_test_scene.enemy_display.team.character_managers
    gokudera = pteam[0]
    gajeel = eteam[0]
    sistema = gokudera.source.main_abilities[0]
    skullring = gokudera.source.main_abilities[1]
    skullbow = gokudera.source.main_abilities[2]
    
    gokudera.add_effect(Effect(Ability("gokudera1"), EffectType.STACK, gokudera, 280000, lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.", mag=1))

    gokudera.used_ability = skullbow
    gokudera.current_targets.append(gokudera)
    gokudera.used_ability.execute(gokudera, pteam, eteam)

    gokudera.used_ability = sistema
    gokudera.current_targets.clear()
    gokudera.current_targets.append(eteam[0])
    gokudera.current_targets.append(eteam[1])
    gokudera.current_targets.append(eteam[2])

    gokudera.used_ability.execute(gokudera, pteam, eteam)
    gokudera.used_ability.execute(gokudera, pteam, eteam)
    gokudera.used_ability.execute(gokudera, pteam, eteam)
    gokudera.used_ability.execute(gokudera, pteam, eteam)
    
    assert eteam[0].source.hp == 60
    assert gokudera.get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 1
    
def test_skull_ring(gokudera_test_scene: BattleScene):
    pteam = gokudera_test_scene.player_display.team.character_managers
    eteam = gokudera_test_scene.enemy_display.team.character_managers
    gokudera = pteam[0]
    gajeel = eteam[0]
    sistema = gokudera.source.main_abilities[0]
    skullring = gokudera.source.main_abilities[1]
    skullbow = gokudera.source.main_abilities[2]
    
    gokudera.add_effect(Effect(Ability("gokudera1"), EffectType.STACK, gokudera, 280000, lambda eff: f"The Sistema C.A.I. is at Stage {eff.mag}.", mag=1))

    gokudera.used_ability = skullring
    gokudera.current_targets.append(gokudera)
    gokudera.used_ability.execute(gokudera, pteam, eteam)
    gokudera.used_ability.execute(gokudera, pteam, eteam)
    
    assert gokudera.get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 3

def test_alaudis_handcuffs(hibari_test_scene: BattleScene):
    pteam = hibari_test_scene.player_display.team.character_managers
    eteam = hibari_test_scene.enemy_display.team.character_managers
    hibari = pteam[0]
    bite = hibari.source.main_abilities[0]
    handcuffs = hibari.source.main_abilities[1]
    porcospino = hibari.source.main_abilities[2]
    gajeel = eteam[0]
    hibari.current_targets.append(gajeel)
    hibari.used_ability = handcuffs
    hibari.used_ability.execute(hibari, pteam, eteam)

    assert gajeel.source.hp == 85

    assert porcospino.target(hibari, pteam, eteam, True) == 0

def test_porcospino(hibari_test_scene: BattleScene):
    pteam = hibari_test_scene.player_display.team.character_managers
    eteam = hibari_test_scene.enemy_display.team.character_managers
    hibari = pteam[0]
    bite = hibari.source.main_abilities[0]
    handcuffs = hibari.source.main_abilities[1]
    porcospino = hibari.source.main_abilities[2]
    gajeel = eteam[0]

    for enemy in eteam:
        hibari.current_targets.append(enemy)

    hibari.used_ability = porcospino
    hibari.used_ability.execute(hibari, pteam, eteam)

    assert handcuffs.target(hibari, pteam, eteam) == 0

    gajeel.used_ability = gajeel.source.current_abilities[0]

    gajeel.current_targets.append(hibari)

    gajeel.used_ability.execute(gajeel, pteam, eteam)

    assert hibari.source.hp == 65
    assert gajeel.source.hp == 90

def test_ice_make_targeting(gray_test_scene: BattleScene):
    pteam = gray_test_scene.player_display.team.character_managers
    eteam = gray_test_scene.enemy_display.team.character_managers
    gray = pteam[0]
    icemake = gray.source.main_abilities[0]
    freezelancer = gray.source.main_abilities[1]
    hammer = gray.source.main_abilities[2]
    unlimited = gray.source.alt_abilities[0]

    assert freezelancer.target(gray, pteam, eteam, True) == 0
    assert hammer.target(gray, pteam, eteam, True) == 0
    assert unlimited.target(gray, pteam, eteam, True) == 0

def test_unlimited(gray_test_scene: BattleScene):
    pteam = gray_test_scene.player_display.team.character_managers
    eteam = gray_test_scene.enemy_display.team.character_managers
    gray = pteam[0]
    icemake = gray.source.main_abilities[0]
    freezelancer = gray.source.main_abilities[1]
    hammer = gray.source.main_abilities[2]
    unlimited = gray.source.alt_abilities[0]

    for player in pteam:
        gray.current_targets.append(player)
    for enemy in eteam:
        gray.current_targets.append(enemy)

    gray.used_ability = unlimited
    gray.used_ability.execute(gray, pteam, eteam)

    gray_test_scene.resolve_ticking_ability()
    gray_test_scene.resolve_ticking_ability()
    gray_test_scene.resolve_ticking_ability()
    gray_test_scene.resolve_ticking_ability()
    gray_test_scene.resolve_ticking_ability()
    gray_test_scene.resolve_ticking_ability()



    for enemy in eteam:
        assert enemy.source.hp == 70
    
    assert gray.get_effect(EffectType.DEST_DEF, "Ice, Make Unlimited").mag == 30

def test_guts(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    assert superawesome.target(gunha, pteam, eteam, True) == 0
    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)

    assert superawesome.target(gunha, pteam, eteam, True) == 3
    assert gunha.has_effect(EffectType.MARK, "Guts")
    assert gunha.get_effect(EffectType.STACK, "Guts").mag == 5

    gunha.source.hp = 75

    gunha.used_ability.execute(gunha, pteam, eteam)
    assert gunha.get_effect(EffectType.STACK, "Guts").mag == 7
    assert gunha.source.hp == 100

def test_super_awesome_full_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = superawesome
    gunha.used_ability.execute(gunha, pteam, eteam)

    assert gajeel.source.hp == 55
    assert gajeel.is_stunned()

def test_super_awesome_mid_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)
    gunha.get_effect(EffectType.STACK, "Guts").alter_mag(-3)

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = superawesome
    gunha.used_ability.execute(gunha, pteam, eteam)

    assert gajeel.source.hp == 55
    assert not gajeel.is_stunned()

def test_super_awesome_no_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)
    gunha.get_effect(EffectType.STACK, "Guts").alter_mag(-5)

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = superawesome
    gunha.used_ability.execute(gunha, pteam, eteam)

    assert gajeel.source.hp == 65

def test_overwhelming_suppression_full_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)
    

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = suppression
    gunha.used_ability.execute(gunha, pteam, eteam)

    gajeel.used_ability = gajeel.source.main_abilities[3]
    gajeel.used_ability.execute(gajeel, pteam, eteam)

    assert not gajeel.check_invuln()
    assert gajeel.get_boosts(0) == -10

def test_overwhelming_suppression_mid_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)
    gunha.get_effect(EffectType.STACK, "Guts").alter_mag(-3)

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = suppression
    gunha.used_ability.execute(gunha, pteam, eteam)

    gajeel.used_ability = gajeel.source.main_abilities[3]
    gajeel.used_ability.execute(gajeel, pteam, eteam)

    assert gajeel.check_invuln()

    assert gajeel.get_boosts(0) == -10

def test_overwhelming_suppression_no_charge(gunha_test_scene:BattleScene):
    pteam = gunha_test_scene.player_display.team.character_managers
    eteam = gunha_test_scene.enemy_display.team.character_managers
    gunha = pteam[0]
    gajeel = eteam[0]

    guts = gunha.source.main_abilities[3]
    superawesome = gunha.source.main_abilities[0]
    suppression = gunha.source.main_abilities[1]
    hypereccentric = gunha.source.main_abilities[2]

    gunha.used_ability = guts
    gunha.current_targets.append(gunha)

    gunha.used_ability.execute(gunha, pteam, eteam)
    gunha.get_effect(EffectType.STACK, "Guts").alter_mag(-5)

    gunha.current_targets.clear()
    gunha.current_targets.append(gajeel)
    gunha.used_ability = suppression
    gunha.used_ability.execute(gunha, pteam, eteam)

    gajeel.used_ability = gajeel.source.main_abilities[3]
    gajeel.used_ability.execute(gajeel, pteam, eteam)

    assert gajeel.check_invuln()

    assert gajeel.get_boosts(0) == -5

def test_twin_lion_fist(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    lionfist = hinata.source.main_abilities[0]

    hinata.used_ability = lionfist
    hinata.current_targets.append(eteam[0])
    hinata.used_ability.execute(hinata, pteam, eteam)

    assert eteam[0].source.hp == 50

def test_twin_lion_fist_with_boost(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    lionfist = hinata.source.main_abilities[0]

    hinata.used_ability = lionfist
    hinata.current_targets.append(eteam[0])

    hinata.add_effect(Effect(hinata.used_ability, EffectType.ALL_BOOST, hinata, 2, lambda eff: "", mag=10))

    hinata.used_ability.execute(hinata, pteam, eteam)

    assert eteam[0].source.hp == 30

def test_twin_lion_fist_with_counter(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    lionfist = hinata.source.main_abilities[0]

    hinata.used_ability = lionfist
    hinata.current_targets.append(eteam[0])

    eteam[0].used_ability = eteam[0].source.main_abilities[0]
    eteam[0].current_targets.append(eteam[0])
    eteam[0].used_ability.execute(eteam[0], eteam, pteam)

    assert eteam[0].has_effect(EffectType.COUNTER, "Casseur de Logistille")

    hinata.used_ability.execute(hinata, pteam, eteam)

    assert eteam[0].source.hp == 75
    assert hinata.is_stunned()

def test_trigrams_dr(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    trigrams = hinata.source.main_abilities[1]

    hinata.used_ability = trigrams
    hinata.current_targets.append(pteam[0])
    hinata.current_targets.append(pteam[1])
    hinata.current_targets.append(pteam[2])

    hinata.used_ability.execute(hinata, pteam, eteam)

    assert pteam[2].check_for_dmg_reduction() == 10

def test_trigrams_dmg(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    trigrams = hinata.source.main_abilities[1]

    hinata.used_ability = trigrams
    hinata.current_targets.append(pteam[0])
    hinata.current_targets.append(pteam[1])
    hinata.current_targets.append(pteam[2])

    hinata.used_ability.execute(hinata, pteam, eteam)

    hinata.current_targets.clear()

    hinata.used_ability.target(hinata, pteam, eteam)
    hinata_test_scene.acting_character = hinata
    hinata_test_scene.selected_ability = hinata.used_ability
    hinata_test_scene.apply_targeting(eteam[0])
    

    hinata.used_ability.execute(hinata, pteam, eteam)

    assert eteam[1].source.hp == 85

def test_lionfist_byakugan_drain(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    lionfist = hinata.source.main_abilities[0]
    byakugan = hinata.source.main_abilities[2]

    ally_use_ability(hinata_test_scene, hinata, hinata, byakugan)

    assert hinata.has_effect(EffectType.MARK, "Byakugan")
    
    ally_use_ability(hinata_test_scene, hinata, eteam[0], lionfist)

    assert eteam[0].source.hp == 50
    assert eteam[0].source.energy_contribution == -1

def test_trigrams_byakugan_drain(hinata_test_scene:BattleScene):
    pteam = hinata_test_scene.player_display.team.character_managers
    eteam = hinata_test_scene.enemy_display.team.character_managers
    hinata = pteam[0]
    lionfist = hinata.source.main_abilities[0]
    trigrams = hinata.source.main_abilities[1]
    byakugan = hinata.source.main_abilities[2]

    ally_use_ability(hinata_test_scene, hinata, hinata, byakugan)

    ally_use_ability(hinata_test_scene, hinata, hinata, trigrams)        
    ally_use_ability(hinata_test_scene, hinata, eteam[0], trigrams)

    assert eteam[0].source.hp == 85
    assert eteam[0].source.energy_contribution == 0
    assert eteam[1].source.energy_contribution == 1

def test_tensa_zangetsu(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]

    bankai = ichigo.source.main_abilities[1]

    ally_use_ability(ichigo_test_scene, ichigo, ichigo, bankai)

    enemy_use_ability(ichigo_test_scene, cmary, pteam[1], cmary.source.main_abilities[2])

    assert ichigo.source.hp == 100
    assert pteam[1].source.hp == 80

def test_tensa_zangetsu_getsuga_tenshou(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]

    bankai = ichigo.source.main_abilities[1]
    getsuga = ichigo.source.main_abilities[0]

    ally_use_ability(ichigo_test_scene, ichigo, ichigo, bankai)

    enemy_use_ability(ichigo_test_scene, cmary, cmary, cmary.source.main_abilities[3])

    ally_use_ability(ichigo_test_scene, ichigo, cmary, getsuga)

    assert cmary.source.hp == 60

def test_enemy_use_ability_on_invuln(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]

    bankai = ichigo.source.main_abilities[1]
    getsuga = ichigo.source.main_abilities[0]

    enemy_use_ability(ichigo_test_scene, cmary, cmary, cmary.source.main_abilities[3])

    ally_use_ability(ichigo_test_scene, ichigo, cmary, getsuga)

    assert cmary.source.hp == 100

def test_zangetsu_strike(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]

    zangetsu = ichigo.source.main_abilities[2]

    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)

    assert cmary.source.hp == 80

    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)

    assert cmary.source.hp == 55

    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)

    assert cmary.source.hp == 25

def test_tensa_zangetsu_strike(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]

    zangetsu = ichigo.source.main_abilities[2]
    bankai = ichigo.source.main_abilities[1]

    ally_use_ability(ichigo_test_scene, ichigo, ichigo, bankai)

    ichigo.adjust_targeting_types()

    assert zangetsu.target_type == Target.MULTI_ENEMY

    ally_use_ability(ichigo_test_scene, ichigo, eteam[1], zangetsu)


    assert cmary.source.hp == 80
    assert eteam[1].source.hp == 80
    assert eteam[0].source.hp == 80
    assert ichigo.get_effect(EffectType.STACK, "Zangetsu Strike").mag == 3

def test_tensa_zangetsu_strike_boost_cancel(ichigo_test_scene:BattleScene):
    pteam = ichigo_test_scene.player_display.team.character_managers
    eteam = ichigo_test_scene.enemy_display.team.character_managers
    ichigo = pteam[0]
    cmary = eteam[2]
    astolfo = eteam[0]
    trap = eteam[0].source.main_abilities[1]

    zangetsu = ichigo.source.main_abilities[2]
    
    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)
    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)
    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)



    assert cmary.source.hp == 25
    assert ichigo.get_effect(EffectType.STACK, "Zangetsu Strike").mag == 3

    enemy_use_ability(ichigo_test_scene, astolfo, ichigo, trap)

    ally_use_ability(ichigo_test_scene, ichigo, cmary, zangetsu)

    assert cmary.source.hp == 5

def test_butou_renjin(ichimaru_test_scene:BattleScene):
    pteam = ichimaru_test_scene.player_display.team.character_managers
    eteam = ichimaru_test_scene.enemy_display.team.character_managers
    ichimaru = pteam[0]
    butou = ichimaru.source.main_abilities[0]
    cmary = eteam[2]

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, butou)

    assert cmary.has_effect(EffectType.CONT_UNIQUE, "Butou Renjin")

    tick_one_turn(ichimaru_test_scene)
    tick_one_turn(ichimaru_test_scene)
    


    assert cmary.source.hp == 70
    assert cmary.get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 2
    
def test_butou_renjin_into_kill(ichimaru_test_scene:BattleScene):
    pteam = ichimaru_test_scene.player_display.team.character_managers
    eteam = ichimaru_test_scene.enemy_display.team.character_managers
    ichimaru = pteam[0]
    butou = ichimaru.source.main_abilities[0]
    kill = ichimaru.source.main_abilities[2]
    cmary = eteam[2]

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, butou)

    assert cmary.has_effect(EffectType.CONT_UNIQUE, "Butou Renjin")

    tick_one_turn(ichimaru_test_scene)
    


    assert cmary.source.hp == 70
    assert cmary.get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 2

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, kill)

    assert cmary.source.hp == 50

    assert not cmary.has_effect(EffectType.STACK, "Kill, Kamishini no Yari")

    tick_one_turn(ichimaru_test_scene)

    assert cmary.source.hp == 30

def test_13_kilometer(ichimaru_test_scene:BattleScene):
    pteam = ichimaru_test_scene.player_display.team.character_managers
    eteam = ichimaru_test_scene.enemy_display.team.character_managers
    ichimaru = pteam[0]
    swing = ichimaru.source.main_abilities[1]
    cmary = eteam[2]

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, swing)

    for enemy in eteam:
        assert enemy.source.hp == 75
        assert enemy.has_effect(EffectType.STACK, "Kill, Kamishini no Yari")

def test_13_kilometer_into_kill(ichimaru_test_scene:BattleScene):
    pteam = ichimaru_test_scene.player_display.team.character_managers
    eteam = ichimaru_test_scene.enemy_display.team.character_managers
    ichimaru = pteam[0]
    swing = ichimaru.source.main_abilities[1]
    kill = ichimaru.source.main_abilities[2]
    cmary = eteam[2]

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, swing)

    for enemy in eteam:
        assert enemy.source.hp == 75
        assert enemy.get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 1

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, kill)
    for enemy in eteam:
        assert enemy.source.hp == 65

    tick_one_turn(ichimaru_test_scene)

    for enemy in eteam:
        assert enemy.source.hp == 55

def test_repeated_kill(ichimaru_test_scene:BattleScene):
    pteam = ichimaru_test_scene.player_display.team.character_managers
    eteam = ichimaru_test_scene.enemy_display.team.character_managers
    ichimaru = pteam[0]
    swing = ichimaru.source.main_abilities[1]
    kill = ichimaru.source.main_abilities[2]
    cmary = eteam[2]

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, swing)

    for enemy in eteam:
        assert enemy.source.hp == 75
        assert enemy.get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 1

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, kill)
    for enemy in eteam:
        assert enemy.source.hp == 65

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, swing)

    for enemy in eteam:
        assert enemy.source.hp == 30

    ally_use_ability(ichimaru_test_scene, ichimaru, cmary, kill)

    for enemy in eteam:
        assert enemy.source.hp == 10
        enemy.source.hp = 40
    
    tick_one_turn(ichimaru_test_scene)

    for enemy in eteam:
        assert enemy.source.hp == 20

def test_fog_of_london(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]

    ally_use_ability(jack_test_scene, jack, eteam[0], fog)

    for enemy in eteam:
        assert enemy.source.hp == 95
        assert enemy.has_effect(EffectType.CONT_AFF_DMG, "Fog of London")
    
def test_maria_lockout(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]
    
    

    assert maria.target(jack, pteam, eteam, True) == 0

def test_maria_with_fog(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]

    ally_use_ability(jack_test_scene, jack, eteam[0], fog)

    assert maria.target(jack, pteam, eteam, True) == 3

    ally_use_ability(jack_test_scene, jack, eteam[0], maria)

    assert eteam[0].source.hp == 65

def test_maria_with_boost(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]

    jack.add_effect(Effect(fog, EffectType.ALL_BOOST, jack, 10, lambda eff: "", mag=10))

    ally_use_ability(jack_test_scene, jack, eteam[0], fog)

    assert maria.target(jack, pteam, eteam, True) == 3

    ally_use_ability(jack_test_scene, jack, eteam[0], maria)

    assert eteam[0].source.hp == 55

def test_streets_of_the_lost_isolation(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]

    ally_use_ability(jack_test_scene, jack, eteam[0], fog)

    assert streets.target(jack, pteam, eteam, True) == 3

    ally_use_ability(jack_test_scene, jack, eteam[1], streets)

    assert eteam[1].check_isolated()

    assert eteam[0].source.main_abilities[0].target(eteam[0], eteam, pteam, True) == 2

def test_streets_of_the_lost_we_are_jack_targeting(jack_test_scene: BattleScene):
    pteam = jack_test_scene.player_display.team.character_managers
    eteam = jack_test_scene.enemy_display.team.character_managers
    jack = pteam[0]
    fog = jack.source.main_abilities[1]
    maria = jack.source.main_abilities[0]
    we_are_jack = jack.source.main_abilities[2]
    streets = jack.source.alt_abilities[0]

    ally_use_ability(jack_test_scene, jack, eteam[0], fog)

    assert we_are_jack.target(jack, pteam, eteam, True) == 0

    ally_use_ability(jack_test_scene, jack, eteam[1], streets)

    assert we_are_jack.target(jack, pteam, eteam, True) == 1

def test_amaterasu(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, eteam[0], amaterasu)

    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)

    assert eteam[0].source.hp == 70

    assert amaterasu.target(itachi, pteam, eteam, True) == 2

def test_tsukuyomi(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, eteam[1], tsukuyomi)

    assert eteam[1].is_stunned()

    enemy_use_ability(itachi_test_scene, eteam[0], eteam[1], eteam[0].source.main_abilities[0])

    assert not eteam[1].is_stunned()
    assert not eteam[1].has_effect(EffectType.ALL_STUN, "Tsukuyomi")

def test_susanoo_switch(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, itachi, susanoo)

    itachi.check_ability_swaps()

    assert itachi.source.current_abilities[0].name == "Totsuka Blade"
    assert itachi.source.current_abilities[1].name == "Yata Mirror"

def test_susanoo_yata_DD(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, itachi, susanoo)

    itachi.check_ability_swaps()

    ally_use_ability(itachi_test_scene, itachi, itachi, yata)

    assert itachi.get_effect(EffectType.DEST_DEF, "Susano'o").mag == 65

def test_susanoo_DD_ending(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, itachi, susanoo)

    itachi.check_ability_swaps()

    hit = eteam[1].source.main_abilities[2]

    enemy_use_ability(itachi_test_scene, eteam[1], itachi, hit)
    enemy_use_ability(itachi_test_scene, eteam[1], itachi, hit)

    itachi.check_ability_swaps()

    assert not itachi.has_effect(EffectType.DEST_DEF, "Susano'o")

def test_susannoo_low_health_ending(itachi_test_scene: BattleScene):
    pteam = itachi_test_scene.player_display.team.character_managers
    eteam = itachi_test_scene.enemy_display.team.character_managers
    itachi = pteam[0]
    amaterasu = itachi.source.main_abilities[0]
    tsukuyomi = itachi.source.main_abilities[1]
    susanoo = itachi.source.main_abilities[2]
    totsuka = itachi.source.alt_abilities[0]
    yata = itachi.source.alt_abilities[1]

    ally_use_ability(itachi_test_scene, itachi, itachi, susanoo)

    itachi.check_ability_swaps()

    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)
    tick_one_turn(itachi_test_scene)

    assert not itachi.has_effect(EffectType.DEST_DEF, "Susano'o")

def test_counter_balance_drain_response(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability_with_response(jiro_test_scene, jiro, jiro, counterbalance)

    for ally in pteam:
        assert ally.has_effect(EffectType.MARK, "Counter-Balance")

    enemy_use_ability(jiro_test_scene, hinata, hinata, hinata.source.main_abilities[2])
    enemy_use_ability(jiro_test_scene, hinata, jiro, hinata.source.main_abilities[0])

    assert hinata.is_stunned()

def test_counter_balance_stun_response(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability_with_response(jiro_test_scene, jiro, jiro, counterbalance)

    for ally in pteam:
        assert ally.has_effect(EffectType.MARK, "Counter-Balance")

    ally_use_ability_with_response(jiro_test_scene, naruto, jiro, naruto.source.main_abilities[1])

    assert naruto.source.energy_contribution == 0

def test_distortion(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, distortion)

    for enemy in eteam:
        assert enemy.source.hp == 95

def test_surround_in_distortion(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, distortion)
    
    jiro.adjust_ability_costs()

    assert surround.total_cost == 1

    ally_use_ability(jiro_test_scene, jiro, hinata, surround)

    assert naruto.source.hp == 90
    assert eteam[2].source.hp == 90
    assert hinata.source.hp == 70

def test_surround(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, surround)

    jiro.adjust_ability_costs()

    assert distortion.total_cost == 1
    tick_one_turn(jiro_test_scene)
    assert hinata.source.hp == 80

def test_distortion_with_surround(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, surround)

    jiro.adjust_ability_costs()

    ally_use_ability(jiro_test_scene, jiro, hinata, distortion)

    assert eteam[1].source.hp == 85
    assert eteam[2].source.hp == 85
    assert hinata.source.hp == 65

def test_surround_self_lockout(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, surround)

    jiro.adjust_ability_costs()

    assert surround.target(jiro, pteam, eteam, True) == 0

def test_distortion_self_lockout(jiro_test_scene: BattleScene):
    pteam = jiro_test_scene.player_display.team.character_managers
    eteam = jiro_test_scene.enemy_display.team.character_managers
    jiro = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]

    counterbalance = jiro.source.main_abilities[0]
    distortion = jiro.source.main_abilities[1]
    surround = jiro.source.main_abilities[2]

    ally_use_ability(jiro_test_scene, jiro, hinata, distortion)

    assert distortion.target(jiro, pteam, eteam, True) == 0

def test_copy_ninja_single_target(kakashi_test_scene: BattleScene):
    pteam = kakashi_test_scene.player_display.team.character_managers
    eteam = kakashi_test_scene.enemy_display.team.character_managers
    kakashi = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]
    e_kakashi = eteam[2]
    copy = kakashi.source.main_abilities[0]
    nindogs = kakashi.source.main_abilities[1]
    raikiri = kakashi.source.main_abilities[2]

    enemy_use_ability(kakashi_test_scene, e_kakashi, e_kakashi, e_kakashi.source.main_abilities[0])

    ally_use_ability(kakashi_test_scene, kakashi, e_kakashi, raikiri)
    assert kakashi.source.hp == 60

def test_nin_dogs_raikiri(kakashi_test_scene: BattleScene):
    pteam = kakashi_test_scene.player_display.team.character_managers
    eteam = kakashi_test_scene.enemy_display.team.character_managers
    kakashi = pteam[0]
    hinata = eteam[0]
    naruto = eteam[1]
    e_kakashi = eteam[2]
    copy = kakashi.source.main_abilities[0]
    nindogs = kakashi.source.main_abilities[1]
    raikiri = kakashi.source.main_abilities[2]

    ally_use_ability(kakashi_test_scene, kakashi, hinata, nindogs)

    ally_use_ability(kakashi_test_scene, kakashi, hinata, raikiri)

    assert hinata.source.hp == 0

def test_teleporting_strike(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability_with_response(kuroko_test_scene, kuroko, eteam[0], teleport)

    assert eteam[0].source.hp == 90
    assert kuroko.check_invuln()

def test_teleport_pin(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], teleport)
    
    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], needle)

    assert eteam[0].source.hp == 75

def test_teleport_throw(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], teleport)

    ally_use_ability_with_response(kuroko_test_scene, kuroko, eteam[0], judgement_throw)
    assert eteam[0].source.hp == 60
    assert eteam[0].check_damage_drain() == -20
    
def test_judgement_throw(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability_with_response(kuroko_test_scene, kuroko, eteam[0], judgement_throw)
    assert eteam[0].source.hp == 85
    assert eteam[0].check_damage_drain() == -10

def test_teleport_after_judgement(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], judgement_throw)
    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], teleport)
    assert eteam[0].source.hp == 60

def test_pin_after_judgement(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], judgement_throw)
    ally_use_ability_with_response(kuroko_test_scene, kuroko, eteam[0], needle)

    assert eteam[0].is_stunned()

def test_needle_pin(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], needle)
    
    enemy_use_ability(kuroko_test_scene, eteam[0], eteam[0], eteam[0].source.main_abilities[3])

    assert not eteam[0].check_invuln()

def test_teleport_on_needle(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], needle)
    ally_use_ability_with_response(kuroko_test_scene, kuroko, eteam[0], teleport)

    assert teleport.cooldown_remaining == 0

def test_throw_on_needle(kuroko_test_scene: BattleScene):
    pteam = kuroko_test_scene.player_display.team.character_managers
    eteam = kuroko_test_scene.enemy_display.team.character_managers
    kuroko = pteam[0]
    
    judgement_throw = kuroko.source.main_abilities[0]
    teleport = kuroko.source.main_abilities[1]
    needle = kuroko.source.main_abilities[2]

    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], needle)
    ally_use_ability(kuroko_test_scene, kuroko, eteam[0], judgement_throw)

    assert eteam[0].source.energy_contribution == 0

def test_ten_year_teen(lambo_test_scene: BattleScene):
    pteam = lambo_test_scene.player_display.team.character_managers
    eteam = lambo_test_scene.enemy_display.team.character_managers
    lambo = pteam[0]
    hinata = eteam[0]

    bazooka = lambo.source.main_abilities[0]
    conductivity = lambo.source.main_abilities[1]
    gyudon = lambo.source.main_abilities[2]
    thunderset = lambo.source.alt_abilities[0]
    cornatta = lambo.source.alt_abilities[1]

    ally_use_ability(lambo_test_scene, lambo, lambo, bazooka)

    lambo.check_ability_swaps()

    assert lambo.has_effect(EffectType.ABILITY_SWAP, "Ten-Year Bazooka")
    assert lambo.source.current_abilities[1].name == "Thunder, Set, Charge!"

def test_ten_year_adult(lambo_test_scene: BattleScene):
    pteam = lambo_test_scene.player_display.team.character_managers
    eteam = lambo_test_scene.enemy_display.team.character_managers
    lambo = pteam[0]
    hinata = eteam[0]

    bazooka = lambo.source.main_abilities[0]
    conductivity = lambo.source.main_abilities[1]
    gyudon = lambo.source.main_abilities[2]
    thunderset = lambo.source.alt_abilities[0]
    cornatta = lambo.source.alt_abilities[1]

    ally_use_ability(lambo_test_scene, lambo, lambo, bazooka)

    lambo.check_ability_swaps()

    ally_use_ability(lambo_test_scene, lambo, lambo, bazooka)

    lambo.check_ability_swaps()

    assert lambo.has_effect(EffectType.UNIQUE, "Ten-Year Bazooka")
    assert lambo.get_effect(EffectType.ABILITY_SWAP, "Ten-Year Bazooka").mag == 22
    assert lambo.source.current_abilities[1].name == "Elettrico Cornata"

def test_conductivity_redirect(lambo_test_scene: BattleScene):
    pteam = lambo_test_scene.player_display.team.character_managers
    eteam = lambo_test_scene.enemy_display.team.character_managers
    lambo = pteam[0]
    naruto = eteam[1]

    bazooka = lambo.source.main_abilities[0]
    conductivity = lambo.source.main_abilities[1]
    gyudon = lambo.source.main_abilities[2]
    thunderset = lambo.source.alt_abilities[0]
    cornatta = lambo.source.alt_abilities[1]

    ally_use_ability(lambo_test_scene, lambo, lambo, conductivity)

    enemy_use_ability(lambo_test_scene, naruto, pteam[1], eteam[1].source.main_abilities[2])
    enemy_use_ability(lambo_test_scene, naruto, pteam[1], eteam[1].source.main_abilities[2])
    enemy_use_ability(lambo_test_scene, naruto, pteam[1], eteam[1].source.main_abilities[2])
    enemy_use_ability(lambo_test_scene, naruto, pteam[1], eteam[1].source.main_abilities[2])

    assert pteam[1].source.hp > 0

    assert lambo.source.hp == 60

def test_gyudon_lockout(lambo_test_scene: BattleScene):
    pteam = lambo_test_scene.player_display.team.character_managers
    eteam = lambo_test_scene.enemy_display.team.character_managers
    lambo = pteam[0]
    naruto = eteam[1]

    bazooka = lambo.source.main_abilities[0]
    conductivity = lambo.source.main_abilities[1]
    gyudon = lambo.source.main_abilities[2]
    thunderset = lambo.source.alt_abilities[0]
    cornatta = lambo.source.alt_abilities[1]

    ally_use_ability(lambo_test_scene, lambo, pteam[1], gyudon)

    for p in pteam:
        assert p.has_effect(EffectType.ALL_DR, "Summon Gyudon")
    
    for e in eteam:
        assert e.has_effect(EffectType.CONT_DMG, "Summon Gyudon")
    
    ally_use_ability(lambo_test_scene, lambo, lambo, bazooka)

    for p in pteam:
        assert not p.has_effect(EffectType.ALL_DR, "Summon Gyudon")
    
    for e in eteam:
        assert not e.has_effect(EffectType.CONT_DMG, "Summon Gyudon")
    
def test_magic_sword_stacking(lapucelle_test_scene: BattleScene):
    pteam = lapucelle_test_scene.player_display.team.character_managers
    eteam = lapucelle_test_scene.enemy_display.team.character_managers
    lapucelle = pteam[0]

    knightsword = lapucelle.source.main_abilities[0]
    magicsword = lapucelle.source.main_abilities[1]
    idealstrike = lapucelle.source.main_abilities[2]

    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    
    lapucelle.adjust_ability_costs()

    assert knightsword.total_cost == 4

    ally_use_ability(lapucelle_test_scene, lapucelle, eteam[0], knightsword)

    assert eteam[0].source.hp == 20

def test_magic_sword_with_boost_negate(lapucelle_test_scene: BattleScene):
    pteam = lapucelle_test_scene.player_display.team.character_managers
    eteam = lapucelle_test_scene.enemy_display.team.character_managers
    lapucelle = pteam[0]
    astolfo = eteam[0]

    knightsword = lapucelle.source.main_abilities[0]
    magicsword = lapucelle.source.main_abilities[1]
    idealstrike = lapucelle.source.main_abilities[2]

    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    ally_use_ability(lapucelle_test_scene, lapucelle, lapucelle, magicsword)
    
    enemy_use_ability(lapucelle_test_scene, astolfo, lapucelle, astolfo.source.main_abilities[1])

    assert lapucelle.has_effect(EffectType.BOOST_NEGATE, "Trap of Argalia - Down With A Touch!")

    ally_use_ability(lapucelle_test_scene, lapucelle, astolfo, knightsword)

    assert astolfo.source.hp == 80

def test_ideal_strike_lockout(lapucelle_test_scene: BattleScene):
    pteam = lapucelle_test_scene.player_display.team.character_managers
    eteam = lapucelle_test_scene.enemy_display.team.character_managers
    lapucelle = pteam[0]
    astolfo = eteam[0]

    knightsword = lapucelle.source.main_abilities[0]
    magicsword = lapucelle.source.main_abilities[1]
    idealstrike = lapucelle.source.main_abilities[2]

    assert idealstrike.target(lapucelle, pteam, eteam, True) == 0

def test_lightning_roar(laxus_test_scene: BattleScene):
    pteam = laxus_test_scene.player_display.team.character_managers
    eteam = laxus_test_scene.enemy_display.team.character_managers
    laxus = pteam[0]

    lightningroar = laxus.source.main_abilities[1]
    thunder_palace = laxus.source.main_abilities[2]

    ally_use_ability(laxus_test_scene, laxus, pteam[0], lightningroar)


    assert pteam[0].check_for_dmg_reduction() == -10

def test_thunder_palace(laxus_test_scene: BattleScene):
    pteam = laxus_test_scene.player_display.team.character_managers
    eteam = laxus_test_scene.enemy_display.team.character_managers
    laxus = pteam[0]

    lightningroar = laxus.source.main_abilities[1]
    thunder_palace = laxus.source.main_abilities[2]

    ally_use_ability(laxus_test_scene, laxus, laxus, thunder_palace)

    tick_one_turn(laxus_test_scene)
    tick_one_turn(laxus_test_scene)

    for e in eteam:
        assert e.source.hp == 60

def test_thunder_palace_cancel(laxus_test_scene: BattleScene):
    pteam = laxus_test_scene.player_display.team.character_managers
    eteam = laxus_test_scene.enemy_display.team.character_managers
    laxus = pteam[0]

    lightningroar = laxus.source.main_abilities[1]
    thunder_palace = laxus.source.main_abilities[2]

    ally_use_ability(laxus_test_scene, laxus, laxus, thunder_palace)

    enemy_use_ability(laxus_test_scene, eteam[1], laxus, eteam[1].source.main_abilities[2])

    assert laxus.source.hp == 70
    assert eteam[1].source.hp == 70
    assert len(laxus.source.current_effects) == 0

def test_lionel_lockout(leone_test_scene: BattleScene):
    pteam = leone_test_scene.player_display.team.character_managers
    eteam = leone_test_scene.enemy_display.team.character_managers
    leone = pteam[0]
    lionel = leone.source.main_abilities[0]
    instinct = leone.source.main_abilities[1]
    lionfist = leone.source.main_abilities[2]

    assert instinct.target(leone, pteam, eteam, True) == 0
    assert lionfist.target(leone, pteam, eteam, True) == 0

def test_lionel_lionfist_kill_on_instinct(leone_test_scene: BattleScene):
    pteam = leone_test_scene.player_display.team.character_managers
    eteam = leone_test_scene.enemy_display.team.character_managers
    leone = pteam[0]
    lionel = leone.source.main_abilities[0]
    instinct = leone.source.main_abilities[1]
    lionfist = leone.source.main_abilities[2]

    ally_use_ability(leone_test_scene, leone, leone, lionel)
    ally_use_ability(leone_test_scene, leone, eteam[0], instinct)
    leone.source.hp = 50
    eteam[0].source.hp = 10

    ally_use_ability(leone_test_scene, leone, eteam[0], lionfist)

    assert leone.source.hp == 80

def test_lionel_lionfist_kill_on_self_instinct(leone_test_scene: BattleScene):
    pteam = leone_test_scene.player_display.team.character_managers
    eteam = leone_test_scene.enemy_display.team.character_managers
    leone = pteam[0]
    lionel = leone.source.main_abilities[0]
    instinct = leone.source.main_abilities[1]
    lionfist = leone.source.main_abilities[2]

    ally_use_ability(leone_test_scene, leone, leone, lionel)
    ally_use_ability(leone_test_scene, leone, leone, instinct)
    leone.source.hp = 50
    eteam[0].source.hp = 10

    ally_use_ability_with_response(leone_test_scene, leone, eteam[0], lionfist)

    assert leone.source.hp == 60
    assert leone.get_effect(EffectType.STUN_IMMUNE, "Beast Instinct").duration == 4

def test_script_fire(levy_test_scene: BattleScene):
    pteam = levy_test_scene.player_display.team.character_managers
    eteam = levy_test_scene.enemy_display.team.character_managers
    levy = pteam[0]
    fire = levy.source.main_abilities[0]
    silent = levy.source.main_abilities[1]
    mask = levy.source.main_abilities[2]

    ally_use_ability_with_response(levy_test_scene, levy, eteam[0], fire)

    enemy_use_ability(levy_test_scene, eteam[1], levy, eteam[1].source.main_abilities[2])
    tick_one_turn(levy_test_scene)

    assert eteam[0].source.hp == 90
    assert eteam[1].source.hp == 80
    assert eteam[2].source.hp == 90

def test_script_silent(levy_test_scene: BattleScene):
    pteam = levy_test_scene.player_display.team.character_managers
    eteam = levy_test_scene.enemy_display.team.character_managers
    levy = pteam[0]
    fire = levy.source.main_abilities[0]
    silent = levy.source.main_abilities[1]
    mask = levy.source.main_abilities[2]

    ally_use_ability(levy_test_scene, levy, levy, silent)

    assert eteam[0].source.main_abilities[0].target(eteam[0], eteam, pteam, True) == 0

def test_script_mask(levy_test_scene: BattleScene):
    pteam = levy_test_scene.player_display.team.character_managers
    eteam = levy_test_scene.enemy_display.team.character_managers
    levy = pteam[0]
    fire = levy.source.main_abilities[0]
    silent = levy.source.main_abilities[1]
    mask = levy.source.main_abilities[2]

    ally_use_ability_with_response(levy_test_scene, levy, pteam[1], mask)

    enemy_use_ability(levy_test_scene, eteam[1], pteam[1], eteam[1].source.main_abilities[1])
    enemy_use_ability(levy_test_scene, eteam[2], pteam[1], eteam[2].source.main_abilities[1])

    assert not pteam[1].is_stunned()
    assert pteam[1].source.hp == 75

def test_crosstail_strike(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    ally_use_ability(lubbock_test_scene, raba, eteam[0], crosstail)

    raba.adjust_ability_costs()

    assert eteam[0].source.hp == 85
    assert eteam[0].has_effect(EffectType.MARK, "Cross-Tail Strike")
    assert crosstail.total_cost == 0

def test_crosstail_strike_failure(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    
    ally_use_ability(lubbock_test_scene, raba, eteam[0], crosstail)
    ally_use_ability(lubbock_test_scene, raba, eteam[0], crosstail)    

    raba.adjust_ability_costs()

    assert crosstail.total_cost == 1

def test_wireshield(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    ally_use_ability(lubbock_test_scene, raba, pteam[1], wireshield)

    raba.adjust_ability_costs()

    assert wireshield.total_cost == 0

def test_wireshield_cancel(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    ally_use_ability(lubbock_test_scene, raba, pteam[1], wireshield)
    ally_use_ability(lubbock_test_scene, raba, pteam[1], wireshield)

    assert not raba.has_effect(EffectType.COST_ADJUST, "Wire Shield")

def test_aoe_crosstail(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    for e in eteam:
        ally_use_ability(lubbock_test_scene, raba, e, crosstail)
    
    ally_use_ability(lubbock_test_scene, raba, eteam[0], crosstail)

    for e in eteam:
        assert not e.has_effect(EffectType.MARK, "Cross-Tail Strike")
        assert e.source.hp == 65

def test_aoe_wireshield(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    for p in pteam:
        ally_use_ability(lubbock_test_scene, raba, p, wireshield)
    
    ally_use_ability_with_response(lubbock_test_scene, raba, raba, wireshield)

    for p in pteam:
        assert not p.has_effect(EffectType.MARK, "Wire Shield")
        assert p.check_invuln()
        assert p.has_effect(EffectType.DEST_DEF, "Wire Shield")

def test_thrust_on_crosstail(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    ally_use_ability(lubbock_test_scene, raba, eteam[0], crosstail)
    ally_use_ability_with_response(lubbock_test_scene, raba, eteam[0], thrust)

    
    assert eteam[0].is_stunned()
    assert eteam[0].source.hp == 55

def test_thrust_through_wireshield(lubbock_test_scene: BattleScene):
    pteam = lubbock_test_scene.player_display.team.character_managers
    eteam = lubbock_test_scene.enemy_display.team.character_managers
    raba = pteam[0]

    crosstail = raba.source.main_abilities[0]
    wireshield = raba.source.main_abilities[1]
    thrust = raba.source.main_abilities[2]

    ally_use_ability(lubbock_test_scene, raba, raba, wireshield)
    ally_use_ability(lubbock_test_scene, raba, eteam[0], thrust)

    tick_one_turn(lubbock_test_scene)

    assert eteam[0].source.hp == 55

def test_gemini_aquarius(lucy_test_scene:BattleScene):
    pteam = lucy_test_scene.player_display.team.character_managers
    eteam = lucy_test_scene.enemy_display.team.character_managers
    lucy = pteam[0]

    aquarius = lucy.source.main_abilities[0]
    gemini = lucy.source.main_abilities[1]
    urano = lucy.source.alt_abilities[0]
    capricorn = lucy.source.main_abilities[2]
    leo = lucy.source.main_abilities[3]

    ally_use_ability(lucy_test_scene, lucy, lucy, gemini)
    ally_use_ability(lucy_test_scene, lucy, lucy, aquarius)

    for p in pteam:
        assert p.check_for_dmg_reduction() == 10
    
    tick_one_turn(lucy_test_scene)

    for e in eteam:
        assert e.source.hp == 70

def test_gemini_capricorn(lucy_test_scene:BattleScene):
    pteam = lucy_test_scene.player_display.team.character_managers
    eteam = lucy_test_scene.enemy_display.team.character_managers
    lucy = pteam[0]

    aquarius = lucy.source.main_abilities[0]
    gemini = lucy.source.main_abilities[1]
    urano = lucy.source.alt_abilities[0]
    capricorn = lucy.source.main_abilities[2]
    leo = lucy.source.main_abilities[3]

    ally_use_ability(lucy_test_scene, lucy, lucy, gemini)
    ally_use_ability(lucy_test_scene, lucy, eteam[0], capricorn)
    
    tick_one_turn(lucy_test_scene)

    assert eteam[0].source.hp == 60

def test_gemini_urano(lucy_test_scene:BattleScene):
    pteam = lucy_test_scene.player_display.team.character_managers
    eteam = lucy_test_scene.enemy_display.team.character_managers
    lucy = pteam[0]

    aquarius = lucy.source.main_abilities[0]
    gemini = lucy.source.main_abilities[1]
    urano = lucy.source.alt_abilities[0]
    capricorn = lucy.source.main_abilities[2]
    leo = lucy.source.main_abilities[3]

    ally_use_ability(lucy_test_scene, lucy, lucy, gemini)
    ally_use_ability(lucy_test_scene, lucy, eteam[0], urano)

    tick_one_turn(lucy_test_scene)

    for e in eteam:
        assert e.source.hp == 60
    
def test_gemini_leo(lucy_test_scene:BattleScene):
    pteam = lucy_test_scene.player_display.team.character_managers
    eteam = lucy_test_scene.enemy_display.team.character_managers
    lucy = pteam[0]

    aquarius = lucy.source.main_abilities[0]
    gemini = lucy.source.main_abilities[1]
    urano = lucy.source.alt_abilities[0]
    capricorn = lucy.source.main_abilities[2]
    leo = lucy.source.main_abilities[3]

    ally_use_ability(lucy_test_scene, lucy, lucy, gemini)
    ally_use_ability(lucy_test_scene, lucy, lucy, leo)

    assert lucy.check_invuln()

def test_smash(midoriya_test_scene: BattleScene):
    pteam = midoriya_test_scene.player_display.team.character_managers
    eteam = midoriya_test_scene.enemy_display.team.character_managers
    midoriya = pteam[0]

    smash = midoriya.source.main_abilities[0]
    shootstyle = midoriya.source.main_abilities[2]
    airforcegloves = midoriya.source.main_abilities[1]

    ally_use_ability_with_response(midoriya_test_scene, midoriya, eteam[0], smash)

    assert midoriya.source.hp == 80
    assert midoriya.is_stunned()

def test_airforcegloves(midoriya_test_scene: BattleScene):
    pteam = midoriya_test_scene.player_display.team.character_managers
    eteam = midoriya_test_scene.enemy_display.team.character_managers
    midoriya = pteam[0]

    smash = midoriya.source.main_abilities[0]
    shootstyle = midoriya.source.main_abilities[2]
    airforcegloves = midoriya.source.main_abilities[1]

    

    ally_use_ability_with_response(midoriya_test_scene, midoriya, eteam[1], airforcegloves)
    enemy_use_ability(midoriya_test_scene, eteam[1], midoriya, eteam[1].source.main_abilities[2])

    eteam[1].source.main_abilities[2].cooldown_remaining == eteam[1].source.main_abilities[2].cooldown + eteam[1].check_for_cooldown_mod()
    assert eteam[1].source.main_abilities[2].cooldown_remaining == 1

