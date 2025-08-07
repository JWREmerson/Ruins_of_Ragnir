# External Imports
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any

# Core Data Classes
@dataclass
class Card:
    name: str
    rules_text: str
    rules: Optional[Callable[..., Any]] = None

@dataclass(kw_only=True)
class GateCard(Card):
    terrain: str
    sub_terrain: str = ""
    starting_echoes: int
    exp_hand: int
    relic_hold: int
    gate_defense: int
    gate_health: int
    ability: str
    rules: str = ""
    connections: List[int] = field(default_factory=list)
    card_type: str = field(init=False, default="Gate")

@dataclass(kw_only=True)
class RuinCard(Card):
    limit: int
    terrain: str
    sub_terrain: str = ""
    occupancy: int
    ability: str
    passive: str = ""
    entry: str = ""
    occupy: str = ""
    exit: str = ""
    connections: List[int] = field(default_factory=list)
    card_type: str = field(init=False, default="Ruin")

@dataclass(kw_only=True)
class HeroCard(Card):
    heroname: str
    summon_condition: str
    adv_hand: int
    health: int
    attack: int
    defense: int
    speed: int
    movement: int
    leadership: int
    race: str
    class_type: str
    elements: List[str] = field(default_factory=list)
    spec_move: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    ability: str
    rules: str = ""
    card_type: str = field(init=False, default="Hero")

@dataclass(kw_only=True)
class MinionCard(Card):
    cost: int
    health: int
    attack: int
    defense: int
    speed: int
    movement: int
    race: List[str] = field(default_factory=list)
    class_type: List[str] = field(default_factory=list)
    spec_move: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    ability: str = ""
    rules: str = ""
    deck_type: str = "Adv"
    card_type: str = field(init=False, default="Minion")

@dataclass(kw_only=True)
class RelicCard(Card):
    cost: int
    elements: List[str] = field(default_factory=list)
    relic_type: str
    charges: int
    charging_condition: str
    ability: str = ""
    rules: str = ""
    deck_type: str = "Adv"
    card_type: str = field(init=False, default="Relic")

@dataclass(kw_only=True)
class GearCard(Card):
    cost: int
    gear_type: str
    gear_subtype: str
    weight: int
    elements: List[str] = field(default_factory=list)
    restrictions: str = ""
    ability: str = ""
    rules: str = ""
    deck_type: str = "Adv"
    card_type: str = field(init=False, default="Gear")

@dataclass(kw_only=True)
class SpellCard(Card):
    cost: int
    spell_type: str
    school: str
    casting_criteria: str
    elements: List[str] = field(default_factory=list)
    ability: str = ""
    rules: str = ""
    deck_type: str = "Adv"
    card_type: str = field(init=False, default="Spell")

@dataclass(kw_only=True)
class GlyphCard(Card):
    cost: int
    glyph_type: str
    school: str
    size: int
    target_criteria: str
    elements: List[str] = field(default_factory=list)
    ability: str = ""
    rules: str = ""
    deck_type: str = "Adv"
    card_type: str = field(init=False, default="Glyph")