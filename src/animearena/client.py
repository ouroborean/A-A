from asyncio.streams import StreamReader, StreamWriter
import pickle
import socket
import os
import pathlib
import sys
import requests
from animearena import mission
from animearena.byte_buffer import ByteBuffer
from animearena.character import Character, get_character_db
from animearena.player import Player
from typing import Callable
from PIL import Image
import typing

if typing.TYPE_CHECKING:
    from animearena.scene_manager import SceneManager

HOST = "127.0.0.1"
PORT = 5692

VERSION = "0.9.915"

class ConnectionHandler:

    writer: StreamWriter
    reader: StreamReader
    waiting_for_opponent: bool
    waiting_for_login: bool
    waiting_for_registration: bool
    scene_manager: "SceneManager"

    def __init__(self, scene_manager):
        self.waiting_for_registration = False
        self.scene_manager = scene_manager
        self.waiting_for_opponent = False
        self.waiting_for_login = False
        self.packets: dict[int, Callable] = {
            0: self.handle_start_package,
            1: self.handle_match_communication,
            2: self.handle_login_failure,
            3: self.handle_login_success,
            4: self.handle_registration,
            5: self.handle_surrender_notification,
            6: self.handle_reconnection,
            7: self.handle_version_check,
            8: self.handle_test_ping
        }

    def handle_test_ping(self, data:list[bytes]):
        print("Received test ping response")

    def send_test_ping(self):
        buffer = ByteBuffer()
        buffer.write_int(11)
        buffer.write_byte(b'\x1f\x1f\x1f')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(buffer.get_byte_array())
        buffer.clear()
        

    def handle_version_check(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        newest_version = buffer.read_string()
        print(f"Running on version: {VERSION}. Newest version: {newest_version}")
        if VERSION != newest_version:
            
            
            s = sys.argv[0]
            
            version_tag = newest_version.replace(".", "-")

            file_name = f"AnimeArena{version_tag}.exe"

            abs_path = pathlib.Path().resolve()
            
            final_path = abs_path / file_name

            url = "https://storage.googleapis.com/a-a-latest/AnimeArena.exe"
            file = requests.get(url, stream=True)
            with open(abs_path / file_name, "wb") as f:
                for block in file.iter_content(1024):
                    if not block:
                        break
                    f.write(block)
            s = sys.argv[0]
            with open("temp.config", "w") as f:
                f.write(s)
            new_env = os.environ.copy()
            new_env.pop("PYSDL2_DLL_PATH")
            os.execve(final_path, [final_path,], new_env)
            
        else:
            
            abs_path = pathlib.Path().resolve()
            if os.path.exists("temp.config"):
                print("Found old config file")
                with open("temp.config", "r") as f:
                    old_file = f.read().strip()
                os.remove("temp.config")
                os.remove(abs_path / old_file)
            
        self.scene_manager.login_scene.updating = False
        self.scene_manager.login_scene.full_render()
        buffer.clear()

    def send_version_request(self):
        buffer = ByteBuffer()
        buffer.write_int(10)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def handle_surrender_notification(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        mission_packages = []
        for _ in range(3):
            mission_package = [buffer.read_int() for i in range(5)]
            mission_packages.append(mission_package)
        self.scene_manager.battle_scene.ingest_mission_packages(mission_packages)
        self.scene_manager.battle_scene.win_game(surrendered = True)

    def send_message(self, message: str):
        try:
            self.writer.write(message.encode('utf-8'))
        except BlockingIOError:
            pass
        except OSError:
            pass

    def send_search_cancellation(self):
        buffer = ByteBuffer()
        buffer.write_int(7)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def send_surrender(self, mission_progress_packages):
        buffer = ByteBuffer()
        buffer.write_int(6)

        for mission_progress_package in mission_progress_packages:
            for mission_progress in mission_progress_package:
                buffer.write_int(mission_progress)

        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def update_avatar(self, avatar: bytes):
        buffer = ByteBuffer()
        buffer.write_int(4)
        print(len(list(avatar)))
        buffer.write_int(len(list(avatar)))
        buffer.write_bytes(list(avatar))
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()
    
    

    def handle_registration(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        message = buffer.read_string()
        buffer.clear()
        self.scene_manager.login_scene.receive_message(message)
        self.scene_manager.login_scene.clicked_register = False


    def handle_login_failure(self, data:list[bytes]):
        print("Received login information back")
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        message = buffer.read_string()
        buffer.clear()
        self.scene_manager.login_scene.receive_message(message)
        self.scene_manager.login_scene.clicked_login = False

    def handle_login_success(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        wins = buffer.read_int()
        losses = buffer.read_int()
        medals = buffer.read_int()
        mission_data = buffer.read_string()
        ava_code = None
        has_avatar = buffer.read_int()
        if has_avatar:
            length = buffer.read_int()
            ava_code = bytes(buffer.read_bytes(length))
    
        self.scene_manager.login(self.scene_manager.login_scene.username_box.text, wins, losses, medals, mission_data, ava_code)

        buffer.clear()

    def send_player_update(self, player):
        buffer = ByteBuffer()
        buffer.write_int(5)
        buffer.write_int(player.wins)
        buffer.write_int(player.losses)
        buffer.write_int(player.medals)
        mission_strings = []
        for name, nums in player.missions.items():
            mission_strings.append(f"{name}/{nums[0]}/{nums[1]}/{nums[2]}/{nums[3]}/{nums[4]}/{nums[5]}")
        mission_string = "|".join(mission_strings)
        buffer.write_string(mission_string)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())

        buffer.clear()


    def handle_match_communication(self, data:list[bytes]):

        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        energy_pool = [buffer.read_int() for i in range(4)]
        pickle_len = buffer.read_int()
        pickle = bytearray(buffer.read_bytes(pickle_len))

        self.scene_manager.battle_scene.player_display.team.energy_pool[4] = 0
        for i, v in enumerate(energy_pool):
            self.scene_manager.battle_scene.player_display.team.energy_pool[i] = v
            self.scene_manager.battle_scene.player_display.team.energy_pool[4] += v
        self.scene_manager.battle_scene.unpickle_match(pickle)
        buffer.clear()

    def send_registration(self, username: str, password: str):
        buffer = ByteBuffer()
        
        buffer.write_int(3)
        buffer.write_string(username)
        buffer.write_string(password)
        buffer.write_byte(b'\x1f\x1f\x1f')
        print(len(buffer.get_byte_array()))
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_registration = True
        buffer.clear()

    def send_login_attempt(self, username: str, password: str):
        print("Sent login")
        buffer = ByteBuffer()
        buffer.write_int(2)
        buffer.write_string(username.strip())
        buffer.write_string(password.strip())
        buffer.write_byte(b'\x1f\x1f\x1f')
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_login = True
        
        buffer.clear()

    def send_match_ending(self):
        buffer = ByteBuffer()
        buffer.write_int(8)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def send_start_package(self, names: list[str], pickled_player: bytes):
        print("Sending start package!")
        buffer = ByteBuffer()
        buffer.write_int(0)
        for name in names:
            buffer.write_string(name)
        buffer.write_int(len(list(pickled_player)))
        buffer.write_bytes(list(pickled_player))
        buffer.write_byte(b'\x1f\x1f\x1f')
        print(len(buffer.get_byte_array()))
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_opponent = True
            print("Sent start package!")
        buffer.clear()
        
    def send_match_communication(self, energy_pool: list, enemy_energy_cont: list, data:bytes):
        buffer = ByteBuffer()
        buffer.write_int(1)

        for i in energy_pool:
            buffer.write_int(i)
        for i in enemy_energy_cont:
            buffer.write_int(i)
        buffer.write_int(len(data))
        buffer.write_bytes(data)
        print(f"Sending match communication of length {len(data)}")
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def check_for_message(self):
        msg = ""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(0)
            s.connect(("127.0.0.1", 5692))
            msg = s.recv(120000)
        except BlockingIOError:
            pass
        except OSError:
            pass
        if msg:
            print(msg.decode('utf-8'))

    def handle_reconnection(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        player_names = [buffer.read_string().strip() for i in range(3)]
        length = buffer.read_int()
        player = buffer.read_bytes(length)
        my_turn = buffer.read_int()
        if my_turn == 1:
            self.scene_manager.battle_scene.waiting_for_turn = False
        elif my_turn == 0:
            self.scene_manager.battle_scene.waiting_for_turn = True
        my_package = not(not(buffer.read_int()))
        energy_pool = [buffer.read_int() for i in range(4)]
        names = [buffer.read_string().strip() for i in range(3)]
        length = buffer.read_int()
        pickled_player = bytes(buffer.read_bytes(length))
        has_match = not(not(buffer.read_int()))
        if has_match:
            pickled_match = bytearray(buffer.buff[buffer.read_pos:])

        player_team = [get_character_db()[name] for name in player_names]
        enemy_team = [Character(name) for name in names]
        player_pouch = pickle.loads(pickled_player)
        enemy_ava = Image.frombytes(player_pouch[3]["mode"], player_pouch[3]["size"], player_pouch[3]["pixels"])
        enemy = Player(player_pouch[0], player_pouch[1], player_pouch[2], enemy_ava)

        self.scene_manager.char_select.selected_team = player_team

        self.scene_manager.char_select.start_battle(names, pickled_player, energy_pool)
        if has_match:
            self.scene_manager.battle_scene.unpickle_match(pickled_match, True, my_package)
        self.scene_manager.battle_scene.full_update()
        for manager in self.scene_manager.battle_scene.player_display.team.character_managers:
            manager.update()


    def send_match_statistics(self, characters, won):
        buffer = ByteBuffer()
        buffer.write_int(9)
        for name in characters:
            buffer.write_string(name)
        if won:
            buffer.write_int(1)
        else:
            buffer.write_int(0)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def handle_start_package(self, data: list[bytes]):

        if self.waiting_for_opponent:
            self.waiting_for_opponent = False
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        packet_id = buffer.read_int()
        first_turn = buffer.read_int()
        if first_turn:
            self.scene_manager.battle_scene.waiting_for_turn = False
            self.scene_manager.battle_scene.moving_first = True
        else:
            self.scene_manager.battle_scene.waiting_for_turn = True
            self.scene_manager.battle_scene.moving_first = False
        phys = buffer.read_int()
        spec = buffer.read_int()
        ment = buffer.read_int()
        wep = buffer.read_int()
        energy = [phys, spec, ment, wep]
        names = [buffer.read_string().strip() for i in range(3)]
        length = buffer.read_int()
        pickled_player = bytes(buffer.read_bytes(length))
        self.scene_manager.char_select.start_battle(names, pickled_player, energy)


    