from asyncio.streams import StreamReader, StreamWriter
import socket
import threading
import os
import pathlib
import sys
import requests
from animearena.byte_buffer import ByteBuffer
from animearena.character import Character
from typing import Callable
import typing
import logging
from animearena.battle_scene import AbilityMessage
import hashlib
if typing.TYPE_CHECKING:
    from animearena.scene_manager import SceneManager

VERSION = "0.9.92"

SALT = b'gawr gura for president'

def hash_the_password(password: str) -> str:
    digest = hashlib.scrypt(password.encode(encoding="utf-8"),
                            salt=SALT,
                            n=16384,
                            r=8,
                            p=1)
    return digest.hex()

def nonce_the_digest(digest: str, nonce: int) -> str:
    new_digest = hashlib.scrypt(digest.encode(encoding='utf-8'),
                            salt=str(nonce).encode(encoding='utf-8'),
                            n=16384,
                            r=8,
                            p=1)
    return new_digest.hex()

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
            8: self.handle_timeout,
            9: self.handle_login_nonce
        }

    
    def handle_timeout(self, data:list[bytes]):
        
        self.scene_manager.battle_scene.handle_timeout()
        

    def update_thread(self, newest_version: str):
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
        with open("animearenatemp.config", "w") as f:
            f.write(s)
        new_env = os.environ.copy()
        new_env.pop("PYSDL2_DLL_PATH")
        os.execve(final_path, [final_path,], new_env)
        
        

    def handle_version_check(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        newest_version = buffer.read_string()
        print(f"Running on version: {VERSION}. Newest version: {newest_version}")
        if VERSION != newest_version:
            
            self.scene_manager.login_scene.updating=True
            self.scene_manager.login_scene.full_render()
            
            update_version_thread = threading.Thread(target=self.update_thread, args=(newest_version,), daemon=True)
            
            update_version_thread.start()
            
        else:
            
            abs_path = pathlib.Path().resolve()
            if os.path.exists("animearenatemp.config"):
                with open("animearenatemp.config", "r") as f:
                    old_file = f.read().strip()
                os.remove("animearenatemp.config")
                os.remove(abs_path / old_file)
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
    
        self.scene_manager.login(self.scene_manager.username_raw, wins, losses, medals, mission_data, ava_code)

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

        used_ability_count = buffer.read_int()
        executed_abilities = list()
        for i in range(used_ability_count):
            executed_ability = AbilityMessage()
            executed_ability.assign_user_id(buffer.read_int())
            executed_ability.assign_ability_id(buffer.read_int())
            executed_ability.set_primary_target(buffer.read_int())
            ally_targets = buffer.read_int()
            for j in range(ally_targets):
                executed_ability.add_to_ally_targets(buffer.read_int())
            enemy_targets = buffer.read_int()
            for j in range(enemy_targets):
                executed_ability.add_to_enemy_targets(buffer.read_int())
            executed_abilities.append(executed_ability)
        execution_order = list()
        execution_order_count = buffer.read_int()
        for i in range(execution_order_count):
            execution_order.append(buffer.read_int())
        for i in range(4):
            buffer.read_int()
        
        potential_energy = list()

        for i in range(6):
            potential_energy.append(buffer.read_int())

        
        if self.scene_manager.battle_scene.skipping_animations:
            self.scene_manager.battle_scene.enemy_execution_loop(executed_abilities, execution_order, potential_energy)
        else:
            self.scene_manager.battle_scene.start_enemy_execution(executed_abilities, execution_order, potential_energy)
        buffer.clear()

    def send_registration(self, username: str, password: str):
        buffer = ByteBuffer()
        
        buffer.write_int(3)
        buffer.write_string(username)
        
        digest = hash_the_password(password)
        buffer.write_string(digest)
        buffer.write_byte(b'\x1f\x1f\x1f')
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_registration = True
        buffer.clear()

    def request_login_nonce(self):
        buffer = ByteBuffer()
        buffer.write_int(11)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()
    
    def handle_login_nonce(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        nonce_key = buffer.read_int()
        digest = hash_the_password(self.scene_manager.password_raw)
        nonced_digest = nonce_the_digest(digest, nonce_key)
        self.send_login_attempt(nonced_digest)
        

    def send_login_attempt(self, password_digest: str):
        buffer = ByteBuffer()
        buffer.write_int(2)
        buffer.write_string(self.scene_manager.username_raw)
        buffer.write_string(password_digest)
        buffer.write_byte(b'\x1f\x1f\x1f')
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_login = True
        buffer.clear()

    def send_match_ending(self, won: bool):
        buffer = ByteBuffer()
        buffer.write_int(8)
        if won:
            buffer.write_int(1)
        else:
            buffer.write_int(0)
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def send_start_package(self, names: list[str], player_pouch: bytes):
        buffer = ByteBuffer()
        buffer.write_int(0)
        for name in names:
            buffer.write_string(name)
        
        buffer.write_string(player_pouch[0])
        buffer.write_int(player_pouch[1])
        buffer.write_int(player_pouch[2])
        buffer.write_string(player_pouch[3])
        buffer.write_int(player_pouch[4][0])
        buffer.write_int(player_pouch[4][1])
        buffer.write_int(len(player_pouch[5]))
        buffer.write_bytes(player_pouch[5])

        buffer.write_byte(b'\x1f\x1f\x1f')
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_opponent = True
        buffer.clear()
    
    def send_match_communication(self, ability_messages: list[AbilityMessage], execution_order: list[int], random_spent: list[int]):
        buffer = ByteBuffer()
        buffer.write_int(1)
        buffer.write_int(len(ability_messages))
        for message in ability_messages:
            buffer.write_int(message.user_id)
            buffer.write_int(message.ability_id)
            buffer.write_int(message.primary_id)
            buffer.write_int(len(message.ally_targets))
            for ally in message.ally_targets:
                buffer.write_int(ally)
            buffer.write_int(len(message.enemy_targets))
            for enemy in message.enemy_targets:
                buffer.write_int(enemy)
        buffer.write_int(len(execution_order))
        for message in execution_order:
            buffer.write_int(message)
        for i in random_spent:
            buffer.write_int(i)
        
        buffer.write_byte(b'\x1f\x1f\x1f')
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def handle_reconnection(self, data:list[bytes]):
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        seed = buffer.read_int()
        # get player team names
        player_character_names = [buffer.read_string().strip() for i in range(3)]
        self.scene_manager.auto_queue = False

        # read enemy player package

        enemy_pouch = list()

        enemy_name = buffer.read_string()
        enemy_wins = buffer.read_int()
        enemy_losses = buffer.read_int()
        enemy_image_mode = buffer.read_string()
        enemy_image_width = buffer.read_int()
        enemy_image_height = buffer.read_int()
        enemy_image_bytes_len = buffer.read_int()
        enemy_image_bytes = buffer.read_bytes(enemy_image_bytes_len)

        enemy_pouch = [enemy_name, enemy_wins, enemy_losses, enemy_image_mode, enemy_image_width, enemy_image_height, enemy_image_bytes]

        enemy_character_names = [buffer.read_string().strip() for i in range(3)]

        first_turn = buffer.read_int()

        time_remaining = buffer.read_int()

        turn_count = buffer.read_int()
        all_turns = list()
        all_execution = list()
        all_random_expenditure = list()
        for _ in range(turn_count):
            used_ability_count = buffer.read_int()
            executed_abilities = list()
            for _ in range(used_ability_count):
                executed_ability = AbilityMessage()
                executed_ability.assign_user_id(buffer.read_int())
                executed_ability.assign_ability_id(buffer.read_int())
                executed_ability.set_primary_target(buffer.read_int())
                ally_targets = buffer.read_int()
                for _ in range(ally_targets):
                    executed_ability.add_to_ally_targets(buffer.read_int())
                enemy_targets = buffer.read_int()
                for _ in range(enemy_targets):
                    executed_ability.add_to_enemy_targets(buffer.read_int())
                executed_abilities.append(executed_ability)
            execution_order = list()
            execution_order_count = buffer.read_int()
            for _ in range(execution_order_count):
                execution_order.append(buffer.read_int())
            random_spent = list()
            for _ in range(4):
                random_spent.append(buffer.read_int())
            
            all_random_expenditure.append(random_spent)    
            all_turns.append(executed_abilities)
            all_execution.append(execution_order)

        pool_count = buffer.read_int()
        energy_pools = list()
        for _ in range(pool_count):
            energy_pool = list()
            for _ in range(6):
                energy_pool.append(buffer.read_int())
            energy_pools.append(energy_pool)

        energy = [0, 0, 0, 0]
        if first_turn:
            energy[energy_pools[0][0]] += 1
        else:
            for i in range(3):
                energy[energy_pools[0][i]] += 1
                
        energy_pools = energy_pools[1:]

        self.scene_manager.char_select.selected_team = [Character(name) for name in player_character_names]

        self.scene_manager.char_select.start_battle(enemy_character_names, enemy_pouch, energy, seed)



        # update battle scene
        self.scene_manager.battle_scene.full_update()

        # update managers
        for manager in self.scene_manager.battle_scene.player_display.team.character_managers:
            manager.update()

        
        self.scene_manager.battle_scene.handle_reconnection_catchup(first_turn, all_turns, all_execution, energy_pools, all_random_expenditure, time_remaining)

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
        seed = buffer.read_int()
        first_turn = buffer.read_int()
        if first_turn:
            self.scene_manager.battle_scene.waiting_for_turn = False
            self.scene_manager.battle_scene.moving_first = True
        else:
            self.scene_manager.battle_scene.waiting_for_turn = True
            self.scene_manager.battle_scene.moving_first = False
        
        start_pool = [buffer.read_int() for i in range(6)]
        energy = [0, 0, 0, 0]
        if first_turn:
            energy[start_pool[0]] += 1
        else:
            for i in range(3):
                energy[start_pool[i]] += 1
        names = [buffer.read_string().strip() for i in range(3)]
        player_pouch = list()

        player_name = buffer.read_string()
        player_wins = buffer.read_int()
        player_losses = buffer.read_int()
        player_image_mode = buffer.read_string()
        player_image_width = buffer.read_int()
        player_image_height = buffer.read_int()
        player_image_bytes_len = buffer.read_int()
        player_image_bytes = buffer.read_bytes(player_image_bytes_len)

        player_pouch = [player_name, player_wins, player_losses, player_image_mode, player_image_width, player_image_height, player_image_bytes]


        self.scene_manager.char_select.start_battle(names, player_pouch, energy, seed)


    