"""Scenario addons discovered once at application startup."""
from .registry import discover

registry = discover()
THEMES = registry.themes()


def generate(game):
    """Generate the selected scenario using its registered definition."""
    registry[game.theme].generate(game)
