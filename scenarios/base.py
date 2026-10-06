"""Scenario extension contracts and shared lot-based generation hooks."""
from abc import ABC, abstractmethod


class Scenario(ABC):
    """Stateless definition; put per-game state on ``game`` or in local context.

    IDs are stable save/API keys. Order controls the seeded random-theme pool.
    A matching static/scenarios/<id>/index.js supplies browser rendering hooks.
    """
    id = ''
    order = 100
    theme = {}

    @abstractmethod
    def generate(self, game):
        """Populate authoritative terrain, structures, traversal and scenery."""


class LotScenario(Scenario):
    """Reusable generator for rectangular buildings with rooms and roof access."""
    road_width = 5
    cross_road = False
    roadside = False
    industrial = False
    face_road = False
    rural_levels = False
    interior_ladders = False

    def generate(self, game):
        from .buildings import generate_lots
        generate_lots(game, self)

    @abstractmethod
    def plan(self, game):
        """Set tiles/road coordinates; return (building-lot list, local context)."""

    def building_name(self, game, index):
        return game.rng.choice(self.theme['names'])

    def building_levels(self, game, lot, index, archetype):
        r=game.rng
        levels=r.choice([2,2,3,4]) if archetype=='residential' and not self.rural_levels else r.choice([1,1,2]) if archetype in ('commercial','industrial','rural') else r.choice([1,2,2,3])
        if self.rural_levels:levels=r.choice([1,1,2])
        if index==0 and not self.rural_levels:levels=max(2,levels)
        return levels

    def configure_building(self, game, building, lot, index):
        """Customize building appearance before geometry is constructed."""

    def wall_archetype(self, building, original):
        return building['archetype']

    def double_door(self, building, side, level, along, entrance):
        return False

    def portal_kind(self, building, level, kind):
        return kind

    def open_interior(self, building):
        return False

    def place_props(self, game, context):
        """Append props and their blocked cells, preserving traversal routes."""

    def scenery_details(self, game, context):
        return dict(road_width=self.road_width)
