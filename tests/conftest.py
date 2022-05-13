import logging
from typing import Tuple
from animearena.character_manager import CharacterManager
from animearena.effects import Effect
import pytest

@pytest.fixture(autouse=True)
def disable_PIL_logging(caplog):
    caplog.set_level(logging.ERROR, logger="PIL.PngImagePlugin")

def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, Tuple) and isinstance(right, CharacterManager) and op == "in":
        list_of_effects = ""
        for eff in right.source.current_effects:
            list_of_effects += "\n" + f"{eff.name} ({eff.eff_type})"
        return [
            f"{right.source.name} has no effect with type {left[0].name} from {left[1]}! {right.source.name}'s list of effects:{list_of_effects}"
        ]
