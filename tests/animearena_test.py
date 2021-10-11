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

def test_casseur(astolfo_test_scene: BattleScene):
    astolfo = astolfo_test_scene.player_display.team.character_managers[0]
    eteam = astolfo_test_scene.enemy_display.team.character_managers
    pteam = astolfo_test_scene.player_display.team.character_managers
    casseur = astolfo.source.current_abilities[0]
    naruto = eteam[1]
    astolfo.current_targets.append(astolfo)
    astolfo.used_ability = casseur
    rasengan = naruto.source.current_abilities[1]
    naruto.current_targets.append(astolfo)
    naruto.used_ability = rasengan

    casseur.execute(astolfo, pteam, eteam)

    rasengan.execute(naruto, pteam, eteam)

    assert astolfo.source.hp == 100
    assert naruto.has_effect(EffectType.ALL_STUN, "Casseur de Logistille")
    assert naruto.has_effect(EffectType.ISOLATE, "Casseur de Logistille")

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

