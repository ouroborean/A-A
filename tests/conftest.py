import logging

import pytest

@pytest.fixture(autouse=True)
def disable_PIL_logging(caplog):
    caplog.set_level(logging.ERROR, logger="PIL.PngImagePlugin")

