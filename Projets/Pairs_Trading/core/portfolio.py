"""
Etat du portefeuille, transversal a toutes les strategies actives.

Avant cette refonte, chaque paire de pairs_cointegration vivait dans un
dict independant a l'interieur de bot.py : rien n'agregeait l'exposition
ou le P&L au niveau du compte. C'est le trou que ce module comble, et
c'est ce qui permet a core.risk de raisonner sur l'ensemble du book
plutot que paire par paire.

save()/load() existent parce que Portfolio() vivait uniquement en
memoire : chaque redemarrage du process (deploiement, crash, restart
systemd) le remettait a zero, position "flat", meme si une position
etait reellement ouverte l'instant d'avant. Le symptome concret : une
strategie evaluee juste apres un restart, avec un z-score deja au-dela
du seuil d'entree, rouvre une position que le process precedent avait
peut-etre deja ouverte -- le bot n'a aucune memoire de ce qu'il a fait.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core.interfaces import Position

DEFAULT_STATE_PATH = Path(__file__).parent.parent / "portfolio_state.json"


@dataclass
class Portfolio:
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    realized_pnl_by_strategy: dict[str, float] = field(default_factory=dict)
    # Historique (ts, pnl_cumule) pour le drawdown et le dashboard.
    equity_curve: list[tuple[str, float]] = field(default_factory=list)

    def positions_for(self, strategy: str) -> dict[str, Position]:
        """Vue filtree, c'est ce que le runner passe a Strategy.evaluate()."""
        return {
            iid: p for iid, p in self.positions.items() if p.strategy == strategy
        }

    def open_position(self, position: Position) -> None:
        if position.instrument_id in self.positions:
            raise ValueError(
                f"position deja ouverte sur {position.instrument_id}"
            )
        self.positions[position.instrument_id] = position

    def close_position(self, instrument_id: str, net_pnl: float, ts: str) -> Position:
        position = self.positions.pop(instrument_id)
        self.realized_pnl += net_pnl
        self.realized_pnl_by_strategy[position.strategy] = (
            self.realized_pnl_by_strategy.get(position.strategy, 0.0) + net_pnl
        )
        self.equity_curve.append((ts, round(self.realized_pnl, 2)))
        return position

    def gross_exposure(self) -> float:
        """Somme des notionnels des deux jambes, toutes positions confondues."""
        return sum(p.notional_a + p.notional_b for p in self.positions.values())

    def net_exposure(self) -> float:
        """
        Exposition directionnelle residuelle du book : somme signee des
        ecarts jambe A / jambe B. Nulle pour un book parfaitement
        dollar-neutral avec beta=1 partout ; s'ecarte de zero exactement
        dans les cas que les notes de pairs_cointegration signalent comme
        dangereux (beta loin de 1 en mode dollar-neutral).
        """
        return sum(p.notional_a - p.notional_b for p in self.positions.values())

    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = float("-inf")
        dd = 0.0
        for _, pnl in self.equity_curve:
            peak = max(peak, pnl)
            dd = min(dd, pnl - peak)
        return round(dd, 2)

    def n_open_positions(self) -> int:
        return len(self.positions)

    def to_dict(self) -> dict:
        return {
            "positions": {iid: asdict(p) for iid, p in self.positions.items()},
            "realized_pnl": self.realized_pnl,
            "realized_pnl_by_strategy": self.realized_pnl_by_strategy,
            "equity_curve": [list(pt) for pt in self.equity_curve],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        return cls(
            positions={
                iid: Position(**p) for iid, p in data.get("positions", {}).items()
            },
            realized_pnl=float(data.get("realized_pnl", 0.0)),
            realized_pnl_by_strategy=dict(data.get("realized_pnl_by_strategy", {})),
            equity_curve=[tuple(pt) for pt in data.get("equity_curve", [])],
        )

    def save(self, path: Path = DEFAULT_STATE_PATH) -> None:
        """
        Ecriture atomique (fichier temporaire + rename) : un kill en plein
        milieu de l'ecriture (OOM, redemarrage systemd) ne doit jamais
        laisser un JSON tronque que load() ne saurait pas relire.
        """
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict()))
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path = DEFAULT_STATE_PATH) -> "Portfolio":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text()))
