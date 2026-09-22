# Architecture

Ce depot est structure pour accueillir plusieurs strategies de trading
independantes autour d'un socle commun (`core/`). Aujourd'hui, une seule
strategie est implementee : `pairs_cointegration`. Le reste de la
hierarchie (autres strategies, agents de recherche, multi-exchange,
persistance en base) est volontairement **non cree** tant qu'il n'y a
pas de code reel a y mettre — voir "Ce qui n'existe pas encore" en bas
de page.

## Vue d'ensemble

```
core/            Contrats et infrastructure partages par toute strategie.
data/            Acces aux donnees de marche.
strategies/      Une strategie = un dossier autonome (logique + config.yaml).
execution/       Le seul endroit qui parle a un exchange.
observability/   Dashboard temps reel (FastAPI + WebSocket).
config/          Configuration globale, independante de toute strategie.
tests/           Tests unitaires, meme arborescence que le code.
docs/            Ce fichier + la doc metier de chaque strategie.
```

## Le contrat central : `core/interfaces.py`

Trois classes font tenir tout le reste :

- **`Strategy`** — `symbols()` (de quoi ai-je besoin a chaque tick) et
  `evaluate(market_data, open_positions) -> list[Signal]` (que dois-je
  faire). Une strategie ne passe jamais d'ordre elle-meme.
- **`Signal`** — la sortie d'une strategie pour un instrument, a un
  instant donne : action (`entree`/`sortie`/`stop`/`attente`), sens,
  score, et un dict `legs` qui porte tout ce qu'`execution/` doit savoir
  pour executer (symboles, prix, notionnels) sans reinterroger la
  strategie.
- **`Position`** — une position ouverte, telle que suivie par
  `core.portfolio.Portfolio`.

## Le flux d'un tick

```
execution/bot.py
  1. core.registry.load_active_strategies()   <- config/active_strategies.yaml
  2. fetch OHLCV pour tous les symboles requis (data/sources/)
  3. pour chaque strategie : strategy.evaluate(market_data, positions_ouvertes)
  4. pour chaque Signal "entree" :
       core.risk.RiskManager.can_open()       <- verifie les limites globales
       execution.order_router.OrderRouter.open()
       core.portfolio.Portfolio.open_position()
  5. pour chaque Signal "sortie"/"stop" :
       execution.order_router.OrderRouter.close()
       core.portfolio.Portfolio.close_position()
  6. core.event_bus.publish() pour chaque evenement -> dashboard
```

`RiskManager` est le seul endroit qui peut refuser une entree : exposition
brute max, nombre de positions concurrentes max, kill switch sur perte
cumulee. Les seuils viennent de `config/settings.yaml`, pas de code en dur.

`OrderRouter` est le seul endroit qui construit un ordre ccxt. S'il ouvre
une jambe et que la seconde echoue, il tente une cloture de compensation
immediate sur la jambe deja remplie plutot que de laisser une exposition
directionnelle non trackee (`execution/order_router.py`, classe
`LegFailure`).

## Configuration : deux niveaux, une seule verite chacun

- `config/settings.yaml` — ce qui est vrai quelle que soit la strategie :
  `dry_run`, `poll_seconds`, les frais d'execution (fait exchange, pas
  choix de strategie), les limites de risque globales.
- `strategies/<nom>/config.yaml` — les seuils propres a CETTE strategie
  (ex. `Z_ENTRY`/`Z_EXIT`/`Z_STOP` pour pairs_cointegration). Aucun autre
  fichier de la strategie ne doit redefinir ces valeurs en dur.

`config/active_strategies.yaml` decide ce qui tourne : ajouter ou retirer
une strategie ne touche a aucun code.

## Lancer les choses

```bash
# Screener : ecrit screening_results.csv a la racine du depot
.venv/bin/python -m strategies.pairs_cointegration.screener

# Backtest sur une paire
.venv/bin/python -m strategies.pairs_cointegration.backtest ETH/USDT SOL/USDT

# Balayage de parametres
.venv/bin/python -m strategies.pairs_cointegration.optimize ETH/USDT SOL/USDT

# Dashboard seul (bot inactif)
.venv/bin/uvicorn observability.server:app --reload --port 8000

# Dashboard + bot (DRY_RUN=True, testnet uniquement)
START_BOT=1 .venv/bin/uvicorn observability.server:app --port 8000

# Tests
.venv/bin/python -m pytest
```

Les cles testnet vont dans `config/secrets.env` (copie de
`config/secrets.env.example`), jamais commite.

## Ce qui n'existe pas encore

Ces dossiers du schema cible ne sont pas crees tant qu'il n'y a pas de
code reel a y mettre — les creer vides n'aurait ete que de la
decoration :

- `strategies/cash_and_carry/`, `strategies/_template/`
- `agents/` (Idea Hub, comite d'agents specialistes)
- `execution/exchanges/kraken.py`, `coinbase.py`
- `observability/db.py`, `audit_log.py`, tableaux Streamlit
- `backtesting/` generique (moteur agnostique de strategie, validation
  sur donnees aleatoires) — tant qu'une seule strategie existe, il n'y a
  rien a generaliser ; `strategies/pairs_cointegration/backtest.py` fait
  ce travail pour l'instant.

Quand l'un de ces morceaux devient reel, il prend sa place dans la
hierarchie ci-dessus — pas avant.
