import sdl2
import sdl2.ext
import sdl2.surface
import sdl2.sdlttf

from animearena import engine
from animearena import character
from animearena import energy
from animearena.character import Character, character_db
from animearena.ability import Ability
from animearena.engine import FilterType
from animearena.energy import Energy
from animearena.character_manager import CharacterManager

from pathlib import Path
from typing import Union

FONT_FILENAME = "Basic-Regular.ttf"
FONTSIZE = 16
RESOURCES = Path(__file__).parent.parent.parent / "resources"
BLUE = sdl2.SDL_Color(0, 0, 255)
RED = sdl2.SDL_Color(255, 0, 0)
GREEN = sdl2.SDL_Color(50, 190, 50)
PURPLE = sdl2.SDL_Color(255, 60, 255)
AQUA = sdl2.SDL_Color(30, 190, 210)
BLACK = sdl2.SDL_Color(0, 0, 0)
WHITE = sdl2.SDL_Color(255, 255, 255)
TRANSPARENT = sdl2.SDL_Color(255,255,255,255)







class BattleScene(engine.Scene):

    font: sdl2.sdlttf.TTF_Font

    player_team_region: engine.Region
    enemy_team_region: engine.Region
    player_character_regions: list[engine.Region] = []
    player_targeting_regions: list[engine.Region] = []
    enemy_targeting_regions: list[engine.Region] = []
    enemy_character_regions: list[engine.Region] = []
    turn_end_region: engine.Region
    energy_display_region: engine.Region
    player_team: list[CharacterManager] = []
    enemy_team: list[CharacterManager] = []
    player_energy_pool: list[int] = [1,0,1,1,3]
    waiting_for_turn: bool

    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scene_manager = scene_manager

        fontpath = str.encode(f"{RESOURCES / FONT_FILENAME}")
        self.font = sdl2.sdlttf.TTF_OpenFont(fontpath, FONTSIZE)

        self.player_team_region = self.region.subregion(x=5, y=145, width = 670, height = 750)
        self.player_character_regions = [self.player_team_region.subregion(x = 0, y=i * 250, width=670, height = 230) for i in range(3)]
        self.enemy_team_region = self.region.subregion(x=765, y = 145, width = 130, height = 750)
        self.enemy_character_regions = [self.enemy_team_region.subregion(x = 0, y = i * 250, width = 130, height = 230) for i in range(3)]
        self.turn_end_region = self.region.subregion(x=375, y=5, width=150, height = 200)
        self.energy_display_region = self.region.subregion(x=205, y=5, width=165, height = 53)

    @property
    def total_energy(self):
        return self.player_energy_pool[0] + self.player_energy_pool[1] + self.player_energy_pool[2] + self.player_energy_pool[3]

    def full_render(self):
        self.region.add_sprite(self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces["background"])), 0, 0)
        self.render_player_team_region()
        self.render_enemy_team_region()
        self.render_turn_end_region()
        self.render_energy_display_region()

    def render_turn_end_region(self):
        self.turn_end_region.clear()
        turn_end_button = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(self.surfaces["end"], width=150,  height=50))
        #turn_end_click
        self.turn_end_region.add_sprite(turn_end_button, 0, 0)
    
    def render_energy_display_region(self):
        self.energy_display_region.clear()
        background = self.sprite_factory.from_color(WHITE, self.energy_display_region.size())
        self.add_bordered_sprite(self.energy_display_region, background, BLACK, 0, 0)
        row = 0
        column = 0
        for i in range(4):
            energy_sprite = self.sprite_factory.from_surface(self.get_scaled_surface(self.surfaces[Energy(i).name]))
            self.energy_display_region.add_sprite(energy_sprite, x= 5 + (column*60), y=7 + (row * 30))
            energy_counter = self.create_text_display(self.font, f"x {self.player_energy_pool[Energy(i)]}", BLACK, WHITE, 0, 0, 40, 3)
            self.energy_display_region.add_sprite(energy_counter, x=18 + (column*60), y=row * 30)
            column += 1
            if column == 2:
                column = 0
                row += 1
        total_counter = self.create_text_display(self.font, f"T x {self.total_energy}", BLACK, WHITE, x= 0, y=0, width=50, height=3)
        self.energy_display_region.add_sprite(total_counter, x=115, y=13)
            

    def render_enemy_team_region(self):
        self.enemy_team_region.clear()

        for i, region in enumerate(self.enemy_character_regions):
            self.render_enemy_character_region(region, self.enemy_team[i])

    def render_enemy_character_region(self, region: engine.Region, manager: CharacterManager):
        region.clear()

        profile_sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(manager.source.profile_image, flipped=True))
        self.add_bordered_sprite(region, profile_sprite, BLACK, 30, 0)

        
        if manager.source.hp == 100:
            hp_bar = self.sprite_factory.from_color(GREEN, size=(100, 20))
        elif manager.source.hp == 0:
            hp_bar = self.sprite_factory.from_color(RED, size=(100, 20))
        else:
            hp_bar = self.sprite_factory.from_color(BLACK, size=(100, 20))
            green_bar = self.sprite_factory.from_color(GREEN,
                                                                size=(manager.source.hp, 20))
            red_bar = self.sprite_factory.from_color(RED,
                                                                size=(100 - manager.source.hp,
                                                                    20))
            sdl2.surface.SDL_BlitSurface(green_bar.surface, None, hp_bar.surface,
                                            sdl2.SDL_Rect(0, 0, 0, 0))
            sdl2.surface.SDL_BlitSurface(red_bar.surface, None, hp_bar.surface,
                                            sdl2.SDL_Rect(manager.source.hp + 1, 0, 0, 0))
        hp_text = sdl2.sdlttf.TTF_RenderText_Blended(self.font,
                                                        str.encode(f"{manager.source.hp}"), BLACK)

        if manager.source.hp == 100:
            hp_text_x = 38
        elif manager.source.hp > 9:
            hp_text_x = 42
        else:
            hp_text_x = 46

        sdl2.surface.SDL_BlitSurface(hp_text, None, hp_bar.surface,
                                        sdl2.SDL_Rect(hp_text_x, 0, 0, 0))

        self.add_bordered_sprite(region, hp_bar, BLACK, 30, 100)

    def show_ability_details(self, ability:Ability, region: engine.Region):
        self.render_energy_cost(ability, region)
        self.render_cooldown(ability, region)

    def render_energy_cost(self, ability: Ability, region: engine.Region):
        total_energy = 0
        for k, v in ability.cost.items():
            for i in range(v):
                region.add_sprite(
                    self.sprite_factory.from_surface(
                        self.get_scaled_surface(self.surfaces[k.name])),
                    155 + (total_energy * 13), 215)
                total_energy += 1

    def render_cooldown(self, ability: Ability, region: engine.Region):
        cooldown_panel = self.create_text_display(self.font,
                                                  f"CD: {ability.cooldown}",
                                                  BLACK, WHITE, 0, 0, 40, 3)
        region.add_sprite(cooldown_panel, x=615, y=210)

    def render_player_team_region(self):
        self.player_team_region.clear()

        for i, region in enumerate(self.player_character_regions):
            self.render_player_character_region(region, self.player_team[i])

    def render_player_character_region(self, region: engine.Region, manager: CharacterManager):
        region.clear()
        profile_sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(manager.source.profile_image))
        self.add_bordered_sprite(region, profile_sprite, BLACK, 0, 0)

        for i, ability in enumerate(manager.source.current_abilities):
            if self.is_available(ability):
                ability_sprite = self.ui_factory.from_surface(sdl2.ext.BUTTON, self.get_scaled_surface(ability.image))
            else:
                ability_sprite = self.create_selected_version(self.get_scaled_surface(ability.image), FilterType.LOCKED)
            ability_sprite.manager = manager
            ability_sprite.ability = ability
            ability_sprite.click += self.ability_click
            self.add_bordered_sprite(region, ability_sprite, BLACK, 150 + (i * 140), 0)

        if type(region.detail_target) == Ability:
            text = region.detail_target.name + ": " + region.detail_target.desc
        else:
            text = region.detail_target.desc

        info_text_panel = self.create_text_display(self.font, text, BLACK,
                                                   WHITE, 5, 0, 520, 110)
        self.add_bordered_sprite(region, info_text_panel, BLACK, 150, 105)
        
        if type(region.detail_target) == Ability:
            self.show_ability_details(region.detail_target, region)

        if manager.source.hp == 100:
            hp_bar = self.sprite_factory.from_color(GREEN, size=(100, 20))
        elif manager.source.hp == 0:
            hp_bar = self.sprite_factory.from_color(RED, size=(100, 20))
        else:
            hp_bar = self.sprite_factory.from_color(BLACK, size=(100, 20))
            green_bar = self.sprite_factory.from_color(GREEN,
                                                                size=(manager.source.hp, 20))
            red_bar = self.sprite_factory.from_color(RED,
                                                                size=(100 - manager.source.hp,
                                                                    20))
            sdl2.surface.SDL_BlitSurface(green_bar.surface, None, hp_bar.surface,
                                            sdl2.SDL_Rect(0, 0, 0, 0))
            sdl2.surface.SDL_BlitSurface(red_bar.surface, None, hp_bar.surface,
                                            sdl2.SDL_Rect(manager.source.hp + 1, 0, 0, 0))
        hp_text = sdl2.sdlttf.TTF_RenderText_Blended(self.font,
                                                        str.encode(f"{manager.source.hp}"), BLACK)

        if manager.source.hp == 100:
            hp_text_x = 38
        elif manager.source.hp > 9:
            hp_text_x = 42
        else:
            hp_text_x = 46

        sdl2.surface.SDL_BlitSurface(hp_text, None, hp_bar.surface,
                                        sdl2.SDL_Rect(hp_text_x, 0, 0, 0))
        self.add_bordered_sprite(region, hp_bar, BLACK, 0, 100)
    
    def is_available(self, ability: Ability) -> bool:
        if not self.waiting_for_turn and ability.resources_available(self.player_energy_pool):
            return True
        return False

    def populate_battle_scene(self, player_team: list[Character], enemy_team: list[Character]):
        self.player_team = [CharacterManager(char, i) for i, char in enumerate(player_team)]
        self.enemy_team = [CharacterManager(char, i) for i, char in enumerate(enemy_team)]

        for i, region in enumerate(self.player_character_regions):
            region.detail_target = self.player_team[i].source

        self.full_render()

    
    
    def ability_click(self, button, _sender):
        self.player_character_regions[button.manager.id].detail_target = button.ability
        self.full_render()

def make_battle_scene(scene_manager) -> BattleScene:

    scene = BattleScene(scene_manager, sdl2.ext.SOFTWARE, RESOURCES)

    assets = {
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
        "end": "end_button.png"
    }

    
    scene.load_assets(**assets)

    return scene