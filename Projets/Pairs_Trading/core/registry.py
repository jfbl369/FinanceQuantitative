"""
Decouverte des strategies actives.

config/active_strategies.yaml est LE fichier qui decide ce qui tourne :
activer ou desactiver une strategie ne touche a aucun code, juste a cette
liste. Chaque entree pointe vers une classe qui implemente
core.interfaces.Strategy et se construit sans argument.
"""

import importlib
from pathlib import Path

import yaml

from core.interfaces import Strategy

ACTIVE_STRATEGIES_PATH = Path(__file__).parent.parent / "config" / "active_strategies.yaml"


def load_active_strategies(path: Path = ACTIVE_STRATEGIES_PATH) -> list[Strategy]:
    cfg = yaml.safe_load(path.read_text()) or {}
    strategies = []
    for entry in cfg.get("active", []):
        module = importlib.import_module(entry["module"])
        cls = getattr(module, entry["class"])
        strategies.append(cls())
    return strategies
