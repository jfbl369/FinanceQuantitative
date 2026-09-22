"""
Est-ce que le hedge ratio tient dans le temps ?

On recalcule beta sur des fenetres glissantes. Si beta bouge peu, la
relation est structurelle et le hedge tiendra demain. S'il derive, la
cointegration mesuree sur toute la periode est une moyenne de regimes
differents et le backtest sera trompeur.
"""

import numpy as np
import pandas as pd

from strategies.pairs_cointegration.cointegration import ols


def beta_stability_pct(log_y: pd.Series, log_x: pd.Series, window: int) -> float:
    """
    Score = 100 * (1 - std(beta_roulant) / |moyenne(beta_roulant)|),
    borne a [0, 100]. 100 = beta parfaitement stable.
    """
    n = len(log_y)
    if n < window * 2:
        return np.nan

    betas = []
    for start in range(0, n - window, window // 2):
        window_y = log_y.values[start : start + window]
        window_x = log_x.values[start : start + window]
        _, beta, _ = ols(window_y, window_x)
        betas.append(beta)

    betas = np.array(betas)
    if len(betas) < 2 or abs(betas.mean()) < 1e-9:
        return np.nan
    score = 100.0 * (1.0 - betas.std() / abs(betas.mean()))
    return float(np.clip(score, 0.0, 100.0))
