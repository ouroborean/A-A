from PIL import Image


class Player:

    def __init__(self, name: str, wins: int, losses: int, avatar: Image):
        self.name = name
        self.wins = wins
        self.losses = losses
        self.avatar = avatar