from pathlib import Path
import importlib.resources
import os

import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
from playsound import playsound
from animearena import engine
from animearena import resource_manager

BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)
FONTSIZE = 16

def play_sound(file_name: str):
    # with importlib.resources.path('animearena.resources', file_name) as path:
    #     playsound(str(path), False)
    pass

class LoginScene(engine.Scene):

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_manager = scene_manager
        self.font = resource_manager.init_font(FONTSIZE)
        self.username_entry = False
        self.password_entry = False
        self.clicked_login = False
        self.clicked_register = False
        self.updating = False
        self.message = ""
        self.username_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
        self.username_box.pressed += self.select_username
        self.username_box.input += self.edit_username_text
        self.password_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
        self.password_box.pressed += self.select_password
        self.password_box.input += self.edit_password_text
        self.login_region = self.region.subregion(x=300, y=200, width=200, height=300)
        self.update_panel_region = self.region.subregion(144, 158, 0, 0)
        self.update_panel_border = self.sprite_factory.from_color(BLACK, (516, 388))
        self.update_message = self.create_text_display(self.font, "Checking for new version! Please wait a moment.", WHITE, BLACK, 0, 0, 400)

    def full_render(self):
        self.region.clear()
        self.region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        self.render_login_region()
        self.render_update_panel_region()

    def render_update_panel_region(self):
        self.update_panel_region.clear()
        if self.updating:
            self.add_bordered_sprite(self.update_panel_region, self.update_panel_border, WHITE, 0, 0)
            self.update_panel_region.add_sprite(self.update_message, 58, 100)

    def prepare_backspace(self):
        if self.username_entry:
            current_text = self.username_box.text
            self.username_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
            self.username_box.pressed += self.select_username
            self.username_box.input += self.edit_username_text                        
            self.scene_manager.uiprocessor.activate(self.username_box)
            self.username_box.text = current_text
        elif self.password_entry:
            current_text = self.password_box.text
            self.password_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
            self.password_box.pressed += self.select_password
            self.password_box.input += self.edit_password_text
            self.scene_manager.uiprocessor.activate(self.password_box)
            self.password_box.text = current_text
        self.handle_backspace()

    def handle_backspace(self):
        if self.username_entry:
            self.username_box.text = self.username_box.text[:-1]
            text_surface = sdl2.sdlttf.TTF_RenderText_Shaded(self.font, str.encode(self.username_box.text), BLACK, WHITE)
            sdl2.surface.SDL_BlitSurface(text_surface, None, self.username_box.surface,
                                         sdl2.SDL_Rect(2, 2, 0, 0))
        elif self.password_entry:
            self.password_box.text = self.password_box.text[:-1]
            hidden_string = ""
            for i in range(len(self.password_box.text)):
                hidden_string += "*"
            text_surface = sdl2.sdlttf.TTF_RenderText_Shaded(self.font, str.encode(hidden_string), BLACK, WHITE)
            sdl2.surface.SDL_BlitSurface(text_surface, None, self.password_box.surface,
                                            sdl2.SDL_Rect(2, 2, 0, 0))
        self.full_render()

    def render_login_region(self):
        self.login_region.clear()
        self.add_bordered_sprite(self.login_region, self.sprite_factory.from_color(BLACK, self.login_region.size()), WHITE, 0, 0)
        if self.message != "":
            message_label = self.create_text_display(self.font, self.message, WHITE, BLACK, 0, 0, 170, height = 40)
            self.login_region.add_sprite(message_label, 25, 20)
        name_label = self.create_text_display(self.font, "Username", WHITE, BLACK, 0, 0, 80)
        self.login_region.add_sprite(name_label, 25, 70)
        password_label = self.create_text_display(self.font, "Password", WHITE, BLACK, 0, 0, 80)
        self.login_region.add_sprite(password_label, 25, 170)
        if self.username_entry:
            self.add_bordered_sprite(self.login_region, self.username_box, AQUA, 25, 100)
        else:
            self.login_region.add_sprite(self.username_box, 25, 100)
        if self.password_entry:
            self.add_bordered_sprite(self.login_region, self.password_box, AQUA, 25, 200)
        else:
            self.login_region.add_sprite(self.password_box, 25, 200)
        login_button = self.create_text_display(self.font, "Log In", WHITE, BLACK, 18, 3, 80)
        login_button.click += self.login_click
        register_button = self.create_text_display(self.font, "Register", WHITE, BLACK, 11, 3, 80)
        register_button.click += self.register_click
        self.add_bordered_sprite(self.login_region, login_button, WHITE, 15, 250)

        self.add_bordered_sprite(self.login_region, register_button, WHITE, 105, 250)
        
    def receive_message(self, message: str):
        self.message = message
        self.full_render()

    def login_click(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.send_login()
    
    def send_login(self):
        if not self.clicked_login and not self.clicked_register and self.scene_manager.connected:
            self.clicked_login = True
            self.scene_manager.username_raw = self.username_box.text.strip()
            self.scene_manager.password_raw = self.password_box.text.strip()
            self.scene_manager.connection.request_login_nonce()

    def register_click(self, button, sender):
        if not self.clicked_login and not self.clicked_register and self.scene_manager.connected:
            play_sound(self.scene_manager.sounds["click"])
            self.clicked_register = True
            self.scene_manager.connection.send_registration(self.username_box.text, self.password_box.text)
            

    def select_username(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.username_entry = True
        self.password_entry = False
        self.full_render()
        
    def print_text_on_box(self, text, box):
        text_surface = sdl2.sdlttf.TTF_RenderText_Shaded(self.font, str.encode(text), BLACK, WHITE)
        sdl2.surface.SDL_BlitSurface(text_surface, None, box.surface, sdl2.SDL_Rect(2, 2, 0, 0))

    def edit_username_text(self, entry, event):
        self.print_text_on_box(entry.text, entry)
    
    def edit_password_text(self, entry, event):
        hidden_string = ""
        for i in range(len(self.password_box.text)):
            hidden_string += "*"
        self.print_text_on_box(hidden_string, entry)
        
    def tab_between_boxes(self):
        if self.username_entry:
            self.scene_manager.play_sound(self.scene_manager.sounds["click"])
            self.username_entry = False
            self.password_entry = True
            current_text = self.password_box.text
            self.password_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
            self.password_box.pressed += self.select_password
            self.password_box.input += self.edit_password_text
            self.scene_manager.uiprocessor.activate(self.password_box)
            self.password_box.text = current_text
            hidden_string = ""
            for i in range(len(self.password_box.text)):
                hidden_string += "*"
            self.print_text_on_box(hidden_string, self.password_box)
            self.full_render()
        elif self.password_entry:
            self.scene_manager.play_sound(self.scene_manager.sounds["click"])
            self.password_entry = False
            self.username_entry = True
            current_text = self.username_box.text
            self.username_box = self.ui_factory.from_color(sdl2.ext.TEXTENTRY, WHITE, (150, 25))
            self.username_box.pressed += self.select_username
            self.username_box.input += self.edit_username_text                        
            self.scene_manager.uiprocessor.activate(self.username_box)
            self.username_box.text = current_text
            self.print_text_on_box(current_text, self.username_box)
            self.full_render()
            

    def select_password(self, button, sender):
        play_sound(self.scene_manager.sounds["click"])
        self.username_entry = False
        self.password_entry = True
        self.full_render()
        

def make_login_scene(scene_manager) -> LoginScene:

    scene = LoginScene(scene_manager, sdl2.ext.SOFTWARE)


    assets = {
        "right_arrow": "arrowright.png",
        "left_arrow": "arrowleft.png",
        "background": "bright_background.png",
        "PHYSICAL": "physicalEnergy.png",
        "SPECIAL": "specialEnergy.png",
        "MENTAL": "mentalEnergy.png",
        "WEAPON": "weaponEnergy.png",
        "RANDOM": "randomEnergy.png",
        "selected": "selected_pane.png",
        "ally": "ally_pane.png",
        "locked": "null_pane.png",
        "enemy": "enemy_pane.png",
        "start": "start_button.png",
        "default": "default.png"
    }
    scene.load_assets(**assets)
    scene.full_render()
    return scene

