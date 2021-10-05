from animearena import battle_scene
from animearena.ability import Ability, ability_info_db, Target, exe_effortless_guard
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
    naruto.current_targets.append(naruto)
    naruto.source.alt_abilities[0].execute(naruto, pteam, eteam)
    naruto.current_targets.clear()

    astolfo.current_targets.clear()
    astolfo.current_targets.append(naruto)
    trap.execute(astolfo, pteam, eteam)

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
    astolfo.apply_stack_effect(Effect(trap, EffectType.STACK, astolfo, 280000, lambda eff: f"Astolfo will deal {eff.mag * 5} additional damage with Trap of Argalia - Down With A Touch!", mag=5))

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

