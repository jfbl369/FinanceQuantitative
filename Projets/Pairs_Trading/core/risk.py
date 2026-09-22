"""
Limites de risque globales, appliquees avant chaque entree -- quelle que
soit la strategie qui l'a proposee.

Avant cette refonte, rien ne plafonnait l'exposition totale si plusieurs
paires s'ouvraient en meme temps, et rien n'arretait le bot apres une
serie de pertes anormale. Les seuils viennent de config/settings.yaml,
pas de code en dur, pour rester modifiables sans toucher a l'execution.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from core.portfolio import Portfolio

SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


@dataclass
class RiskLimits:
    max_gross_exposure_usdt: float
    max_concurrent_positions: int
    max_cumulative_loss_usdt: float  # negatif : -5000 = kill switch a -5000 USDT

    @classmethod
    def from_settings(cls, path: Path = SETTINGS_PATH) -> "RiskLimits":
        cfg = yaml.safe_load(path.read_text())["risk"]
        return cls(
            max_gross_exposure_usdt=float(cfg["max_gross_exposure_usdt"]),
            max_concurrent_positions=int(cfg["max_concurrent_positions"]),
            max_cumulative_loss_usdt=float(cfg["max_cumulative_loss_usdt"]),
        )


class RiskManager:
    """
    Un seul point de decision : execution/bot.py doit appeler can_open()
    avant tout ordre d'ouverture. Aucune autre couche ne doit re-implementer
    ces verifications.
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def can_open(
        self, portfolio: Portfolio, notional_a: float, notional_b: float
    ) -> tuple[bool, str]:
        if portfolio.realized_pnl <= self.limits.max_cumulative_loss_usdt:
            return False, (
                f"kill switch : perte cumulee {portfolio.realized_pnl:,.2f} USDT "
                f"<= limite {self.limits.max_cumulative_loss_usdt:,.2f}"
            )

        if portfolio.n_open_positions() >= self.limits.max_concurrent_positions:
            return False, (
                f"positions concurrentes max atteinte "
                f"({self.limits.max_concurrent_positions})"
            )

        projected_gross = portfolio.gross_exposure() + notional_a + notional_b
        if projected_gross > self.limits.max_gross_exposure_usdt:
            return False, (
                f"exposition brute projetee {projected_gross:,.2f} USDT "
                f"> limite {self.limits.max_gross_exposure_usdt:,.2f}"
            )

        return True, ""
