"""Python test for the helper."""
from src.utils import greet

def test_greet():
    assert greet("world") == "hello, world"
