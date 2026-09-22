"""Client ccxt pointe sur le testnet Binance. Jamais le marche reel."""

import os

import ccxt
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/secrets.env")
API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
API_SECRET = os.getenv("BINANCE_TESTNET_SECRET", "")


def make_testnet_exchange():
    ex = ccxt.binance({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            # Par defaut ccxt charge aussi les marches futures (linear/inverse)
            # a chaque load_markets(). On ne trade que du spot : pas de raison
            # de dependre du testnet futures (autre domaine, autre certificat,
            # autre disponibilite) pour un bot qui ne l'utilisera jamais.
            "fetchMarkets": ["spot"],
        },
    })
    ex.set_sandbox_mode(True)   # bascule les URL vers testnet.binance.vision
    return ex
