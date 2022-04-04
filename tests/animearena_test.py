from distutils.log import ERROR
from http import server
from pickle import PUT

from animearena.energy import Energy
from animearena.scene_manager import SceneManager
from animearena.character import Character
from animearena.effects import Effect, EffectType
from animearena.client import ConnectionHandler
from animearena.scene_manager import SceneManager
from animearena import engine

import logging
import asyncio
import pytest
import sdl2
import sdl2dll
import sdl2.ext
import dill as pickle

from animearena.battle_scene import BattleScene, make_battle_scene, CharacterManager, MatchPouch


class TestGame:

    player1: BattleScene
    player2: BattleScene
    active_player_id = int

    def __init__(self, player1_team: list[Character], player2_team: list[Character], scene_manager):

        self.player1 = make_battle_scene(scene_manager)
        self.player1.setup_scene(player1_team, player2_team)
        self.player2 = make_battle_scene(scene_manager)
        self.player2.setup_scene(player2_team, player1_team)

        self.active_player_id = 0

    @property
    def active_player(self) -> BattleScene:
        if self.active_player_id == 0:
            return self.player1
        else:
            return self.player2

    @property
    def pteam(self) -> list[CharacterManager]:
        return self.active_player.pteam

    @property
    def eteam(self) -> list[CharacterManager]:
        return self.active_player.eteam


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
        logging.debug("%s used %s targeting %s", actor.source.name, actor.used_ability.name, self.get_target_names_for_debugger(target_index_list))
        for i in target_index_list:
            if i < 3:
                actor.current_targets.append(self.active_player.pteam[i])
            else:
                actor.current_targets.append(self.active_player.eteam[i - 3])

    def target_action(self, character_index: int, ability_index: int) -> int:
        actor = self.active_player.pteam[character_index]
        actor.current_targets.clear()
        return actor.source.current_abilities[ability_index].target(actor, self.active_player.pteam, self.active_player.eteam)

    def execute_abilities(self):
        for character in self.pteam:
            if character.acted:
                character.execute_ability()
            character.check_ability_swaps()
            character.adjust_targeting_types()
        for character in self.eteam:
            character.check_ability_swaps()
            character.adjust_targeting_types()

    def execute_empty_round(self):
        self.execute_abilities()
        self.active_player.resolve_ticking_ability()
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
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa").user.progress_mission(1, 1)
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

        pouch1, pouch2 = self.active_player.pickle_match(self.active_player.player_display.team,
                                           self.active_player.enemy_display.team)
        match = MatchPouch(pouch1, pouch2)
        msg = pickle.dumps(match)

        self.swap_turns(msg)

        self.execute_turn()


    def execute_turn(self):
        self.execute_abilities()
        self.active_player.resolve_ticking_ability()
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
                yatsu = manager.get_effect(EffectType.MARK, "Yatsufusa").user.progress_mission(1, 1)
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

        pouch1, pouch2 = self.active_player.pickle_match(self.active_player.player_display.team,
                                           self.active_player.enemy_display.team)
        match = MatchPouch(pouch1, pouch2)
        msg = pickle.dumps(match)

        self.swap_turns(msg)

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


    def swap_turns(self, message):

        self.toggle_active_player()
        self.active_player.unpickle_match(message, rejoin=True)


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
            "byakuya": Character("byakuya")}
    yield data

@pytest.fixture(scope="package")
def setup_scene_manager():
    scene_manager = SceneManager()
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

def reset_character(character: Character):
    character.hp = 100
    character.current_effects.clear()
    character.current_abilities = character.main_abilities
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

#region Hinata Tests
def test_hinata_twin_lion(hinata_test_game: TestGame):

    hinata_test_game.queue_action(0, 0, [3])
    hinata_test_game.execute_abilities()

    assert hinata_test_game.eteam[0].source.hp == 60

def test_hinata_twin_lion(hinata_test_game: TestGame):

    #Pass turn
    hinata_test_game.execute_turn()


    #Use Ruler's Counter on Herself.
    hinata_test_game.queue_action(0, 2, [0])
    hinata_test_game.execute_turn()
    
    hinata_test_game.dump_effects(hinata_test_game.eteam[0])

    #Use Hinata's Twin Lion Fists
    hinata_test_game.queue_action(0, 0, [3])
    hinata_test_game.execute_abilities()



    hinata_test_game.dump_effects(hinata_test_game.pteam[0])

    #Assert Hinata and Ruler have both taken 20 damage
    assert hinata_test_game.eteam[0].source.hp == 80
    assert hinata_test_game.pteam[0].source.hp == 80

def test_hinata_trigrams(hinata_test_game: TestGame):

    hinata_test_game.queue_action(0, 1, [0, 1, 2])
    hinata_test_game.execute_turn()

    
    assert hinata_test_game.eteam[2].check_for_dmg_reduction() == 10

    hinata_test_game.execute_turn()


    hinata_test_game.queue_action(0, 1, [0, 1, 2, 3, 4, 5])
    hinata_test_game.execute_turn()


    assert hinata_test_game.eteam[2].check_for_dmg_reduction() == 10
    assert hinata_test_game.pteam[2].source.hp == 85

#endregion

#region Neji Tests

def test_trigrams(neji_test_game: TestGame):

    neji_test_game.queue_action(0, 0, [3])
    neji_test_game.execute_empty_round()

    assert neji_test_game.pteam[0].source.current_abilities[0].name == "Chakra Point Strike"
    assert neji_test_game.eteam[0].source.hp == 98

    neji_test_game.execute_empty_round()

    assert neji_test_game.eteam[0].source.hp == 94

    neji_test_game.execute_empty_round()

    assert neji_test_game.eteam[0].source.hp == 86

    neji_test_game.execute_turn()

    assert neji_test_game.pteam[0].source.hp == 70

    assert neji_test_game.eteam[0].has_effect(EffectType.CONT_USE, "Eight Trigrams - 128 Palms")

    neji_test_game.queue_action(0, 0, [3])
    neji_test_game.execute_turn()

    assert not neji_test_game.pteam[0].has_effect(EffectType.CONT_USE, "Eight Trigrams - 128 Palms")

def test_mountain_crusher(neji_test_game: TestGame):

    neji_test_game.queue_action(0, 1, [3])
    neji_test_game.execute_turn()

    assert neji_test_game.pteam[0].source.hp == 75

    neji_test_game.queue_action(0, 3, [0])
    neji_test_game.execute_turn()

    neji_test_game.queue_action(0, 1, [3])
    neji_test_game.execute_empty_round()

    assert neji_test_game.eteam[0].source.hp == 35

def test_selfless_genius(neji_test_game: TestGame):

    neji_test_game.pteam[1].source.hp = 5
    neji_test_game.queue_action(0, 2, [1])
    neji_test_game.execute_turn()

    neji_test_game.queue_action(0, 1, [4])
    neji_test_game.execute_turn()

    assert neji_test_game.pteam[0].source.dead
    assert neji_test_game.pteam[1].has_effect(EffectType.ALL_BOOST, "Selfless Genius")

def test_selfless_genius_failure(neji_test_game: TestGame):

    neji_test_game.queue_action(0, 2, [1])
    neji_test_game.queue_action(1, 2, [4])
    neji_test_game.execute_abilities()

    assert neji_test_game.pteam[1].source.dead
    assert not neji_test_game.pteam[0].source.dead

#endregion

#region Minato Tests
def test_kunai(minato_test_game: TestGame):

    minato_test_game.queue_action(0, 1, [3])
    minato_test_game.execute_empty_round()

    assert minato_test_game.eteam[0].has_effect(EffectType.MARK, "Marked Kunai")

def test_flying_raijin(minato_test_game: TestGame):

    minato_test_game.queue_action(0, 0, [3])
    minato_test_game.execute_empty_round()

    assert minato_test_game.pteam[0].source.current_abilities[0].cooldown_remaining == 2

    minato_test_game.execute_empty_round()
    minato_test_game.execute_empty_round()

    assert minato_test_game.pteam[0].source.current_abilities[0].cooldown_remaining == 0

    minato_test_game.queue_action(0, 1, [3])
    minato_test_game.execute_empty_round()

    minato_test_game.queue_action(0, 0, [3])
    minato_test_game.execute_turn()

    assert minato_test_game.eteam[0].source.current_abilities[0].cooldown_remaining == 0
    assert minato_test_game.eteam[0].check_invuln()

def test_shiki_fuujin(minato_test_game: TestGame):

    minato_test_game.queue_action(0, 2, [3])
    minato_test_game.execute_empty_round()
    assert minato_test_game.pteam[0].source.dead
    assert minato_test_game.eteam[0].source.current_abilities[0].total_cost == 3

#endregion

#region Itachi Tests
def test_amaterasu(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 0, [3])
    itachi_test_game.execute_empty_round()

    assert itachi_test_game.target_action(0, 0) == 2
    assert itachi_test_game.eteam[0].source.hp == 90

def test_tsukuyomi(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 1, [3])
    itachi_test_game.execute_turn()

    assert itachi_test_game.pteam[0].is_stunned()

    itachi_test_game.queue_action(1, 2, [0])
    itachi_test_game.execute_turn()

    assert not itachi_test_game.eteam[0].is_stunned()

def test_susanoo(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 2, [0])
    itachi_test_game.execute_empty_round()

    assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Totsuka Blade"
    assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Yata Mirror"

def test_yata_mirror(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 2, [0])
    itachi_test_game.execute_empty_round()
    
    assert itachi_test_game.pteam[0].get_dest_def_total() == 45

    itachi_test_game.queue_action(0, 1, [0])
    itachi_test_game.execute_empty_round()

    assert itachi_test_game.pteam[0].get_dest_def_total() == 65

def test_susano_shatter_failure(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 2, [0])
    itachi_test_game.execute_turn()

    itachi_test_game.queue_action(0, 0, [3])
    itachi_test_game.execute_turn()

    assert not itachi_test_game.pteam[0].has_effect(EffectType.ABILITY_SWAP, "Susano'o")
    assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Amaterasu"
    assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Tsukuyomi"

def test_susano_weakness_failure(itachi_test_game: TestGame):
    itachi_test_game.queue_action(0, 2, [0])
    itachi_test_game.execute_empty_round()

    assert itachi_test_game.pteam[0].source.hp == 90

    itachi_test_game.pteam[0].source.hp = 20
    itachi_test_game.execute_empty_round()

    assert not itachi_test_game.pteam[0].has_effect(EffectType.ABILITY_SWAP, "Susano'o")
    assert itachi_test_game.pteam[0].source.current_abilities[0].name == "Amaterasu"
    assert itachi_test_game.pteam[0].source.current_abilities[1].name == "Tsukuyomi"

#endregion

#region Kakashi Tests

def test_raikiri_and_dogs(kakashi_test_game: TestGame):
    kakashi_test_game.queue_action(0, 1, [3])
    kakashi_test_game.execute_turn()

    assert kakashi_test_game.pteam[0].is_stunned()

    kakashi_test_game.execute_turn()

    kakashi_test_game.queue_action(0, 2, [3])
    kakashi_test_game.execute_abilities()

    assert kakashi_test_game.eteam[0].source.dead

def test_copy_ninja(kakashi_test_game: TestGame):
    kakashi_test_game.queue_action(0, 0, [0])
    kakashi_test_game.execute_turn()

    kakashi_test_game.queue_action(2, 0, [3])
    kakashi_test_game.execute_turn()

    kakashi_test_game.dump_effects(kakashi_test_game.eteam[2])
    assert kakashi_test_game.eteam[2].source.hp == 80
    assert kakashi_test_game.eteam[2].is_stunned()

def test_self_kamui(kakashi_test_game: TestGame):
    kakashi_test_game.queue_action(0, 3, [0])
    kakashi_test_game.execute_turn()
    
    kakashi_test_game.queue_action(2, 0, [3])
    kakashi_test_game.execute_turn()

    assert kakashi_test_game.pteam[0].source.hp == 100
    assert not kakashi_test_game.pteam[0].is_stunned()

def test_target_kamui(kakashi_test_game: TestGame):
    kakashi_test_game.queue_action(0, 3, [3])
    kakashi_test_game.execute_turn()

    assert kakashi_test_game.pteam[0].source.hp == 80

    kakashi_test_game.queue_action(2, 3, [2])
    kakashi_test_game.execute_turn()

    kakashi_test_game.queue_action(0, 3, [5])
    kakashi_test_game.execute_turn()

    assert kakashi_test_game.pteam[2].source.hp == 80
    assert kakashi_test_game.pteam[2].has_effect(EffectType.ISOLATE, "Kamui")

#endregion

#region Shikamaru Tests

def test_shadow_pin(shikamaru_test_game: TestGame):
    shikamaru_test_game.queue_action(0, 2, [3])
    shikamaru_test_game.execute_turn()

    assert not shikamaru_test_game.eteam[0].hostile_target(shikamaru_test_game.pteam[0])

def test_shadow_bind_prolif(shikamaru_test_game: TestGame):
    shikamaru_test_game.queue_action(0, 2, [3])
    shikamaru_test_game.execute_empty_round()

    shikamaru_test_game.queue_action(0, 0, [5])
    shikamaru_test_game.execute_abilities()

    assert shikamaru_test_game.eteam[0].is_stunned()
    assert shikamaru_test_game.eteam[2].is_stunned()

def test_shadow_neck_bind_prolif(shikamaru_test_game: TestGame):
    shikamaru_test_game.queue_action(0, 2, [3])
    shikamaru_test_game.execute_empty_round()

    shikamaru_test_game.queue_action(0, 1, [5])
    shikamaru_test_game.execute_abilities()

    assert shikamaru_test_game.eteam[0].source.hp == 85
    assert shikamaru_test_game.eteam[2].source.hp == 85


#endregion

#region Ichigo Tests

def test_zangetsu_buildup(ichigo_test_game: TestGame):
    ichigo_test_game.queue_action(0, 2, [3])
    ichigo_test_game.execute_empty_round()

    assert ichigo_test_game.eteam[0].source.hp == 80

    ichigo_test_game.queue_action(0, 2, [3])
    ichigo_test_game.execute_empty_round()

    assert ichigo_test_game.eteam[0].source.hp == 55

    ichigo_test_game.queue_action(0, 2, [3])
    ichigo_test_game.execute_empty_round()

    assert ichigo_test_game.eteam[0].source.hp == 25

def test_empowered_getsuga(ichigo_test_game: TestGame):
    ichigo_test_game.queue_action(0, 1, [0])
    ichigo_test_game.execute_turn()

    ichigo_test_game.queue_action(1, 3, [1])
    ichigo_test_game.queue_action(0, 1, [1])
    ichigo_test_game.execute_turn()

    ichigo_test_game.queue_action(0, 0, [4])
    ichigo_test_game.execute_abilities()

    assert ichigo_test_game.eteam[1].source.hp == 60



    

#endregion

