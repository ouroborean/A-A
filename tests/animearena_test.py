from animearena import battle_scene
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

    naruto.current_targets.append(e_team[0])

    Ability("narutoalt2").execute(naruto, e_team, p_team)

    assert e_team[0].source.hp == 85
    assert e_team[0].is_stunned() == False
    assert naruto.has_effect(EffectType.MARK, "Uzumaki Barrage")

    Ability("narutoalt2").execute(naruto, e_team, p_team)

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

    toad_taijutsu.execute(naruto, p_team, e_team)

    assert len(fucking_ruler.source.current_effects) == 1
    assert fucking_ruler.source.hp == 65
    fucking_ruler.refresh_character(True)
    assert fucking_ruler.source.main_abilities[0].total_cost == 3


    