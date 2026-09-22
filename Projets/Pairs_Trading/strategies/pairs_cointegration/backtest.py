"""
Backtest barre par barre d'une paire. Pas de vectorisation, pas de
VectorBT : une boucle for qu'on peut lire ligne a ligne et ou on voit
exactement ce que l'execution ferait en live.

Deux precautions contre le mensonge classique du backtest :

  1. Le beta est estime UNE FOIS sur la fenetre d'initialisation, puis
     fige. Utiliser le beta de la regression sur toute la periode
     reviendrait a connaitre le futur des la premiere barre.

  2. Le z-score est roulant (voir signals.py), pas global, pour la
     meme raison.

Il reste un biais assume : on execute au close de la barre ou le signal
apparait, sans slippage. Sur du 1h en majors liquides c'est acceptable ;
sur du 1m ca ne le serait pas.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # pas de fenetre, on ecrit un PNG

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from data.sources.ccxt_source import get_ohlcv
from strategies.pairs_cointegration.cointegration import ols
from strategies.pairs_cointegration.signals import (
    FLAT, LONG_SPREAD, SHORT_SPREAD,
    Z_ENTRY, Z_EXIT, Z_STOP, ZSCORE_WINDOW,
    compute_zscore, decide, entry_side,
)

_CONFIG = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())
_SETTINGS = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "config" / "settings.yaml").read_text()
)

# --- Constantes ---------------------------------------------------------
NOTIONAL_PER_LEG = float(_CONFIG["sizing"]["notional_per_leg"])
# Fait exchange, pas choix de strategie : source unique dans settings.yaml,
# pour que le backtest ne suppose jamais des frais differents du live.
FEE_PER_EXECUTION_PCT = float(_SETTINGS["execution"]["fee_per_execution_pct"])

# False = dollar-neutral : notional sur A, notional sur B.
# True  = beta-neutral   : notional sur A, notional x beta sur B.
# Si beta s'ecarte de 1, le dollar-neutral laisse une exposition
# directionnelle residuelle au marche. optimize.py teste les deux.
BETA_HEDGED = bool(_CONFIG["sizing"]["beta_hedged"])

TIMEFRAME = _CONFIG["market"]["timeframe"]
HISTORY_DAYS = int(_CONFIG["market"]["history_days"])


def _fees(notional_a: float, notional_b: float) -> float:
    """Frais d'un aller-retour complet : 4 executions."""
    rate = FEE_PER_EXECUTION_PCT / 100.0
    return 2.0 * rate * (notional_a + notional_b)


def run_backtest(
    price_a: pd.Series,
    price_b: pd.Series,
    name_a: str = "A",
    name_b: str = "B",
    z_entry: float = Z_ENTRY,
    z_exit: float = Z_EXIT,
    z_stop: float = Z_STOP,
    window: int = ZSCORE_WINDOW,
    beta_hedged: bool = BETA_HEDGED,
    verbose: bool = True,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Rejoue l'historique barre par barre.
    Retourne (trades, equity, zscore).
    """
    df = pd.concat([price_a.rename("a"), price_b.rename("b")], axis=1).dropna()
    log_a, log_b = np.log(df["a"]), np.log(df["b"])

    if len(df) < window * 2:
        raise ValueError(f"Historique trop court : {len(df)} barres, il en faut {window*2}")

    # --- Beta estime sur la fenetre d'init, puis fige -------------------
    alpha, beta, _ = ols(log_a.values[:window], log_b.values[:window])

    spread = log_a - (alpha + beta * log_b)
    z = compute_zscore(spread, window)

    notional_a = NOTIONAL_PER_LEG
    notional_b = NOTIONAL_PER_LEG * abs(beta) if beta_hedged else NOTIONAL_PER_LEG

    position = FLAT
    entry = None
    trades = []
    pnl_cum = 0.0
    equity = pd.Series(0.0, index=df.index)

    # decide() est appele avec les seuils passes en argument : on
    # reconstruit sa logique ici pour pouvoir balayer les seuils dans
    # optimize.py sans toucher aux constantes globales.
    for i in range(window, len(df)):
        ts = df.index[i]
        zi = z.iloc[i]
        pa, pb = df["a"].iloc[i], df["b"].iloc[i]

        equity.iloc[i] = pnl_cum

        if not np.isfinite(zi):
            continue

        abs_z = abs(zi)

        if position == FLAT:
            if z_entry <= abs_z < z_stop:
                position = entry_side(zi)
                entry = {
                    "entry_ts": ts, "entry_z": zi,
                    "entry_a": pa, "entry_b": pb,
                    "side": "long_spread" if position == LONG_SPREAD else "short_spread",
                }
            continue

        # En position : sortie, stop, ou on attend.
        action = None
        if abs_z <= z_exit:
            action = "sortie"
        elif position == LONG_SPREAD and zi <= -z_stop:
            action = "stop"
        elif position == SHORT_SPREAD and zi >= z_stop:
            action = "stop"

        if action is None:
            continue

        # --- Cloture : P&L des deux jambes ------------------------------
        ret_a = pa / entry["entry_a"] - 1.0
        ret_b = pb / entry["entry_b"] - 1.0

        if position == LONG_SPREAD:
            # spread trop bas -> A sous-evalue : on achete A, on vend B
            gross = notional_a * ret_a - notional_b * ret_b
        else:
            gross = -notional_a * ret_a + notional_b * ret_b

        fees = _fees(notional_a, notional_b)
        net = gross - fees
        pnl_cum += net
        equity.iloc[i] = pnl_cum

        trades.append({
            **entry,
            "exit_ts": ts, "exit_z": zi, "exit_a": pa, "exit_b": pb,
            "action": action,
            "bars_held": i - df.index.get_loc(entry["entry_ts"]),
            "gross_pnl": round(gross, 2),
            "fees": round(fees, 2),
            "net_pnl": round(net, 2),
            "pnl_cum": round(pnl_cum, 2),
        })

        position = FLAT
        entry = None

    # Une position encore ouverte a la fin n'est pas comptee : on ne
    # credite pas un profit latent qui n'a jamais ete realise.
    equity = equity.iloc[window:].ffill()
    trades_df = pd.DataFrame(trades)

    if verbose:
        _print_summary(trades_df, equity, beta, name_a, name_b, position)

    return trades_df, equity, z


def summarize(trades_df: pd.DataFrame, equity: pd.Series) -> dict:
    """Metriques d'un backtest, utilisees aussi par optimize.py."""
    if trades_df.empty:
        return {"n_trades": 0, "pnl": 0.0, "win_rate": np.nan,
                "convergence_rate": np.nan, "max_drawdown": 0.0,
                "avg_bars_held": np.nan}

    n = len(trades_df)
    n_conv = int((trades_df["action"] == "sortie").sum())
    dd = float((equity - equity.cummax()).min())

    return {
        "n_trades": n,
        "pnl": round(float(trades_df["net_pnl"].sum()), 2),
        "win_rate": round(100.0 * (trades_df["net_pnl"] > 0).mean(), 1),
        # Taux de convergence = trades fermes par retour a la moyenne
        # plutot que par stop. C'est la metrique qui dit si l'hypothese
        # de cointegration tient encore.
        "convergence_rate": round(100.0 * n_conv / n, 1),
        "max_drawdown": round(dd, 2),
        "avg_bars_held": round(float(trades_df["bars_held"].mean()), 1),
    }


def _print_summary(trades_df, equity, beta, name_a, name_b, open_position):
    s = summarize(trades_df, equity)
    print(f"\n=== {name_a} / {name_b} ===")
    print(f"beta (fige sur la fenetre d'init) : {beta:.4f}")
    print(f"sizing : {NOTIONAL_PER_LEG:,.0f} USDT/jambe, "
          f"{'beta-neutral' if BETA_HEDGED else 'dollar-neutral'}")
    if s["n_trades"] == 0:
        print("Aucun trade declenche sur la periode.")
        return
    print(f"trades           : {s['n_trades']}")
    print(f"P&L net          : {s['pnl']:+,.2f} USDT")
    print(f"taux de reussite : {s['win_rate']}%")
    print(f"convergence      : {s['convergence_rate']}%  "
          f"({int(trades_df['action'].eq('stop').sum())} stops)")
    print(f"drawdown max     : {s['max_drawdown']:,.2f} USDT")
    print(f"duree moyenne    : {s['avg_bars_held']:.0f} barres")
    print(f"frais totaux     : {trades_df['fees'].sum():,.2f} USDT")
    if open_position != FLAT:
        print("(une position etait encore ouverte a la fin, non comptee)")


def plot(z, equity, trades_df, name_a, name_b, path):
    """Deux panneaux : z-score du spread avec les seuils, et equity curve."""
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(15, 9), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    z_plot = z.loc[equity.index]
    ax1.plot(z_plot.index, z_plot.values, lw=0.7, color="#1f77b4", label="z-score du spread")
    for lvl, c, ls in [(Z_ENTRY, "orange", "--"), (-Z_ENTRY, "orange", "--"),
                       (Z_EXIT, "green", ":"), (-Z_EXIT, "green", ":"),
                       (Z_STOP, "red", "-."), (-Z_STOP, "red", "-.")]:
        ax1.axhline(lvl, color=c, ls=ls, lw=1, alpha=0.8)
    ax1.axhline(0, color="black", lw=0.5, alpha=0.4)

    if not trades_df.empty:
        ax1.scatter(trades_df["entry_ts"], trades_df["entry_z"],
                    marker="o", s=28, color="black", zorder=5, label="entree")
        won = trades_df[trades_df["net_pnl"] > 0]
        lost = trades_df[trades_df["net_pnl"] <= 0]
        ax1.scatter(won["exit_ts"], won["exit_z"], marker="x", s=40,
                    color="green", zorder=5, label="sortie gagnante")
        ax1.scatter(lost["exit_ts"], lost["exit_z"], marker="x", s=40,
                    color="red", zorder=5, label="sortie perdante")

    ax1.set_ylabel("z-score")
    ax1.set_title(f"{name_a} / {name_b}  —  seuils {Z_ENTRY} / {Z_EXIT} / {Z_STOP}")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(alpha=0.25)

    ax2.plot(equity.index, equity.values, color="#2ca02c", lw=1.2)
    ax2.fill_between(equity.index, 0, equity.values,
                     where=equity.values >= 0, color="#2ca02c", alpha=0.15)
    ax2.fill_between(equity.index, 0, equity.values,
                     where=equity.values < 0, color="#d62728", alpha=0.15)
    ax2.axhline(0, color="black", lw=0.5)
    ax2.set_ylabel("P&L cumule (USDT)")
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print(f"graphique -> {path}")


def save_dashboard_json(z, equity, trades_df, name_a, name_b, price_a, price_b, path):
    """
    Meme donnees que plot(), en JSON pour observability/dashboards --
    le dashboard web les affiche avec Chart.js plutot qu'une image
    matplotlib statique. Reduit aux barres couvertes par l'equity
    (post fenetre d'initialisation), comme le graphique.

    price_a/price_b (prix spot bruts, pas le spread) servent a comprendre
    VISUELLEMENT un drawdown : un decrochage du P&L qui coincide avec un
    des deux prix qui s'effondre plus vite que l'autre montre que la
    relation a temporairement casse, plutot que d'avoir a le deviner
    depuis le z-score seul.
    """
    z_plot = z.loc[equity.index]
    price_a_plot = price_a.loc[equity.index]
    price_b_plot = price_b.loc[equity.index]

    out = {
        "pair": f"{name_a.split('/')[0]}-{name_b.split('/')[0]}",
        "name_a": name_a, "name_b": name_b,
        "z_entry": Z_ENTRY, "z_exit": Z_EXIT, "z_stop": Z_STOP,
        "zscore": [
            {"ts": ts.isoformat(), "z": None if pd.isna(v) else round(float(v), 4)}
            for ts, v in z_plot.items()
        ],
        "prices": [
            {"ts": ts.isoformat(), "a": round(float(pa), 6), "b": round(float(pb), 6)}
            for ts, pa, pb in zip(
                price_a_plot.index, price_a_plot.values, price_b_plot.values
            )
        ],
        "equity": [
            {"ts": ts.isoformat(), "pnl_cum": round(float(v), 2)}
            for ts, v in equity.items()
        ],
        "trades": [
            {
                "entry_ts": t["entry_ts"].isoformat(), "entry_z": t["entry_z"],
                "exit_ts": t["exit_ts"].isoformat(), "exit_z": t["exit_z"],
                "action": t["action"], "net_pnl": t["net_pnl"],
            }
            for t in trades_df.to_dict("records")
        ] if not trades_df.empty else [],
    }

    Path(path).write_text(json.dumps(out))
    print(f"donnees dashboard -> {path}")


if __name__ == "__main__":
    import sys

    sym_a = sys.argv[1] if len(sys.argv) > 2 else "ETH/USDT"
    sym_b = sys.argv[2] if len(sys.argv) > 2 else "SOL/USDT"

    since = pd.Timestamp.utcnow() - pd.Timedelta(days=HISTORY_DAYS)
    data = get_ohlcv([sym_a, sym_b], TIMEFRAME, since)

    trades, equity, z = run_backtest(
        data[sym_a]["close"], data[sym_b]["close"], sym_a, sym_b
    )

    tag = f"{sym_a.split('/')[0]}_{sym_b.split('/')[0]}"
    if not trades.empty:
        trades.to_csv(f"backtest_trades_{tag}.csv", index=False)
        print(f"trades -> backtest_trades_{tag}.csv")
    plot(z, equity, trades, sym_a, sym_b, f"backtest_{tag}.png")
    save_dashboard_json(
        z, equity, trades, sym_a, sym_b,
        data[sym_a]["close"], data[sym_b]["close"],
        f"backtest_{tag}.json",
    )
