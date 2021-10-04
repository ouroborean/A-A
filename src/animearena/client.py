from asyncio.streams import StreamReader, StreamWriter
import socket
from animearena.byte_buffer import ByteBuffer
from time import sleep
from typing import Callable

class ConnectionHandler:

    writer: StreamWriter
    waiting_for_opponent: bool

    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self.waiting_for_opponent = False
        self.packets: dict[int, Callable] = {
            0: self.handle_start_package,
            1: self.handle_match_communication
        }
    
    def send_message(self, message: str):
        try:
            self.writer.write(message.encode('utf-8'))
        except BlockingIOError:
            pass
        except OSError:
            pass
    
    def handle_match_communication(self, data:list[bytes]):

        buffer = ByteBuffer()
        buffer.write_bytes(data)
        buffer.read_int()
        pickle = bytearray(buffer.buff[buffer.read_pos:])

        self.scene_manager.battle_scene.unpickle_match(pickle)
        buffer.clear()


    def send_team_names(self, names: list[str]):
        
        buffer = ByteBuffer()
        buffer.write_int(0)
        for name in names:
            buffer.write_string(name)
        if self.writer.write(buffer.get_byte_array()):
            self.waiting_for_opponent = True
        buffer.clear()
        
    def send_match_communication(self, data:bytes):
        buffer = ByteBuffer()
        buffer.write_int(1)
        buffer.write_bytes(data)
        self.writer.write(buffer.get_byte_array())
        buffer.clear()

    def check_for_message(self):
        msg = ""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(0)
            s.connect(("127.0.0.1", 5692))
            msg = s.recv(4096)
        except BlockingIOError:
            pass
        except OSError:
            pass
        if msg:
            print(msg.decode('utf-8'))

    def handle_start_package(self, data: list[bytes]):

        if self.waiting_for_opponent:
            self.waiting_for_opponent = False
        buffer = ByteBuffer()
        buffer.write_bytes(data)
        packet_id = buffer.read_int()
        first_turn = buffer.read_int()
        if first_turn:
            self.scene_manager.battle_scene.waiting_for_turn = False
        else:
            self.scene_manager.battle_scene.waiting_for_turn = True
        names = [buffer.read_string().strip() for i in range(3)]
        self.scene_manager.char_select.start_battle(names)


    