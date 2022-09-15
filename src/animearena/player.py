from PIL import Image

from animearena.mission import mission_db

class Player:

    def __init__(self, name: str, wins: int, losses: int, avatar: Image, mission_data: str = "", medals: int = 0, missions_complete: dict = {}):
        self.name = name
        self.wins = wins
        self.losses = losses
        self.avatar = avatar
        self.medals = medals
        self.mission_data = mission_data
        self.clan = None
        self.title = "Beta Tester"
        if mission_data:
            self.missions = self.get_current_mission_progress(mission_data)
            if not missions_complete:
                self.missions_complete = self.get_completed_status(mission_data)
            else:
                self.missions_complete = missions_complete
                for name in self.missions.keys():
                    for i in range(5):
                        if self.missions[name][i] >= mission_db[name][i].max and not self.missions_complete[name][i]:
                            self.missions_complete[name][i] = True
                            self.medals += 1

            
    
    def get_current_mission_progress(self, mission_data:str) -> dict:
        mission_dict = {}
        for mission_set in mission_data.split("|"):
            mission_data = mission_set.split("/")
            mission_dict[mission_data[0]] = []
            for i in range(6):
                mission_dict[mission_data[0]].append(int(mission_data[i+1]))
        return mission_dict

    def get_completed_status(self, mission_data:str) -> dict:
        mission_dict = {}
        for mission_set in mission_data.split("|"):
            mission_data = mission_set.split("/")
            mission_dict[mission_data[0]] = []
            for i in range(5):
                mission_dict[mission_data[0]].append(int(mission_data[i+1]) >= mission_db[mission_data[0]][i].max)
        return mission_dict


