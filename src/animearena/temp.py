    def __init__(self, scene_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scene_manager = scene_manager

        fontpath = str.encode(f"{RESOURCES / FONT_FILENAME}")
        self.font = sdl2.sdlttf.TTF_OpenFont(fontpath, FONTSIZE)

        self.team_region = self.region.subregion(x=5, y=145, width = 670, height = 750)
        self.character_regions = [self.player_team_region.subregion(x = 0, y=i * 250, width=670, height = 230) for i in range(3)]
        self.enemy_team_region = self.region.subregion(x=765, y = 145, width = 130, height = 750)
        self.enemy_character_regions = [self.enemy_team_region.subregion(x = 0, y = i * 250, width = 130, height = 230) for i in range(3)]
        self.turn_end_region = self.region.subregion(x=375, y=5, width=150, height = 200)
        self.energy_display_region = self.region.subregion(x=205, y=5, width=165, height = 53)