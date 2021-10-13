
from animearena.character import Character



class CharacterManager():
    source:Character
    def __init__(self, character:Character, id: int):
        self.id = id
        self.source = character