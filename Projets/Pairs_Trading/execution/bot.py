"""
Boucle principale d'execution : generique, ne connait aucune strategie
par son nom. Les strategies actives viennent de core.registry
(config/active_strategies.yaml) ; chacune ne fait que rendre des Signal,
jamais un ordre. C'est ici, via execution/order_router.py, que Signal
devient des ordres reels -- apres verification par core.risk.

    #########################################################
    #  DRY_RUN = True : AUCUN ORDRE N'EST PASSE, NULLE PART. #
    #  Ne passer a False que volontairement, et meme alors   #
    #  les ordres partent sur le TESTNET Binance uniquement.  #
    #########################################################

Tourne dans le meme process asyncio que observability/server.py : il
appelle directement publish() plutot que de faire un POST HTTP a lui-meme.

Lancement :
    START_BOT=1 .venv/bin/uvicorn observability.server:app --port 8000
"""

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from core.event_bus import publish, run_sync
from core.interfaces import Position
from core.portfolio import Portfolio
from core.registry import load_active_strategies
from core.risk import RiskLimits, RiskManager
from data.sources.binance_ws_stream import stream_trades
from data.sources.ccxt_source import get_ohlcv
from execution.exchanges.binance_testnet import make_testnet_exchange
from execution.order_router import LegFailure, OrderRouter

_SETTINGS = yaml.safe_load(
    (Path(__file__).parent.parent / "config" / "settings.yaml").read_text()
)

# --- Garde-fou --------------------------------------------------------
# Source unique : config/settings.yaml (execution.dry_run). NE PAS
# MODIFIER cette valeur sans demande explicite -- meme a False, les
# ordres partent sur le TESTNET Binance uniquement, jamais le marche reel.
DRY_RUN = bool(_SETTINGS["execution"]["dry_run"])

# --- Constantes -------------------------------------------------------
POLL_SECONDS = int(_SETTINGS["execution"]["poll_seconds"])
FEE_PER_EXECUTION_PCT = float(_SETTINGS["execution"]["fee_per_execution_pct"])
TIMEFRAME = "1h"
FETCH_BARS = 1000   # >= la plus grande fenetre de z-score utilisee, avec marge


async def _relay_live_prices(symbols: list[str]) -> None:
    """
    Republie chaque trade execute (flux WebSocket public Binance) sur le
    bus d'evenements, pour un affichage temps reel du dashboard. N'a
    aucune influence sur la strategie : le z-score reste calcule sur
    l'OHLCV horaire par la boucle principale de run().
    """
    async for tick in stream_trades(symbols):
        ts = datetime.fromtimestamp(tick["ts_ms"] / 1000, tz=timezone.utc).isoformat()
        publish({"ts": ts, "action": "price", "symbol": tick["symbol"], "price": tick["price"]})


async def run():
    """Boucle infinie : fetch, evaluation des strategies actives, decision, push vers le dashboard."""
    strategies = load_active_strategies()
    if not strategies:
        print("[bot] aucune strategie active — la boucle s'arrete ici.")
        return

    # Recharge les positions eventuellement ouvertes par un process
    # precedent : sans ca, un simple restart (deploiement, crash, systemd)
    # reinitialise l'etat a "flat" et le bot peut rouvrir une position
    # deja ouverte des le premier tick si le z-score est encore au-dela
    # du seuil d'entree.
    portfolio = Portfolio.load()
    risk = RiskManager(RiskLimits.from_settings())
    exchange = make_testnet_exchange()
    router = OrderRouter(exchange, dry_run=DRY_RUN, fee_per_execution_pct=FEE_PER_EXECUTION_PCT)

    symbols = sorted({s for strat in strategies for s in strat.symbols()})

    print(f"[bot] DRY_RUN={DRY_RUN} | {len(strategies)} strategie(s) : "
          f"{', '.join(s.name for s in strategies)}")
    print(f"[bot] portfolio charge : {portfolio.n_open_positions()} position(s) ouverte(s), "
          f"P&L realise {portfolio.realized_pnl:+.2f} USDT")

    # Tache independante de la boucle principale : les trades arrivent en
    # continu, pas au rythme de POLL_SECONDS. Cancel explicite dans le
    # finally sinon elle survivrait a un arret de run() (create_task ne
    # lie pas le cycle de vie de la tache enfant a la coroutine appelante).
    price_task = asyncio.create_task(_relay_live_prices(symbols))

    try:
        await _run_loop(strategies, symbols, portfolio, risk, router)
    finally:
        price_task.cancel()
        with suppress(asyncio.CancelledError):
            await price_task


async def _run_loop(strategies, symbols, portfolio, risk, router):
    while True:
        try:
            since = pd.Timestamp.utcnow() - pd.Timedelta(hours=FETCH_BARS)
            # get_ohlcv est synchrone (ccxt) -> thread.
            data = await run_sync(get_ohlcv, symbols, TIMEFRAME, since)

            for strat in strategies:
                open_positions = portfolio.positions_for(strat.name)
                signals = strat.evaluate(data, open_positions)

                for sig in signals:
                    # publish() doit TOUJOURS partir pour ce signal, meme si
                    # l'ordre echoue -- sinon une InsufficientFunds ou une
                    # coupure reseau sur UNE paire fait taire le dashboard
                    # pour toutes les autres jusqu'a la prochaine exception.
                    pnl = None
                    action_out = sig.action

                    if sig.action == "entree":
                        legs = sig.legs
                        ok, reason = risk.can_open(
                            portfolio, legs["notional_a"], legs["notional_b"]
                        )
                        if not ok:
                            print(f"[risk] entree refusee {sig.instrument_id}: {reason}")
                            action_out = "attente"
                        else:
                            try:
                                await router.open(sig)
                            except LegFailure as exc:
                                print(f"[bot] {sig.instrument_id}: {exc}")
                                action_out = "attente"
                            except Exception as exc:
                                print(f"[bot] {sig.instrument_id}: entree echouee "
                                      f"({type(exc).__name__}: {exc})")
                                action_out = "attente"
                            else:
                                portfolio.open_position(Position(
                                    instrument_id=sig.instrument_id,
                                    strategy=strat.name,
                                    side=sig.side,
                                    notional_a=legs["notional_a"],
                                    notional_b=legs["notional_b"],
                                    entry={"py": legs["py"], "px": legs["px"], "ts": sig.ts},
                                ))
                                portfolio.save()

                    elif sig.action in ("sortie", "stop"):
                        position = open_positions.get(sig.instrument_id)
                        if position is None:
                            action_out = "attente"
                        else:
                            try:
                                pnl = round(await router.close(sig, position), 2)
                            except Exception as exc:
                                print(f"[bot] {sig.instrument_id}: {sig.action} echouee "
                                      f"({type(exc).__name__}: {exc})")
                                action_out = "attente"
                            else:
                                portfolio.close_position(sig.instrument_id, pnl, sig.ts)
                                portfolio.save()

                    publish({
                        "ts": sig.ts,
                        "pair": sig.instrument_id,
                        "z": sig.score,
                        # "attente" n'est pas un evenement interessant pour
                        # le journal : on l'envoie comme "tick" pour
                        # alimenter la courbe, le dashboard ne le journalise pas.
                        "action": "tick" if action_out == "attente" else action_out,
                        "pnl": pnl,
                        # Prix spot des deux jambes : le dashboard en a besoin
                        # pour le graphique de prix, en plus du z-score.
                        "sym_y": sig.legs.get("sym_y"),
                        "sym_x": sig.legs.get("sym_x"),
                        "price_y": sig.legs.get("py"),
                        "price_x": sig.legs.get("px"),
                    })

        except Exception as exc:
            # Une coupure reseau ou un rate limit ne doit pas tuer le bot.
            print(f"[bot] erreur: {type(exc).__name__}: {exc}")

        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    print("execution/bot.py ne se lance pas seul : il a besoin du serveur pour publier.")
    print("Utilise :  START_BOT=1 .venv/bin/uvicorn observability.server:app --port 8000")
