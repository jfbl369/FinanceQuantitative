"""
Bus d'evenements asyncio, independant de tout transport.

Extrait de l'ancien server.py : n'importe quelle strategie ou composant
d'execution peut publier ("execution/bot.py appelle publish()"), et
n'importe quel observateur peut s'abonner (observability/server.py
s'abonne pour rediffuser aux WebSocket). Le bus ne sait rien de FastAPI
ni de HTTP -- ca reste dans observability/.
"""

import asyncio
from collections import deque
from typing import Any

HISTORY_SIZE = 500


class EventBus:
    def __init__(self, history_size: int = HISTORY_SIZE):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._history: deque = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue] = set()

    def publish(self, event: dict[str, Any]) -> None:
        """
        Depose un evenement dans la file. Appelable depuis n'importe ou
        dans la boucle asyncio, ne bloque jamais (la file est non bornee).

        Format attendu : {"ts", "pair", "z", "action", "pnl"} pour la
        strategie pairs_cointegration ; d'autres strategies peuvent
        ajouter des cles, le bus ne les interprete pas.
        """
        self._queue.put_nowait(event)

    def history(self) -> list[dict[str, Any]]:
        """Les derniers evenements, pour un client qui vient de se connecter."""
        return list(self._history)

    def subscribe(self) -> asyncio.Queue:
        """
        Un nouvel abonne recoit son propre file : le bus ne connait pas
        les WebSocket, juste des consommateurs asyncio.Queue.
        """
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def run(self) -> None:
        """Vide la file principale et redistribue a chaque abonne."""
        while True:
            event = await self._queue.get()
            self._history.append(event)
            for q in list(self._subscribers):
                q.put_nowait(event)


# Bus process-wide unique : execution/ et observability/ partagent la
# meme instance, comme le faisaient EVENT_QUEUE/HISTORY/CLIENTS dans
# l'ancien server.py.
BUS = EventBus()
publish = BUS.publish


async def run_sync(fn, *args):
    """
    Execute une fonction bloquante (tout appel ccxt, toute lecture disque)
    dans un thread.

    Sans ca, un fetch_ohlcv de 300 ms gele la boucle asyncio : les
    WebSocket ne recoivent plus rien pendant ce temps et le dashboard se
    fige. Utilitaire asyncio generique, colocalise ici parce que c'est le
    seul autre point d'infrastructure partage par execution/ et
    observability/.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fn, *args)
