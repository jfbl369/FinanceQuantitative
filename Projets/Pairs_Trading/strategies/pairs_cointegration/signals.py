"""
Z-score du spread et regle de decision.

Tous les seuils de risque viennent de config.yaml, charge une seule fois
ici. Aucun autre fichier de la strategie ne doit redefinir un seuil :
screener.py, backtest.py et strategy.py les importent d'ici, comme ca il
n'existe qu'une seule verite.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_CONFIG = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())

# --- Seuils -------------------------------------------------------------
Z_ENTRY = float(_CONFIG["zscore"]["entry"])
Z_EXIT = float(_CONFIG["zscore"]["exit"])
Z_STOP = float(_CONFIG["zscore"]["stop"])
ZSCORE_WINDOW = int(_CONFIG["zscore"]["window_bars"])

# Positions
FLAT = 0
LONG_SPREAD = 1   # spread juge trop bas -> on parie qu'il remonte
SHORT_SPREAD = -1  # spread juge trop haut -> on parie qu'il baisse


def compute_zscore(spread: pd.Series, window: int = ZSCORE_WINDOW) -> pd.Series:
    """
    Z-score roulant du spread : (spread - moyenne roulante) / ecart-type roulant.

    Les `window` premieres barres valent NaN : c'est voulu, on n'a pas
    encore assez d'historique pour juger si un ecart est anormal.
    """
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std()
    z = (spread - mean) / std
    # Un ecart-type nul (serie plate) donnerait des inf : on les neutralise.
    return z.replace([np.inf, -np.inf], np.nan)


def entry_side(z: float) -> int:
    """Sens de la position a ouvrir pour un z donne."""
    return SHORT_SPREAD if z > 0 else LONG_SPREAD


def decide(z: float, position_actuelle: int) -> str:
    """
    Retourne "entree", "sortie", "stop" ou "attente".

    position_actuelle : 0 (flat), +1 (long spread) ou -1 (short spread).
    Le sens a prendre sur une "entree" se lit avec entry_side(z).
    """
    if z is None or not np.isfinite(z):
        return "attente"

    abs_z = abs(z)

    if position_actuelle == FLAT:
        # On n'entre pas au-dela du stop : on serait stoppe des la barre
        # suivante. Un ecart de 4 sigma n'est pas une opportunite plus
        # belle qu'un 2 sigma, c'est le signe que la relation a casse.
        if abs_z >= Z_STOP:
            return "attente"
        if abs_z >= Z_ENTRY:
            return "entree"
        return "attente"

    # En position.
    if abs_z <= Z_EXIT:
        return "sortie"

    # Stop uniquement si le spread s'est encore ECARTE dans le sens qui
    # nous fait perdre. Un long spread (z tres negatif) se stoppe sur un
    # z encore plus negatif, pas sur un z tres positif -- lequel serait
    # au contraire un profit enorme, deja capture par la sortie ci-dessus.
    if position_actuelle == LONG_SPREAD and z <= -Z_STOP:
        return "stop"
    if position_actuelle == SHORT_SPREAD and z >= Z_STOP:
        return "stop"

    return "attente"


if __name__ == "__main__":
    cas = [
        (0.0, FLAT), (1.9, FLAT), (2.1, FLAT), (-2.1, FLAT), (4.0, FLAT),
        (2.5, SHORT_SPREAD), (0.4, SHORT_SPREAD), (3.6, SHORT_SPREAD),
        (-3.6, SHORT_SPREAD), (-3.6, LONG_SPREAD), (-0.2, LONG_SPREAD),
    ]
    for z, pos in cas:
        print(f"z={z:+5.1f}  position={pos:+d}  ->  {decide(z, pos)}")
