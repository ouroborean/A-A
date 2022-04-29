"""Main game initialization and event loop."""

from asyncio.exceptions import CancelledError
import logging
import asyncio
import contextvars
import time
import sdl2
import sdl2.ext
import sdl2.sdlttf
from playsound import playsound
from animearena import client
from animearena.byte_buffer import ByteBuffer
from animearena.scene_manager import SceneManager
from pydub import AudioSegment
from pydub.playback import play



WHITE = sdl2.SDL_Color(255, 255, 255)

MAX_RETRIES = 5
CURRENT_TIMEOUTS = 0

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
    
    
    
    
    with SceneManager(window) as scene_manager:
    
        cm = client.ConnectionHandler(scene_manager)
        
        scene_manager.bind_connection(cm)

        scene_manager.initialize_scenes()

        scene_manager.set_scene_to_current(scene_manager.login_scene)

        server_loop_task = server_loop(scene_manager)
        
        game_loop_task = game_loop(scene_manager, window, server_loop_task)
        
        asyncio.run(game_loop_task)
        
        sdl2.ext.quit()
        
        return 0


target_fps = contextvars.ContextVar('target_fps', default=60)

async def server_loop(scene_manager: SceneManager):
    VERSION_CHECKED = False
    cancelled = False
    timeouts = 0
    while not scene_manager.connected:
        try:
            #34.125.127.187
            reader, writer = await asyncio.wait_for(asyncio.open_connection("34.125.127.187", 5692, limit = 1024 * 256, happy_eyeballs_delay=0.25), 1)
            
            scene_manager.connected = True
            scene_manager.connection.writer = writer
        except asyncio.TimeoutError:
            if timeouts < MAX_RETRIES:
                timeouts += 1
            else:
                #TODO Display server connection error message
                pass
        except asyncio.CancelledError:
            cancelled = True
            break
    while True and not cancelled:
        if not VERSION_CHECKED:
            print("Checking version")
            scene_manager.connection.send_version_request()
            VERSION_CHECKED = True
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
            scene_manager.dispatch_message(packet_id, data)
            buffer.clear()
        
        await asyncio.sleep(.1)
    

async def game_loop(scene_manager: SceneManager, window: sdl2.ext.Window, server_loop_task):
    running = True
    tasktask = asyncio.create_task(server_loop_task)
    while running:
        start = time.monotonic()
        scene_manager.reset_event_trigger()
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                tasktask.cancel()
                await tasktask
                if scene_manager.current_scene == scene_manager.battle_scene:
                    scene_manager.battle_scene.timer.cancel()
                running = False
                break
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN and scene_manager.current_scene == scene_manager.login_scene and not scene_manager.login_scene.clicked_login and not scene_manager.login_scene.clicked_register and scene_manager.connected:
                    scene_manager.play_sound(scene_manager.sounds["click"])
                    scene_manager.login_scene.send_login()
                if event.key.keysym.sym == sdl2.SDLK_TAB and scene_manager.current_scene == scene_manager.login_scene:
                    scene_manager.login_scene.tab_between_boxes()
                if event.key.keysym.sym == sdl2.SDLK_BACKSPACE and scene_manager.current_scene == scene_manager.login_scene:
                    scene_manager.login_scene.prepare_backspace()
            for sprite in scene_manager.current_scene.eventables():
                scene_manager.uiprocessor.dispatch(sprite, event)
                if scene_manager.current_scene.triggered_event:
                    break
        scene_manager.battle_scene.target_clicked = False
        if scene_manager.current_scene == scene_manager.battle_scene:
            if not scene_manager.battle_scene.waiting_for_turn:
                scene_manager.battle_scene.draw_timer_region()
            scene_manager.battle_scene.check_for_hp_bar_changes()
            scene_manager.battle_scene.get_hovered_button()
            scene_manager.battle_scene.show_hover_text()
        if scene_manager.current_scene.window_closing:
            scene_manager.current_scene.window_closing = False
            scene_manager.current_scene.window_up = False
        scene_manager.spriterenderer.render(scene_manager.current_scene.renderables())
        window.refresh()
        done = time.monotonic()
        elapsed_time = start - done
        scene_manager.frame_count += 1
        if scene_manager.frame_count > 60:
            scene_manager.frame_count = 0
        sleep_duration = max((1.0 / target_fps.get()) - elapsed_time, 0)
        await asyncio.sleep(sleep_duration)
    logging.debug("Broke game loop!")

main()