from PIL import Image

from animearena import mission

class Player:

    def __init__(self, name: str, wins: int, losses: int, avatar: Image, mission_data: str = ""):
        self.name = name
        self.wins = wins
        self.losses = losses
        self.avatar = avatar
        self.mission_data = mission_data
        if mission_data:
            self.missions = self.get_current_mission_progress(mission_data)
    
    def get_current_mission_progress(self, mission_data:str) -> dict:
        mission_dict = {}
        for mission_set in mission_data.split("|"):
            mission_data = mission_set.split("/")
            mission_dict[mission_data[0]] = []
            for i in range(5):
                mission_dict[mission_data[0]].append(mission_data[i+1])
        return mission_dict



