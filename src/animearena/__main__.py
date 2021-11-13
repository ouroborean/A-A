"""Main game initialization and event loop."""

from asyncio.exceptions import CancelledError
import logging
import asyncio
import contextvars
import time
import easygui
import sys
import os
import sdl2
import sdl2.ext
import sdl2.sdlttf
import PIL.Image
from playsound import playsound
from animearena import character_select_scene
from animearena import battle_scene
from animearena import login_scene
from animearena import client
from animearena.byte_buffer import ByteBuffer
from animearena.scene_manager import SceneManager
from pydub import AudioSegment
from pydub.playback import play




WHITE = sdl2.SDL_Color(255, 255, 255)

def main():
    """Main game entry point."""
    print('getcwd:      ', os.getcwd())
    
    logging.basicConfig(level=logging.DEBUG,
                        format="%(levelname)s:%(relativeCreated)d:%(module)s:%(message)s")
    logging.getLogger("PIL").setLevel(69) # turn off PIL logging
    sdl2.ext.init()
    logging.debug("SDL2 video system initialized")
    sdl2.sdlttf.TTF_Init()
    logging.debug("SDL2 font system initialized")


    window = sdl2.ext.Window("Anime Arena", size=(800, 700))
    window.show()
    
    uiprocessor = sdl2.ext.UIProcessor()
    scene_manager = SceneManager(window)
    cm = client.ConnectionHandler(scene_manager)
    scene_manager.bind_connection(cm)

    scene_manager.char_select = character_select_scene.make_character_select_scene(scene_manager)

    scene_manager.battle_scene = battle_scene.make_battle_scene(scene_manager)

    scene_manager.login_scene = login_scene.make_login_scene(scene_manager)


    scene_manager.set_scene_to_current(scene_manager.login_scene)
    scene_manager.spriterenderer.render(scene_manager.current_scene.renderables())

    server_loop_task = server_loop(scene_manager)
    game_loop_task = game_loop(scene_manager, uiprocessor, window, server_loop_task)
    
    
    
    asyncio.run(game_loop_task)
    
        
    sdl2.ext.quit()
    return 0


target_fps = contextvars.ContextVar('target_fps', default=60)

async def server_loop(scene_manager):
    max_retries = 5
    timeouts = 0
    cancelled = False
    while not scene_manager.connected:
        try:
            #35.219.128.93
            reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 5692, limit = 1024 * 256, happy_eyeballs_delay=0.25), 1)
            
            scene_manager.connected = True
            scene_manager.connection.writer = writer
        except asyncio.TimeoutError:
            if timeouts < max_retries:
                timeouts += 1
            else:
                #TODO Display server connection error message
                pass
        except asyncio.CancelledError:
            cancelled = True
            break

    while True and not cancelled:
        try:
            data = await reader.readuntil(b'\x1f\x1f\x1f')
        except CancelledError:
            writer.close()
            await writer.wait_closed()
            break
        except asyncio.exceptions.IncompleteReadError:
            break
        except asyncio.exceptions.LimitOverrunError as err:
            print(f"{err.consumed}")
        if data:
            buffer = ByteBuffer()
            buffer.write_bytes(data[:-3])
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
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN and scene_manager.current_scene == scene_manager.login_scene and not scene_manager.login_scene.clicked_login and not scene_manager.login_scene.clicked_register and scene_manager.connected:
                    scene_manager.play_sound(scene_manager.sounds["click"])
                    scene_manager.login_scene.send_login()
                if event.key.keysym.sym == sdl2.SDLK_TAB and scene_manager.current_scene == scene_manager.login_scene:
                    if scene_manager.login_scene.username_entry:
                        scene_manager.play_sound(scene_manager.sounds["click"])
                        scene_manager.login_scene.username_entry = False
                        scene_manager.login_scene.password_entry = True
                        current_text = scene_manager.login_scene.password_box.text
                        scene_manager.login_scene.password_box = scene_manager.login_scene.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
                        scene_manager.login_scene.password_box.pressed += scene_manager.login_scene.select_password
                        scene_manager.login_scene.password_box.input += scene_manager.login_scene.edit_password_text
                        uiprocessor.activate(scene_manager.login_scene.password_box)
                        scene_manager.login_scene.password_box.text = current_text
                        hidden_string = ""
                        for i in range(len(scene_manager.login_scene.password_box.text)):
                            hidden_string += "*"
                        scene_manager.login_scene.print_text_on_box(hidden_string, scene_manager.login_scene.password_box)
                        scene_manager.login_scene.full_render()
                    elif scene_manager.login_scene.password_entry:
                        scene_manager.play_sound(scene_manager.sounds["click"])
                        scene_manager.login_scene.password_entry = False
                        scene_manager.login_scene.username_entry = True
                        current_text = scene_manager.login_scene.username_box.text
                        scene_manager.login_scene.username_box = scene_manager.login_scene.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
                        scene_manager.login_scene.username_box.pressed += scene_manager.login_scene.select_username
                        scene_manager.login_scene.username_box.input += scene_manager.login_scene.edit_username_text                        
                        uiprocessor.activate(scene_manager.login_scene.username_box)
                        scene_manager.login_scene.username_box.text = current_text
                        scene_manager.login_scene.print_text_on_box(current_text, scene_manager.login_scene.username_box)
                        scene_manager.login_scene.full_render()
                if event.key.keysym.sym == sdl2.SDLK_BACKSPACE and scene_manager.current_scene == scene_manager.login_scene:
                    if scene_manager.login_scene.username_entry:
                        current_text = scene_manager.login_scene.username_box.text
                        scene_manager.login_scene.username_box = scene_manager.login_scene.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
                        scene_manager.login_scene.username_box.pressed += scene_manager.login_scene.select_username
                        scene_manager.login_scene.username_box.input += scene_manager.login_scene.edit_username_text                        
                        uiprocessor.activate(scene_manager.login_scene.username_box)
                        scene_manager.login_scene.username_box.text = current_text
                    elif scene_manager.login_scene.password_entry:
                        current_text = scene_manager.login_scene.password_box.text
                        scene_manager.login_scene.password_box = scene_manager.login_scene.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
                        scene_manager.login_scene.password_box.pressed += scene_manager.login_scene.select_password
                        scene_manager.login_scene.password_box.input += scene_manager.login_scene.edit_password_text
                        uiprocessor.activate(scene_manager.login_scene.password_box)
                        scene_manager.login_scene.password_box.text = current_text
                    
                    scene_manager.login_scene.handle_backspace()
            for sprite in scene_manager.current_scene.eventables():
                uiprocessor.dispatch(sprite, event)
                if scene_manager.current_scene.triggered_event:
                    break
        scene_manager.battle_scene.target_clicked = False
        if scene_manager.current_scene == scene_manager.battle_scene:
            for manager in scene_manager.current_scene.player_display.team.character_managers:
                if manager.source.hp != manager.source.current_hp:
                    manager.draw_hp_bar()
            for manager in scene_manager.current_scene.enemy_display.team.character_managers:
                if manager.source.hp != manager.source.current_hp:
                    manager.draw_hp_bar()
        if scene_manager.current_scene.window_closing:
            scene_manager.current_scene.window_closing = False
            scene_manager.current_scene.window_up = False
        scene_manager.spriterenderer.render(scene_manager.current_scene.renderables())
        window.refresh()
        done = time.monotonic()
        elapsed_time = start - done
        sleep_duration = max((1.0 / target_fps.get()) - elapsed_time, 0)
        await asyncio.sleep(sleep_duration)
    logging.debug("Broke game loop!")

main()