"""
Serveur temps reel : FastAPI + WebSocket.

Le flux est un vrai push : execution/bot.py appelle publish() (via
core.event_bus), le bus le redistribue a tous les abonnes -- ici, une
tache par navigateur connecte. Aucun polling, aucun CSV relu en boucle.

Les 500 derniers evenements restent en memoire dans le bus. Quand un
navigateur se connecte, il recoit d'abord cet historique, puis le flux
live -- sans quoi un dashboard ouvert en retard afficherait une page
vide jusqu'au prochain tick.

Lancement :
    .venv/bin/uvicorn observability.server:app --reload --port 8000
Puis ouvrir http://127.0.0.1:8000

Par defaut le bot ne demarre PAS : le serveur sert juste le dashboard.
Pour le demarrer avec le serveur : START_BOT=1 .venv/bin/uvicorn observability.server:app
"""

import asyncio
import csv
import json
import os
import re
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from core.event_bus import BUS, run_sync

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
DASHBOARD_PATH = HERE / "dashboards" / "pairs_dashboard.html"
# Ecrit par strategies/pairs_cointegration/screener.py, a la racine du
# depot (execute via `python -m ...` depuis REPO_ROOT).
SCREENING_CSV = REPO_ROOT / "screening_results.csv"
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"


async def _forward_to_client(ws: WebSocket, queue: asyncio.Queue) -> None:
    """Vide la file d'abonnement de ce client et la pousse sur son WebSocket."""
    while True:
        event = await queue.get()
        await ws.send_json(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(BUS.run())]

    if os.getenv("START_BOT") == "1":
        # Import tardif : execution.bot importe publish() depuis core.event_bus,
        # pas depuis ce module -- plus de risque de cycle, mais on garde
        # l'import tardif pour ne charger ccxt/dotenv que si necessaire.
        from execution import bot
        tasks.append(asyncio.create_task(bot.run()))
        print("bot demarre dans le meme process")
    else:
        print("bot NON demarre (START_BOT != 1) — dashboard seul")

    yield

    for t in tasks:
        t.cancel()
        with suppress(asyncio.CancelledError):
            await t


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(DASHBOARD_PATH)


@app.get("/status")
async def status():
    """
    Etat d'execution reel, lu depuis config/settings.yaml -- le dashboard
    ne doit jamais afficher un badge DRY_RUN code en dur : il refleterait
    l'etat au moment ou la page a ete ecrite, pas l'etat au moment ou
    elle est servie.
    """
    settings = yaml.safe_load(SETTINGS_PATH.read_text())
    return JSONResponse({"dry_run": bool(settings["execution"]["dry_run"])})


@app.get("/backtest/{pair}")
async def backtest(pair: str):
    """
    Donnees d'un backtest (z-score + trades + equity), ecrites par
    strategies/pairs_cointegration/backtest.py via save_dashboard_json().
    `pair` est au format "CRV-SUSHI" (celui publie sur l'event bus) ;
    le fichier sur disque est nomme avec un underscore ("CRV_SUSHI"),
    convention heritee de backtest.py.
    """
    if not re.fullmatch(r"[A-Za-z0-9]+-[A-Za-z0-9]+", pair):
        return JSONResponse({"error": "format de paire invalide"}, status_code=400)

    path = REPO_ROOT / f"backtest_{pair.replace('-', '_')}.json"
    if not path.exists():
        return JSONResponse(
            {"error": "pas de backtest pour cette paire — lance "
                      "strategies/pairs_cointegration/backtest.py dessus"},
            status_code=404,
        )
    content = await run_sync(path.read_text)
    return JSONResponse(json.loads(content))


@app.get("/screening")
async def screening():
    """
    Les resultats du screener, lus une fois au chargement de la page.
    Ces valeurs ne changent pas en direct : pas besoin de WebSocket.
    """
    if not SCREENING_CSV.exists():
        return JSONResponse([], status_code=200)
    # Lecture disque bloquante -> thread, meme raison que pour ccxt.
    rows = await run_sync(lambda: list(csv.DictReader(SCREENING_CSV.open())))
    return JSONResponse(rows)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # D'abord l'historique, ensuite le live.
    for event in BUS.history():
        await ws.send_json(event)

    queue = BUS.subscribe()
    forward_task = asyncio.create_task(_forward_to_client(ws, queue))
    try:
        # On garde la connexion ouverte. Le client n'envoie rien, mais
        # ce receive_text() est ce qui detecte sa deconnexion.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        forward_task.cancel()
        with suppress(asyncio.CancelledError):
            await forward_task
        BUS.unsubscribe(queue)
