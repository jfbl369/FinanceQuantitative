"""
Telechargement OHLCV via ccxt (Binance spot public).

Note importante : on lit les prix du marche REEL, pas du testnet.
Le testnet Binance a un carnet fictif et un historique inutilisable
pour de la statistique (series plates, trous, prix aberrants).
Le testnet ne sert qu'a passer des ordres (execution/), toute la mesure
statistique -- screening, backtest, z-score -- se fait sur les vrais prix.
Les endpoints OHLCV publics ne demandent aucune cle API.
"""

import time

import ccxt
import pandas as pd

from data.sources.base_source import DataSource

# Binance renvoie au maximum 1000 bougies par requete : il faut paginer.
MAX_BARS_PER_CALL = 1000
# Pause entre deux requetes pour rester sous le rate limit public.
SLEEP_BETWEEN_CALLS = 0.25

TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


class CCXTSource(DataSource):
    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    def get_ohlcv(
        self, symbols: list[str], timeframe: str, since
    ) -> dict[str, pd.DataFrame]:
        """
        Telecharge l'OHLCV de chaque symbole depuis `since` jusqu'a maintenant.

        symbols   : ex ["ETH/USDT", "SOL/USDT"]
        timeframe : ex "1h"
        since     : timestamp en millisecondes (int), ou datetime/str parsable par pandas
        """
        if not isinstance(since, int):
            ts = pd.Timestamp(since)
            # Une valeur deja tz-aware ne doit pas etre re-localisee.
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
            since = int(ts.timestamp() * 1000)

        step_ms = TIMEFRAME_MS[timeframe]
        now_ms = self.exchange.milliseconds()

        out = {}
        for symbol in symbols:
            rows = []
            cursor = since

            while cursor < now_ms:
                batch = self.exchange.fetch_ohlcv(
                    symbol, timeframe=timeframe, since=cursor, limit=MAX_BARS_PER_CALL
                )
                if not batch:
                    break
                rows.extend(batch)
                # On repart de la derniere bougie recue + 1 pas, pas de
                # `cursor + N*step` : si l'exchange a des trous, on
                # boucle sinon a l'infini.
                cursor = batch[-1][0] + step_ms
                if len(batch) < MAX_BARS_PER_CALL:
                    break
                time.sleep(SLEEP_BETWEEN_CALLS)

            df = pd.DataFrame(
                rows, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.set_index("timestamp")
            # Une meme bougie peut revenir sur deux pages : on deduplique.
            df = df[~df.index.duplicated(keep="first")].sort_index()

            out[symbol] = df
            print(f"{symbol:12s} {len(df):5d} barres  {df.index[0]} -> {df.index[-1]}")

        return out


def get_ohlcv(symbols: list[str], timeframe: str, since) -> dict[str, pd.DataFrame]:
    """Fonction libre pratique : instancie une source par defaut et delegue."""
    return CCXTSource().get_ohlcv(symbols, timeframe, since)


if __name__ == "__main__":
    since = pd.Timestamp.utcnow() - pd.Timedelta(days=365)
    data = get_ohlcv(["ETH/USDT", "SOL/USDT"], "1h", since)

    for symbol, df in data.items():
        print(f"\n=== {symbol} ===")
        print(df.tail(3))
        print(f"close min={df['close'].min():.2f}  max={df['close'].max():.2f}")
