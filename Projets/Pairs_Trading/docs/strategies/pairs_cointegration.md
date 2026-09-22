# pairs_cointegration — logique metier

## Etat actuel

Les 6 paires L1 majors d'origine restent toutes rejetees (p-values de
0.26 a 0.52, loin de 0.05) — confirme sur donnees fraiches, pas un
artefact de cache. Diagnostic pose avant d'elargir : sur une paire
synthetique construite pour etre cointegree, le screener rend bien
`verdict=OK` (adf_pvalue proche de 0, beta recouvre correctement) — le
pipeline de calcul n'est pas en cause, le rejet des L1 est un vrai
resultat de marche (correles, pas cointegres, voir section 3).

L'univers a ete elargi (`strategies/pairs_cointegration/config.yaml`,
cle `pairs`) avec des couples ou une relation d'equilibre est plus
plausible : wrapped-vs-natif, L2/staking vs leur L1, DeFi blue chips,
stablecoins. Resultat : **`CRV-SUSHI` passe tous les filtres**
(`verdict=OK`, coint p=0.045, demi-vie 199h, `net_amplitude_pct=10.9`,
`expected_pnl_per_trade=11.7`) — premiere paire tradable trouvee.
`stability_pct=69` est juste sous le seuil de confiance de 70 evoque en
section 2 : a surveiller, pas un rejet.

Deux resultats annexes instructifs :
- `ARB-ETH` : cointegre (p=0.024) mais demi-vie 245h, tout juste
  au-dessus de la limite de 240h — quasi-miss, pas un rejet franc.
- `WBTC-BTC` : demi-vie tres rapide (6.4h, peg corrige quasi instantanement)
  mais amplitude negative (-0.26%) — l'ecart est trop petit pour payer
  les frais. Confirme que wrapped-vs-natif est economiquement lie mais
  pas exploitable apres couts.
- `USDC-FDUSD` : rejete des l'etape 1, FDUSD seul est deja stationnaire
  (attendu pour un stablecoin) — disqualifie avant meme le test de
  cointegration.

---

# Les 4 choix qui ont fixe les seuils actuels — en clair

Resume d'abord :

| Choix | Reponse retenue | Verdict |
|---|---|---|
| Frais | 0.4% | **Objectivement juste.** Pas un avis, un fait comptable. |
| Historique | 1h × 365j | **Bon defaut.** Reversible en une ligne de config.yaml. |
| Couples | 6 majors L1 | **Bon depart.** Le screener en elimine la moitie, c'est normal. |
| Sizing | 10k/jambe dollar-neutral | **Le seul choix discutable.** Voir §4. |

---

## 1. Les frais — la question qui n'en etait pas une

Un trade de pairs trading n'est pas *un* ordre, c'est **quatre**.

```
Ouverture :  j'achete ETH     (0.1%)
             je vends SOL     (0.1%)
Fermeture :  je vends ETH     (0.1%)
             je rachete SOL   (0.1%)
                              ------
                              0.4%
```

Ce n'est pas un parametre de strategie, c'est ce que Binance preleve —
d'ou son emplacement dans `config/settings.yaml` (`execution.fee_per_execution_pct`),
pas dans le `config.yaml` de la strategie : c'est un fait exchange,
partage par toute strategie qui passerait des ordres sur Binance.

**Pourquoi ca compte enormement ici :** le gain vise sur un trade, c'est
`(Z_ENTRY − Z_EXIT) × sigma_du_spread`, soit `1.5 × sigma`. Si le spread
d'une paire a un sigma de 2%, le gain brut est de 3%. Sur 3% brut :
- a 0.1% de frais, on garde 2.9% → la paire a l'air excellente
- a 0.4% de frais, on garde 2.6% → toujours bon

Mais sur une paire serree a sigma = 0.3% :
- a 0.1%, on « gagne » 0.35% → la paire passe le filtre
- a 0.4%, on **perd** 0.05% → la paire est un piege

C'est exactement la classe de paires que le screener doit eliminer. Avec
0.1% ces paires seraient gardees, tradees, et perdraient de l'argent
lentement sans raison apparente.

---

## 2. L'historique — 365 jours × 1h

Le compromis :

- **Trop court** (90j) : les tests statistiques (ADF, cointegration) ont
  besoin de points. Sur 2000 barres, l'ADF ne detecte pas grand-chose de
  fiable. Et les « croisements par an » sont extrapoles depuis 3 mois,
  donc tres bruites.
- **Trop long** (365j) : on traverse plusieurs regimes de marche. Une
  paire peut sembler cointegree *en moyenne sur l'annee* alors que la
  relation a casse il y a 4 mois et ne reviendra pas.

365j est le choix « statistiquement solide », et le risque de regime
que ca introduit est instrumente : c'est la colonne `stability_pct` du
CSV (`strategies/pairs_cointegration/stability.py`).

Elle recalcule le hedge ratio (beta) sur des fenetres glissantes de 30
jours et mesure s'il derive :
- `stability_pct` proche de 100 → beta identique toute l'annee, la
  relation est structurelle, les 365j sont legitimes
- `stability_pct` bas (< 70) → beta a bouge, la cointegration mesuree sur
  l'annee est une moyenne de regimes differents, **mefiance sur cette
  paire meme si sa p-value est excellente**

`market.history_days` dans `strategies/pairs_cointegration/config.yaml`
est une ligne a changer pour tout re-tester sur 180j.

---

## 3. Les couples

Six couples de majors L1. Deux choses a savoir :

**Ce n'est pas grave si la plupart sont rejetes.** C'est le metier. Sur 6
paires crypto testees honnetement, en garder 1 ou 2 est un resultat
normal (aujourd'hui : 0, voir "Etat actuel" en haut de page). Le
screener affiche un `verdict` explicite par paire (« pas cointegre »,
« demi-vie trop longue », « amplitude mangee par les frais ») qui dit
*pourquoi* chacune tombe.

**La cointegration en crypto est fragile** parce que tout est correle au
Bitcoin. Deux L1 montent et descendent ensemble, ce qui donne une belle
correlation — mais correlation ≠ cointegration. La correlation dit « ils
bougent ensemble » ; la cointegration dit « leur ecart revient toujours
au meme endroit ». C'est la deuxieme qui se trade, et elle est beaucoup
plus rare.

---

## 4. Le sizing — le seul choix discutable

« 10 000 USDT/jambe, dollar-neutral » contre l'alternative « beta-hedged ».
La difference n'est pas cosmetique.

**Dollar-neutral** = 10 000 $ sur A, 10 000 $ sur B.
**Beta-neutral** = 10 000 $ sur A, 10 000 × beta $ sur B.

Pourquoi ca change tout : la regression dit que quand B bouge de 1%, A
bouge de `beta` %. Le P&L sur la position s'ecrit

```
PnL = 10000 × (variation de A) − N_B × (variation de B)
    = 10000 × beta × (var. B) − N_B × (var. B)
    = (10000 × beta − N_B) × (variation de B)
```

Si `N_B = 10000` et que `beta = 1.0`, la parenthese est nulle : neutre,
le P&L ne depend que du spread. Parfait.

Si `beta = 1.4`, la parenthese vaut `4000` : **4 000 $ d'exposition
directionnelle residuelle** au marche. On croit trader un spread, on
trade en fait un spread *plus* un petit pari sur la hausse du crypto.
Quand le marche entier chute, on perd — sans comprendre pourquoi,
puisque la paire etait censee etre market-neutral.

Le dollar-neutral n'est correct que si beta ≈ 1. Le sizing est controle
par `sizing.beta_hedged` dans `strategies/pairs_cointegration/config.yaml`,
et `strategies/pairs_cointegration/optimize.py` teste les deux sur des
donnees reelles plutot que de trancher a l'intuition.

---

## 5. « Un programme qui decide apres backtest »

Choisir des seuils dans l'abstrait, c'est deviner.
`strategies/pairs_cointegration/optimize.py` rejoue le backtest sur
toutes les combinaisons de

- `Z_ENTRY` ∈ {1.5, 2.0, 2.5, 3.0}
- `Z_EXIT` ∈ {0.0, 0.5, 1.0}
- `Z_STOP` ∈ {3.0, 3.5, 4.0}
- `ZSCORE_WINDOW` ∈ {14j, 30j, 60j}
- `BETA_HEDGED` ∈ {True, False}

et sort un tableau classe par performance, avec pour chaque ligne le
P&L, le nombre de trades, le taux de convergence et le drawdown max.

**Deux avertissements, a lire avant de regarder ce tableau :**

1. **La meilleure ligne du tableau n'est pas le bon reglage.** Sur ~200
   combinaisons testees, la meilleure est en grande partie chanceuse.
   Elle a colle au bruit de *ces* 365 jours precis, et ne se reproduira
   pas. C'est le sur-apprentissage, et c'est la facon n°1 dont un
   backtest ment.

2. **Ce qu'il faut chercher, c'est un plateau, pas un pic.** Si
   `Z_ENTRY = 2.0` marche bien ET que 1.5 et 2.5 marchent bien aussi, la
   zone est robuste : prendre 2.0. Si `Z_ENTRY = 2.3` est spectaculaire
   mais que 2.2 et 2.4 sont mauvais, ce n'est pas un reglage, c'est un
   accident. A fuir.

---

## Ce qui reste vrai quoi qu'il arrive

`DRY_RUN = True`, testnet uniquement, aucun ordre reel. Aucun de ces
choix ne peut couter d'argent tant qu'on reste dans cette configuration
— ils ne coutent que du temps de calcul.
