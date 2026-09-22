"""
Test de cointegration Engle-Granger, dans les deux sens.

Ordre des tests, chacun peut disqualifier la paire :
  1. ADF sur chaque log-prix seul -> doit etre NON stationnaire (sinon
     c'est un artefact : un prix stationnaire, ca n'existe pas en crypto).
  2. OLS dans les deux sens -> on garde le sens le plus cointegre.
  3. coint() de statsmodels -> le vrai test (Engle-Granger, valeurs
     critiques corrigees pour le fait que beta est estime ; un
     adfuller() brut sur le residu sur-rejette et ment).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint


def ols(y: np.ndarray, x: np.ndarray):
    """Regresse y sur x avec constante. Retourne (alpha, beta, residus)."""
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit()
    alpha, beta = res.params[0], res.params[1]
    return alpha, beta, res.resid


def adf_pvalue(log_price: pd.Series) -> float:
    """p-value ADF sur une serie seule. On VEUT une valeur haute (non stationnaire)."""
    return float(adfuller(log_price, autolag="AIC")[1])


def best_direction(log_a: pd.Series, log_b: pd.Series, name_a: str, name_b: str):
    """
    coint(y, x) fait sa propre regression et corrige les valeurs critiques
    du fait que beta est estime. On l'appelle dans les deux sens et on
    garde le plus significatif.

    Retourne dict avec y/x/sym_y/sym_x/coint_p/alpha/beta/spread.
    """
    p_ab = coint(log_a, log_b)[1]
    p_ba = coint(log_b, log_a)[1]

    if p_ab <= p_ba:
        y, x, sym_y, sym_x, coint_p = log_a, log_b, name_a, name_b, p_ab
    else:
        y, x, sym_y, sym_x, coint_p = log_b, log_a, name_b, name_a, p_ba

    alpha, beta, resid = ols(y.values, x.values)
    spread = pd.Series(resid, index=y.index)

    return {
        "y": y, "x": x, "sym_y": sym_y, "sym_x": sym_x,
        "coint_p": float(coint_p), "alpha": float(alpha), "beta": float(beta),
        "spread": spread,
    }
