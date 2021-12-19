import sdl2
import sdl2.ext
import sdl2dll
from typing import Tuple
import typing
import importlib.resources
from PIL import Image
from animearena import battle_scene, character
from animearena.character import character_db
from playsound import playsound

if typing.TYPE_CHECKING:
    from animearena.character_select_scene import CharacterSelectScene
    from animearena.battle_scene import BattleScene
    from animearena.login_scene import LoginScene

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
    char_select: "CharacterSelectScene"
    battle_scene: "BattleScene"
    login_scene: "LoginScene"
    frame_count: int
    def __init__(self, window: sdl2.ext.Window = None):
        self.frame_count = 0
        self.surfaces = {}
        self.sounds = {}
        if window:
            self.window = window
            self.factory = sdl2.ext.SpriteFactory(sdl2.ext.SOFTWARE, free=False)
            self.spriterenderer = self.factory.create_sprite_render_system(window)
        for char in character_db.keys():
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
        self.connected = False

    def play_sound(self, file_name: str):
        # with importlib.resources.path('animearena.resources', file_name) as path:
        #     playsound(str(path), False)
        pass


    def set_scene_to_current(self, scene):
        self.current_scene = scene

    def bind_connection(self, connection):
        self.connection = connection

    def login(self, username, wins, losses, mission_data, ava_code=None):
        self.play_sound(self.sounds["login"])
        self.set_scene_to_current(self.char_select)
        self.char_select.settle_player(username, wins, losses, mission_data, ava_code)

    def package_mission_data(self, mission_data) -> str:
        mission_strings = []
        for name, nums in mission_data.items():
            mission_strings.append(f"{name}/{nums[0]}/{nums[1]}/{nums[2]}/{nums[3]}/{nums[4]}")
        mission_string = "|".join(mission_strings)
        return mission_string

    def return_to_select(self, player):
        self.change_window_size(800, 700)
        self.set_scene_to_current(self.char_select)
        self.char_select.settle_player(player.name, player.wins, player.losses, self.package_mission_data(player.missions))

    def start_battle(self, player_team, enemy_team, player, enemy, energy):
        self.play_sound(self.sounds["game_start"])
        self.change_window_size(900, 1000)
        self.set_scene_to_current(self.battle_scene)
        self.battle_scene.setup_scene(player_team, enemy_team, player, enemy, energy)

    def change_window_size(self, new_width: int, new_height: int):
        sdl2.SDL_SetWindowSize(self.window.window, new_width, new_height)
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)

    def create_new_window(self, size: Tuple[int, int], name: str):
        self.window.close()
        self.window = sdl2.ext.Window(name, size)
        self.window.show()
        self.spriterenderer = self.factory.create_sprite_render_system(self.window)