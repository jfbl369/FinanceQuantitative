from core.interfaces import Position
from core.portfolio import Portfolio
from core.risk import RiskLimits, RiskManager

LIMITS = RiskLimits(
    max_gross_exposure_usdt=50_000.0,
    max_concurrent_positions=2,
    max_cumulative_loss_usdt=-1_000.0,
)


def _position(instrument_id):
    return Position(
        instrument_id=instrument_id, strategy="pairs_cointegration", side=1,
        notional_a=10_000.0, notional_b=10_000.0,
        entry={"py": 1.0, "px": 1.0, "ts": "t0"},
    )


def test_can_open_true_when_within_all_limits():
    rm = RiskManager(LIMITS)
    ok, reason = rm.can_open(Portfolio(), notional_a=10_000.0, notional_b=10_000.0)
    assert ok
    assert reason == ""


def test_can_open_false_when_gross_exposure_would_be_exceeded():
    rm = RiskManager(LIMITS)
    portfolio = Portfolio()
    portfolio.open_position(_position("A-B"))  # 20k deja engages

    ok, reason = rm.can_open(portfolio, notional_a=20_000.0, notional_b=20_000.0)

    assert not ok
    assert "exposition brute" in reason


def test_can_open_false_when_max_concurrent_positions_reached():
    rm = RiskManager(LIMITS)
    portfolio = Portfolio()
    portfolio.open_position(_position("A-B"))
    portfolio.open_position(_position("C-D"))  # limite = 2

    ok, reason = rm.can_open(portfolio, notional_a=100.0, notional_b=100.0)

    assert not ok
    assert "positions concurrentes" in reason


def test_can_open_false_when_kill_switch_triggered():
    rm = RiskManager(LIMITS)
    portfolio = Portfolio()
    portfolio.realized_pnl = -1_500.0  # au-dela de max_cumulative_loss_usdt

    ok, reason = rm.can_open(portfolio, notional_a=100.0, notional_b=100.0)

    assert not ok
    assert "kill switch" in reason
