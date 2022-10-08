

from re import T
from animearena.scene_manager import SceneManager
from animearena.character import Character
from animearena.effects import Effect, EffectType
from animearena.scene_manager import SceneManager
from animearena.ability import Target

import logging
import pytest

from animearena.battle_scene import BattleScene, make_battle_scene, CharacterManager, AbilityMessage


class TestGame:

    player1: BattleScene
    player2: BattleScene
    active_player_id = int

    def __init__(self, player1_team: list[Character], player2_team: list[Character], scene_manager):

        self.player1 = make_battle_scene(scene_manager)
        self.player1.setup_scene(player1_team, player2_team)
        self.player1.player_display.team.energy_pool[0] = 20
        self.player1.player_display.team.energy_pool[1] = 20
        self.player1.player_display.team.energy_pool[2] = 20
        self.player1.player_display.team.energy_pool[3] = 20
        self.player1.player_display.team.energy_pool[4] = 80
        self.player2 = make_battle_scene(scene_manager)
        self.player2.setup_scene(player2_team, player1_team)
        self.player1.waiting_for_turn = False
        self.active_player_id = 0

    @property
    def active_player(self) -> BattleScene:
        if self.active_player_id == 0:
            return self.player1
        else:
            return self.player2

    @property
    def acting_order(self):
        return self.active_player.acting_order

    @property
    def pteam(self) -> list[CharacterManager]:
        return self.active_player.pteam

    @property
    def eteam(self) -> list[CharacterManager]:
        return self.active_player.eteam

    def quick_target(self, char_index, ability_index: int):
        char = self.eteam[char_index - 3] if char_index >= 3 else self.pteam[char_index] 
        return char.source.current_abilities[ability_index].target(char, self.pteam if char.id == "ally" else self.eteam, self.eteam if char.id == "ally" else self.pteam, fake_targeting=True)

    def toggle_active_player(self):
        if self.active_player_id == 0:
            self.active_player_id = 1
        else:
            self.active_player_id = 0

    def get_target_names_for_debugger(self, target_index_list: list[int]):
        output = []
        for i in target_index_list:
            if i > 2:
                output.append(f"Enemy {self.eteam[i - 3].source.name}")
            else:
                output.append(f"Ally {self.pteam[i].source.name}")
        return output

    def queue_action(self, character_index: int, ability_index: int, target_index_list: list[int]):
        actor = self.active_player.pteam[character_index]
        actor.acted = True
        actor.used_ability = actor.source.current_abilities[ability_index]
        actor.current_targets.clear()
        self.acting_order.append(actor)
        logging.debug("%s used %s targeting %s", actor.source.name, actor.used_ability.name, self.get_target_names_for_debugger(target_index_list))
        for i in target_index_list:
            if i < 3:
                actor.current_targets.append(self.active_player.pteam[i])
            else:
                if not actor.primary_target:
                    actor.primary_target = self.active_player.eteam[i - 3]
                actor.current_targets.append(self.active_player.eteam[i - 3])

    def player_action(self, character_index: int, ability_index: int, target_index_list: list[int]):
        self.queue_action(character_index, ability_index, target_index_list)
        self.execute_turn()
        
    def player_action_pass(self, character_index: int, ability_index: int, target_index_list: list[int]):
        self.queue_action(character_index, ability_index, target_index_list)
        self.pass_turn()
        
    def enemy_action(self, character_index: int, ability_index: int, target_index_list: list[int]):
        self.queue_enemy_action(character_index, ability_index, target_index_list)
        self.execute_enemy_turn()

    def queue_enemy_action(self, character_index: int, ability_index: int, target_index_list: list[int]):
        actor = self.active_player.eteam[character_index]
        actor.acted = True
        actor.used_ability = actor.source.current_abilities[ability_index]
        actor.current_targets.clear()
        self.acting_order.append(actor)
        for i in target_index_list:
            if i < 3:
                actor.current_targets.append(self.active_player.eteam[i])
            else:
                if not actor.primary_target:
                    actor.primary_target = self.active_player.pteam[i - 3]
                actor.current_targets.append(self.active_player.pteam[i - 3])

    def target_action(self, character_index: int, ability_index: int) -> int:
        actor = self.active_player.pteam[character_index]
        actor.current_targets.clear()
        return actor.source.current_abilities[ability_index].target(actor, self.active_player.pteam, self.active_player.eteam)

    def execute_enemy_abilities(self):
        for character in self.acting_order:
            if character.acted:
                self.active_player.ability_messages.append(AbilityMessage(character))
                character.execute_ability()
                character.acted = False
                character.primary_target = None
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        for character in self.pteam:
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        
        self.acting_order.clear()

    def execute_abilities(self):
        for character in self.acting_order:
            if character.acted:
                character.execute_ability()
                character.acted = False
                character.primary_target = None
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        for character in self.eteam:
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        self.acting_order.clear()

    def pass_turn(self):
        self.execute_turn()
        self.execute_enemy_turn()

    def execute_enemy_turn(self):
        
        self.active_player.get_execution_order_base("enemy")
        for action in self.active_player.execution_order:
            if action < 3:
                
                self.eteam[action].execute_ability()
            elif action > 2:
                self.resolve_ticking_ability(self.cont_list[action - 3])
        for character in self.pteam:
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        for character in self.eteam:
            character.acted = False
            character.primary_target = None
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        self.active_player.execution_order.clear()
        self.acting_order.clear()
        
        self.active_player.sharingan_reflecting = False
        self.active_player.sharingan_reflector = None

        for manager in self.active_player.pteam:
            if manager.source.name == "kuroko" and manager.check_invuln():
                manager.progress_mission(1, 1)
            if manager.source.name == "cmary" and manager.check_invuln() and manager.has_effect(EffectType.ALL_INVULN, "Quickdraw - Sniper"):
                manager.progress_mission(4, 1)

        self.active_player.tick_effect_duration()
        self.active_player.tick_enemy_cooldowns()
        
        game_lost = True
        for manager in self.active_player.pteam:
            manager.refresh_character()
            manager.received_ability.clear()
            if not manager.source.dead:
                game_lost = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)
        game_won = True
        for manager in self.active_player.eteam:
            manager.refresh_character(True)
            manager.received_ability.clear()
            if not manager.source.dead:
                game_won = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)

        #region Yatsufusa Resurrection handling
        for manager in self.active_player.pteam:
            if manager.source.dead and manager.has_effect(
                    EffectType.MARK, "Yatsufusa"):
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa")
                manager.source.dead = False
                yatsu.user.progress_mission(1, 1)
                manager.source.hp = 40
                manager.remove_effect(
                    manager.get_effect(EffectType.MARK, "Yatsufusa"))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.UNIQUE, yatsu.user, 280000,
                        lambda eff:
                        "This character has been animated by Kurome."))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.DEF_NEGATE, yatsu.user,
                        280000, lambda eff:
                        "This character cannot reduce damage or become invulnerable."
                    ))
                manager.add_effect(
                    Effect(
                        yatsu.source,
                        EffectType.COST_ADJUST,
                        yatsu.user,
                        280000,
                        lambda eff:
                        "This character's abilities costs have been increased by one random energy.",
                        mag=51))
                manager.adjust_ability_costs()
        #endregion
        if game_lost:
            self.active_player.lose_game()
        if game_won and not game_lost:
            self.active_player.win_game()

    def execute_turn(self):
        self.active_player.get_execution_order_base("ally")
        
        for action in self.active_player.execution_order:
            if action < 3:
                if self.pteam[action].acted:
                    self.pteam[action].execute_ability()
                    logging.debug("%s used %s", self.pteam[action].source.name, self.pteam[action].used_ability.name)
            elif action > 2:
                self.resolve_ticking_ability(self.cont_list[action - 3])
        for character in self.pteam:
            character.acted = False
            character.primary_target = None
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        for character in self.eteam:
            character.check_ability_swaps()
            character.adjust_targeting_types()
            character.adjust_ability_costs()
        self.active_player.execution_order.clear()
        self.acting_order.clear()
        
        self.active_player.sharingan_reflecting = False
        self.active_player.sharingan_reflector = None
        
        for manager in self.active_player.pteam:
            if manager.source.name == "kuroko" and manager.check_invuln():
                manager.progress_mission(1, 1)
            if manager.source.name == "cmary" and manager.check_invuln() and manager.has_effect(EffectType.ALL_INVULN, "Quickdraw - Sniper"):
                manager.progress_mission(4, 1)

        self.active_player.tick_effect_duration()
        self.active_player.tick_ability_cooldown()

        game_lost = True
        for manager in self.active_player.pteam:
            manager.refresh_character()
            manager.received_ability.clear()
            if not manager.source.dead:
                game_lost = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)
        game_won = True
        for manager in self.active_player.eteam:
            manager.refresh_character(True)
            manager.received_ability.clear()
            if not manager.source.dead:
                game_won = False
            else:
                temp_yatsufusa_storage = None
                if manager.has_effect(EffectType.MARK, "Yatsufusa"):
                    temp_yatsufusa_storage = manager.get_effect(
                        EffectType.MARK, "Yatsufusa")
                manager.source.current_effects.clear()
                if temp_yatsufusa_storage:
                    manager.source.current_effects.append(
                        temp_yatsufusa_storage)

        #region Yatsufusa Resurrection handling
        for manager in self.active_player.eteam:
            if manager.source.dead and manager.has_effect(
                    EffectType.MARK, "Yatsufusa"):
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa")
                manager.source.dead = False
                yatsu.user.progress_mission(1, 1)
                manager.source.hp = 40
                manager.remove_effect(
                    manager.get_effect(EffectType.MARK, "Yatsufusa"))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.UNIQUE, yatsu.user, 280000,
                        lambda eff:
                        "This character has been animated by Kurome."))
                manager.add_effect(
                    Effect(
                        yatsu.source, EffectType.DEF_NEGATE, yatsu.user,
                        280000, lambda eff:
                        "This character cannot reduce damage or become invulnerable."
                    ))
                manager.add_effect(
                    Effect(
                        yatsu.source,
                        EffectType.COST_ADJUST,
                        yatsu.user,
                        280000,
                        lambda eff:
                        "This character's abilities costs have been increased by one random energy.",
                        mag=51))

        #endregion
        if game_lost:
            self.active_player.lose_game()
        if game_won and not game_lost:
            self.active_player.win_game()


    def dump_effects(self, character: CharacterManager):
        logging.debug(f"Dumping effects for {character.source.name}")
        logging.debug("Non-system effects on %s: %s", character.source.name, [
            (eff.name, eff.eff_type.name, eff.duration) for eff in character.source.current_effects
            if not is_system_effect(eff)
        ])
        
        logging.debug("System effects:")
        for effect in character.source.current_effects:
            if effect.eff_type == EffectType.SYSTEM or effect.system:
                logging.debug(f"{effect.name}: {effect.eff_type.name} ({effect.duration})")


def is_system_effect(eff) -> bool:
    return not (eff.eff_type != EffectType.SYSTEM and eff.system != True)


@pytest.fixture(scope="package")
def character_data():
    data = {"naruto": Character("naruto"),
            "itachi": Character("itachi"),
            "minato": Character("minato"),
            "neji": Character("neji"),
            "hinata": Character("hinata"),
            "shikamaru": Character("shikamaru"),
            "kakashi": Character("kakashi"),
            "ichigo": Character("ichigo"),
            "orihime": Character("orihime"),
            "rukia": Character("rukia"),
            "ichimaru": Character("ichimaru"),
            "aizen": Character("aizen"),
            "midoriya": Character("midoriya"),
            "toga": Character("toga"),
            "mirio": Character("mirio"),
            "shigaraki": Character("shigaraki"),
            "todoroki": Character("todoroki"),
            "uraraka": Character("uraraka"),
            "jiro": Character("jiro"),
            "natsu": Character("natsu"),
            "gray": Character("gray"),
            "gajeel": Character("gajeel"),
            "wendy": Character("wendy"),
            "erza": Character("erza"),
            "levy": Character("levy"),
            "laxus": Character("laxus"),
            "lucy": Character("lucy"),
            "saber": Character("saber"),
            "jack": Character("jack"),
            "chu": Character("chu"),
            "astolfo": Character("astolfo"),
            "frankenstein": Character("frankenstein"),
            "gilgamesh": Character("gilgamesh"),
            "jeanne": Character("jeanne"),
            "misaka": Character("misaka"),
            "kuroko": Character("kuroko"),
            "sogiita": Character("sogiita"),
            "misaki": Character("misaki"),
            "frenda": Character("frenda"),
            "naruha": Character("naruha"),
            "accelerator": Character("accelerator"),
            "tsunayoshi": Character("tsunayoshi"),
            "yamamoto": Character("yamamoto"),
            "hibari": Character("hibari"),
            "gokudera": Character("gokudera"),
            "ryohei": Character("ryohei"),
            "lambo": Character("lambo"),
            "chrome": Character("chrome"),
            "tatsumi": Character("tatsumi"),
            "mine": Character("mine"),
            "akame": Character("akame"),
            "leone": Character("leone"),
            "raba": Character("raba"),
            "sheele": Character("sheele"),
            "seryu": Character("seryu"),
            "kurome": Character("kurome"),
            "esdeath": Character("esdeath"),
            "snowwhite": Character("snowwhite"),
            "ruler": Character("ruler"),
            "ripple": Character("ripple"),
            "nemu": Character("nemu"),
            "cmary": Character("cmary"),
            "cranberry": Character("cranberry"),
            "swimswim": Character("swimswim"),
            "pucelle": Character("pucelle"),
            "chachamaru": Character("chachamaru"),
            "saitama": Character("saitama"),
            "tatsumaki": Character("tatsumaki"),
            "mirai": Character("mirai"),
            "touka": Character("touka"),
            "killua": Character("killua"),
            "sheele": Character("sheele"),
            "byakuya": Character("byakuya"),
            "chelsea": Character("chelsea")}
    yield data

@pytest.fixture(scope="package")
def setup_scene_manager():
    scene_manager = SceneManager(testing=True)
    yield scene_manager

@pytest.fixture
def naruto_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["naruto"], char["snowwhite"], char["hinata"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def hinata_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["hinata"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def neji_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["neji"], char["minato"], char["naruto"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def minato_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["minato"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def itachi_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["itachi"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["saber"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def kakashi_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["kakashi"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def shikamaru_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["shikamaru"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["ruler"], char["mirio"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def ichigo_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["ichigo"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def orihime_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["orihime"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def rukia_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["rukia"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def byakuya_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["byakuya"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def ichimaru_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["ichimaru"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def aizen_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["aizen"], char["ruler"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def midoriya_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["midoriya"], char["levy"], char["mirio"]])
    enemy_team = get_reset_team([char["snowwhite"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def uraraka_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["uraraka"], char["snowwhite"], char["mirio"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def todoroki_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["todoroki"], char["snowwhite"], char["mirio"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def mirio_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["mirio"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["accelerator"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def toga_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["toga"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def shigaraki_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["shigaraki"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def jiro_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["jiro"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def natsu_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["natsu"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def lucy_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["lucy"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def gray_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["gray"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def erza_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["erza"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["shikamaru"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)


@pytest.fixture
def gajeel_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["gajeel"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def wendy_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["wendy"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def levy_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["levy"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["shikamaru"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def laxus_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["laxus"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["shikamaru"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def saber_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["saber"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["shikamaru"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)


@pytest.fixture
def chu_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["chu"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["naruto"], char["gajeel"], char["naruha"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def naruto_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["naruto"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def astolfo_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["astolfo"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["accelerator"], char["nemu"], char["ichigo"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def jack_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["jack"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def frankenstein_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["frankenstein"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["naruto"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def gilgamesh_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["gilgamesh"], char["snowwhite"], char["naruto"]])
    enemy_team = get_reset_team([char["itachi"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def jeanne_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["jeanne"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def misaka_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["misaka"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def kuroko_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["kuroko"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def gunha_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["sogiita"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def shokuhou_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["misaki"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def frenda_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["frenda"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["midoriya"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def naruha_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["naruha"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def accelerator_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["accelerator"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["shikamaru"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def tsuna_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["tsunayoshi"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def yamamoto_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["yamamoto"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def gokudera_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["gokudera"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def ryohei_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["ryohei"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["ichigo"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def lambo_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["lambo"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def hibari_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["hibari"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def chrome_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["chrome"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def tatsumi_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["tatsumi"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def akame_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["akame"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def leone_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["leone"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def mine_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["mine"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["gajeel"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def raba_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["raba"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def sheele_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["sheele"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["chu"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def chelsea_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["chelsea"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["tsunayoshi"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def seryu_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["seryu"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def kurome_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["kurome"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def esdeath_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["esdeath"], char["snowwhite"], char["wendy"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def snowwhite_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["snowwhite"], char["misaka"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["saber"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def lapucelle_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["pucelle"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def ripple_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["ripple"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def nemurin_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["nemu"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def ruler_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["ruler"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["itachi"], char["hibari"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def swimswim_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["swimswim"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def cmary_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["cmary"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def cranberry_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["cranberry"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["mirio"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def saitama_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["saitama"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["naruto"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def tatsumaki_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["tatsumaki"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["mine"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def chachamaru_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["chachamaru"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def mirai_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["mirai"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def touka_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["touka"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

@pytest.fixture
def killua_test_game(setup_scene_manager, character_data) -> TestGame:
    char = character_data
    ally_team = get_reset_team([char["killua"], char["snowwhite"], char["itachi"]])
    enemy_team = get_reset_team([char["ruler"], char["erza"], char["byakuya"]])
    return TestGame(ally_team, enemy_team, scene_manager=setup_scene_manager)

def reset_character(character: Character):
    character.hp = 100
    character.current_effects.clear()
    character.current_abilities = character.main_abilities
    for ability in character.current_abilities:
        ability.cooldown_remaining = 0
    character.energy_contribution = 1
    character.dead = False

def get_reset_team(characters: list[Character]):
    for character in characters:
        reset_character(character)
    return characters

#region Base Tests

def test_test_game(naruto_test_game: TestGame):
    assert naruto_test_game.active_player.pteam[0].source.name == "naruto"

def test_test_game_turn_switch(naruto_test_game: TestGame):
    assert naruto_test_game.pteam[0].source.name == "naruto"

    naruto_test_game.execute_abilities()

    assert naruto_test_game.eteam[0].source.name == "ruler"
#endregion

#region Naruto Tests

def test_sage_mode_drain_response(naruto_test_game:TestGame):
    game=naruto_test_game
    
    game.pass_turn()
    
    game.enemy_action(1, 2, [1])
    game.player_action(0, 2, [0])
    game.enemy_action(1, 2, [3])
    
    assert game.eteam[1].hp == 80

#endregion

# #region Hinata Tests
# def test_hinata_twin_lion(hinata_test_game: TestGame):

#     hinata_test_game.queue_action(0, 0, [3])
#     hinata_test_game.execute_abilities()

#     assert hinata_test_game.eteam[0].source.hp == 60

# def test_hinata_twin_lion(hinata_test_game: TestGame):

#     #Pass turn
#     hinata_test_game.execute_turn()


#     #Use Ruler's Counter on Herself.
#     hinata_test_game.queue_enemy_action(0, 2, [0])
#     hinata_test_game.execute_enemy_turn()
    
#     hinata_test_game.dump_effects(hinata_test_game.eteam[0])

#     #Use Hinata's Twin Lion Fists
#     hinata_test_game.queue_action(0, 0, [3])
#     hinata_test_game.execute_abilities()



#     hinata_test_game.dump_effects(hinata_test_game.pteam[0])

#     #Assert Hinata and Ruler have both taken 20 damage
#     assert hinata_test_game.eteam[0].source.hp == 80
#     assert hinata_test_game.pteam[0].source.hp == 80

# def test_hinata_trigrams(hinata_test_game: TestGame):

#     hinata_test_game.queue_action(0, 1, [0, 1, 2])
#     hinata_test_game.execute_turn()

    
#     assert hinata_test_game.pteam[2].check_for_dmg_reduction() == 10

#     hinata_test_game.execute_enemy_turn()


#     hinata_test_game.queue_action(0, 1, [0, 1, 2, 3, 4, 5])
#     hinata_test_game.execute_turn()


#     assert hinata_test_game.pteam[2].check_for_dmg_reduction() == 10
#     assert hinata_test_game.eteam[2].source.hp == 85

# #endregion

# #region Neji Tests

# def test_trigrams(neji_test_game: TestGame):

#     neji_test_game.queue_action(0, 0, [3])
#     neji_test_game.pass_turn()

#     assert neji_test_game.pteam[0].source.current_abilities[0].name == "Chakra Point Strike"
#     assert neji_test_game.eteam[0].source.hp == 98

#     neji_test_game.pass_turn()

#     assert neji_test_game.eteam[0].source.hp == 94

#     neji_test_game.pass_turn()

#     assert neji_test_game.eteam[0].source.hp == 86

#     neji_test_game.execute_turn()

#     assert neji_test_game.eteam[0].source.hp == 70

#     assert neji_test_game.pteam[0].has_effect(EffectType.CONT_USE, "Eight Trigrams - 128 Palms")

#     neji_test_game.queue_enemy_action(0, 0, [3])
#     neji_test_game.execute_enemy_turn()

#     assert not neji_test_game.pteam[0].has_effect(EffectType.CONT_USE, "Eight Trigrams - 128 Palms")

# def test_mountain_crusher(neji_test_game: TestGame):

#     neji_test_game.queue_action(0, 1, [3])
#     neji_test_game.execute_turn()

#     assert neji_test_game.eteam[0].source.hp == 75

#     neji_test_game.queue_enemy_action(0, 3, [0])
#     neji_test_game.execute_enemy_turn()

#     neji_test_game.queue_action(0, 1, [3])
#     neji_test_game.pass_turn()

#     assert neji_test_game.eteam[0].source.hp == 35

# def test_selfless_genius(neji_test_game: TestGame):

#     neji_test_game.pteam[1].source.hp = 5
#     neji_test_game.queue_action(0, 2, [1])
#     neji_test_game.execute_turn()

#     neji_test_game.queue_enemy_action(0, 1, [4])
#     neji_test_game.execute_enemy_turn()

#     assert neji_test_game.pteam[0].source.dead
#     assert neji_test_game.pteam[1].has_effect(EffectType.ALL_BOOST, "Selfless Genius")

# def test_selfless_genius_failure(neji_test_game: TestGame):

#     neji_test_game.queue_action(0, 2, [1])
#     neji_test_game.queue_action(1, 2, [4])
#     neji_test_game.execute_abilities()

#     assert neji_test_game.pteam[1].source.dead
#     assert not neji_test_game.pteam[0].source.dead

# #endregion

# #region Minato Tests
# def test_kunai(minato_test_game: TestGame):

#     minato_test_game.queue_action(0, 1, [3])
#     minato_test_game.pass_turn()

#     assert minato_test_game.eteam[0].has_effect(EffectType.MARK, "Marked Kunai")

# def test_flying_raijin(minato_test_game: TestGame):

#     minato_test_game.queue_action(0, 0, [3])
#     minato_test_game.pass_turn()

#     assert minato_test_game.pteam[0].source.current_abilities[0].cooldown_remaining == 1

#     minato_test_game.pass_turn()
#     minato_test_game.pass_turn()

#     assert minato_test_game.pteam[0].source.current_abilities[0].cooldown_remaining == 0

#     minato_test_game.queue_action(0, 1, [3])
#     minato_test_game.pass_turn()

#     minato_test_game.queue_action(0, 0, [3])
#     minato_test_game.execute_turn()

#     assert minato_test_game.pteam[0].source.current_abilities[0].cooldown_remaining == 0
#     assert minato_test_game.pteam[0].check_invuln()

# def test_shiki_fuujin(minato_test_game: TestGame):

#     minato_test_game.queue_action(0, 2, [3])
#     minato_test_game.pass_turn()
#     assert minato_test_game.pteam[0].source.dead
#     minato_test_game.eteam[0].adjust_ability_costs()
#     assert minato_test_game.eteam[0].source.current_abilities[0].total_cost == 2

# #endregion

# #region Itachi Tests
# def test_amaterasu(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 0, [3])
#     itachi_test_game.pass_turn()

#     assert itachi_test_game.target_action(0, 0) == 2
#     assert itachi_test_game.eteam[0].source.hp == 90

# def test_tsukuyomi(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 1, [3])
#     itachi_test_game.execute_turn()

#     assert itachi_test_game.eteam[0].is_stunned()

#     itachi_test_game.queue_enemy_action(1, 2, [0])
#     itachi_test_game.execute_enemy_turn()

#     assert not itachi_test_game.eteam[0].is_stunned()

# def test_susanoo(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 2, [0])
#     itachi_test_game.pass_turn()

#     assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Totsuka Blade"
#     assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Yata Mirror"

# def test_yata_mirror(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 2, [0])
#     itachi_test_game.pass_turn()
    
#     assert itachi_test_game.pteam[0].get_dest_def_total() == 45

#     itachi_test_game.queue_action(0, 1, [0])
#     itachi_test_game.pass_turn()

#     assert itachi_test_game.pteam[0].get_dest_def_total() == 65

# def test_susano_shatter_failure(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 2, [0])
#     itachi_test_game.execute_turn()

#     itachi_test_game.queue_enemy_action(0, 0, [3])
#     itachi_test_game.execute_enemy_turn()

#     assert not itachi_test_game.pteam[0].has_effect(EffectType.ABILITY_SWAP, "Susano'o")
#     assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Amaterasu"
#     assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Tsukuyomi"

# def test_susano_weakness_failure(itachi_test_game: TestGame):
#     itachi_test_game.queue_action(0, 2, [0])
#     itachi_test_game.pass_turn()

#     assert itachi_test_game.pteam[0].source.hp == 90

#     itachi_test_game.pteam[0].source.hp = 20
#     itachi_test_game.pass_turn()

#     assert not itachi_test_game.pteam[0].has_effect(EffectType.ABILITY_SWAP, "Susano'o")
#     assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Amaterasu"
#     assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Tsukuyomi"

# #endregion

# #region Kakashi Tests

# def test_raikiri_and_dogs(kakashi_test_game: TestGame):
#     kakashi_test_game.queue_action(0, 1, [3])
#     kakashi_test_game.execute_turn()

#     assert kakashi_test_game.eteam[0].is_stunned()

#     kakashi_test_game.execute_enemy_turn()

#     kakashi_test_game.queue_action(0, 2, [3])
#     kakashi_test_game.execute_abilities()

#     assert kakashi_test_game.eteam[0].source.dead

# def test_copy_ninja(kakashi_test_game: TestGame):
#     kakashi_test_game.queue_action(0, 0, [0])
#     kakashi_test_game.execute_turn()

#     kakashi_test_game.queue_enemy_action(2, 0, [3])
#     kakashi_test_game.execute_enemy_turn()

#     kakashi_test_game.dump_effects(kakashi_test_game.eteam[2])
#     assert kakashi_test_game.eteam[2].source.hp == 80
#     assert kakashi_test_game.eteam[2].is_stunned()

# def test_self_kamui(kakashi_test_game: TestGame):
#     kakashi_test_game.queue_action(0, 3, [0])
#     kakashi_test_game.execute_turn()
    
#     kakashi_test_game.queue_action(2, 0, [3])
#     kakashi_test_game.execute_turn()

#     assert kakashi_test_game.pteam[0].source.hp == 100
#     assert not kakashi_test_game.pteam[0].is_stunned()

# def test_target_kamui(kakashi_test_game: TestGame):
#     kakashi_test_game.queue_action(0, 3, [3])
#     kakashi_test_game.execute_turn()

#     assert kakashi_test_game.eteam[0].source.hp == 80

#     kakashi_test_game.queue_enemy_action(2, 3, [2])
#     kakashi_test_game.execute_enemy_turn()

#     kakashi_test_game.queue_action(0, 3, [5])
#     kakashi_test_game.execute_turn()

#     assert kakashi_test_game.eteam[2].source.hp == 80
#     assert kakashi_test_game.eteam[2].has_effect(EffectType.ISOLATE, "Kamui")

# #endregion

# #region Shikamaru Tests

# def test_shadow_pin(shikamaru_test_game: TestGame):
#     shikamaru_test_game.queue_action(0, 2, [3])
#     shikamaru_test_game.execute_turn()

#     assert not shikamaru_test_game.pteam[0].hostile_target(shikamaru_test_game.eteam[0])

# def test_shadow_bind_prolif(shikamaru_test_game: TestGame):
#     shikamaru_test_game.queue_action(0, 2, [3])
#     shikamaru_test_game.pass_turn()

#     shikamaru_test_game.queue_action(0, 0, [5])
#     shikamaru_test_game.execute_abilities()

#     assert shikamaru_test_game.eteam[0].is_stunned()
#     assert shikamaru_test_game.eteam[2].is_stunned()

# def test_shadow_neck_bind_prolif(shikamaru_test_game: TestGame):
#     shikamaru_test_game.queue_action(0, 2, [3])
#     shikamaru_test_game.pass_turn()

#     shikamaru_test_game.queue_action(0, 1, [5])
#     shikamaru_test_game.execute_abilities()

#     assert shikamaru_test_game.eteam[0].source.hp == 85
#     assert shikamaru_test_game.eteam[2].source.hp == 85


# #endregion

# #region Ichigo Tests

# def test_zangetsu_buildup(ichigo_test_game: TestGame):
#     ichigo_test_game.queue_action(0, 2, [3])
#     ichigo_test_game.pass_turn()

#     assert ichigo_test_game.eteam[0].source.hp == 80

#     ichigo_test_game.queue_action(0, 2, [3])
#     ichigo_test_game.pass_turn()

#     assert ichigo_test_game.eteam[0].source.hp == 55

#     ichigo_test_game.queue_action(0, 2, [3])
#     ichigo_test_game.pass_turn()

#     assert ichigo_test_game.eteam[0].source.hp == 25

# def test_empowered_getsuga(ichigo_test_game: TestGame):
#     ichigo_test_game.queue_action(0, 1, [0])
#     ichigo_test_game.execute_turn()

#     ichigo_test_game.queue_action(1, 3, [1])
#     ichigo_test_game.queue_action(0, 1, [1])
#     ichigo_test_game.execute_turn()

#     ichigo_test_game.queue_action(0, 0, [4])
#     ichigo_test_game.execute_abilities()

#     assert ichigo_test_game.eteam[1].source.hp == 60



    

# #endregion

# #region Orihime Tests

# def test_shunshun_lockout(orihime_test_game: TestGame):

#     orihime_test_game.active_player.player_display.team.energy_pool[1] = 4
#     orihime_test_game.active_player.player_display.team.energy_pool[4] = 4
    

#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()

#     assert not orihime_test_game.pteam[0].source.current_abilities[0].can_use(orihime_test_game.active_player, orihime_test_game.pteam[0])

    
#     orihime_test_game.queue_action(0, 1, [0])
#     orihime_test_game.pass_turn()

#     assert not orihime_test_game.pteam[0].source.current_abilities[1].can_use(orihime_test_game.active_player, orihime_test_game.pteam[0])

#     assert orihime_test_game.pteam[0].source.current_abilities[2].can_use(orihime_test_game.active_player, orihime_test_game.pteam[0])
    
#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     assert not orihime_test_game.pteam[0].source.current_abilities[2].can_use(orihime_test_game.active_player, orihime_test_game.pteam[0])

# def test_koten_zanshun(orihime_test_game: TestGame):
#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [3])
#     orihime_test_game.queue_action(1, 1, [3])
#     orihime_test_game.pass_turn()

#     assert orihime_test_game.eteam[0].source.hp == 65

# def test_soten_kishun(orihime_test_game: TestGame):
#     orihime_test_game.pteam[1].source.hp = 60

#     orihime_test_game.queue_action(0, 1, [0])
#     orihime_test_game.pass_turn()
    
#     orihime_test_game.queue_action(0, 3, [1])
#     orihime_test_game.pass_turn()

#     orihime_test_game.pass_turn()

#     assert orihime_test_game.pteam[1].source.hp == 100

# def test_santen_kesshun(orihime_test_game: TestGame):
#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [1])
#     orihime_test_game.execute_turn()

#     assert orihime_test_game.pteam[1].get_dest_def_total() == 30

# def test_resisting_shield(orihime_test_game: TestGame):
#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [1])
#     orihime_test_game.execute_turn()

#     assert orihime_test_game.pteam[1].get_dest_def_total() == 35

#     orihime_test_game.queue_enemy_action(0, 0, [4])
#     orihime_test_game.execute_enemy_turn()

#     assert orihime_test_game.pteam[1].source.hp == 100
#     assert orihime_test_game.eteam[0].source.hp == 85

# def test_inviolate_shield(orihime_test_game: TestGame):

#     orihime_test_game.pteam[0].source.hp = 60

#     orihime_test_game.queue_action(0, 1, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [0, 1, 2])
#     orihime_test_game.execute_turn()

#     orihime_test_game.queue_enemy_action(0, 0, [3])
#     orihime_test_game.execute_enemy_turn()

#     assert orihime_test_game.pteam[0].source.hp == 70

#     orihime_test_game.execute_turn()

#     assert orihime_test_game.pteam[0].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")
#     assert orihime_test_game.pteam[1].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")
#     assert orihime_test_game.pteam[2].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")

#     orihime_test_game.queue_enemy_action(0, 0, [3])
#     orihime_test_game.execute_enemy_turn()

#     assert not orihime_test_game.pteam[0].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")
#     assert not orihime_test_game.pteam[1].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")
#     assert not orihime_test_game.pteam[2].has_effect(EffectType.DEST_DEF, "Five-God Inviolate Shield")

# def test_empowering_shield(orihime_test_game: TestGame):

#     orihime_test_game.pteam[1].source.hp = 50

#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()
    
#     orihime_test_game.queue_action(0, 1, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [1])
#     orihime_test_game.queue_action(1, 1, [3])
#     orihime_test_game.execute_turn()

#     assert orihime_test_game.eteam[0].source.hp == 80
#     assert orihime_test_game.pteam[1].source.hp == 60

# def test_dance(orihime_test_game: TestGame):

#     orihime_test_game.pteam[0].source.hp = 50
#     orihime_test_game.pteam[1].source.hp = 50
#     orihime_test_game.pteam[2].source.hp = 50

#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()
    
#     orihime_test_game.queue_action(0, 1, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [0, 1, 2, 3, 4, 5])
#     orihime_test_game.execute_turn()

#     for char in orihime_test_game.pteam:
#         assert char.source.hp == 75
#         assert char.check_invuln()

#     for char in orihime_test_game.eteam:
#         assert char.source.hp == 75

# def test_shunshun_returning(orihime_test_game: TestGame):
#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [3])
#     orihime_test_game.pass_turn()

#     assert orihime_test_game.eteam[0].has_effect(EffectType.ALL_DR, "Lone-God Slicing Shield")

#     orihime_test_game.queue_action(0, 0, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 2, [0])
#     orihime_test_game.pass_turn()

#     orihime_test_game.queue_action(0, 3, [1])
#     orihime_test_game.pass_turn()

#     assert not orihime_test_game.eteam[0].has_effect(EffectType.ALL_DR, "Lone-God Slicing Shield")

# #endregion

# #region Rukia Tests

# def test_tsukishiro(rukia_test_game: TestGame):
#     rukia_test_game.execute_turn()

#     rukia_test_game.queue_enemy_action(0, 3, [0])
#     rukia_test_game.execute_enemy_turn()

#     rukia_test_game.queue_action(0, 0, [3])
#     rukia_test_game.execute_turn()

#     assert rukia_test_game.eteam[0].source.hp == 75
#     assert rukia_test_game.eteam[0].is_stunned()

# def test_shirafune(rukia_test_game: TestGame):
#     rukia_test_game.queue_action(0, 2, [0])
#     rukia_test_game.execute_turn()

#     rukia_test_game.queue_enemy_action(0, 1, [3])
#     rukia_test_game.execute_enemy_turn()
    
#     rukia_test_game.queue_action(0, 1, [3, 4, 5])
#     rukia_test_game.execute_turn()

#     assert rukia_test_game.eteam[1].source.hp == 100
#     assert rukia_test_game.eteam[0].source.hp == 70
#     assert rukia_test_game.eteam[0].is_stunned()

# #endregion

# #region Byakuya Tests

# def test_white_imperial_sword(byakuya_test_game: TestGame):
    

#     byakuya_test_game.queue_action(0, 2, [0])
#     byakuya_test_game.pass_turn()

#     byakuya_test_game.queue_action(0, 2, [3])
#     byakuya_test_game.execute_turn()

#     assert byakuya_test_game.eteam[0].source.hp == 20

# #endregion

# #region Ichimaru Tests

# def test_butou_renjin(ichimaru_test_game: TestGame):
    
#     ichimaru_test_game.queue_action(0, 0, [3])
#     ichimaru_test_game.pass_turn()
    
#     ichimaru_test_game.pass_turn()
#     ichimaru_test_game.pass_turn()
    
#     assert ichimaru_test_game.active_player.eteam[0].source.hp == 70
#     assert ichimaru_test_game.active_player.eteam[0].get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 2

# def test_13_kilometer(ichimaru_test_game: TestGame):
    
#     ichimaru_test_game.queue_action(0, 1, [3, 4, 5])
#     ichimaru_test_game.pass_turn()
    
#     for enemy in ichimaru_test_game.active_player.eteam:
#         assert enemy.source.hp == 75
#         assert enemy.has_effect(EffectType.STACK, "Kill, Kamishini no Yari")

# def test_kamishini(ichimaru_test_game: TestGame):
    
#     ichimaru_test_game.queue_action(0, 1, [3, 4, 5])
#     ichimaru_test_game.pass_turn()
    
#     ichimaru_test_game.queue_action(0, 0, [3])
#     ichimaru_test_game.pass_turn()
    
#     ichimaru_test_game.pass_turn()
#     ichimaru_test_game.pass_turn()
    
#     assert ichimaru_test_game.active_player.eteam[0].source.hp == 45
#     assert ichimaru_test_game.active_player.eteam[0].get_effect(EffectType.STACK, "Kill, Kamishini no Yari").mag == 3
    
#     ichimaru_test_game.queue_action(0, 2, [3, 4, 5])
#     ichimaru_test_game.pass_turn()
    
#     assert ichimaru_test_game.active_player.eteam[0].source.hp == 15
#     assert ichimaru_test_game.active_player.eteam[1].source.hp == 65
#     assert ichimaru_test_game.active_player.eteam[2].source.hp == 65
    
# def multi_kamishini(ichimaru_test_game: TestGame):
    
#     ichimaru_test_game.active_player.eteam[0].source.hp
    
# #endregion

# #region Aizen Tests

# def test_shatter(aizen_test_game: TestGame):
    
#     game = aizen_test_game
#     game.queue_action(0, 0, [3])
#     game.execute_turn()
    
#     assert game.active_player.eteam[0].source.current_abilities[0].total_cost == 2

# def test_shatter_on_coffin(aizen_test_game: TestGame):
#     game = aizen_test_game
    
#     game.queue_action(0, 2, [3])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 2, [0])
#     game.execute_enemy_turn()
    
#     assert game.active_player.eteam[0].source.current_abilities[2].cooldown_remaining == 5
    
#     game.queue_action(0, 0, [3])
#     game.execute_turn()
    
#     assert game.active_player.eteam[0].source.current_abilities[2].cooldown_remaining == 7

# def test_shatter_on_power(aizen_test_game: TestGame):
#     game = aizen_test_game
    
#     game.queue_action(0, 1, [3])
#     game.pass_turn()
    
#     game.queue_action(0, 0, [3])
#     game.pass_turn()
    
#     assert game.active_player.pteam[0].source.current_abilities[0].total_cost == 1

# def test_power_on_shatter(aizen_test_game: TestGame):
#     game = aizen_test_game
#     game.queue_action(0, 0, [3])
#     game.pass_turn()
    
#     game.queue_action(0, 1, [3])
#     game.pass_turn()
    
#     assert game.active_player.eteam[0].source.hp == 55
    
# def test_power_on_coffin(aizen_test_game: TestGame):
#     game = aizen_test_game
#     game.queue_action(0, 2, [3])
#     game.pass_turn()
    
#     game.queue_action(0, 1, [3])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 3, [0])
#     game.execute_enemy_turn()
    
#     assert not game.active_player.eteam[0].check_invuln()
    
# def test_coffin(aizen_test_game: TestGame):
#     game = aizen_test_game
#     game.queue_action(0, 2, [3])
#     game.execute_turn()
    
#     assert game.active_player.eteam[0].is_stunned()
    
# def test_coffin_on_shatter(aizen_test_game: TestGame):
#     game=aizen_test_game
#     game.queue_action(0, 0, [3])
#     game.pass_turn()
    
#     game.queue_action(0, 2, [3])
#     game.execute_turn()
    
#     for enemy in game.active_player.eteam:
#         assert enemy.is_stunned()
        
# def test_coffin_on_power(aizen_test_game: TestGame):
#     game=aizen_test_game
#     game.queue_action(0, 1, [3])
#     game.pass_turn()
    
#     game.queue_action(0, 2, [3])
#     game.execute_turn()
    
#     assert game.active_player.eteam[0].is_stunned()
#     assert game.active_player.eteam[0].source.hp == 55

# #endregion

# #region Midoriya Tests

# def test_midoriya_smash(midoriya_test_game:TestGame):
#     game=midoriya_test_game
#     game.queue_action(0, 0, [3])
#     game.pass_turn()
    
#     assert game.pteam[0].hp == 80
#     assert game.eteam[0].hp == 55
    
#     game.queue_action(1, 2, [0])
#     game.queue_action(0, 0, [3])
#     game.pass_turn()
    
#     assert game.pteam[0].hp == 80
#     assert game.eteam[0].hp == 10

# def test_shoot_style(midoriya_test_game:TestGame):
#     game=midoriya_test_game
#     game.queue_action(0, 2, [3, 4, 5])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 0, [3])
#     game.execute_enemy_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 80
    
#     assert game.pteam[0].hp == 100
    
# def test_air_force_gloves(midoriya_test_game: TestGame):
#     game=midoriya_test_game
#     game.queue_action(0, 1, [3])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.eteam[0].source.current_abilities[0].cooldown_remaining == 1



# #endregion

# #region Uraraka Tests

# def test_zero_gravity_ally(uraraka_test_game:TestGame):
#     game = uraraka_test_game
    
#     game.queue_action(0, 0, [1])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(1, 3, [1])
#     game.execute_enemy_turn()
    
#     assert game.pteam[1].hp == 95
    
#     assert game.target_action(1, 0) == 3
    

# def test_zero_gravity_enemy(uraraka_test_game:TestGame):
#     game=uraraka_test_game
    
#     game.queue_action(0, 0, [3])
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 3, [0])
#     game.execute_enemy_turn()
    
#     assert not game.eteam[0].check_invuln()
    
#     game.queue_action(1, 0, [3])
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 75
    
# def test_enemy_meteor_storm(uraraka_test_game:TestGame):
#     game=uraraka_test_game
    
#     game.player_action_pass(0, 0, [3])
#     assert (EffectType.DEF_NEGATE, "Quirk - Zero Gravity") in game.eteam[0]
#     game.player_action(0, 1, [3, 4, 5])
#     assert game.eteam[0].hp == 75
#     assert (EffectType.DEF_NEGATE, "Quirk - Zero Gravity") in game.eteam[0]
#     assert game.eteam[1].hp == 85

# def test_ally_meteor_storm(uraraka_test_game:TestGame):
#     game = uraraka_test_game
    
#     game.player_action_pass(0, 0, [1])
#     game.queue_action(0, 1, [3, 4, 5])
#     game.queue_action(1, 0, [3])
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 65
#     assert game.eteam[1].hp == 85

# def test_enemy_home_run(uraraka_test_game:TestGame):
#     game = uraraka_test_game
#     game.player_action_pass(0, 0, [3])
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].hp == 70
#     assert game.eteam[0].source.energy_contribution == 0
    
# def test_ally_home_run(uraraka_test_game:TestGame):
#     game = uraraka_test_game
#     game.player_action_pass(0, 0, [1])
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].hp == 80
#     assert game.pteam[1].check_invuln()

# #endregion

# #region Todoroki Tests

# def test_half_cold(todoroki_test_game: TestGame):
    
#     game = todoroki_test_game
#     game.player_action_pass(0, 0, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 80
        
#     assert game.pteam[0].source.current_abilities[0].all_costs[4] == 1
#     assert game.pteam[0].source.current_abilities[1].all_costs[4] == 1
#     assert game.pteam[0].source.current_abilities[2].all_costs[4] == 1
#     assert game.pteam[0].source.current_abilities[3].all_costs[4] == 2
    
#     game.player_action_pass(0, 0, [3, 4, 5])
#     game.player_action_pass(0, 0, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 40
    
#     assert game.pteam[0].source.current_abilities[0].all_costs[4] == 3
#     assert game.pteam[0].source.current_abilities[1].all_costs[4] == 3
#     assert game.pteam[0].source.current_abilities[2].all_costs[4] == 3
#     assert game.pteam[0].source.current_abilities[3].all_costs[4] == 4
    
# def test_half_hot(todoroki_test_game:TestGame):
#     game = todoroki_test_game
#     game.player_action_pass(0, 1, [3])
#     assert game.eteam[0].hp == 70
#     assert game.pteam[1].hp == 90
    
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].hp == 10
#     assert game.pteam[2].hp == 40
    
# def test_heatwave(todoroki_test_game:TestGame):
#     game=todoroki_test_game
#     game.player_action_pass(0, 0, [3, 4, 5])
#     game.player_action_pass(0, 1, [3])
#     # enemy team HP at 50, 80, 80
    
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     assert game.eteam[0].hp == 20
#     assert game.eteam[1].hp == 65
#     assert game.eteam[2].hp == 65
    
#     assert not (EffectType.STACK, "Quirk - Half-Hot") in game.pteam[0]
#     assert not (EffectType.STACK, "Quirk - Half-Cold") in game.pteam[0]

# #endregion

# #region Mirio Tests

# def test_permeation(mirio_test_game:TestGame):
#     game = mirio_test_game
#     game.player_action(0, 0, [0])
    
#     game.enemy_action(0, 1, [3])
#     assert game.pteam[0].hp == 100
    
#     assert (EffectType.MARK, "Phantom Menace") in game.eteam[0]

# def test_protect_ally(mirio_test_game: TestGame):
#     game = mirio_test_game
#     game.player_action(0, 2, [1])
    
#     game.enemy_action(0, 1, [4])
    
#     assert game.pteam[1].hp == 100
    
#     assert (EffectType.MARK, "Phantom Menace") in game.eteam[0]

# def test_phantom_menace(mirio_test_game: TestGame):
#     game = mirio_test_game
    
#     game.player_action(0, 0, [0])
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 0, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 100
    
#     for enemy in game.eteam:
#         assert (EffectType.MARK, "Phantom Menace") in enemy
    
#     game.player_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 65
#     assert game.eteam[1].hp == 85
#     assert game.eteam[2].hp == 85

# #endregion

# #region Toga Tests

# def test_thirsting_knife_stacks(toga_test_game:TestGame):
#     game=toga_test_game
    
#     game.player_action_pass(0, 0, [3])
    
#     assert (EffectType.STACK, "Quirk - Transform") in game.eteam[0]
#     assert game.eteam[0].get_effect(EffectType.STACK, "Quirk - Transform").mag == 2
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 70
#     assert game.eteam[0].get_effect(EffectType.STACK, "Quirk - Transform").mag == 6
    

# def test_vacuum_syringe_stacks(toga_test_game:TestGame):
#     game=toga_test_game
    
#     game.player_action_pass(0, 1, [3])
    
#     assert (EffectType.STACK, "Quirk - Transform") in game.eteam[0]
#     assert game.eteam[0].get_effect(EffectType.STACK, "Quirk - Transform").mag == 1
    
#     game.player_action_pass(0, 0, [3])
#     assert game.eteam[0].get_effect(EffectType.STACK, "Quirk - Transform").mag == 4

# def test_transform(toga_test_game:TestGame):
#     game=toga_test_game
    
#     game.player_action_pass(0, 0, [4])
#     game.player_action_pass(0, 2, [4])
    
#     assert (EffectType.UNIQUE, "Quirk - Transform") in game.pteam[0]
#     assert game.pteam[0].source.name == "naruto"
#     assert game.pteam[0].is_toga
#     assert game.pteam[0].source.current_abilities[0].name == "Rasengan"
#     assert game.pteam[0].source.alt_abilities[0].name == "Odama Rasengan"

# def test_transform_falloff(toga_test_game:TestGame):
#     game=toga_test_game
    
#     game.player_action_pass(0, 0, [4])
#     game.player_action_pass(0, 2, [4])
#     game.player_action(0, 1, [0])
    
#     assert (EffectType.ABILITY_SWAP, "Shadow Clones") in game.pteam[0]
#     assert game.pteam[0].source.current_abilities[0].name == "Odama Rasengan"
    
#     game.enemy_action(0, 0, [3])
    
#     assert (EffectType.ALL_STUN, "In The Name Of Ruler!") in game.pteam[0]
    
#     game.pass_turn()
    
#     logging.debug("%s", game.pteam[0])
#     assert len(game.pteam[0].source.current_effects) == 2

# def test_transform_effect_persistence(toga_test_game: TestGame):
#     game = toga_test_game
#     game.player_action_pass(0, 0, [5])
#     game.player_action_pass(0, 2, [5])
#     game.player_action_pass(0, 2, [0])
#     game.player_action(0, 0, [0, 1, 2])
    
#     assert (EffectType.DEST_DEF, "Scatter, Senbonzakura") in game.pteam[0]
#     assert not (EffectType.TARGET_SWAP, "Bankai - Senbonzakura Kageyoshi") in game.pteam[0]
#     assert (EffectType.DEST_DEF, "Scatter, Senbonzakura") in game.pteam[1]
#     assert (EffectType.DEST_DEF, "Scatter, Senbonzakura") in game.pteam[2]
    

# #endregion

# #region Shigaraki Tests

# def test_decaying_touch(shigaraki_test_game:TestGame):
#     game = shigaraki_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 85
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 65
    
# def test_decaying_breakthrough(shigaraki_test_game:TestGame):
#     game = shigaraki_test_game
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.player_action_pass(0, 0, [4])
    
#     assert game.eteam[0].hp == 90
#     assert game.eteam[1].hp == 85
#     assert game.eteam[2].hp == 90
    
#     game.player_action_pass(0, 1, [3, 4, 5])
    
#     assert game.eteam[0].hp == 80
#     assert game.eteam[1].hp == 65
#     assert game.eteam[2].hp == 80
    
# def test_destroy_what_you_love(shigaraki_test_game:TestGame):
#     game = shigaraki_test_game
    
#     game.player_action(0, 2, [1, 2])
    
#     game.enemy_action(0, 1, [4])
#     # Ruler deals 20 damage (Up 5) to PC 2
    
#     game.player_action(1, 0, [3])
#     # Snow White deals 25 damage (Up 10) to EC 1
    
#     assert game.pteam[1].hp == 80
#     assert game.eteam[0].hp == 75

# #endregion

# #region Jiro Tests

# def test_heartbeat_distortion(jiro_test_game:TestGame):
#     game = jiro_test_game
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.player_action_pass(0, 2, [4])
    
#     assert game.eteam[0].hp == 90
#     assert game.eteam[1].hp == 70
    
#     assert not game.pteam[0].source.current_abilities[1].can_use(game.active_player, game.pteam[0])

# def test_heartbeat_surround(jiro_test_game:TestGame):
#     game = jiro_test_game
    
#     game.player_action_pass(0, 2, [3])
#     game.player_action_pass(0, 1, [3, 4, 5])
    
#     assert game.eteam[0].hp == 65
#     assert game.eteam[1].hp == 85
    
#     assert not game.pteam[0].source.current_abilities[2].can_use(game.active_player, game.pteam[0])

# def test_counter_balance(jiro_test_game:TestGame):
#     game = jiro_test_game
#     game.pass_turn()
#     game.enemy_action(1, 2, [1])
#     game.player_action(0, 0, [3, 4, 5])
#     game.queue_enemy_action(0, 0, [3])
#     game.queue_enemy_action(1, 2, [5])
#     game.execute_enemy_turn()
    
#     assert game.eteam[0].check_energy_contribution()[4] == 0
#     assert game.eteam[1].is_stunned()

# #endregion

# #region Natsu Tests

# def test_roar_with_fist(natsu_test_game: TestGame):
#     game = natsu_test_game
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 75
    
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].hp == 40

# def test_sword_horn_with_fist(natsu_test_game: TestGame):
#     game=natsu_test_game
#     game.player_action_pass(0, 2, [3])
#     assert game.eteam[0].hp == 60
    
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].hp == 30

# #endregion

# #region Lucy Tests

# def test_aquarius(lucy_test_game:TestGame):
#     game = lucy_test_game

#     game.player_action(0, 0, [0, 1, 2, 3, 4, 5])
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].hp == 95
#     assert game.eteam[0].hp == 85
    
# def test_leo(lucy_test_game:TestGame):
#     game = lucy_test_game
    
#     game.player_action(0, 2, [4])
    
#     assert game.eteam[1].hp == 80
    
# def test_gemini_aquarius(lucy_test_game:TestGame):
#     game = lucy_test_game
    
#     game.player_action_pass(0, 1, [0])
#     game.player_action_pass(0, 0, [0, 1, 2, 3, 4, 5])
#     game.pass_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 70
        
# def test_gemini_leo(lucy_test_game:TestGame):
#     game = lucy_test_game
    
#     game.player_action_pass(0, 1, [0])
#     game.player_action_pass(0, 2, [4])
#     game.pass_turn()
    
#     assert game.eteam[1].hp == 60
    
# def test_gemini_urano(lucy_test_game:TestGame):
#     game = lucy_test_game
    
#     game.player_action_pass(0, 1, [0])
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.pass_turn()
    
#     for enemy in game.eteam:
#         assert enemy.source.hp == 60

# #endregion

# #region Gray Tests

# def test_lockout(gray_test_game: TestGame):
#     game = gray_test_game
    
#     assert not game.pteam[0].source.current_abilities[1].can_use(game.active_player, game.pteam[0])
#     assert not game.pteam[0].source.current_abilities[2].can_use(game.active_player, game.pteam[0])
#     assert not game.pteam[0].source.current_abilities[3].can_use(game.active_player, game.pteam[0])
    
#     game.player_action_pass(0, 0, [0])
    
#     assert game.pteam[0].source.current_abilities[1].can_use(game.active_player, game.pteam[0])
#     assert game.pteam[0].source.current_abilities[2].can_use(game.active_player, game.pteam[0])
#     assert game.pteam[0].source.current_abilities[3].can_use(game.active_player, game.pteam[0])

# def test_freeze_lancer(gray_test_game: TestGame):
#     game=gray_test_game
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.pass_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 70

# def test_ice_hammer(gray_test_game: TestGame):
#     game=gray_test_game
    
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].hp == 80
#     assert game.eteam[0].is_stunned()
    
# def test_unlimited(gray_test_game: TestGame):
#     game=gray_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [0, 1, 2, 3, 4, 5])
    
#     game.pass_turn()
#     game.pass_turn()
#     game.pass_turn()
    
#     assert game.pteam[2].get_dest_def_total() == 20
#     assert game.eteam[2].hp == 80
    

# #endregion

# #region Erza Tests

# def test_clear_heart(erza_test_game: TestGame):
#     game = erza_test_game
    
#     game.player_action(0, 0, [0])
#     game.enemy_action(0, 0, [3])
    
#     assert not game.pteam[0].is_stunned()
    
#     game.player_action_pass(0, 0, [0])
#     #15
#     game.pass_turn()
#     #35
#     game.pass_turn()
#     #60
    
#     missing_health = 0
#     for enemy in game.eteam:
#         missing_health += 100 - enemy.hp
    
#     assert missing_health == 60
    
# def test_heavens_wheel(erza_test_game:TestGame):
#     game = erza_test_game
#     game.player_action(0, 1, [0])
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].hp == 100
    
#     game.player_action_pass(0, 1, [5])
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 85
#     assert game.eteam[2].hp == 65
    
# def test_nakagamis(erza_test_game:TestGame):
#     game = erza_test_game
#     game.player_action_pass(0, 2, [0])
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].source.energy_contribution == 0
    
# def test_adamantine(erza_test_game:TestGame):
#     game = erza_test_game
#     game.player_action_pass(0, 3, [0])
#     game.player_action(0, 3, [1, 2])
    
#     assert game.pteam[1].check_invuln()
#     assert game.pteam[2].check_invuln()
    

# #endregion

# #region Gajeel Tests

# def test_iron_shadow_resistance(gajeel_test_game:TestGame):
#     game = gajeel_test_game
    
#     game.player_action(0, 2, [0])
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 85

# #endregion

# #region Wendy Tests

# def test_troia_diminish(wendy_test_game: TestGame):
#     game = wendy_test_game
    
#     game.pteam[1].source.hp = 10
    
#     game.player_action_pass(0, 2, [1])
#     game.player_action_pass(0, 2, [1])
#     game.player_action_pass(0, 2, [1])
    
#     assert game.pteam[1].hp == 80
    
# def test_shredding_wedding(wendy_test_game:TestGame):
#     game = wendy_test_game
    
#     game.player_action(0, 1, [4])
#     game.enemy_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 80
    
#     game.player_action(1, 0, [4])
    
#     assert game.pteam[1].hp == 80
    
#     game.enemy_action(2, 0, [1])
    
#     assert game.eteam[2].hp == 80
    
# #endregion

# #region Levy Tests

# def test_fire_script(levy_test_game: TestGame):
#     game = levy_test_game
    
#     game.player_action(0, 0, [3, 4, 5])
    
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(1, 3, [1])
#     game.execute_enemy_turn()
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 80
#     assert game.eteam[1].hp == 80
#     assert game.eteam[2].hp == 90

# def test_silent_script(levy_test_game: TestGame):
#     game=levy_test_game
    
#     game.player_action(0, 1, [0, 1, 2, 3, 4, 5])
    
#     assert game.eteam[2].source.current_abilities[0].target(game.eteam[2], game.eteam, game.pteam, fake_targeting = True) == 4
#     assert game.eteam[0].source.current_abilities[2].target(game.eteam[0], game.eteam, game.pteam, fake_targeting = True) == 1
    
# def test_mask_script(levy_test_game: TestGame):
#     game=levy_test_game
    
#     game.player_action(0, 2, [1])
    
#     game.queue_enemy_action(0, 0, [4])
#     game.queue_enemy_action(1, 1, [4])
#     game.execute_enemy_turn()
    
#     assert game.pteam[1].hp == 100
#     assert not game.pteam[1].is_stunned()
    

# #endregion

# #region Laxus Tests

# def test_lightning_roar(laxus_test_game: TestGame):
#     game = laxus_test_game
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 60
#     assert game.eteam[0].is_stunned()
    
#     game.execute_enemy_turn()
#     logging.debug(game.eteam[0])
#     game.player_action(1, 0, [3])
    
#     assert game.eteam[0].hp == 35

# def test_thunder_palace_trigger(laxus_test_game: TestGame):
#     game = laxus_test_game
#     game.player_action(0, 2, [0])
    
#     game.enemy_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 85

# def test_thunder_palace_cancel(laxus_test_game: TestGame):
#     game = laxus_test_game
#     game.player_action(0, 2, [0])
    
#     game.execute_enemy_turn()
#     game.pass_turn()
    
#     game.execute_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 60
# #endregion

# #region Saber Tests

# def test_wind_blade_cancel(saber_test_game: TestGame):
#     game = saber_test_game
    
#     game.pteam[0].source.hp = 10
    
#     game.player_action(0, 1, [4])
#     game.enemy_action(0, 0, [3])
    
#     assert not game.pteam[0].is_stunned()
    
#     game.pass_turn()
#     game.pass_turn()
    
#     assert game.eteam[1].hp == 70
    
#     game.player_action(0, 1, [4])
    
    
    
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].source.dead
#     assert not (EffectType.CONT_DMG, "Wind Blade Combat") in game.eteam[1]
    
    
# def test_avalon_lockout(saber_test_game: TestGame):
#     game = saber_test_game
#     game.player_action_pass(0, 2, [2])
    
#     assert game.pteam[0].source.current_abilities[2].target(game.pteam[0], game.pteam, game.eteam, fake_targeting=True) == 2
    
# #endregion

# #region Chu Tests

# def test_assault_piercing(chu_test_game:TestGame):
#     game=chu_test_game
    
#     game.execute_turn()
#     game.queue_enemy_action(0, 1, [0])
#     game.queue_enemy_action(1, 2, [1])
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 85
#     game.enemy_action(1, 2, [1])
#     assert (EffectType.ALL_DR, "Blacksteel Gajeel") in game.eteam[1]
    
#     game.player_action(0, 0, [4])
#     assert game.eteam[1].hp == 100
    

# def test_flawless_deflection(chu_test_game:TestGame):
#     game=chu_test_game
#     game.execute_turn()
#     game.enemy_action(1, 2, [1])
#     game.player_action(0, 1, [0])
#     game.enemy_action(1, 0, [3, 4, 5])
    
#     assert game.pteam[0].hp == 100
    
# def test_gae_bolg_shatter(chu_test_game:TestGame):
#     game=chu_test_game
#     game.execute_turn()
#     game.enemy_action(2, 1, [2])
#     game.player_action(0, 2, [5])
    
#     assert game.eteam[2].get_dest_def_total() == 0
    
# #endregion

# #region Astolfo Tests

# def test_casseur(astolfo_test_game:TestGame):
#     game=astolfo_test_game
#     game.player_action(0, 0, [0])
#     game.enemy_action(0, 0, [3])
#     assert game.pteam[0].hp == 100
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[0].check_isolated()
    
#     game.pass_turn()
#     game.pass_turn()
    
    
#     game.player_action(0, 0, [0])
#     game.enemy_action(0, 1, [4, 3, 5])
    
#     assert game.pteam[1].hp == 100
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[0].check_isolated()

# def test_argalia_trigger(astolfo_test_game:TestGame):
#     game=astolfo_test_game
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 80
#     assert not (EffectType.STACK, "Trap of Argalia - Down With A Touch!") in game.pteam[0]
    
#     game.queue_enemy_action(1, 0, [1])
#     game.queue_enemy_action(2, 2, [3])
#     game.execute_enemy_turn()
    
#     assert (EffectType.STACK, "Zangetsu Strike") in game.eteam[2]
    
#     game.player_action(0, 1, [5])
    
#     assert (EffectType.STACK, "Trap of Argalia - Down With A Touch!") in game.pteam[0]
    
#     game.enemy_action(1, 2, [0])
    
#     game.player_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 65
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!").mag == 2
    
# def test_black_luna(astolfo_test_game:TestGame):
#     game=astolfo_test_game
    
#     game.pass_turn()
#     game.queue_enemy_action(2, 2, [3])
#     game.queue_enemy_action(0, 1, [3, 4, 5])
#     game.execute_enemy_turn()
    
#     for ally in game.pteam:
#         assert (EffectType.CONT_DMG, "Plasma Bomb") in ally
    
#     game.player_action(0, 2, [0, 1, 2, 3, 4, 5])
    
#     for ally in game.pteam:
#         assert not (EffectType.CONT_DMG, "Plasma Bomb") in ally
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Trap of Argalia - Down With A Touch!").mag == 3
    
#     game.enemy_action(2, 2, [5])
    
#     assert game.pteam[2].hp == 65
    
    
# #endregion

# #region Jack Tests

# def test_maria_lockout(jack_test_game:TestGame):
#     game=jack_test_game
    
#     assert not game.pteam[0].source.current_abilities[0].can_use(game.active_player, game.pteam[0])
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     assert game.pteam[0].source.current_abilities[0].can_use(game.active_player, game.pteam[0])
    
# def test_streets_targeting(jack_test_game:TestGame):
#     game=jack_test_game
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.player_action(0, 1, [4])
    
#     assert game.eteam[0].source.current_abilities[2].target(game.eteam[0], game.eteam, game.pteam, fake_targeting=True) == 2
    
#     assert game.eteam[1].source.alt_abilities[2].target(game.eteam[1], game.eteam, game.pteam, fake_targeting = True) == 1
    

# #endregion

# #region Frankenstein Tests

# def test_bridal_chest(frankenstein_test_game:TestGame):
#     game=frankenstein_test_game
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     for enemy in game.eteam:
#         assert enemy.hp == 80
    
#     game.pass_turn()
#     game.pass_turn()
    
#     missing_hp = 0
    
#     for enemy in game.eteam:
#         missing_hp += 100 - enemy.hp
        
#     assert missing_hp == 100
    

# def test_galvanism(frankenstein_test_game:TestGame):
#     game=frankenstein_test_game
    
#     game.pteam[0].source.hp = 20
    
#     game.player_action(0, 3, [0])
    
#     game.enemy_action(0, 0, [3])
    
#     assert game.pteam[0].hp == 45
    
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].hp == 70
    
#     game.queue_enemy_action(0, 0, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_abilities()
    
#     assert game.pteam[0].hp == 95
    
#     game.player_action(0, 0, [4])
    
#     assert game.eteam[1].hp == 60
    
    
    
# def test_blasted_tree(frankenstein_test_game:TestGame):
#     game=frankenstein_test_game
    
#     game.player_action(0, 2, [3])
#     assert game.eteam[0].source.dead
#     assert game.pteam[0].source.dead
    

# #endregion

# #region Gilgamesh Tests

# def test_gate_of_babylon(gilgamesh_test_game:TestGame):
#     game=gilgamesh_test_game
    
#     game.player_action_pass(0, 0, [0])
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 75
    
#     assert not (EffectType.STACK, "Gate of Babylon") in game.pteam[0]
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [0])
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 35
    
# def test_enkidu(gilgamesh_test_game:TestGame):
#     game=gilgamesh_test_game
    
#     game.execute_turn()
    
#     game.enemy_action(0, 0, [3])
    
#     game.player_action(0, 1, [3])
    
#     game.enemy_action(0, 0, [4])
    
#     assert game.pteam[0].hp == 90
#     assert game.pteam[1].hp == 100
#     assert game.eteam[0].is_stunned()
#     game.pass_turn()
#     game.pass_turn()
    
# def test_enuma_elish(gilgamesh_test_game:TestGame):
#     game=gilgamesh_test_game
    
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].source.current_abilities[0].can_use(game.active_player, game.eteam[0])
    
#     game.player_action(0, 2, [5])
    
#     assert not game.eteam[2].source.current_abilities[0].can_use(game.active_player, game.eteam[0])

# #endregion

# #region Jeanne Tests

# def test_flag_of_ruler(jeanne_test_game:TestGame):
#     game=jeanne_test_game
    
#     game.player_action(0, 0, [1, 2])
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(1, 0, [5])
#     game.execute_enemy_turn()
    
#     assert game.pteam[1].hp == 100
#     assert game.pteam[2].hp == 95

# def test_luminosite(jeanne_test_game:TestGame):
#     game=jeanne_test_game
    
#     game.player_action(0, 1, [0, 1, 2])
    
#     for ally in game.pteam:
#         assert ally.check_invuln()
    
# def test_crimson_holy_maiden(jeanne_test_game:TestGame):
#     game=jeanne_test_game
    
#     game.player_action_pass(0, 2, [0])
#     assert game.pteam[0].source.current_abilities[2].name == "Crimson Holy Maiden"
    
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 85
        
#     assert game.pteam[0].hp == 65
    
#     game.pass_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 70
        
#     assert game.pteam[0].hp == 30

# #endregion

# #region Kuroko Tests

# def test_throw(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action(0, 0, [3])
#     game.enemy_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 85
#     assert game.pteam[0].hp == 95
    
# def test_teleport(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 90
#     assert game.pteam[0].check_invuln()
    
# def test_pin(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action(0, 2, [3])
    
#     game.enemy_action(0, 3, [0])
    
#     assert not game.eteam[0].check_invuln()
    
# def test_throw_on_pin(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action_pass(0, 2, [3])
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].source.energy_contribution == 0
    
# def test_throw_on_teleport(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action_pass(0, 1, [3])
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].hp == 60
    
#     assert game.eteam[0].get_boosts(20) == 0
    
# def test_pin_on_throw(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].is_stunned()
    
# def test_pin_on_teleport(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action(0, 1, [3])
    
#     game.enemy_action(0, 3, [0])
    
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].hp == 75
    
# def test_teleport_on_throw(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].hp == 60
    
# def test_teleport_on_pin(kuroko_test_game:TestGame):
#     game=kuroko_test_game
    
#     game.player_action_pass(0, 2, [3])
#     game.player_action(0, 1, [3])
    
#     assert game.pteam[0].source.current_abilities[1].cooldown_remaining == 0
    

# #endregion

# #region Gunha Tests

# def test_guts_lockout(gunha_test_game:TestGame):
#     game=gunha_test_game
#     assert game.quick_target(0, 0) == 0
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 2) == 0
    
# def test_super_awesome_punch(gunha_test_game:TestGame):
#     game=gunha_test_game
    
#     game.player_action_pass(0, 3, [0])
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 55
#     assert game.eteam[0].is_stunned()
    
#     assert not (EffectType.STACK, "Guts") in game.pteam[0]
    
#     game.player_action_pass(0, 3, [0])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Guts").mag == 3
    
#     game.player_action(0, 0, [4])
    
#     assert game.eteam[1].hp == 55
    
#     assert not (EffectType.STACK, "Guts") in game.pteam[0]
    
#     game.player_action(0, 0, [5])
    
#     assert game.eteam[2].hp == 65
    
    
# def test_overwhelming_suppression(gunha_test_game:TestGame):
#     game=gunha_test_game
    
#     game.player_action_pass(0, 3, [0])
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 3, [1])
#     game.execute_enemy_abilities()
    
#     assert game.pteam[0].hp == 95
#     assert not game.eteam[1].check_invuln()
    
#     game.pass_turn()
#     game.pass_turn()
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Guts").mag == 2
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 3, [1])
#     game.execute_enemy_abilities()
    
#     assert game.pteam[0].hp == 90
#     assert game.eteam[1].check_invuln()
    
#     assert not (EffectType.STACK, "Guts") in game.pteam[0]
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 3, [1])
#     game.execute_enemy_abilities()
    
#     assert game.pteam[0].hp == 80
#     assert game.eteam[1].check_invuln()
    
    
    
# def test_hyper_eccentric_punch(gunha_test_game:TestGame):
#     game=gunha_test_game
    
#     game.player_action_pass(0, 3, [0])
    
#     assert game.pteam[0].source.current_abilities[2].target_type == Target.MULTI_ENEMY
    
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 75
        
#     assert game.pteam[0].source.current_abilities[2].target_type == Target.SINGLE
    
#     game.player_action_pass(0, 2, [3])
    
#     assert game.eteam[0].hp == 50
#     assert not (EffectType.STACK, "Guts") in game.pteam[0]
    
#     game.player_action_pass(0, 2, [3])
    
#     assert game.eteam[0].hp == 30
    
    
# def test_guts_refill(gunha_test_game:TestGame):
#     game=gunha_test_game
    
#     game.pteam[0].source.set_hp(20)
    
#     game.player_action_pass(0, 3, [0])
#     game.player_action_pass(0, 0, [3])
    
#     assert not (EffectType.STACK, "Guts") in game.pteam[0]
    
#     game.player_action_pass(0, 3, [0])
#     assert game.pteam[0].hp == 55
    
#     game.player_action_pass(0, 3, [0])
#     assert game.pteam[0].hp == 90
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Guts").mag == 6

# #endregion

# #region Shokuhou Tests

# def test_mental_out(shokuhou_test_game:TestGame):
#     game=shokuhou_test_game
    
#     game.player_action_pass(0, 0, [4])
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].hp == 75
#     assert game.eteam[0].is_stunned()
    
#     game.pass_turn()
#     game.pass_turn()
#     game.pass_turn()
    
#     game.player_action_pass(0, 0, [3])
#     assert game.pteam[0].source.current_abilities[0].name == "Minion - Tama"
    
#     game.player_action(0, 0, [2])
    
#     game.enemy_action(1, 0, [5])
    
#     assert game.pteam[2].hp == 100
#     assert game.eteam[1].hp == 80
    
# def test_ally_mobilization(shokuhou_test_game:TestGame):
#     game=shokuhou_test_game
    
#     game.player_action(0, 2, [1, 2])
    
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(1, 0, [5])
#     game.execute_enemy_turn()
    
#     assert game.pteam[1].hp == 100
#     assert game.pteam[2].hp == 90
#     assert not game.pteam[2].is_stunned()
    
    
# def test_exterior_mental_out(shokuhou_test_game:TestGame):
#     game=shokuhou_test_game
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].hp == 60
    
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
    
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].get_effect(EffectType.ALL_STUN, "Mental Out").duration == 5

# def test_loyal_guard_lockout(shokuhou_test_game:TestGame):
#     game=shokuhou_test_game
    
#     assert game.quick_target(0, 3) == 1
    
#     game.pteam[1].source.dead = True
#     game.pteam[1].source.set_hp(0)
#     game.pteam[2].source.dead = True
#     game.pteam[2].source.set_hp(0)
    
#     assert game.quick_target(0, 3) == 0

# #endregion

# #region Frenda Tests

# def test_close_combat_bombs(frenda_test_game:TestGame):
#     game=frenda_test_game
    
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].get_effect(EffectType.STACK, "Close Combat Bombs").mag == 4
    
# def test_doll_trap_transfer(frenda_test_game:TestGame):
#     game=frenda_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [0])
    
#     game.enemy_action(0, 1, [3])
    
#     assert not (EffectType.STACK, "Doll Trap") in game.pteam[0]
#     assert (EffectType.STACK, "Doll Trap") in game.eteam[0]
#     assert game.eteam[0].get_effect(EffectType.STACK, "Doll Trap").mag == 2
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [1])
#     game.player_action(0, 0, [2])
    
#     game.enemy_action(1, 2, [3, 4, 5])
    
#     assert not (EffectType.STACK, "Doll Trap") in game.pteam[0]
#     assert not (EffectType.STACK, "Doll Trap") in game.pteam[1]
#     assert not (EffectType.STACK, "Doll Trap") in game.pteam[2]
    
#     assert game.eteam[1].get_effect(EffectType.STACK, "Doll Trap").mag == 3
    
    
# def test_detonate(frenda_test_game:TestGame):
#     game=frenda_test_game
    
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
#     game.player_action_pass(0, 1, [3])
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [0])
    
#     game.enemy_action(0, 1, [3])
    
#     assert not (EffectType.STACK, "Doll Trap") in game.pteam[0]
#     assert (EffectType.STACK, "Doll Trap") in game.eteam[0]
#     assert game.eteam[0].get_effect(EffectType.STACK, "Doll Trap").mag == 2
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [1])
#     game.player_action(0, 0, [2])
    
#     game.enemy_action(1, 2, [3, 4, 5])

#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [2])

#     game.player_action(0, 2, [0, 1, 2, 3, 4, 5])

#     assert game.eteam[0].hp == 0
#     assert game.eteam[1].hp == 40
#     assert game.pteam[0].hp == 45
#     assert game.pteam[2].hp == 60

# #endregion

# #region Naruha Tests

# def test_rabbit_suit_lockout(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     assert game.quick_target(0, 0) == 0
#     assert game.quick_target(0, 3) == 0
    
#     game.player_action(0, 1, [0])
    
#     assert game.quick_target(0, 0) == 3
#     assert game.quick_target(0, 3) == 1
    
    
# def test_bunny_assault(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     game.player_action_pass(0, 1, [0])
    
#     game.player_action_pass(0, 0, [3])
#     game.pass_turn()
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 55
#     assert game.pteam[0].get_dest_def_total() == 120
    
#     game.player_action(0, 0, [3])
    
#     game.enemy_action(0, 0, [3])
    
#     assert not (EffectType.CONT_DMG, "Bunny Assault") in game.pteam[0]
#     assert game.pteam[0].get_dest_def_total() == 120
    

# def test_enraged_blow(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     game.player_action_pass(0, 1, [0])
    
#     game.player_action(0, 1, [4])
    
#     assert game.eteam[1].hp == 60
#     assert game.eteam[1].is_stunned()
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].get_dest_def_total() == 20
    
# def test_umbrella(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     game.player_action_pass(0, 1, [0])
#     game.pteam[0].get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").alter_dest_def(-90)
    
#     game.player_action(0, 2, [3])
#     assert game.eteam[0].hp == 75
    
#     game.enemy_action(0, 1, [3])
#     assert not (EffectType.DEST_DEF, "Perfect Paper - Rampage Suit") in game.pteam[0]
    
#     game.player_action(0, 2, [3])
#     assert game.eteam[0].hp == 60
    
# def test_rabbit_guard(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     game.player_action_pass(0, 1, [0])
#     game.player_action_pass(0, 3, [0])
    
#     game.pteam[0].get_dest_def_total() == 125
    
    
# def test_rabbit_suit_failure(naruha_test_game:TestGame):
#     game=naruha_test_game
    
#     game.player_action(0, 1, [0])
    
#     game.pteam[0].get_effect(EffectType.DEST_DEF, "Perfect Paper - Rampage Suit").alter_dest_def(-90)
    
#     game.enemy_action(0, 1, [3])
    
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 0) == 0
#     assert game.quick_target(0, 3) == 0

# #endregion

# #region Accelerator Tests

# def test_plasma_bomb_immunity(accelerator_test_game:TestGame):
#     game=accelerator_test_game
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     game.queue_enemy_action(1, 1, [3])
#     game.queue_enemy_action(0, 0, [3])
#     game.execute_enemy_turn()
#     assert game.pteam[0].is_stunned()
#     assert game.pteam[0].hp == 85
#     assert not (EffectType.CONT_AFF_DMG, "Shadow Neck Bind") in game.pteam[0]
    

# def test_vector_reflection(accelerator_test_game:TestGame):
#     game=accelerator_test_game
    
#     game.player_action(0, 2, [0])
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 100
#     assert game.eteam[0].hp == 80
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[2].hp == 80
#     assert game.eteam[2].is_stunned()

# #endregion

# #region Tsunayoshi Tests

# def test_zero_point_breakthrough(tsuna_test_game:TestGame):
#     game=tsuna_test_game
    
#     game.player_action(0, 1, [0])
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].hp == 100
#     assert game.eteam[0].is_stunned()
    
#     game.player_action(0, 0, [3, 4, 5])
    
#     assert game.eteam[0].hp == 65
#     assert game.eteam[1].hp == 75

# def test_burning_axle(tsuna_test_game:TestGame):
#     game=tsuna_test_game
    
#     game.queue_action(0, 2, [3])
#     game.queue_action(1, 0, [3])
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 35
    
#     assert game.eteam[0].is_stunned()
    
# #endregion

# #region Yamamoto Tests

# def test_shinotsuku_duration_refresh(yamamoto_test_game:TestGame):
#     game=yamamoto_test_game
    
#     game.player_action_pass(0, 0, [3])
#     assert game.eteam[0].get_effect(EffectType.ALL_BOOST, "Shinotsuku Ame").duration == 4
    
#     game.pass_turn()
#     assert game.eteam[0].get_effect(EffectType.ALL_BOOST, "Shinotsuku Ame").duration == 2
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].get_effect(EffectType.ALL_BOOST, "Shinotsuku Ame").duration == 5
#     assert len(game.eteam[0].source.current_effects) == 1
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Asari Ugetsu").mag == 2

# def test_utsuhi_ame(yamamoto_test_game:TestGame):
#     game=yamamoto_test_game
    
#     game.player_action_pass(0, 1, [3])
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 80
#     assert game.pteam[0].get_effect(EffectType.STACK, "Asari Ugetsu").mag == 1
    
#     game.player_action(0, 1, [3])
#     game.enemy_action(0, 1, [3])
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 40
#     assert game.pteam[0].get_effect(EffectType.STACK, "Asari Ugetsu").mag == 4
    
# def test_scontro_di_rondine(yamamoto_test_game:TestGame):
#     game=yamamoto_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.pteam[0].get_effect(EffectType.STACK, "Asari Ugetsu").mag = 10
#     game.player_action_pass(0, 2, [0])
    
#     assert game.pteam[0].get_effect(EffectType.ALL_DR, "Asari Ugetsu").duration == 19
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 40
    
#     game.pass_turn()
#     game.pass_turn()
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 20
    
    
# def test_beccata_di_rondine(yamamoto_test_game:TestGame):
#     game=yamamoto_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.pteam[0].get_effect(EffectType.STACK, "Asari Ugetsu").mag = 10
#     game.player_action_pass(0, 2, [0])
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.player_action_pass(0, 1, [3, 4, 5])
    
#     assert game.eteam[0].hp == 55
#     assert game.eteam[1].hp == 85
#     assert game.eteam[2].hp == 85
#     assert game.eteam[0].check_damage_drain() == 10
#     assert game.eteam[1].check_damage_drain() == 10
#     assert game.eteam[2].check_damage_drain() == 10
    
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 45
#     assert game.eteam[1].hp == 75
#     assert game.eteam[2].hp == 75
#     assert game.eteam[0].check_damage_drain() == 5
#     assert game.eteam[1].check_damage_drain() == 5
#     assert game.eteam[2].check_damage_drain() == 5
    

# #endregion

# #region Gokudera Tests

# def test_sistema(gokudera_test_game:TestGame):
#     game=gokudera_test_game
    
#     assert (EffectType.STACK, "Sistema C.A.I.") in game.pteam[0]
    
#     game.player_action_pass(0, 0, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 90
        
#     game.player_action(0, 0, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 80
        
#     assert game.eteam[0].is_stunned()
    
#     game.execute_enemy_turn()
    
#     game.pteam[0].source.set_hp(85)
    
#     game.player_action(0, 0, [3, 4, 5])
    
#     assert game.eteam[0].hp == 60
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[1].hp == 70
#     assert game.pteam[0].hp == 100
    
#     game.execute_enemy_turn()
    
#     game.pteam[0].source.set_hp(75)
#     game.pteam[1].source.set_hp(75)
#     game.pteam[2].source.set_hp(75)
    
#     game.player_action(0, 0, [0, 1, 2, 3, 4, 5])
    
#     assert game.eteam[0].hp == 35
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[1].hp == 45
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[2].hp == 45
#     assert game.eteam[2].is_stunned()
    
#     game.pteam[0].hp == 95
#     game.pteam[1].hp == 95
#     game.pteam[2].hp == 95
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 1
    
    

# def test_skull_ring(gokudera_test_game:TestGame):
#     game=gokudera_test_game
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 1
    
#     game.player_action_pass(0, 1, [0])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 2
    
#     game.player_action_pass(0, 1, [0])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 3
    
#     game.player_action_pass(0, 1, [0])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 4
    
#     game.player_action_pass(0, 1, [0])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 1
    
# def test_vongola_bow(gokudera_test_game:TestGame):
#     game=gokudera_test_game
    
#     game.player_action_pass(0, 2, [0])
    
#     game.player_action_pass(0, 0, [3, 4, 5])
#     game.player_action_pass(0, 0, [3, 4, 5])
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Sistema C.A.I.").mag == 1
    
    
# #endregion

# #region Ryohei Tests
    
# def test_maximum_cannon(ryohei_test_game:TestGame):
#     game=ryohei_test_game
    
#     game.player_action_pass(0, 3, [0])
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 80
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 2, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 65
#     assert game.pteam[0].get_effect(EffectType.STACK, "Maximum Cannon").mag == 1
    
#     assert game.pteam[0].source.current_abilities[0].total_cost == 2
    
#     game.player_action(0, 0, [3])
    
#     assert game.eteam[0].hp == 45
    
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
#     assert not (EffectType.STACK, "Maximum Cannon") in game.pteam[0]
    
    
# def test_kangaryu(ryohei_test_game:TestGame):
#     game=ryohei_test_game
    
#     game.pteam[0].source.set_hp(30)
    
#     game.player_action_pass(0, 3, [0])
#     game.player_action(0, 1, [0])
    
#     assert game.pteam[0].hp == 45
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 2, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 10
#     assert game.pteam[0].get_effect(EffectType.STACK, "Kangaryu").mag == 1
    
#     assert game.pteam[0].source.current_abilities[1].total_cost == 2
    
#     game.player_action(0, 1, [0])
    
#     assert game.pteam[0].hp == 45
    
#     assert game.pteam[0].source.current_abilities[1].total_cost == 1
    
#     assert not (EffectType.STACK, "Kangaryu") in game.pteam[0]
    
    
# def test_headgear(ryohei_test_game:TestGame):
#     game=ryohei_test_game
    
#     game.player_action(0, 3, [0])
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 2, [3])
#     game.execute_enemy_turn()
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(1, 2, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 25
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Kangaryu").mag == 2
    
#     assert game.pteam[0].source.current_abilities[1].total_cost == 3
    
#     game.player_action_pass(0, 2, [0])
    
#     assert game.pteam[0].source.current_abilities[1].total_cost == 1
    
#     game.player_action(0, 1, [0])
    
#     assert game.pteam[0].hp == 80
    
#     assert game.pteam[0].get_effect(EffectType.STACK, "Kangaryu").mag == 2
    
    
    
# #endregion

# #region Lambo Tests

# def test_gyudon_bazooka_dropoff(lambo_test_game:TestGame):
#     game=lambo_test_game
    
#     game.player_action_pass(0, 2, [0, 1, 2, 3, 4, 5])
    
#     for ally in game.pteam:
#         assert (EffectType.ALL_DR, "Summon Gyudon") in ally
        
#     for enemy in game.eteam:
#         assert (EffectType.CONT_DMG, "Summon Gyudon") in enemy
    
#     game.player_action_pass(0, 0, [0])
    
#     for ally in game.pteam:
#         assert not (EffectType.ALL_DR, "Summon Gyudon") in ally
        
#     for enemy in game.eteam:
#         assert not (EffectType.CONT_DMG, "Summon Gyudon") in enemy
    

# def test_gyudon_death_dropoff(lambo_test_game:TestGame):
#     game=lambo_test_game
    
#     game.player_action(0, 2, [0, 1, 2, 3, 4, 5])
    
#     for ally in game.pteam:
#         assert (EffectType.ALL_DR, "Summon Gyudon") in ally
        
#     for enemy in game.eteam:
#         assert (EffectType.CONT_DMG, "Summon Gyudon") in enemy
        
#     game.pteam[0].source.set_hp(5)
    
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].source.dead
    
#     for ally in game.pteam:
#         assert not (EffectType.ALL_DR, "Summon Gyudon") in ally
        
#     for enemy in game.eteam:
#         assert not (EffectType.CONT_DMG, "Summon Gyudon") in enemy
    
    
    
# def test_conductivity(lambo_test_game:TestGame):
#     game=lambo_test_game
    
#     game.player_action(0, 1, [1, 2])
    
#     game.enemy_action(0, 1, [4])
    
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(2, 0, [5])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 70
#     assert game.pteam[1].hp == 100
#     assert game.pteam[2].hp == 75
    
    
# def test_ten_year_bazooka_one(lambo_test_game:TestGame):
#     game=lambo_test_game
    
#     game.player_action(0, 0, [0])
    
#     assert (EffectType.PROF_SWAP, "Ten-Year Bazooka") in game.pteam[0]
#     assert game.pteam[0].source.current_abilities[1].name == "Thunder, Set, Charge!"
    
    
# def test_ten_year_bazooka_two(lambo_test_game:TestGame):
#     game=lambo_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action(0, 0, [0])
    
#     assert (EffectType.PROF_SWAP, "Ten-Year Bazooka") in game.pteam[0]
#     assert game.pteam[0].source.current_abilities[1].name == "Elettrico Cornata"

# #endregion

# #region Hibari Tests

# def test_porcospino(hibari_test_game: TestGame):
#     game=hibari_test_game
    
#     game.player_action(0, 2, [3, 4, 5])
    
#     assert game.quick_target(0, 1) == 0
    
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(2, 0, [5])
#     game.execute_enemy_turn()
    
#     assert game.eteam[0].hp == 90
#     assert game.eteam[2].hp == 90
    
# def test_handcuffs(hibari_test_game: TestGame):
#     game=hibari_test_game
    
#     game.player_action(0, 1, [4])
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[1].hp == 85
#     assert game.quick_target(0, 2) == 0
    

# #endregion

# #region Chrome Tests

# def test_you_are_needed_lockout(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 2) == 0
#     assert game.quick_target(0, 3) == 0
    
#     game.player_action(0, 0, [0])
    
    
#     assert game.quick_target(0, 1) == 3
#     assert game.quick_target(0, 2) == 3
#     assert game.quick_target(0, 3) == 1
    

# def test_illusory_breakdown(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     game.player_action_pass(0, 0, [0])
    
#     game.player_action(0, 1, [3])
#     game.enemy_action(2, 0, [3])
    
#     assert game.pteam[0].hp == 95
#     assert not (EffectType.MARK, "Illusory Breakdown") in game.pteam[0]
    
#     game.player_action_pass(0, 1, [3])
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 75
#     assert game.eteam[0].is_stunned()
    
# def test_mental_immolation(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action(0, 2, [3])
#     game.enemy_action(2, 0, [3])
    
#     assert game.pteam[0].hp == 90
#     assert not (EffectType.MARK, "Mental Immolation") in game.pteam[0]
    
#     game.player_action_pass(0, 2, [3])
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 80
#     assert game.eteam[0].source.energy_contribution == 0
    
# def test_mukuro_switch(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     game.player_action(0, 0, [0])
    
#     game.enemy_action(2, 0, [3])
    
#     assert (EffectType.PROF_SWAP, "You Are Needed") in game.pteam[0]
#     assert game.pteam[0].source.current_abilities[0].name == "Trident Combat"
#     assert game.pteam[0].source.current_abilities[1].name == "Illusory World Destruction"
#     assert game.pteam[0].source.current_abilities[2].name == "Mental Annihilation"
#     assert game.pteam[0].source.current_abilities[3].name == "Trident Deflection"
    
    
    
# def test_illusory_world_destruction(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     game.player_action(0, 0, [0])
    
#     game.enemy_action(2, 0, [3])
    
#     game.player_action(0, 1, [0])
#     assert game.pteam[0].get_dest_def_total() == 30
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert not (EffectType.UNIQUE, "Illusory World Destruction") in game.pteam[0]
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].get_dest_def_total() == 30
    
#     game.execute_turn()
    
#     for enemy in game.eteam:
#         assert enemy.hp == 75
#         assert enemy.is_stunned()
    
    
# def test_mental_annihilation(chrome_test_game:TestGame):
#     game=chrome_test_game
    
#     game.player_action(0, 0, [0])
    
#     game.enemy_action(2, 0, [3])
    
#     game.player_action(0, 2, [3])
#     assert game.pteam[0].get_dest_def_total() == 30
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert not (EffectType.UNIQUE, "Mental Annihilation") in game.pteam[0]
    
#     game.player_action(0, 2, [3])
#     assert game.pteam[0].get_dest_def_total() == 30
    
#     game.enemy_action(0, 3, [0])
    
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 65

# #endregion

# #region Tatsumi Tests

# def test_neuntote_lockout(tatsumi_test_game:TestGame):
#     game=tatsumi_test_game
    
#     assert game.quick_target(0, 2) == 0
    
#     game.player_action(0, 1, [0])
    
#     assert game.quick_target(0, 2) == 3

# def test_killing_strike(tatsumi_test_game:TestGame):
#     game=tatsumi_test_game
    
#     game.player_action_pass(1, 0, [3])
    
#     assert game.eteam[0].hp == 85
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 50
    
#     game.queue_action(2, 1, [4])
#     game.queue_action(0, 0, [4])
#     game.execute_turn()
    
#     assert game.eteam[1].hp == 65
    
#     game.player_action(0, 0, [4])
    
#     assert game.eteam[1].hp == 20
    
# def test_neuntote(tatsumi_test_game:TestGame):
#     game=tatsumi_test_game
    
#     game.eteam[0].source.set_hp(185)
    
#     game.player_action_pass(0, 1, [0])
    
#     game.player_action_pass(0, 2, [3])
#     game.player_action_pass(0, 2, [3])
#     game.player_action_pass(0, 2, [3])
    
#     assert game.eteam[0].hp == 10

# #endregion

# #region Akame Tests

# def test_one_cut_lockout(akame_test_game:TestGame):
#     game=akame_test_game
    
#     assert game.quick_target(0, 1) == 0
    
#     game.player_action(0, 0, [3])
    
#     assert game.quick_target(0, 1) == 1
    

# def test_one_cut_killing(akame_test_game:TestGame):
#     game=akame_test_game
    
#     game.eteam[0].source.set_hp(175)
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 1, [3])
    
#     assert game.eteam[0].hp == 75
    
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 0
    
    
# def test_little_war_horn(akame_test_game:TestGame):
#     game=akame_test_game
    
#     assert game.quick_target(0, 1) == 0
    
#     game.player_action(0, 2, [0])
    
#     game.enemy_action(0, 3, [0])
    
#     assert game.quick_target(0, 1) == 3

# #endregion

# #region Leone Tests

# def test_lionel_lockout(leone_test_game:TestGame):
#     game=leone_test_game
    
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 2) == 0
#     assert game.quick_target(0, 3) == 0
    
#     game.player_action_pass(0, 0, [0])
    
#     assert game.quick_target(0, 1) == 4
#     assert game.quick_target(0, 2) == 3
#     assert game.quick_target(0, 3) == 1
#     assert game.pteam[0].hp == 110

# def test_lion_fist(leone_test_game:TestGame):
#     game=leone_test_game
    
#     game.player_action_pass(0, 0, [0])
    
#     game.player_action(0, 2, [3])
#     assert game.eteam[0].hp == 65
#     assert game.pteam[0].hp == 130
    
# def test_instinctual_dodge_healing(leone_test_game:TestGame):
#     game=leone_test_game
    
#     game.player_action_pass(0, 0, [0])
    
#     game.player_action(0, 3, [0])
#     assert game.pteam[0].check_invuln()
#     assert game.pteam[0].hp == 130
    
# def test_self_beast_instinct(leone_test_game:TestGame):
#     game=leone_test_game
    
#     game.eteam[0].source.set_hp(35)
    
#     game.player_action(0, 0, [0])
#     game.enemy_action(0, 2, [0])
    
#     game.player_action(0, 1, [0])
#     game.enemy_action(0, 0, [3])
    
#     assert not game.pteam[0].is_stunned()
    
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].source.dead
#     assert game.pteam[0].get_effect(EffectType.STUN_IMMUNE, "Beast Instinct").duration == 4
    
    
# def test_enemy_beast_instinct(leone_test_game:TestGame):
#     game=leone_test_game
    
#     game.eteam[0].source.set_hp(55)
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action(0, 1, [3])
#     game.enemy_action(0, 3, [0])
    
#     game.player_action(0, 2, [3])
    
#     assert game.eteam[0].source.dead
#     assert game.pteam[0].hp == 160

# #endregion

# #region Mine Tests

# def test_pumpkin(mine_test_game:TestGame):
#     game=mine_test_game
#     game.pteam[0].source.set_hp(130)
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 75
    
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].hp == 115
    
#     game.player_action(0, 0, [4])
#     assert game.eteam[1].hp == 65
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.queue_enemy_action(1, 1, [3])
#     game.execute_enemy_turn()
#     assert game.pteam[0].hp == 55
    
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
    
# def test_cutdown_shot(mine_test_game:TestGame):
#     game=mine_test_game
    
#     for enemy in game.eteam:
#         enemy.source.set_hp(110)
    
#     game.player_action(0, 1, [3, 4, 5])
#     assert game.eteam[0].hp == 85
#     assert game.eteam[1].hp == 85
#     assert not game.eteam[1].is_stunned()
    
#     game.enemy_action(0, 1, [3])
#     assert game.pteam[0].hp == 85
    
#     game.player_action(0, 1, [3, 4, 5])
#     assert game.eteam[0].hp == 60
#     assert game.eteam[1].hp == 60
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[2].is_stunned()
    
#     game.execute_enemy_turn()
    
#     game.execute_turn()
    
#     game.queue_enemy_action(0, 1, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 45
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.is_stunned()
#         assert enemy.hp == 10
    
    
# def test_scouter(mine_test_game:TestGame):
#     game=mine_test_game
    
#     game.player_action(0, 2, [0])
#     game.enemy_action(0, 3, [0])
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 60
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     assert game.eteam[0].hp == 30
#     assert game.eteam[1].hp == 70
#     assert game.eteam[2].hp == 70
    

# #endregion

# #region Raba Tests

# def test_cross_tail_strike(raba_test_game:TestGame):
#     game=raba_test_game
    
#     game.player_action_pass(0, 0, [3])
#     assert game.eteam[0].hp == 85
#     assert game.pteam[0].source.current_abilities[0].total_cost == 0
#     assert (EffectType.MARK, "Cross-Tail Strike") in game.eteam[0]
    
#     game.player_action_pass(0, 0, [3])
#     assert game.eteam[0].hp == 70
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
#     assert (EffectType.MARK, "Cross-Tail Strike") in game.eteam[0]
    
#     game.player_action_pass(0, 0, [4])
#     game.player_action_pass(0, 0, [5])
    
#     assert game.eteam[1].hp == 85
#     assert game.eteam[2].hp == 85
    
#     for enemy in game.eteam:
#         assert (EffectType.MARK, "Cross-Tail Strike") in enemy
        
#     game.player_action_pass(0, 0, [4])
    
#     assert game.eteam[0].hp == 50
#     assert game.eteam[1].hp == 65
#     assert game.eteam[2].hp == 65
    
#     for enemy in game.eteam:
#         assert not (EffectType.MARK, "Cross-Tail Strike") in enemy
    
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
    
    

# def test_wire_shield(raba_test_game:TestGame):
#     game=raba_test_game
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].get_dest_def_total() == 15
#     assert game.pteam[0].source.current_abilities[1].total_cost == 0
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].get_dest_def_total() == 30
#     assert game.pteam[0].source.current_abilities[0].total_cost == 1
    
#     game.player_action_pass(0, 1, [1])
#     assert game.pteam[1].get_dest_def_total() == 15
#     assert game.pteam[0].source.current_abilities[1].total_cost == 0
#     game.player_action_pass(0, 1, [2])
    
#     game.player_action(0, 1, [0])
#     for ally in game.pteam:
#         assert ally.check_invuln()
#         assert not (EffectType.MARK, "Wire Shield") in ally
    
#     assert game.pteam[0].source.current_abilities[1].total_cost == 1
    
    
# def test_heartseeker_thrust(raba_test_game:TestGame):
#     game=raba_test_game
    
#     game.player_action_pass(0, 2, [3])
#     assert game.eteam[0].hp == 70
    
#     game.player_action_pass(0, 0, [4])
#     assert game.eteam[1].hp == 85
    
#     game.player_action(0, 2, [4])
#     assert game.eteam[1].hp == 55
#     assert game.eteam[1].is_stunned()
#     game.execute_enemy_turn()
    
#     game.player_action_pass(0, 1, [0])
#     game.player_action_pass(0, 2, [5])
#     assert game.eteam[2].hp == 70
#     game.player_action(0, 2, [4])
#     assert game.eteam[1].hp == 25
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[2].hp == 55
#     game.execute_enemy_turn()
#     game.pass_turn()
#     assert game.eteam[1].hp == 10
    

# #endregion

# #region Sheele Tests

# def test_extase(sheele_test_game:TestGame):
#     game=sheele_test_game
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 65
#     game.enemy_action(2, 0, [2])
#     game.player_action(0, 0, [5])
#     assert game.eteam[2].hp == 75
    
# def test_savior_strike(sheele_test_game:TestGame):
#     game=sheele_test_game
    
#     game.execute_turn()
#     game.enemy_action(0, 0, [4])
#     assert game.pteam[1].hp == 85
#     assert (EffectType.CONT_UNIQUE, "Relentless Assault") in game.pteam[1]
#     assert (EffectType.CONT_USE, "Relentless Assault") in game.eteam[0]
    
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 75
#     assert not (EffectType.CONT_UNIQUE, "Relentless Assault") in game.pteam[1]
#     assert not (EffectType.CONT_USE, "Relentless Assault") in game.eteam[0]
    
    
# def test_blinding_light(sheele_test_game:TestGame):
#     game=sheele_test_game
    
#     game.execute_turn()
#     game.enemy_action(1, 3, [1])
#     assert game.eteam[1].check_for_dmg_reduction() == 15
#     game.player_action_pass(0, 2, [4])
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[1].check_for_dmg_reduction() == 0
#     game.player_action(0, 0, [4])
#     assert game.eteam[1].hp == 55

# #endregion

# #region Chelsea Tests

# def test_mortal_wound(chelsea_test_game:TestGame):
#     game=chelsea_test_game
    
#     assert game.quick_target(0, 0) == 3
    
#     game.player_action(0, 0, [4])
#     assert game.eteam[1].hp == 85
#     assert game.quick_target(0, 0) == 2
    
#     game.enemy_action(1, 0, [3, 4, 5])
    
#     assert game.pteam[0].hp == 80
#     assert game.pteam[1].hp == 90
#     assert game.pteam[2].hp == 90
    
#     game.pass_turn()
#     assert game.eteam[1].hp == 70
    
# def test_fight_in_shadows(chelsea_test_game:TestGame):
#     game=chelsea_test_game
    
#     game.player_action(0, 1, [4])
#     game.enemy_action(0, 2, [1])
#     assert not (EffectType.COUNTER_RECEIVE, "Minion - Tama") in game.eteam[1]
#     assert game.eteam[0].is_stunned()
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 55
#     game.execute_enemy_turn()
#     game.pass_turn()
#     assert game.eteam[0].hp == 10
    
    
# def test_smoke_bomb(chelsea_test_game:TestGame):
#     game=chelsea_test_game
    
#     game.execute_turn()
#     game.enemy_action(0, 2, [2])
#     game.player_action(0, 2, [0, 1, 2, 3, 4, 5])
    
#     for ally in game.pteam:
#         assert ally.get_dest_def_total() == 10
        
#     assert game.eteam[2].hp == 85

# #endregion

# #region Seryu Tests

# def test_self_destruct_switch(seryu_test_game:TestGame):
#     game=seryu_test_game
#     game.pteam[0].source.set_hp(60)
    
#     assert game.pteam[0].source.current_abilities[0].name == "Body Modification - Arm Gun"
    
#     game.execute_turn()
#     game.enemy_action(0, 1, [3])
    
#     assert game.pteam[0].source.current_abilities[0].name == "Body Modification - Self Destruct"
    
    
# def test_self_destruct_absolute(seryu_test_game:TestGame):
#     game=seryu_test_game
#     game.pteam[0].source.set_hp(60)
    
#     game.execute_turn()
#     game.enemy_action(0, 1, [3])
    
#     game.queue_action(1, 2, [0])
#     game.queue_action(0, 0, [3, 4, 5])
#     game.execute_turn()
    
#     assert game.pteam[0].source.dead
#     for enemy in game.eteam:
#         assert enemy.hp == 70
    
# def test_raging_koro_switch(seryu_test_game:TestGame):
#     game=seryu_test_game
    
#     game.player_action_pass(0, 1, [3])
#     assert game.eteam[0].hp == 80
    
#     assert game.pteam[0].source.current_abilities[1].name == "Insatiable Justice"
    
#     game.pass_turn()
    
#     assert game.eteam[0].hp == 60
    
# def test_insatiable_justice(seryu_test_game:TestGame):
#     game=seryu_test_game
    
#     game.eteam[0].source.set_hp(70)
#     game.player_action(0, 1, [3])
#     game.enemy_action(1, 2, [0])
    
#     assert game.quick_target(0, 1) == 1
    
#     game.player_action(0, 1, [3])
    
#     assert game.eteam[0].hp == 0
#     assert game.eteam[0].source.dead == True
    
    
    
    

# #endregion

# #region Kurome Tests

# def test_yatsufusa_ally_kill(kurome_test_game:TestGame):
#     game=kurome_test_game
    
#     game.pteam[1].source.set_hp(10)
#     game.player_action(0, 1, [1])
#     game.execute_enemy_turn()
    
#     logging.debug("%s", game.pteam[1])
#     assert not game.pteam[1].source.dead
#     assert (EffectType.UNIQUE, "Yatsufusa") in game.pteam[1]
#     assert game.pteam[1].hp == 40
#     assert game.pteam[1].source.current_abilities[0].total_cost == 2

# def test_yatsufusa_enemy_kill(kurome_test_game:TestGame):
#     game=kurome_test_game
    
#     game.eteam[0].source.set_hp(10)
#     game.player_action_pass(0, 1, [3])
#     game.player_action(0, 0, [4, 5])
    
#     assert game.eteam[1].hp == 70
#     assert game.eteam[2].hp == 70
    
# def test_doping_rampage(kurome_test_game:TestGame):
#     game=kurome_test_game
    
#     game.pteam[0].source.set_hp(15)
#     game.player_action(0, 2, [0])
#     game.enemy_action(2, 0, [3])
#     assert game.pteam[0].hp == 1
#     assert not game.pteam[0].source.dead
    
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 65
    
#     assert game.pteam[0].source.dead

# #endregion

# #region Esdeath Tests

# def test_demon_extract_lockout(esdeath_test_game:TestGame):
#     game=esdeath_test_game
    
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 2) == 0
#     assert game.quick_target(0, 3) == 1
    
#     game.player_action(0, 0, [0])
    
#     assert game.quick_target(0, 0) == 6
#     assert game.quick_target(0, 1) == 3
#     assert game.quick_target(0, 2) == 3
#     assert game.quick_target(0, 3) == 1
    
# def test_frozen_castle_targeting(esdeath_test_game:TestGame):
#     game=esdeath_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action(0, 1, [3, 4])
    
#     assert game.quick_target(3, 0) == 1
#     assert game.quick_target(5, 0) == 3
#     assert game.quick_target(2, 2) == 2
#     assert game.quick_target(1, 0) == 1
    
#     assert game.pteam[0].source.current_abilities[2].target_type == Target.MULTI_ENEMY
    
# def test_weiss_schnabel(esdeath_test_game:TestGame):
#     game=esdeath_test_game
    
#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 2, [3])
#     assert game.eteam[0].hp == 90
#     assert game.pteam[0].source.current_abilities[2].total_cost == 1
#     assert game.pteam[0].source.current_abilities[2].all_costs[1] == 0
    
#     game.player_action_pass(0, 2, [4])
#     assert game.eteam[0].hp == 80
#     assert game.eteam[1].hp == 85
#     game.pass_turn()
#     assert game.eteam[0].hp == 70
    
    
#     assert game.pteam[0].source.current_abilities[2].total_cost == 2
#     assert game.pteam[0].source.current_abilities[2].all_costs[1] == 1
    
#     game.player_action_pass(0, 1, [3, 4, 5])
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     assert game.eteam[0].hp == 60
#     assert game.eteam[1].hp == 75
#     assert game.eteam[2].hp == 90
    
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     assert game.eteam[0].hp == 35
#     assert game.eteam[1].hp == 50
#     assert game.eteam[2].hp == 65
    
    
    
# def test_mahapadma(esdeath_test_game:TestGame):
#     game=esdeath_test_game
    
#     game.player_action_pass(0, 0, [0])
#     assert game.pteam[0].source.current_abilities[0].name == "Mahapadma"
    
#     game.player_action_pass(0, 0, [0, 1, 2, 3, 4, 5])
    
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[1].is_stunned()
#     assert game.eteam[2].is_stunned()
#     assert game.pteam[1].is_stunned()
#     assert game.pteam[2].is_stunned()
    
#     game.pass_turn()
    
#     assert not game.eteam[0].is_stunned()
#     assert not game.eteam[1].is_stunned()
#     assert not game.eteam[2].is_stunned()
#     assert game.pteam[1].is_stunned()
#     assert game.pteam[2].is_stunned()
    
#     game.execute_turn()
#     assert not game.pteam[1].is_stunned()
#     assert not game.pteam[2].is_stunned()
#     assert game.pteam[0].is_stunned()
    

# #endregion

# #region Snow White Tests

# def test_hear_distress_enemy(snowwhite_test_game:TestGame):
#     game=snowwhite_test_game
    
#     game.player_action(0, 1, [3])
#     game.enemy_action(0, 1, [5])
#     assert game.pteam[2].hp == 100
#     assert game.eteam[0].source.energy_contribution == 0
    
#     game.player_action(0, 1, [4])
#     game.enemy_action(1, 0, [4])
#     assert game.pteam[1].hp == 50
#     assert game.eteam[1].source.energy_contribution == 1

# def test_hear_distress_ally(snowwhite_test_game:TestGame):
#     game=snowwhite_test_game
    
#     game.player_action(0, 1, [1])
#     game.queue_enemy_action(0, 1, [4])
#     game.queue_enemy_action(2, 0, [4])
#     game.execute_enemy_turn()
    
#     assert game.pteam[1].hp == 75
#     assert game.pteam[1].source.energy_contribution == 3
    
# def test_rabbits_foot(snowwhite_test_game:TestGame):
#     game=snowwhite_test_game
    
#     game.pteam[1].source.set_hp(10)
    
#     game.player_action(0, 2, [1])
#     game.enemy_action(2, 0, [4])
    
#     assert game.pteam[1].hp == 35

# #endregion

# #region La Pucelle Tests

# def test_magic_sword(lapucelle_test_game:TestGame):
#     game=lapucelle_test_game
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].source.current_abilities[0].total_cost == 2
#     assert game.pteam[0].check_for_cooldown_mod(game.pteam[0].source.current_abilities[0]) == 1
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].source.current_abilities[0].total_cost == 3
#     assert game.pteam[0].check_for_cooldown_mod(game.pteam[0].source.current_abilities[0]) == 2
#     game.player_action_pass(0, 0, [3])
#     assert game.eteam[0].hp == 40
    
# def test_ideal_strike(lapucelle_test_game:TestGame):
#     game=lapucelle_test_game
    
#     assert game.quick_target(0, 2) == 0
    
#     game.pteam[0].source.set_hp(45)
    
#     game.enemy_action(0, 2, [0])
#     game.player_action(0, 2, [3])
#     assert game.pteam[0].hp == 45
#     assert game.eteam[0].hp == 60
    

# #endregion

# #region Ripple Tests

# def test_shuriken_throw(ripple_test_game:TestGame):
#     game=ripple_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 1, [4])
    
#     assert game.eteam[0].hp == 80
#     assert game.eteam[1].hp == 85
    
#     game.player_action_pass(0, 0, [4])
#     game.player_action_pass(0, 1, [4])
    
#     assert game.eteam[0].hp == 60
#     assert game.eteam[1].hp == 65
    
#     game.player_action_pass(0, 0, [5])
#     game.player_action_pass(0, 1, [5])
    
#     assert game.eteam[0].hp == 40
#     assert game.eteam[1].hp == 45
#     assert game.eteam[2].hp == 80
    
# def test_countless_stars(ripple_test_game:TestGame):
#     game=ripple_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 2, [3, 4, 5])
#     for enemy in game.eteam:
#         assert enemy.hp == 95
        
#     game.player_action_pass(0, 1, [4])
    
#     assert game.eteam[1].hp == 65
#     assert game.eteam[0].hp == 60
    

# #endregion

# #region Nemurin Tests

# def test_nap_lockout(nemurin_test_game:TestGame):
#     game=nemurin_test_game
    
#     assert game.quick_target(0, 1) == 0
#     assert game.quick_target(0, 2) == 0
#     assert game.quick_target(0, 3) == 0
    
#     game.player_action(0, 0, [0])
    
#     assert game.quick_target(0, 1) == 3
#     assert game.quick_target(0, 2) == 2
#     assert game.quick_target(0, 3) == 1

# #endregion

# #region Ruler Tests

# def test_in_the_name_of_ruler(ruler_test_game:TestGame):
#     game=ruler_test_game
    
#     game.player_action(0, 0, [3])
    
#     game.enemy_action(1, 0, [3])
    
#     assert not game.pteam[0].is_stunned()
#     assert not game.eteam[0].is_stunned()
    
#     game.execute_turn()
    
#     game.enemy_action(0, 0, [3])
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].is_stunned()
#     game.execute_enemy_turn()
#     assert game.eteam[0].is_stunned()

# def test_minael_yunael(ruler_test_game:TestGame):
#     game=ruler_test_game
    
#     game.player_action_pass(0, 1, [0])
#     assert game.pteam[0].get_dest_def_total() == 10
    
#     game.player_action(0, 1, [3])
#     assert game.eteam[0].hp == 85
    
# def test_tama(ruler_test_game:TestGame):
#     game=ruler_test_game
    
#     game.player_action(0, 2, [2])
#     game.enemy_action(1, 0, [5])
    
#     assert game.pteam[2].hp == 100
#     assert game.eteam[1].hp == 80


# #endregion

# #region Swim Swim Tests

# def test_dive_defensive(swimswim_test_game:TestGame):
#     game=swimswim_test_game
    
#     game.player_action(0, 1, [0])
#     game.queue_enemy_action(0, 0, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert game.pteam[0].hp == 100
#     assert not game.pteam[0].is_stunned()

# def test_dive_offensive(swimswim_test_game:TestGame):
#     game=swimswim_test_game
    
#     game.player_action(0, 1, [0])
#     game.enemy_action(0, 3, [0])
    
#     assert game.quick_target(0, 0) == 3
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 75
    
# def test_vitality_pills(swimswim_test_game:TestGame):
#     game=swimswim_test_game
    
#     game.player_action(0, 2, [0])
#     game.enemy_action(0, 1, [3])
#     assert game.pteam[0].hp == 95
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].hp == 65

# #endregion

# #region Calamity Mary Tests

# def test_pistol_switch(cmary_test_game:TestGame):
#     game=cmary_test_game
    
#     assert game.pteam[0].source.current_abilities[0].name == "Quickdraw - Pistol"
    
#     game.player_action_pass(0, 0, [3])
    
#     assert game.eteam[0].hp == 85
#     assert game.pteam[0].source.current_abilities[0].name == "Quickdraw - Rifle"
    
# def test_rifle_switch(cmary_test_game:TestGame):
#     game=cmary_test_game
    
#     game.player_action_pass(0, 0, [3])
#     game.player_action_pass(0, 0, [4])
#     assert game.eteam[1].hp == 85
#     assert game.pteam[0].source.current_abilities[0].name == "Quickdraw - Rifle"
#     game.pass_turn()
#     assert game.pteam[0].source.current_abilities[0].name == "Quickdraw - Sniper"
#     assert game.eteam[1].hp == 70
    
# def test_hidden_mine(cmary_test_game:TestGame):
#     game=cmary_test_game
    
#     game.player_action(0, 1, [3])
#     game.enemy_action(0, 1, [3])
#     assert game.eteam[0].hp == 80
    
#     game.player_action(0, 1, [3])
#     game.enemy_action(0, 3, [0])
#     assert game.eteam[0].hp == 80
    
# def test_grenade_toss(cmary_test_game:TestGame):
#     game=cmary_test_game
    
#     game.player_action_pass(0, 2, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 80
        
#     game.player_action_pass(0, 1, [4])
    
#     game.player_action(0, 2, [3, 4, 5])
    
#     assert game.eteam[0].hp == 60
#     assert game.eteam[1].hp == 40
#     assert game.eteam[2].hp == 60
    
    
# #endregion

# #region Cranberry Tests

# def test_illusory_disorientation(cranberry_test_game:TestGame):
#     game=cranberry_test_game
    
#     assert game.pteam[0].source.current_abilities[0].name == "Illusory Disorientation"
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].source.current_abilities[0].total_cost == 2
#     assert game.pteam[0].source.current_abilities[0].name == "Merciless Finish"

# def test_merciless_finish(cranberry_test_game:TestGame):
#     game=cranberry_test_game
    
#     game.player_action(0, 0, [3])
#     assert game.quick_target(0, 0) == 3
    
#     game.enemy_action(0, 1, [4])
#     assert game.pteam[0].source.current_abilities[0].name == "Merciless Finish"
    
#     game.player_action(0, 0, [3])
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[0].hp == 85
    
#     game.execute_enemy_turn()
#     game.execute_turn()
#     assert game.eteam[0].is_stunned()
#     assert game.eteam[0].hp == 70
    
#     game.player_action_pass(0, 0, [3])
#     assert game.quick_target(0, 0) == 3
    
#     game.player_action(0, 0, [4])
#     game.enemy_action(0, 0, [3])
    
#     assert not game.eteam[1].is_stunned()
#     assert not (EffectType.CONT_USE, "Merciless Finish") in game.pteam[0]
    
    
    
# def test_fortissimo(cranberry_test_game:TestGame):
#     game=cranberry_test_game
    
#     game.queue_enemy_action(2, 0, [2])
#     game.queue_enemy_action(0, 3, [0])
#     game.execute_enemy_turn()
    
#     game.player_action(0, 1, [3, 4, 5])
#     assert game.eteam[0].hp == 50
#     assert game.eteam[1].hp == 75
#     assert game.eteam[2].hp == 50
    
    
# def test_mental_radar(cranberry_test_game:TestGame):
#     game=cranberry_test_game
    
    
#     game.enemy_action(0, 2, [1])
#     game.queue_action(0, 2, [0, 1, 2])
#     game.queue_action(1, 0, [4])
#     game.execute_turn()
#     assert game.eteam[1].hp == 85
#     assert game.pteam[1].hp == 100
    
# #endregion

# #region Saitama Tests

# def test_serious_punch(saitama_test_game:TestGame):
#     game=saitama_test_game

#     game.player_action(0, 2, [3])
#     game.queue_enemy_action(0, 0, [3])
#     game.queue_enemy_action(1, 0, [3])
#     game.queue_enemy_action(2, 0, [3])
#     game.execute_enemy_turn()
    
#     assert not game.pteam[0].is_stunned()
#     assert game.pteam[0].hp == 100
    
#     game.execute_turn()
    
#     assert game.eteam[0].hp == 65

# #endregion

# #region Tatsumaki Tests

# def test_gather_power(tatsumaki_test_game:TestGame):
#     game=tatsumaki_test_game
    
#     game.player_action_pass(0, 0, [3, 4, 5])
#     game.pass_turn()
#     for enemy in game.eteam:
#         assert enemy.hp == 80
        
#     game.player_action(0, 1, [0, 1, 2])
#     for ally in game.pteam:
#         assert ally.check_for_dmg_reduction() == 10
        
#     game.player_action_pass(0, 2, [0])
    
#     game.player_action_pass(0, 0, [3, 4, 5])
#     game.pass_turn()
#     for enemy in game.eteam:
#         assert enemy.hp == 50
        
#     game.player_action(0, 1, [0, 1, 2])
#     for ally in game.pteam:
#         assert ally.check_for_dmg_reduction() == 15
    
#     assert game.pteam[0].source.current_abilities[2].cooldown == 3

# def test_arrest_return_assault(tatsumaki_test_game:TestGame):
#     game=tatsumaki_test_game
    
#     game.player_action(0, 1, [0, 1, 2])
#     game.enemy_action(0, 1, [4])
    
#     assert game.pteam[1].hp == 95
    
#     assert game.pteam[0].source.current_abilities[1].name == "Return Assault"
    
#     game.player_action_pass(0, 1, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 80
    
#     game.player_action(0, 1, [0, 1, 2])
#     game.enemy_action(1, 1, [3, 4, 5])
    
#     assert game.pteam[0].hp == 85
#     assert game.pteam[1].hp == 80
#     assert game.pteam[2].hp == 85
    
#     game.player_action(0, 1, [3, 4, 5])
    
#     for enemy in game.eteam:
#         assert enemy.hp == 20
    

# #endregion

# #region Chachamaru Tests

# def test_satellite_cannon(chachamaru_test_game:TestGame):
#     game=chachamaru_test_game

#     game.player_action_pass(0, 0, [3])
#     assert game.quick_target(0, 1) == 1

#     game.player_action_pass(0, 0, [4])
#     assert game.quick_target(0, 1) == 2

#     game.player_action_pass(0, 0, [5])
#     assert game.quick_target(0, 1) == 3

#     game.player_action_pass(0, 1, [3, 4, 5])
#     for enemy in game.eteam:
#         assert enemy.hp == 65

# def test_active_combat_mode(chachamaru_test_game:TestGame):
#     game=chachamaru_test_game

#     game.player_action_pass(0, 0, [3])

#     game.player_action_pass(0, 2, [3])
#     assert game.eteam[0].hp == 90
#     assert game.pteam[0].get_dest_def_total() == 15

#     game.pass_turn()
#     game.pass_turn()
#     assert game.eteam[0].hp == 70
#     assert game.pteam[0].get_dest_def_total() == 45

#     game.player_action(0, 2, [4])
#     assert game.quick_target(0, 1) == 0

#     game.enemy_action(0, 0, [3])
#     assert not (EffectType.CONT_DMG, "Active Combat Mode") in game.eteam[1]
# #endregion

# #region Mirai Tests

# def test_blood_suppression_removal(mirai_test_game:TestGame):
#     game=mirai_test_game

#     game.player_action_pass(0, 0, [0])
#     assert game.pteam[0].hp == 90
#     assert game.pteam[0].source.current_abilities[0].name == "Blood Bullet"

#     game.player_action_pass(0, 1, [3])
#     assert game.eteam[0].hp == 60
#     game.pass_turn()
#     assert game.eteam[0].hp == 50
#     assert game.pteam[0].hp == 70


# def test_blood_bullet(mirai_test_game:TestGame):
#     game=mirai_test_game

#     game.player_action_pass(0, 0, [0])
#     game.player_action_pass(0, 0, [4])
#     game.pass_turn()

#     assert game.eteam[1].hp == 60
        
# def test_blood_shield(mirai_test_game:TestGame):
#     game=mirai_test_game

#     game.player_action_pass(0, 0, [0])
#     game.player_action(0, 2, [0])
#     game.queue_enemy_action(2, 0, [3])
#     game.queue_enemy_action(0, 1, [3])
#     game.execute_enemy_turn()

#     assert game.pteam[0].hp == 65

# #endregion

# #region Touka Tests

# def test_raikou(touka_test_game:TestGame):
#     game=touka_test_game

#     game.player_action(0, 2, [3])
#     assert game.eteam[0].hp == 80

#     game.enemy_action(0, 1, [3])
#     assert game.pteam[0].hp == 85
#     assert game.eteam[0].source.current_abilities[1].cooldown_remaining == 2
    
# def test_draw_stance(touka_test_game:TestGame):
#     game=touka_test_game
#     game.player_action(0, 0, [0])
#     assert game.pteam[0].source.current_abilities[0].name == "Raikiri"
#     game.enemy_action(0, 1, [3])
#     assert game.pteam[0].source.current_abilities[0].name == "Draw Stance"
#     assert game.eteam[0].hp == 85

# #endregion

# #region Killua Tests

# def test_lightning_palm(killua_test_game:TestGame):
#     game=killua_test_game
#     game.queue_action(0, 0, [3])
#     game.queue_action(1, 0, [3])
#     game.execute_turn()

#     assert game.eteam[0].hp == 65

#     game.enemy_action(0, 0, [4])
#     assert not game.pteam[1].is_stunned()
    
# def test_narukami(killua_test_game:TestGame):
#     game=killua_test_game
#     game.enemy_action(0, 2, [2])
#     game.queue_action(0, 1, [3])
#     game.queue_action(1, 0, [3])
#     game.execute_turn()
#     assert game.eteam[0].hp == 65
#     game.execute_enemy_turn()
#     game.player_action(1, 0, [5])
#     assert game.eteam[2].hp == 85
#     assert game.pteam[1].hp == 100
    
# def test_godspeed(killua_test_game:TestGame):
#     game=killua_test_game
#     assert game.pteam[0].source.current_abilities[2].name == "Godspeed"
#     game.player_action_pass(0, 2, [0])
#     assert game.pteam[0].source.current_abilities[2].name == "Whirlwind Rush"

#     game.player_action(0, 0, [3])
#     for ally in game.pteam:
#         assert (EffectType.STUN_IMMUNE, "Lightning Palm") in ally
#     assert game.eteam[0].hp == 75
    
# def test_whirlwind_palm(killua_test_game:TestGame):
#     game=killua_test_game
#     game.player_action_pass(0, 2, [0])
#     game.queue_action(0, 2, [3])
#     game.queue_action(1, 0, [3])
#     game.queue_action(2, 0, [3])
#     game.execute_turn()

#     assert game.eteam[0].hp == 35
#     logging.debug("%s", game.pteam[1])
#     assert game.pteam[1].check_invuln()
#     assert game.pteam[2].check_invuln()

# #endregion
