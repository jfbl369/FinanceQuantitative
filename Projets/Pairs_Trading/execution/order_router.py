"""
Point unique qui parle a l'exchange. Les strategies ne construisent
jamais un ordre ccxt elles-memes : elles rendent des Signal (voir
core.interfaces), et c'est ici que Signal devient deux ordres marche
(jambe Y, jambe X).

Convention Signal.side, heritee de pairs_cointegration.signals :
  side > 0 (LONG_SPREAD)  -> on achete la jambe Y, on vend la jambe X
  side < 0 (SHORT_SPREAD) -> on vend la jambe Y, on achete la jambe X

Si la 2e jambe echoue apres que la 1re a rempli, on tente immediatement
une cloture de compensation sur la jambe qui a rempli, pour ne jamais
laisser une exposition directionnelle non couverte trainer sans que le
bot le sache. C'etait un trou de l'ancienne version de bot.py : une
exception sur la 2e jambe laissait l'etat interne "flat" alors qu'une
jambe etait deja executee sur l'exchange.
"""

from core.event_bus import run_sync


class LegFailure(Exception):
    """Une jambe a echoue apres que l'autre a rempli ; compensation tentee."""


class OrderRouter:
    def __init__(self, exchange, dry_run: bool, fee_per_execution_pct: float):
        self.exchange = exchange
        self.dry_run = dry_run
        self.fee_rate = fee_per_execution_pct / 100.0

    def _fees(self, notional_a: float, notional_b: float) -> float:
        """Frais d'un aller-retour complet : 4 executions. Meme formule que backtest.py."""
        return 2.0 * self.fee_rate * (notional_a + notional_b)

    async def _place(self, symbol: str, side: str, notional: float, price: float):
        if self.dry_run:
            print(f"[DRY_RUN] {side.upper():5s} {symbol:10s} "
                  f"{notional:,.0f} USDT @ {price:.4f} — aucun ordre envoye")
            return None
        amount = notional / price
        return await run_sync(self.exchange.create_order, symbol, "market", side, amount)

    async def open(self, signal) -> None:
        """Ouvre les deux jambes d'un signal 'entree'."""
        legs = signal.legs
        sym_y, sym_x = legs["sym_y"], legs["sym_x"]
        notional_a, notional_b = legs["notional_a"], legs["notional_b"]
        py, px = legs["py"], legs["px"]

        side_y, side_x = ("buy", "sell") if signal.side > 0 else ("sell", "buy")

        await self._place(sym_y, side_y, notional_a, py)
        try:
            await self._place(sym_x, side_x, notional_b, px)
        except Exception as exc:
            # La jambe Y est deja remplie, la jambe X a echoue : on est
            # nu sur Y. On la referme immediatement au marche plutot que
            # de laisser une exposition directionnelle non trackee.
            compensating_side = "sell" if side_y == "buy" else "buy"
            try:
                await self._place(sym_y, compensating_side, notional_a, py)
            except Exception as compensating_exc:
                raise LegFailure(
                    f"{sym_x} a echoue ({exc}) ET la compensation sur "
                    f"{sym_y} a aussi echoue ({compensating_exc}) : "
                    f"position nue non couverte, intervention manuelle requise"
                ) from compensating_exc
            raise LegFailure(
                f"{sym_x} a echoue ({exc}) apres remplissage de {sym_y} : "
                f"compensation reussie, aucune exposition residuelle"
            ) from exc

    async def close(self, signal, position) -> float:
        """Ferme les deux jambes d'une position ouverte et retourne le P&L net en USDT."""
        legs = signal.legs
        entry = position.entry
        sym_y, sym_x = legs["sym_y"], legs["sym_x"]
        py, px = legs["py"], legs["px"]
        notional_a, notional_b = position.notional_a, position.notional_b

        ret_y = py / entry["py"] - 1.0
        ret_x = px / entry["px"] - 1.0

        if position.side > 0:
            gross = notional_a * ret_y - notional_b * ret_x
            side_y, side_x = "sell", "buy"
        else:
            gross = -notional_a * ret_y + notional_b * ret_x
            side_y, side_x = "buy", "sell"

        await self._place(sym_y, side_y, notional_a, py)
        await self._place(sym_x, side_x, notional_b, px)

        return gross - self._fees(notional_a, notional_b)
