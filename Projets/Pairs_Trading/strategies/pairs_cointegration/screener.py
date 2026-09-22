"""
Screening de paires cointegrees.

Le principe : on ne veut PAS de series stationnaires prises isolement
(un prix stationnaire, ca n'existe pas en crypto -- si l'ADF dit
stationnaire sur une serie seule, c'est un artefact et la paire est
suspecte). On veut deux series NON stationnaires dont une combinaison
lineaire, elle, est stationnaire : c'est ca, la cointegration.

Orchestre cointegration.py (etapes 1-3), stability.py et tradability.py
(etapes 4-6) et rend un verdict par paire.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from data.sources.ccxt_source import get_ohlcv
from strategies.pairs_cointegration.cointegration import adf_pvalue, best_direction
from strategies.pairs_cointegration.signals import Z_ENTRY, Z_EXIT
from strategies.pairs_cointegration.stability import beta_stability_pct
from strategies.pairs_cointegration.tradability import (
    crossings_per_year, half_life_hours, net_amplitude_pct,
)

_CONFIG = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())

COST_ROUNDTRIP_PCT = float(_CONFIG["costs"]["cost_roundtrip_pct"])
ADF_NONSTATIONARY_MIN_PVALUE = float(_CONFIG["screening"]["adf_nonstationary_min_pvalue"])
COINT_MAX_PVALUE = float(_CONFIG["screening"]["coint_max_pvalue"])
HALF_LIFE_MIN_HOURS = float(_CONFIG["screening"]["half_life_min_hours"])
HALF_LIFE_MAX_HOURS = float(_CONFIG["screening"]["half_life_max_hours"])
STABILITY_WINDOW = int(_CONFIG["screening"]["stability_window_bars"])

TIMEFRAME = _CONFIG["market"]["timeframe"]
HISTORY_DAYS = int(_CONFIG["market"]["history_days"])
BARS_PER_YEAR = 365 * 24

PAIRS = [tuple(p) for p in _CONFIG["pairs"]]


def test_pair(price_a: pd.Series, price_b: pd.Series, name_a="A", name_b="B") -> dict:
    """
    Applique toute la batterie de tests a un couple de series de prix.
    Retourne un dict avec toutes les valeurs mesurees + un verdict.
    """
    # Alignement strict sur les timestamps communs : une barre manquante
    # d'un cote decalerait toute la regression.
    df = pd.concat([price_a.rename("a"), price_b.rename("b")], axis=1).dropna()
    log_a = np.log(df["a"])
    log_b = np.log(df["b"])
    n_bars = len(df)

    out = {
        "pair": f"{name_a.split('/')[0]}-{name_b.split('/')[0]}",
        "n_bars": n_bars,
        "cost_roundtrip_pct": COST_ROUNDTRIP_PCT,
        "verdict": "",
    }

    # --- 1. ADF sur chaque serie seule : on VEUT non stationnaire --------
    adf_a_p = adf_pvalue(log_a)
    adf_b_p = adf_pvalue(log_b)
    out["adf_a_pvalue"] = round(adf_a_p, 4)
    out["adf_b_pvalue"] = round(adf_b_p, 4)

    if adf_a_p < ADF_NONSTATIONARY_MIN_PVALUE or adf_b_p < ADF_NONSTATIONARY_MIN_PVALUE:
        out["verdict"] = "REJETE: une serie est deja stationnaire seule"

    # --- 2 & 3. OLS dans les deux sens, coint() decide du sens ----------
    direction = best_direction(log_a, log_b, name_a, name_b)
    y, x = direction["y"], direction["x"]
    sym_y, sym_x = direction["sym_y"], direction["sym_x"]
    coint_p, alpha, beta, spread = (
        direction["coint_p"], direction["alpha"], direction["beta"], direction["spread"]
    )

    # `direction` texte est pour l'oeil humain ; sym_y / sym_x sont pour
    # execution/, qui n'a pas a re-parser une chaine de caracteres.
    out["direction"] = f"log({sym_y.split('/')[0]}) ~ log({sym_x.split('/')[0]})"
    out["sym_y"] = sym_y
    out["sym_x"] = sym_x
    out["beta"] = round(beta, 4)
    out["alpha"] = round(alpha, 4)
    out["adf_pvalue"] = round(coint_p, 4)  # p-value du test de coint.

    if not out["verdict"] and coint_p > COINT_MAX_PVALUE:
        out["verdict"] = f"REJETE: pas cointegre (p={coint_p:.3f})"

    # --- 4. Demi-vie ----------------------------------------------------
    hl = half_life_hours(spread.values)
    out["half_life_hours"] = round(hl, 2) if np.isfinite(hl) else np.nan

    if not out["verdict"]:
        if not np.isfinite(hl):
            out["verdict"] = "REJETE: pas de retour a la moyenne (AR(1) degenere)"
        elif hl < HALF_LIFE_MIN_HOURS:
            out["verdict"] = f"REJETE: demi-vie trop courte ({hl:.1f}h) = bruit"
        elif hl > HALF_LIFE_MAX_HOURS:
            out["verdict"] = f"REJETE: demi-vie trop longue ({hl:.0f}h) = capital bloque"

    # --- 5. Croisements par an -----------------------------------------
    out["crossings_per_year"] = round(
        crossings_per_year(spread.values, n_bars, BARS_PER_YEAR), 1
    )

    # --- 6. Amplitude vs frais ------------------------------------------
    sigma_pct, mad_pct, net_amp = net_amplitude_pct(spread, COST_ROUNDTRIP_PCT)
    out["spread_sigma_pct"] = round(sigma_pct, 3)
    out["mad_pct"] = round(mad_pct, 3)
    out["net_amplitude_pct"] = round(net_amp, 3)

    if not out["verdict"] and out["net_amplitude_pct"] <= 0:
        out["verdict"] = "REJETE: amplitude mangee par les frais"

    # --- Stabilite du beta ----------------------------------------------
    stab = beta_stability_pct(y, x, STABILITY_WINDOW)
    out["stability_pct"] = round(stab, 1) if np.isfinite(stab) else np.nan

    # --- Esperance par trade --------------------------------------------
    # Un trade type entre a |z| = Z_ENTRY et sort a |z| = Z_EXIT :
    # il capture (Z_ENTRY - Z_EXIT) ecarts-types de spread, moins les frais.
    gross = (Z_ENTRY - Z_EXIT) * sigma_pct
    out["expected_pnl_per_trade"] = round(gross - COST_ROUNDTRIP_PCT, 3)

    if not out["verdict"] and out["expected_pnl_per_trade"] <= 0:
        out["verdict"] = "REJETE: esperance par trade negative apres frais"

    if not out["verdict"]:
        out["verdict"] = "OK"

    return out


if __name__ == "__main__":
    symbols = sorted({s for pair in PAIRS for s in pair})
    since = pd.Timestamp.utcnow() - pd.Timedelta(days=HISTORY_DAYS)

    print(f"Telechargement {len(symbols)} symboles, {TIMEFRAME}, {HISTORY_DAYS}j\n")
    data = get_ohlcv(symbols, TIMEFRAME, since)

    print("\nScreening...\n")
    rows = []
    for sym_a, sym_b in PAIRS:
        r = test_pair(data[sym_a]["close"], data[sym_b]["close"], sym_a, sym_b)
        rows.append(r)
        print(f"{r['pair']:12s} {r['verdict']}")

    cols = [
        "pair", "direction", "beta", "adf_pvalue", "half_life_hours",
        "crossings_per_year", "spread_sigma_pct", "cost_roundtrip_pct",
        "net_amplitude_pct", "stability_pct", "expected_pnl_per_trade",
        "verdict", "alpha", "sym_y", "sym_x",
        "adf_a_pvalue", "adf_b_pvalue", "mad_pct", "n_bars",
    ]
    df = pd.DataFrame(rows)[cols]
    df = df.sort_values("expected_pnl_per_trade", ascending=False)
    df.to_csv("screening_results.csv", index=False)

    print("\n=== screening_results.csv ===")
    print(df.to_string(index=False))
