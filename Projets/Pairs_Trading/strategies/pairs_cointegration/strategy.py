"""
Implementation de core.interfaces.Strategy pour le pairs trading par
cointegration.

Ne passe jamais d'ordre : evaluate() ne fait que lire le marche et
rendre des Signal. C'est execution/bot.py, via execution/order_router.py,
qui decide s'il peut executer (core.risk) et qui parle a l'exchange.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from core.interfaces import Position, Signal, Strategy
from strategies.pairs_cointegration.signals import (
    FLAT, ZSCORE_WINDOW, compute_zscore, decide, entry_side,
)

_CONFIG = yaml.safe_load(
    (Path(__file__).parent / "config.yaml").read_text()
)

# false = dollar-neutral : notional sur A, notional sur B.
# true  = beta-neutral   : notional sur A, notional x beta sur B.
NOTIONAL_PER_LEG = float(_CONFIG["sizing"]["notional_per_leg"])
BETA_HEDGED = bool(_CONFIG["sizing"]["beta_hedged"])

SCREENING_CSV = "screening_results.csv"

# Ne trader que les paires dont le screener a valide la cointegration.
# Passer a True force le trading de paires REJETEES : a n'utiliser que
# pour tester la plomberie du dashboard, jamais pour evaluer une strategie.
ALLOW_REJECTED_PAIRS = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PairsCointegrationStrategy(Strategy):
    name = "pairs_cointegration"

    def __init__(self, screening_csv: str = SCREENING_CSV):
        self.screening_csv = screening_csv
        self._pairs = self._load_pairs()

    def _load_pairs(self) -> list[dict]:
        """Lit screening_results.csv et retourne les paires a suivre."""
        if not os.path.exists(self.screening_csv):
            print(f"[pairs_cointegration] {self.screening_csv} introuvable "
                  f"— lance d'abord screener.py")
            return []

        df = pd.read_csv(self.screening_csv)
        ok = df[df["verdict"] == "OK"]

        if ok.empty and ALLOW_REJECTED_PAIRS:
            print("[pairs_cointegration] AUCUNE paire validee. "
                  "ALLOW_REJECTED_PAIRS=True : je suis quand meme les "
                  "paires rejetees, en observation.")
            ok = df

        return [
            {
                "pair": r["pair"],
                "sym_y": r["sym_y"],
                "sym_x": r["sym_x"],
                "alpha": float(r["alpha"]),
                "beta": float(r["beta"]),
            }
            for _, r in ok.iterrows()
        ]

    def symbols(self) -> list[str]:
        return sorted({s for p in self._pairs for s in (p["sym_y"], p["sym_x"])})

    def evaluate(
        self,
        market_data: dict[str, pd.DataFrame],
        open_positions: dict[str, Position],
    ) -> list[Signal]:
        signals = []
        ts = _now_iso()

        for p in self._pairs:
            instrument_id = p["pair"]

            dy = market_data[p["sym_y"]]["close"]
            dx = market_data[p["sym_x"]]["close"]
            df = pd.concat([dy.rename("y"), dx.rename("x")], axis=1).dropna()

            if len(df) < ZSCORE_WINDOW + 5:
                print(f"[pairs_cointegration] {instrument_id}: pas assez "
                      f"d'historique ({len(df)} barres)")
                continue

            spread = np.log(df["y"]) - (p["alpha"] + p["beta"] * np.log(df["x"]))
            z = compute_zscore(spread).iloc[-1]
            if not np.isfinite(z):
                continue
            z = float(z)

            position = open_positions.get(instrument_id)
            current_side = position.side if position else FLAT

            action = decide(z, current_side)
            side = entry_side(z) if action == "entree" else current_side

            py, px = float(df["y"].iloc[-1]), float(df["x"].iloc[-1])
            notional_a = NOTIONAL_PER_LEG
            notional_b = (
                NOTIONAL_PER_LEG * abs(p["beta"]) if BETA_HEDGED else NOTIONAL_PER_LEG
            )

            signals.append(Signal(
                strategy=self.name,
                instrument_id=instrument_id,
                action=action,
                side=side,
                score=round(z, 4),
                legs={
                    "sym_y": p["sym_y"], "sym_x": p["sym_x"],
                    "alpha": p["alpha"], "beta": p["beta"],
                    "py": py, "px": px,
                    "notional_a": notional_a, "notional_b": notional_b,
                },
                ts=ts,
            ))

        return signals
