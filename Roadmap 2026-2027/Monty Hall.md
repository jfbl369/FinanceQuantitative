# Monty Hall

## Pourquoi ça compte
Brainteaser classique testé quasi systématiquement en entretien quant/trading pour vérifier que le candidat sait remettre en cause son intuition et raisonner proprement avec des probabilités conditionnelles. Le piège n'est pas la difficulté du calcul, mais la résistance de l'intuition fausse — l'interviewer regarde comment tu argumentes, pas juste si tu connais "la réponse".

## Énoncé
Trois portes. Derrière une, une voiture ; derrière les deux autres, une chèvre. Tu choisis une porte (disons porte 1). Le présentateur, qui sait où est la voiture, ouvre une des deux portes restantes en révélant une chèvre (disons porte 3). Il te propose de changer pour la porte restante (porte 2). Dois-tu changer ?

**Réponse : oui, changer double la probabilité de gagner (de 1/3 à 2/3).**

## Formule

Probabilité de gagner en restant sur son choix initial :
$$
P(\text{voiture en porte 1}) = \frac{1}{3}
$$

Par complémentarité, la probabilité que la voiture soit derrière une des deux autres portes (2 ou 3) est :
$$
P(\text{voiture en porte 2 ou 3}) = \frac{2}{3}
$$

Le présentateur ouvre toujours une chèvre parmi les portes non choisies, sans changer la probabilité globale de ce groupe — il ne fait que révéler *laquelle* des deux portes du groupe est vide. Donc :
$$
P(\text{voiture en porte 2} \mid \text{présentateur ouvre porte 3}) = \frac{2}{3}
$$

## Exemple chiffré

Imagine 300 parties, également réparties sur les 3 positions possibles de la voiture :

| Voiture en porte | Nombre de parties | Tu choisis porte 1 | Présentateur ouvre | Résultat si tu restes | Résultat si tu changes |
|---|---|---|---|---|---|
| Porte 1 | 100 | Porte 1 | Porte 2 ou 3 (au choix) | Gagne | Perd |
| Porte 2 | 100 | Porte 1 | Porte 3 (forcé, seule chèvre restante) | Perd | Gagne |
| Porte 3 | 100 | Porte 1 | Porte 2 (forcé, seule chèvre restante) | Perd | Gagne |

Sur 300 parties : rester sur son choix initial gagne 100 fois (1/3). Changer gagne 200 fois (2/3).

Le point clé visible dans le tableau : quand la voiture n'est pas en porte 1 (200 cas sur 300), le présentateur n'a **aucun choix** — il est forcé d'ouvrir l'unique porte avec une chèvre, ce qui te dit exactement où est la voiture si tu changes.

## Dérivation / intuition

La version qui convainc le plus vite en entretien : **le présentateur ajoute de l'information, mais seulement si tu changes de porte.**

- Ta porte initiale (porte 1) a 1/3 de chance de cacher la voiture, et cette probabilité ne bouge jamais — le présentateur n'ouvre jamais TA porte, donc aucune information nouvelle ne te concerne si tu restes.
- Les deux autres portes (2 et 3) se partageaient 2/3 à elles deux. Une fois que le présentateur élimine une chèvre certaine parmi elles, ce 2/3 ne se répartit pas à nouveau sur 3 portes — il se concentre entièrement sur la seule porte restante du groupe.

Astuce pour convaincre son intuition récalcitrante : pousser le problème à 100 portes. Tu choisis 1 porte parmi 100 (1% de chance). Le présentateur ouvre 98 portes vides parmi les 99 restantes, ne laissant qu'une seule porte fermée en face de la tienne. Il paraît évident que cette porte restante concentre les 99% de probabilité que tu n'avais pas au départ.

## Piège classique en entretien

- **Erreur la plus fréquente** : penser qu'après l'ouverture d'une porte, il reste "2 portes donc 50/50" — c'est faux car ça ignore que le choix du présentateur n'est pas aléatoire (il sait où est la voiture et évite toujours de la révéler).
- **Variante piège** : si le présentateur choisit sa porte *au hasard* parmi les deux restantes (et qu'il se trouve que par chance il révèle une chèvre), alors la probabilité devient bien 50/50 — parce que l'information apportée par son choix n'est plus la même. L'interviewer peut poser cette variante juste pour voir si tu sur-appliques la réponse "il faut toujours changer" sans comprendre pourquoi.
- **Ce qui est évalué** : ta capacité à formaliser avec $P(\cdot \mid \cdot)$ plutôt qu'à réciter la conclusion "il faut changer" sans savoir la redériver sous une variante différente.

## Lien
- Roadmap : [Semaine 1](../../README.md#semaine-1--combinatoire--probabilités-conditionnelles)
- Livre source : A Practical Guide to Quantitative Finance Interviews (Zhou), chapitre Probability Theory — brainteasers classiques
