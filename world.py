"""Compatibility facade for world generation; scenarios own their definitions."""
from scenarios import THEMES, generate
from scenarios.assets import transport_models
from scenarios.common import PROP_SIZE, edge_key

TRANSPORT_MODELS = transport_models()
