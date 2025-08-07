# Pull in the card‐dataclasses from your top-level models.py
from models import (
    GateCard,
    RuinCard,
    HeroCard,
    MinionCard,
    GearCard,
    SpellCard,
    RelicCard,
    GlyphCard,
)

from .loader import (
    load_gates,
    load_ruins,
    load_heroes,
    load_minions,
    load_gears,
    load_spells,
    load_relics,
    load_glyphs,
    load_all_cards,
)