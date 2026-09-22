"""
Balayage de parametres : au lieu de choisir des seuils a l'intuition,
on rejoue le backtest sur toutes les combinaisons et on regarde.

    LIRE CECI AVANT DE REGARDER LE CLASSEMENT
    -----------------------------------------
    La meilleure ligne du tableau n'est PAS le bon reglage.

    Sur ~200 combinaisons, la premiere est en grande partie chanceuse :
    elle a colle au bruit de CES 365 jours precis. C'est du
    sur-apprentissage, et c'est la facon numero un dont un backtest ment.

    Ce qu'il faut chercher, c'est un PLATEAU, pas un pic. Si Z_ENTRY=2.0
    marche bien ET que 1.5 et 2.5 marchent bien aussi, la zone est
    robuste. Si 2.3 est spectaculaire mais que 2.2 et 2.4 sont mauvais,
    ce n'est pas un reglage, c'est un accident.

    D'ou les deux sorties de ce script :
      1. le classement brut (a lire avec mefiance)
      2. la moyenne par valeur de chaque parametre, les autres etant
         balayes -- c'est CA qui montre les plateaux, et c'est sur ca
         qu'il faut decider.

Lancement :
    .venv/bin/python -m strategies.pairs_cointegration.optimize ETH/USDT SOL/USDT
"""

import itertools
import sys
import warnings

import pandas as pd

from data.sources.ccxt_source import get_ohlcv
from strategies.pairs_cointegration.backtest import run_backtest, summarize

warnings.filterwarnings("ignore")

# --- Grille de recherche ------------------------------------------------
GRID = {
    "z_entry": [1.5, 2.0, 2.5, 3.0],
    "z_exit": [0.0, 0.5, 1.0],
    "z_stop": [3.0, 3.5, 4.0],
    "window": [24 * 14, 24 * 30, 24 * 60],
    "beta_hedged": [False, True],
}

TIMEFRAME = "1h"
HISTORY_DAYS = 365
MIN_TRADES = 10   # en dessous, le resultat n'est pas statistiquement lisible


def sweep(price_a, price_b, name_a, name_b) -> pd.DataFrame:
    keys = list(GRID)
    combos = list(itertools.product(*(GRID[k] for k in keys)))
    print(f"{len(combos)} combinaisons a tester...\n")

    rows = []
    for i, values in enumerate(combos, 1):
        params = dict(zip(keys, values))

        # Une sortie au-dessus de l'entree n'a pas de sens : on sortirait
        # a l'instant meme ou on entre.
        if params["z_exit"] >= params["z_entry"]:
            continue
        # Un stop sous l'entree stopperait chaque trade des l'ouverture.
        if params["z_stop"] <= params["z_entry"]:
            continue

        try:
            trades, equity, _ = run_backtest(
                price_a, price_b, name_a, name_b, verbose=False, **params
            )
        except ValueError:
            continue  # historique trop court pour cette fenetre

        rows.append({**params, **summarize(trades, equity)})

        if i % 25 == 0:
            print(f"  {i}/{len(combos)}")

    return pd.DataFrame(rows)


def plateaus(df: pd.DataFrame):
    """
    Pour chaque parametre, la performance moyenne par valeur, les autres
    parametres etant balayes. Un parametre robuste montre une progression
    lisse ; un parametre sur-appris montre un pic isole.
    """
    print("\n" + "=" * 62)
    print("PLATEAUX — moyenne par valeur, tous autres parametres balayes")
    print("C'est ce tableau qui doit decider, pas le classement.")
    print("=" * 62)

    usable = df[df["n_trades"] >= MIN_TRADES]
    if usable.empty:
        print(f"Aucune combinaison n'atteint {MIN_TRADES} trades.")
        return

    for param in GRID:
        g = usable.groupby(param).agg(
            pnl_moyen=("pnl", "mean"),
            pnl_median=("pnl", "median"),
            trades=("n_trades", "mean"),
            convergence=("convergence_rate", "mean"),
            drawdown=("max_drawdown", "mean"),
            n=("pnl", "size"),
        ).round(1)
        print(f"\n--- {param} ---")
        print(g.to_string())


def main():
    sym_a = sys.argv[1] if len(sys.argv) > 2 else "ETH/USDT"
    sym_b = sys.argv[2] if len(sys.argv) > 2 else "SOL/USDT"

    since = pd.Timestamp.utcnow() - pd.Timedelta(days=HISTORY_DAYS)
    data = get_ohlcv([sym_a, sym_b], TIMEFRAME, since)

    df = sweep(data[sym_a]["close"], data[sym_b]["close"], sym_a, sym_b)
    if df.empty:
        print("Aucune combinaison exploitable.")
        return

    df = df.sort_values("pnl", ascending=False)
    df.to_csv("optimize_results.csv", index=False)

    print("\n" + "=" * 62)
    print(f"CLASSEMENT BRUT — top 15 (a lire avec mefiance, voir en-tete)")
    print("=" * 62)
    top = df[df["n_trades"] >= MIN_TRADES].head(15)
    print((top if not top.empty else df.head(15)).to_string(index=False))

    plateaus(df)

    print("\n-> optimize_results.csv")
    print("\nRappel : choisis une valeur au MILIEU d'une zone qui marche,")
    print("pas la ligne numero 1 du classement.")


if __name__ == "__main__":
    main()
