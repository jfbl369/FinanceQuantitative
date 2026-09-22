import numpy as np
import pandas as pd
import pytest

from strategies.pairs_cointegration.cointegration import ols
from strategies.pairs_cointegration.signals import (
    FLAT, LONG_SPREAD, SHORT_SPREAD, Z_ENTRY, Z_EXIT, Z_STOP,
    compute_zscore, decide, entry_side,
)
from strategies.pairs_cointegration.tradability import (
    crossings_per_year, half_life_hours, net_amplitude_pct,
)


# --- signals.decide : la machine a etats qui protege le capital ---------

@pytest.mark.parametrize("z,position,expected", [
    (0.0, FLAT, "attente"),
    (Z_ENTRY - 0.1, FLAT, "attente"),           # sous le seuil d'entree
    (Z_ENTRY + 0.1, FLAT, "entree"),
    (-(Z_ENTRY + 0.1), FLAT, "entree"),
    (Z_STOP + 0.5, FLAT, "attente"),            # trop tard, deja casse
    (Z_EXIT + 0.5, SHORT_SPREAD, "attente"),
    (Z_EXIT - 0.1, SHORT_SPREAD, "sortie"),
    (Z_STOP + 0.1, SHORT_SPREAD, "stop"),
    (-(Z_STOP + 0.1), LONG_SPREAD, "stop"),
    # Un short spread ne se stoppe PAS sur un z tres negatif : c'est un
    # profit, deja capture par la sortie, pas une casse de la relation.
    (-(Z_STOP + 0.1), SHORT_SPREAD, "attente"),
])
def test_decide_state_machine(z, position, expected):
    assert decide(z, position) == expected


def test_decide_handles_nan_and_none_as_wait():
    assert decide(float("nan"), FLAT) == "attente"
    assert decide(None, SHORT_SPREAD) == "attente"


def test_entry_side_sign():
    assert entry_side(2.5) == SHORT_SPREAD   # spread trop haut -> on le short
    assert entry_side(-2.5) == LONG_SPREAD   # spread trop bas -> on le long


# --- signals.compute_zscore : roulant, pas global ------------------------

def test_compute_zscore_first_window_bars_are_nan():
    # rolling(window=30) : les 29 premieres barres n'ont pas assez
    # d'historique, la 30e (index 29) est la premiere valeur valide.
    spread = pd.Series(np.random.default_rng(0).normal(size=100))
    z = compute_zscore(spread, window=30)
    assert z.iloc[:29].isna().all()
    assert z.iloc[29:].notna().all()


def test_compute_zscore_flat_series_gives_nan_not_inf():
    spread = pd.Series([1.0] * 50)
    z = compute_zscore(spread, window=10)
    assert not np.isinf(z.dropna()).any()


# --- cointegration.ols : OLS de base ------------------------------------

def test_ols_recovers_known_linear_relationship():
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    true_alpha, true_beta = 0.7, 1.3
    y = true_alpha + true_beta * x  # sans bruit : recuperation exacte

    alpha, beta, resid = ols(y, x)

    assert alpha == pytest.approx(true_alpha, abs=1e-9)
    assert beta == pytest.approx(true_beta, abs=1e-9)
    assert np.allclose(resid, 0.0, atol=1e-9)


# --- tradability.half_life_hours -----------------------------------------

def test_half_life_hours_on_mean_reverting_ar1_series():
    rng = np.random.default_rng(1)
    phi = 0.9  # demi-vie theorique = -ln(2)/ln(0.9) ~= 6.58
    n = 3000
    spread = np.zeros(n)
    for t in range(1, n):
        spread[t] = phi * spread[t - 1] + rng.normal(scale=0.1)

    hl = half_life_hours(spread)

    assert hl == pytest.approx(-np.log(2) / np.log(phi), rel=0.25)


def test_half_life_hours_huge_or_nan_on_random_walk():
    # phi estime sur un vrai random walk est bruite (biais Dickey-Fuller) :
    # pas forcement >= 1 exactement, mais assez pres de 1 pour rendre la
    # demi-vie inexploitable (tres grande) ou degenerescente (NaN).
    rng = np.random.default_rng(2)
    spread = np.cumsum(rng.normal(size=500))  # phi ~= 1 : ne revient jamais
    hl = half_life_hours(spread)
    assert np.isnan(hl) or hl > 200.0  # au-dela, HALF_LIFE_MAX_HOURS rejette deja


def test_half_life_hours_nan_on_degenerate_oscillation():
    spread = np.array([1.0, -1.0] * 100)  # phi <= 0
    assert np.isnan(half_life_hours(spread))


# --- tradability.crossings_per_year --------------------------------------

def test_crossings_per_year_counts_sign_changes_around_mean():
    spread = np.array([1.0, -1.0, 1.0, -1.0, 1.0])  # 4 traversees sur 5 barres
    result = crossings_per_year(spread, n_bars=5, bars_per_year=5)
    assert result == 4.0


# --- tradability.net_amplitude_pct ---------------------------------------

def test_net_amplitude_pct_positive_amplitude_beats_small_costs():
    spread = pd.Series(np.random.default_rng(3).normal(scale=0.05, size=1000))
    sigma_pct, mad_pct, net = net_amplitude_pct(spread, cost_roundtrip_pct=0.01)
    assert sigma_pct > 0
    assert mad_pct > 0
    assert net == pytest.approx(2.0 * mad_pct - 0.01)


def test_net_amplitude_pct_negative_when_costs_dominate():
    spread = pd.Series(np.random.default_rng(3).normal(scale=0.001, size=1000))
    _, _, net = net_amplitude_pct(spread, cost_roundtrip_pct=1.0)
    assert net < 0
