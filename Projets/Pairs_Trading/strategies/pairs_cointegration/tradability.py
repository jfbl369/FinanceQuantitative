"""
Est-ce que le retour a la moyenne, une fois confirme, est exploitable :
assez rapide pour ne pas bloquer le capital, assez frequent pour generer
des trades, assez ample pour payer les frais ?
"""

import numpy as np

from strategies.pairs_cointegration.cointegration import ols


def half_life_hours(spread: np.ndarray) -> float:
    """
    Demi-vie du retour a la moyenne, par AR(1) :
        spread_t = a + phi * spread_{t-1} + eps
        half_life = -ln(2) / ln(phi)

    phi >= 1 : la serie ne revient pas (marche aleatoire ou divergente).
    phi <= 0 : oscillation d'une barre a l'autre = bruit, pas un signal.
    Dans les deux cas la demi-vie n'a pas de sens -> NaN.
    """
    lagged = spread[:-1]
    current = spread[1:]
    _, phi, _ = ols(current, lagged)
    if phi <= 0 or phi >= 1:
        return np.nan
    return float(-np.log(2) / np.log(phi))


def crossings_per_year(spread: np.ndarray, n_bars: int, bars_per_year: float) -> float:
    """Nombre de fois par an ou le spread traverse sa moyenne."""
    centered = spread - spread.mean()
    signs = np.sign(centered)
    signs = signs[signs != 0]
    crossings = int(np.sum(signs[1:] != signs[:-1]))
    return float(crossings * bars_per_year / n_bars)


def net_amplitude_pct(spread, cost_roundtrip_pct: float) -> tuple[float, float, float]:
    """
    Amplitude nette de frais.

    Le spread est en log : 0.01 de spread ~= 1% d'ecart relatif.
    On mesure la dispersion par MAD (mediane des ecarts absolus a la
    mediane) et non par l'ecart-type : la MAD ne se fait pas exploser
    par les quelques spikes de liquidation qui polluent le crypto.

    Retourne (sigma_pct, mad_pct, net_amplitude_pct).
    Aller-retour complet du spread = 2 x MAD, moins les frais.
    """
    mad = float(np.median(np.abs(spread - spread.median())))
    sigma_pct = float(spread.std()) * 100.0
    mad_pct = mad * 100.0
    net = 2.0 * mad_pct - cost_roundtrip_pct
    return sigma_pct, mad_pct, net
