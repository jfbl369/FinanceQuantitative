"""
Flux de prix en direct (WebSocket public Binance, trades executes).

Independant du rythme d'evaluation de la strategie (bougies 1h, poll
toutes les 30s) : ce flux sert UNIQUEMENT a l'affichage temps reel du
dashboard. Aucune decision de trading ne se base dessus -- le z-score
reste calcule sur l'OHLCV horaire, comme documente dans
strategies/pairs_cointegration/. Descendre la strategie elle-meme a la
seconde n'aurait pas de sens : ce serait exactement le bruit de
microstructure que HALF_LIFE_MIN_HOURS est cense filtrer.

Endpoint public, aucune cle API requise -- ce sont des donnees de marche,
pas un compte.
"""

import asyncio
import json
import ssl
from typing import AsyncIterator

import certifi
import websockets

STREAM_URL = "wss://stream.binance.com:9443/stream"
RECONNECT_DELAY_S = 2.0

# Sans ca, websockets utilise le contexte SSL par defaut de Python, qui
# sur certains environnements (notamment macOS avec un Python non lie au
# trousseau systeme) n'a AUCUNE chaine de certificats configuree et
# rejette tout, y compris le vrai certificat Binance. requests/ccxt
# n'ont pas ce probleme car ils passent deja par certifi en interne ;
# websockets ne le fait pas tout seul.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


async def stream_trades(symbols: list[str]) -> AsyncIterator[dict]:
    """
    symbols : ex ["CRV/USDT", "SUSHI/USDT"].

    Yield indefiniment {"symbol": "CRV/USDT", "price": float, "ts_ms": int}
    a chaque trade execute sur Binance. Reconnecte automatiquement sur
    coupure reseau -- ne leve jamais, c'est un flux d'affichage, une
    coupure ne doit pas remonter jusqu'a faire planter le bot.
    """
    stream_names = [f"{s.replace('/', '').lower()}@trade" for s in symbols]
    symbol_by_stream = dict(zip(stream_names, symbols))
    url = f"{STREAM_URL}?streams={'/'.join(stream_names)}"

    while True:
        try:
            async with websockets.connect(url, ssl=_SSL_CONTEXT) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    data = msg.get("data", {})
                    if data.get("e") != "trade":
                        continue
                    symbol = symbol_by_stream.get(msg.get("stream"))
                    if symbol is None:
                        continue
                    yield {
                        "symbol": symbol,
                        "price": float(data["p"]),
                        "ts_ms": int(data["T"]),
                    }
        except Exception as exc:
            print(f"[binance_ws_stream] coupure ({type(exc).__name__}: {exc}), "
                  f"reconnexion dans {RECONNECT_DELAY_S}s")
            await asyncio.sleep(RECONNECT_DELAY_S)
