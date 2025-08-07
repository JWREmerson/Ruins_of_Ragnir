# External Imports
import json
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar

# Internal Imports
from config import DATA_DIR

# Pull classes from models.py
from models import (
    GateCard,
    HeroCard,
    MinionCard,
    GearCard,
    SpellCard,
    RuinCard,
    RelicCard,
    GlyphCard,
)

T = TypeVar("T")
def _load_json(filename: str) -> Any:
    path = Path(DATA_DIR) / filename
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_cards(filename: str, model: Type[T], key: str = "cards") -> List[T]:
    raw = _load_json(filename)
    entries = raw.get(key)
    if entries is None:
        raise KeyError(f"Expected top-level key '{key}' in {filename}")

    instances: List[T] = []
    
    for entry in entries:
        data = entry.copy()
        # Map JSON 'rules' text to the dataclass 'rules_text' field
        rules_text = data.pop("rules", "")
        # Remove any JSON-only fields
        data.pop("card_type", None)
        # Insert into kwargs for dataclass
        data["rules_text"] = rules_text
        instances.append(model(**data))

    return instances

# Allows for loading of all card types from .json and loading it into the class
def load_gates() -> List[GateCard]:
    return _load_cards("GateCards.json", GateCard)

def load_heroes() -> List[HeroCard]:
    return _load_cards("HeroCards.json", HeroCard)

def load_ruins() -> List[RuinCard]:
    return _load_cards("RuinCards.json", RuinCard)

def load_minions() -> List[MinionCard]:
    return _load_cards("MinionCards.json", MinionCard)

def load_gears() -> List[GearCard]:
    return _load_cards("GearCards.json", GearCard)

def load_spells() -> List[SpellCard]:
    return _load_cards("SpellCards.json", SpellCard)

def load_relics() -> List[RelicCard]:
    return _load_cards("RelicCards.json", RelicCard)

def load_glyphs() -> List[GlyphCard]:
    return _load_cards("GlyphCards.json", GlyphCard)

def load_all_cards() -> Dict[str, List[Any]]:
    return {
        "minions": load_minions(),
        "gears": load_gears(),
        "spells": load_spells(),
        "ruins": load_ruins(),
        "gates": load_gates(),
        "heroes": load_heroes(),
    }