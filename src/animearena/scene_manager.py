import sdl2
import sdl2.ext
from typing import Tuple
import typing
import importlib.resources
from PIL import Image
from animearena.character import get_character_db
from animearena.character_select_scene import CharacterSelectScene, make_character_select_scene
from animearena.battle_scene import BattleScene, make_battle_scene
from animearena.login_scene import LoginScene, make_login_scene
from animearena.tutorial_scene import TutorialScene, make_tutorial_scene
from playsound import playsound

if typing.TYPE_CHECKING:
    from animearena.client import ConnectionHandler
    from animearena.engine import Scene

def get_image_from_path(file_name: str) -> Image:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return Image.open(path)

class SceneManager:
    """Manager for all game scenes"""
    window: sdl2.ext.Window
    spriterenderer: sdl2.ext.SpriteRenderSystem
    factory: sdl2.ext.SpriteFactory
    connected: bool
    surfaces: dict
    sounds: dict
    char_select: CharacterSelectScene
    battle_scene: BattleScene
    login_scene: LoginScene
    tutorial_scene: TutorialScene
    frame_count: int
    connection: "ConnectionHandler"
    current_scene: "Scene"
    username_raw: str
    password_raw: str
    uiprocessor: sdl2.ext.UIProcessor
    mouse_x: int
    mouse_y: int
    
    def __init__(self, window: sdl2.ext.Window = None):
        self.username_raw = ""
        self.password_raw = ""
        self.frame_count = 0
        self.surfaces = dict()
        self.sounds = dict()
        self.connection = None
        self.uiprocessor = sdl2.ext.UIProcessor()
        self.mouse_x = 0
        self.mouse_y = 0
        if window:
            self.window = window
            self.factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE, free=False)
            self.spriterenderer = self.factory.create_sprite_render_system(window)
        for char in get_character_db().keys():
            self.surfaces[char + "allyprof"] = get_image_from_path(char + "prof.png")
            self.surfaces[char + "enemyprof"] = get_image_from_path(char + "prof.png").transpose(Image.FLIP_LEFT_RIGHT)
            self.surfaces[char + "banner"] = get_image_from_path(char + "banner.png")
            for i in range(4):
                self.surfaces[char + str(i + 1)] = get_image_from_path(char + str(i + 1) + ".png")
            for i in range(4):
                try:
                    self.surfaces[char + "alt" + str(i + 1)] = get_image_from_path(char + "alt" + str(i + 1) + ".png")
                    
                except FileNotFoundError:
                    break
            for i in range(2):
                try:
                    self.surfaces[char + "altprof" + str(i + 1)] = get_image_from_path(char + "altprof" + str(i + 1) + ".png")
                    self.surfaces[char + "enemyaltprof" + str(i + 1)] = get_image_from_path(char + "altprof" + str(i + 1) + ".png").transpose(Image.FLIP_LEFT_RIGHT)
                except FileNotFoundError:
                    break
        self.sounds["page"] = "page_turn.wav"
        self.sounds["undo"] = "undo_click.wav"
        self.sounds["select"] = "champ_select.wav"
        self.sounds["click"] = "ability_click.wav"
        self.sounds["game_start"] = "in_game.wav"
        self.sounds["login"] = "log_in.wav"
        self.sounds["turnstart"] = "turn_back.wav"
        self.sounds["turnend"] = "turn_send.wav"
        self.surfaces["banner"] = get_image_from_path("banner_bar.png")
        self.surfaces["won"] = get_image_from_path("youwon.png")
        self.surfaces["lost"] = get_image_from_path("youlost.png")
        self.surfaces["add"] = get_image_from_path("add_button.png")
        self.surfaces["remove"] = get_image_from_path("remove_button.png")
        self.surfaces["quit"] = get_image_from_path("quit_button.png")
        self.surfaces["end"] = get_image_from_path("end_button.png")
        self.surfaces["default_prof"] = get_image_from_path("default.png")
        self.surfaces["start"] = get_image_from_path("start_button.png")
        self.surfaces["search"] = get_image_from_path("searching_panel.png")
        self.surfaces["background"] = get_image_from_path("bright_background.png")
        self.surfaces["right_arrow"] = get_image_from_path("arrowright.png")
        self.surfaces["left_arrow"] = get_image_from_path("arrowleft.png")
        self.surfaces["RANDOM"] = get_image_from_path("randomEnergy.png")
        self.surfaces["PHYSICAL"] = get_image_from_path("physicalEnergy.png")
        self.surfaces["SPECIAL"] = get_image_from_path("specialEnergy.png")
        self.surfaces["MENTAL"] = get_image_from_path("mentalEnergy.png")
        self.surfaces["WEAPON"] = get_image_from_path("weaponEnergy.png")
        self.surfaces["selected"] = get_image_from_path("selected_pane.png")
        self.surfaces["locked"] = get_image_from_path("null_pane.png")
        self.surfaces["char_select_blotter"] = get_image_from_path("blotter.png")
        self.surfaces["in_game_background"] = get_image_from_path("in_game_background.png")
        self.surfaces["lock_icon"] = get_image_from_path("lock_icon.png")
        self.surfaces["phys_icon"] = get_image_from_path("phys_icon.png")
        self.surfaces["spec_icon"] = get_image_from_path("spec_icon.png")
        self.surfaces["wep_icon"] = get_image_from_path("wep_icon.png")
        self.surfaces["ment_icon"] = get_image_from_path("ment_icon.png")
        self.surfaces["rand_icon"] = get_image_from_path("rand_icon.png")
        self.surfaces["exclusive_icon"] = get_image_from_path("exclusive_icon.png")
        self.surfaces["how_to"] = get_image_from_path("how_to.png")
        self.surfaces["scroll_wheel"] = get_image_from_path("scroll_wheel.png")
        self.surfaces["used_slot"] = get_image_from_path("used_ability.png")
        self.connected = False

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.battle_scene.timer.cancel()

    def dispatch_message(self, packet_id: int, data: list[bytes]):
        self.connection.packets[packet_id](data)

    def play_sound(self, file_name: str):
        # with importlib.resources.path('animearena.resources', file_name) as path:
        #     playsound(str(path), False)
        pass

    def update_mouse_position(self, x: int, y: int):
        self.mouse_x = x
        self.mouse_y = y

    def initialize_scenes(self):
        self.char_select = make_character_select_scene(self)
        self.battle_scene = make_battle_scene(self)
        self.login_scene = make_login_scene(self)
        self.tutorial_scene = make_tutorial_scene(self)

    def set_scene_to_current(self, scene: "Scene"):
        self.current_scene = scene
        self.spriterenderer.render(self.current_scene.renderables())

    def bind_connection(self, connection):
        self.connection = connection

    def login(self, username, wins, losses, medals, mission_data, ava_code=None):
        self.play_sound(self.sounds["login"])
        self.set_scene_to_current(self.char_select)
        self.char_select.settle_player(username, wins, losses, medals, mission_data, ava_code)

    def package_mission_data(self, mission_data) -> str:
        mission_strings = []
        for name, nums in mission_data.items():
            mission_strings.append(f"{name}/{nums[0]}/{nums[1]}/{nums[2]}/{nums[3]}/{nums[4]}/{nums[5]}")
        mission_string = "|".join(mission_strings)
        return mission_string

    def return_to_select(self, player):
        self.change_window_size(800, 700)
        self.set_scene_to_current(self.char_select)
        self.char_select.settle_player(player.name, player.wins, player.losses, player.medals, self.package_mission_data(player.missions), mission_complete = player.missions_complete)

    def start_battle(self, player_team, enemy_team, player, enemy, energy, seed):
        self.play_sound(self.sounds["game_start"])
        self.change_window_size(900, 700)
        self.battle_scene.setup_scene(player_team, enemy_team, player, enemy, energy, seed)
        self.set_scene_to_current(self.battle_scene)

    def start_tutorial(self, player):
        self.change_window_size(1100, 1100)
        self.set_scene_to_current(self.tutorial_scene)
        self.tutorial_scene.start_tutorial(player)

    def change_window_size(self, new_width: int, new_height: int):
        sdl2.SDL_SetWindowSize(self.window.window, new_width, new_height)
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)

    def create_new_window(self, size: Tuple[int, int], name: str):
        self.window.close()
        self.window = sdl2.ext.Window(name, size)
        self.window.show()
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)
        
    def reset_event_trigger(self):
        self.current_scene.triggered_event = False  
    