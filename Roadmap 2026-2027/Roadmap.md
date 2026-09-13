# Roadmap Quant — Sprint 3 mois

**Objectif** : niveau maths/finance quant solide pour entretiens techniques (banque, fonds d'investissement, private markets) + certification CAIA Level 1.
**Rythme** : 15h+/semaine — ~7h maths, ~5h CAIA, ~3-4h Python (arrimé aux maths de la semaine).
**Règle d'or** : un livre principal par semaine. Les fallbacks ne sont ouverts qu'en cas de blocage sur une notion précise (max 20-30 min), jamais comme point de départ.

---

## Mois 1 — Le socle (probabilités & algèbre linéaire)

### Semaine 1 — Combinatoire & probabilités conditionnelles

**Livre principal : A Practical Guide to Quantitative Finance Interviews (Xinfeng Zhou — le "Green Book")**
- [x] Chapitre Combinatorics — tous les exercices
- [ ] Chapitre Probability Theory (partie 1 : probabilités conditionnelles, indépendance, Bayes) — tous les exercices
- [ ] Refaire à la main, sans regarder la solution avant 10 min de blocage minimum

**Fallback si notion de base fragile** : *Probabilités pour les Non-Probabilistes* (Appel) — chapitres sur les probabilités conditionnelles et Bayes
**Fallback ultra-basique** : *Statistics for Dummies* — chapitre probabilités de base

**Python**
- [ ] Simulateur Monty Hall (vérifier 1/3 vs 2/3 par simulation)
- [ ] Simulateur marche aléatoire simple 1D (vérifier espérance de retour à l'origine)

**CAIA**
- [ ] Chapitre "Introduction to Alternative Investments" — lecture complète + notes
- [ ] Comprendre la structure de l'examen (nombre de questions, pondération par thème, format)

---

### Semaine 2 — Variables aléatoires, espérance, distributions

**Livre principal : Green Book (Zhou)**
- [ ] Chapitre Probability Theory (partie 2 : espérance, variance, covariance) — tous les exercices
- [ ] Chapitre Distributions (normale, log-normale, binomiale, Poisson, exponentielle) — tous les exercices
- [ ] Brainteasers classiques : œufs qui tombent, ponts et gardes, piles consécutives

**Fallback** : *Probabilités pour les Non-Probabilistes* (Appel) — chapitres distributions et espérance conditionnelle

**Python**
- [ ] Simulateur de lancers de dés — vérifier espérance/variance calculées à la main
- [ ] Générateur de variables log-normales — vérifier visuellement la forme de la distribution du prix d'un actif

**CAIA**
- [ ] Chapitre "Real Assets" — lecture complète + notes
- [ ] Créer les premières flashcards/résumés de définitions clés

**Notebook CAIA #1 — Frais de hedge funds**
- [ ] Simuler une série de rendements bruts mensuels (avec mois négatifs)
- [ ] Calculer management fee + performance fee avec high-water mark
- [ ] Modéliser hurdle rate (hard vs soft)
- [ ] Visualiser NAV brute vs nette
- [ ] Bonus : simulation du biais de survie (100 fonds, exclusion des perdants, biais sur la moyenne)

---

### Semaine 3 — Algèbre linéaire (vecteurs, matrices, valeurs propres)

**Livre principal : Introductory Mathematical Analysis for Quantitative Finance (Ritelli & Spaletta)**
- [ ] Chapitre vecteurs et matrices — opérations de base, exercices
- [ ] Chapitre déterminants et systèmes linéaires — exercices
- [ ] Chapitre valeurs propres / vecteurs propres — dérivation + exercices à la main

**Fallback si le rythme est trop rapide** : cours vidéo MIT OpenCourseWare (Gilbert Strang) — séances sur les valeurs propres
**Fallback ultra-basique** : *Calculus for Dummies* — si manipulation d'expressions algébriques fragile

**Python**
- [ ] Implémenter calcul de valeurs propres/vecteurs propres à la main (méthode de la puissance itérée) et comparer à numpy.linalg.eig

**CAIA**
- [ ] Chapitre "Private Equity" (partie 1 : structures, cycle de vie du fonds) — lecture + notes

---

### Semaine 4 — Décomposition spectrale, PCA, Cholesky

**Livre principal : Ritelli & Spaletta**
- [ ] Chapitre décomposition spectrale / diagonalisation — exercices
- [ ] Chapitre matrices définies positives, décomposition de Cholesky — exercices

**Fallback** : MIT OCW Strang — séance PCA / décomposition spectrale

**Python**
- [ ] Pricer d'option européenne par Monte Carlo (Black-Scholes) + comparaison à la formule fermée
- [ ] PCA from-scratch sur une courbe de taux (level/slope/curvature) — réutiliser données du projet fixed income existant
- [ ] Simulation de variables corrélées via Cholesky (vérifier la matrice de covariance simulée vs cible)

**CAIA**
- [ ] Chapitre "Private Equity" (partie 2 : valorisation, cash flows) — lecture + notes
- [ ] Chapitre "Hedge Funds" (partie 1 : stratégies, structures) — lecture + notes

**Notebook CAIA #2 — J-curve Private Equity**
- [ ] Simuler calendrier de capital calls (années 1-5) et distributions (années 4-10)
- [ ] Calculer NAV cumulée par année → tracer la J-curve
- [ ] Implémenter IRR par Newton-Raphson from scratch
- [ ] Calculer DPI, RVPI, TVPI par année
- [ ] Faire varier le rythme de déploiement et observer l'impact sur la profondeur de la J-curve

---

## Mois 2 — Calcul et calcul stochastique

### Semaine 5 — Calcul différentiel, dérivées partielles

**Livre principal : Ritelli & Spaletta**
- [ ] Chapitre dérivées et règles de dérivation — exercices
- [ ] Chapitre dérivées partielles, gradient — exercices
- [ ] Chapitre séries de Taylor — exercices, application aux approximations de Greeks

**Fallback** : *Calculus Essentials for Dummies* — si dérivées de base pas automatiques
**Fallback avancé** : *Calculus II for Dummies* — si dérivées partielles nouvelles pour toi

**Python**
- [ ] Implémenter calcul de Greeks par différences finies (delta, gamma, vega) sur le pricer Monte Carlo de la semaine 4

**CAIA**
- [ ] Chapitre "Hedge Funds" (partie 2 : due diligence, risques) — lecture + notes

---

### Semaine 6 — Optimisation (Lagrange, Newton-Raphson, descente de gradient)

**Livre principal : Ritelli & Spaletta**
- [ ] Chapitre optimisation sans contrainte — exercices
- [ ] Chapitre multiplicateurs de Lagrange — exercices à la main (2-3 problèmes de portefeuille simplifiés)

**Fallback** : notes de ton propre projet OLS (gradient descent déjà implémenté) — relire tes dérivations pour faire le pont explicite

**Python**
- [ ] Calcul des Greeks analytiques (formules fermées Black-Scholes) et comparaison avec les différences finies de la semaine 5
- [ ] Documenter les écarts et leurs causes (pas de discrétisation, erreur numérique)

**CAIA**
- [ ] Chapitre "Real Estate" (partie 1 : structures d'investissement, indices) — lecture + notes

**Notebook CAIA #3 — Cap rate, NOI, effet de levier**
- [ ] Construire un pro forma simple (loyers, vacance, charges → NOI)
- [ ] Calculer cap rate et cash-on-cash return
- [ ] Ajouter dette variable (LTV) et calculer le rendement equity levier
- [ ] Identifier le point de bascule où le levier devient destructeur
- [ ] Heatmap de sensibilité LTV × taux d'intérêt

---

### Semaine 7 — Calcul stochastique : fondations discrètes

**Livre principal : Green Book (Zhou) — chapitre Stochastic Processes and Stochastic Calculus**
- [ ] Section marches aléatoires et chaînes de Markov — tous les exercices
- [ ] Section introduction au mouvement brownien et martingales — tous les exercices

**Approfondissement : Stochastic Calculus for Finance I (Shreve — modèle binomial)**
- [ ] Chapitre 1 : The Binomial No-Arbitrage Pricing Model — lecture + exercices
- [ ] Chapitre 2 : Probability Theory on Coin Toss Space — lecture + exercices
- [ ] Chapitre 3 : State Prices — lecture + exercices
- [ ] Chapitre 4 : American Derivative Securities — lecture (survol si temps limité)

**Fallback si le français aide à ancrer** : *Introduction au calcul stochastique appliqué à la finance* — chapitres correspondants
**Fallback condensé** : *Cours de Calcul stochastique Master 2IF EVRY* — comme résumé de consolidation après Shreve I

**Python**
- [ ] Implémenter le modèle binomial (CRR) from scratch pour pricer une option européenne
- [ ] Comparer convergence du binomial vers Black-Scholes quand le nombre de pas augmente

**CAIA**
- [ ] Chapitre "Real Estate" (partie 2 : REITs, dette immobilière) — lecture + notes

---

### Semaine 8 — Calcul stochastique : temps continu, Itô, Black-Scholes

**Livre principal : Green Book (Zhou) — chapitre Finance (options, Black-Scholes, Greeks) + fin du chapitre Stochastic Calculus**
- [ ] Section lemme d'Itô et applications — tous les exercices
- [ ] Section pricing d'options et Black-Scholes — tous les exercices

**Approfondissement : Stochastic Calculus for Finance II (Shreve — temps continu)**
- [ ] Chapitre 1 : General Probability Theory — lecture + exercices clés
- [ ] Chapitre 3 : Brownian Motion — lecture + exercices
- [ ] Chapitre 4 : Stochastic Calculus (lemme d'Itô) — lecture + dérivation à la main
- [ ] Chapitre 5 : Risk-Neutral Pricing (dérivation de Black-Scholes) — lecture + dérivation complète à la main

**Exercices croisés** : *Problems and Solutions in Mathematical Finance Vol. 1* (Chin/Nel/Olafsson) — chapitres calcul stochastique et Black-Scholes
**Lecture de contexte (après seulement, jamais avant d'avoir dérivé toi-même)** : *Formule de Black-Scholes* / *Fischer Black and Revolutionary Finance*

**Python**
- [ ] Simulation de mouvement brownien (trajectoires) et vérification empirique de la loi normale des increments
- [ ] Dérivation codée de Black-Scholes via PDE (différences finies) et comparaison avec la formule fermée et le Monte Carlo

**CAIA**
- [ ] Chapitre "Structured Products" (introduction) — lecture + notes

**Notebook CAIA #4 — Corrélation cachée en période de crise**
- [ ] Récupérer/simuler rendements actions/obligations/hedge funds/PE incluant une période de crise
- [ ] Calculer corrélations en période normale vs en période de crise (rolling ou split d'échantillon)
- [ ] Visualiser la matrice de corrélation qui se resserre en drawdown
- [ ] Bonus : lissage artificiel des rendements PE/immobilier (autocorrélation, unsmoothing)

**⚠️ Point de vigilance** : si ce mur bloque, sacrifier une partie du Mois 3 "spécialisation" pour revenir ici — jamais l'inverse.

---

## Mois 3 — Consolidation, entretiens, spécialisation

### Semaine 9 — Mode entretien : probabilités et pricing

**Livre principal : Quant Job Interview (Mark Joshi)**
- [ ] Chapitres probabilités/brainteasers — toutes les questions
- [ ] Chapitres pricing d'options — toutes les questions

**En parallèle** : *Heard on the Street* (Timothy Crack) — chapitres brainteasers et probabilités (corpus complémentaire plus large, statistique et finance générale, pas redondant avec le Green Book)

**Python**
- [ ] Refactoriser le pricer Black-Scholes (semaine 8) en outil réutilisable (fonction propre, tests unitaires simples)

**CAIA**
- [ ] Chapitre "Commodities" (partie 1 : marchés, contrats forward/futures) — lecture + notes

---

### Semaine 10 — Mode entretien : statistique et séries temporelles

**Livre principal : Quant Job Interview (Mark Joshi) — suite**
- [ ] Chapitres statistique et estimation — toutes les questions
- [ ] Chapitres séries temporelles / marchés — toutes les questions

**Révision transverse** : *FAQ in Quantitative Finance* (Wilmott) — parcourir les Q&A des thèmes déjà couverts

**Python**
- [ ] Outil de valorisation d'actif illiquide (private debt) : actualisation de flux avec courbe de taux + spread de crédit
- [ ] VaR et Expected Shortfall calculés from scratch sur un portefeuille simulé

**CAIA**
- [ ] Chapitre "Commodities" (partie 2 : roll yield, contango/backwardation) — lecture + notes

**Notebook CAIA #5 — Contango/backwardation et structurés**
- [ ] Simuler une courbe forward de matières premières
- [ ] Calculer roll yield en contango vs backwardation
- [ ] Comparer rendement spot vs rendement d'un indice roulé
- [ ] Construire et tracer 2-3 payoffs de structurés (capital garanti + call, reverse convertible, autocall simplifié)

---

### Semaine 11 — Spécialisation selon cible d'entretien

**Livre principal — choisir selon la cible qui se précise** :
- [ ] Banque/desk risque → *Handbook of Financial Risk Management* (Roncalli) — chapitres VaR/ES/stress testing
- [ ] Fonds systématique → *Quantitative Portfolio Management* (Isichenko) — chapitres construction de portefeuille
- [ ] Private markets/rates → *The Handbook of Fixed Income Securities* — chapitres pricing obligataire et courbes

**Python**
- [ ] Démarrer mini backtester/dashboard de risque (Sharpe, drawdown) sur portefeuille simulé — structure du projet

**CAIA**
- [ ] Révision complète Private Equity + Hedge Funds (mock questions)

---

### Semaine 12 — Consolidation finale, mocks, révisions

**Maths**
- [ ] Reprendre tous les exercices ratés/difficiles du Green Book, Zhou (semaines 1-2, 7-8)
- [ ] Reprendre tous les exercices ratés/difficiles de Quant Job Interview, Joshi, et Heard on the Street, Crack (semaines 9-10)
- [ ] Sessions de mock interview technique chronométrées (brainteasers + pricing + stats)

**Python**
- [ ] Finaliser le mini backtester/dashboard de risque (Sharpe, VaR, ES, drawdown) — synthèse de tout le sprint

**CAIA**
- [ ] Révision complète Real Estate + Commodities + Structured Products
- [ ] Mock exam complet (conditions d'examen)
- [ ] Identifier et retravailler les 2-3 thèmes les plus faibles

---

## Bibliothèque — statut de référence

**Utilisés dans le plan** : A Practical Guide to Quantitative Finance Interviews / "Green Book" (Xinfeng Zhou), Heard on the Street (Timothy Crack), Probabilités pour les Non-Probabilistes (Appel), Ritelli & Spaletta, Stochastic Calculus for Finance I & II (Shreve), Introduction au calcul stochastique appliqué à la finance, Cours EVRY, Problems and Solutions in Mathematical Finance Vol. 1, Quant Job Interview (Joshi), FAQ in Quantitative Finance (Wilmott), Handbook of Financial Risk Management (Roncalli), Quantitative Portfolio Management (Isichenko), Handbook of Fixed Income Securities

**Note terminologique** : le "Green Book" désigne *A Practical Guide to Quantitative Finance Interviews* de Xinfeng Zhou (nom donné à la couleur de sa couverture) — pas *Heard on the Street* de Timothy Crack, qui est un livre distinct et complémentaire. Le Green Book (Zhou) est plus large et plus exigeant (probabilités, algèbre linéaire, calcul stochastique, finance, programmation) ; Heard on the Street (Crack) est plus accessible et couvre davantage de statistique/finance générale — les deux sont considérés comme quasi indispensables ensemble pour un poste quant.

**Fallbacks nommés (dépannage ponctuel, max 20-30 min)** : Statistics for Dummies, Calculus for Dummies / Essentials / II, Business Math for Dummies, MIT OCW (Strang), manuels Magnard/Stewart

**En réserve pour après le sprint** : Candelpergher, De l'intégration aux probabilités (Garet & Kurtzmann / Ouvrard), Couverture des risques dans les marchés financiers (El Karoui), Advances in Financial Machine Learning (López de Prado), Financial Risk Management with Machine Learning, Chaînes de Markov et simulations (El Karoui), Processus de Markov et applications (Pardoux), Analyse et étude des processus markoviens décisionnels, Rosenbaum Investment Banking, Finding Alphas (Tulchinsky), Inside the Black Box, Quantitative Trading, Commodity Derivatives / Commodity Option Pricing / Commodities For Dummies (sauf si CAIA oriente fortement vers les commodities)

**Non positionnés — à préciser si besoin** : math-deep.pdf, Mathematics-notation-list.pdf, Powell-SDAM, Maths.xlsx, Symboles.docx
