import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf
from animearena import engine
from PIL import Image
import importlib.resources
from pathlib import Path

RESOURCES = Path(__file__).parent.parent.parent / "resources"

WHITE = sdl2.SDL_Color(255, 255, 255)
def get_image_from_path(file_name: str) -> Image:
    with importlib.resources.path('animearena.resources', file_name) as path:
        return Image.open(path)


class TutorialScene(engine.Scene):

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_manager = scene_manager
        self.stored_player = None
        self.tutorial_slides = [get_image_from_path(f"{i+1}.png") for i in range(78)]
        self.current_slide = 0
        self.slide_region = self.region.subregion(100, 0, 900, 1100)
        self.left_button_region = self.region.subregion(0, 525, 50, 50)
        self.right_button_region = self.region.subregion(1050, 525, 50, 50)
        self.exit_button_region = self.region.subregion(1050, 0, 50, 50)
        self.left_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["left_arrow"], 50, 50))
        self.left_button.click += self.left_click

        self.right_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["right_arrow"], 50, 50))
        self.right_button.click += self.right_click

        self.exit_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.scene_manager.surfaces["exclusive_icon"], 50, 50))
        self.exit_button.click += self.exit_click
    
    def render_navigation_buttons(self):
        self.left_button_region.clear()
        self.right_button_region.clear()
        self.exit_button_region.clear()
        if self.current_slide > 0:
            self.left_button_region.add_sprite(self.left_button, 0, 0)
        
        if self.current_slide < len(self.tutorial_slides) - 1:
            self.right_button_region.add_sprite(self.right_button, 0, 0)

        self.exit_button_region.add_sprite(self.exit_button, 0, 0)


    def render_tutorial_slide(self):
        self.slide_region.clear()
        self.slide_region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.tutorial_slides[self.current_slide]), free=True), 0, 0)

    def full_render(self):

        self.region.clear()
        self.region.add_sprite(self.sprite_factory.from_color(WHITE, self.region.size()), 0, 0)
        self.render_navigation_buttons()
        self.render_tutorial_slide()
        
    def start_tutorial(self, player):
        self.current_slide = 0
        self.stored_player = player
        self.full_render()

    def left_click(self, button, sender):
        self.current_slide -= 1
        self.full_render()

    def right_click(self, button, sender):
        self.current_slide += 1
        self.full_render()

    def exit_click(self, button, sender):
        self.scene_manager.return_to_select(self.stored_player)


def make_tutorial_scene(scene_manager) -> TutorialScene:
    scene = TutorialScene(scene_manager, sdl2.ext.SOFTWARE)

    return scene
