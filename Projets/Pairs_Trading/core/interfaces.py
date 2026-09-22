"""
Contrats communs a toute strategie. Ce module ne connait aucune strategie
concrete : execution/bot.py et core/registry.py ne parlent qu'a travers
ces classes, jamais a une implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# Actions possibles pour un signal, communes a toutes les strategies.
ACTION_ENTER = "entree"
ACTION_EXIT = "sortie"
ACTION_STOP = "stop"
ACTION_WAIT = "attente"


@dataclass
class Signal:
    """
    Sortie d'une strategie pour un instrument donne, a un instant donne.

    `legs` transporte tout ce que l'execution a besoin de connaitre pour
    passer les ordres (symboles, prix, beta, ...) sans que execution/
    ait a re-interroger la strategie : Signal est auto-suffisant.
    """
    strategy: str
    instrument_id: str
    action: str
    side: int | None
    score: float
    legs: dict[str, Any] = field(default_factory=dict)
    ts: str = ""


@dataclass
class Position:
    """Position ouverte, telle que suivie par core.portfolio.Portfolio."""
    instrument_id: str
    strategy: str
    side: int
    notional_a: float
    notional_b: float
    entry: dict[str, Any]


class Strategy(ABC):
    """
    Toute strategie active doit implementer cette interface.

    Le cycle de vie est stateless du point de vue du runner : a chaque
    tick, execution/bot.py fournit les donnees de marche et les positions
    actuellement ouvertes pour cette strategie, et recoit en retour la
    liste des signaux a executer. La strategie ne passe jamais d'ordre
    elle-meme -- c'est le role d'execution/order_router.py.
    """

    name: str

    @abstractmethod
    def symbols(self) -> list[str]:
        """Symboles dont la strategie a besoin a chaque tick."""

    @abstractmethod
    def evaluate(
        self,
        market_data: dict[str, pd.DataFrame],
        open_positions: dict[str, Position],
    ) -> list[Signal]:
        """Produit les signaux du tick courant, un par instrument suivi."""
