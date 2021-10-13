"""Main game initialization and event loop."""

from asyncio.exceptions import CancelledError
import logging
from typing import Tuple
import asyncio
import contextvars
import time
import sys


import sdl2
import sdl2.ext
import sdl2.sdlttf

from animearena import engine, character_select_scene, battle_scene, client
from animearena.byte_buffer import ByteBuffer
from animearena.scene_manager import SceneManager

def main():
    """Main game entry point."""
    logging.basicConfig(level=logging.DEBUG,
                        format="%(levelname)s:%(relativeCreated)d:%(module)s:%(message)s")
    logging.getLogger("PIL").setLevel(69) # turn off PIL logging
    sdl2.ext.init()
    logging.debug("SDL2 video system initialized")
    sdl2.sdlttf.TTF_Init()
    logging.debug("SDL2 font system initialized")

    window = sdl2.ext.Window("Anime Arena", size=(800, 700))
    window.show()
    scene_manager = SceneManager(window)
    cm = client.ConnectionHandler(scene_manager)
    scene_manager.bind_connection(cm)
    uiprocessor = sdl2.ext.UIProcessor()

    scene_manager.char_select = character_select_scene.make_character_select_scene(scene_manager)

    scene_manager.battle_scene = battle_scene.make_battle_scene(scene_manager)

    scene_manager.set_scene_to_current(scene_manager.char_select)

    scene_manager.spriterenderer.render(scene_manager.current_scene.renderables())

    server_loop_task = server_loop(scene_manager)
    game_loop_task = game_loop(scene_manager, uiprocessor, window, server_loop_task)
    
    
    
    asyncio.run(game_loop_task)
    
        
    sdl2.ext.quit()
    return 0


target_fps = contextvars.ContextVar('target_fps', default=60)

async def server_loop(scene_manager):
    reader, writer = await asyncio.open_connection("127.0.0.1", 5692)
    scene_manager.connection.writer = writer
    while True:
        try:
            data = await reader.read(4096)
        except CancelledError:
            writer.close()
            await writer.wait_closed()
            break
        if data:
            buffer = ByteBuffer()
            buffer.write_bytes(data)
            packet_id = buffer.read_int(False)
            logging.debug(f"Received packet id: {packet_id}")
            scene_manager.connection.packets[packet_id](data)
            buffer.clear()
        
        await asyncio.sleep(.1)
    

async def game_loop(scene_manager, uiprocessor, window, server_loop_task):
    running = True
    tasktask = asyncio.create_task(server_loop_task)
    while running:
        start = time.monotonic()

        scene_manager.current_scene.triggered_event = False
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                tasktask.cancel()
                await tasktask
                running = False
                break

            for sprite in scene_manager.current_scene.eventables():
                uiprocessor.dispatch(sprite, event)
                if scene_manager.current_scene.triggered_event:
                    break

        scene_manager.spriterenderer.render(scene_manager.current_scene.renderables())
        window.refresh()
        done = time.monotonic()
        elapsed_time = start - done
        sleep_duration = max((1.0 / target_fps.get()) - elapsed_time, 0)
        await asyncio.sleep(sleep_duration)
    logging.debug("Broke game loop!")

main()