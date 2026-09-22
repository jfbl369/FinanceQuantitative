from core.interfaces import Position
from core.portfolio import Portfolio


def _position(instrument_id="ETH-SOL", strategy="pairs_cointegration",
              side=1, notional_a=10_000.0, notional_b=10_000.0):
    return Position(
        instrument_id=instrument_id, strategy=strategy, side=side,
        notional_a=notional_a, notional_b=notional_b,
        entry={"py": 100.0, "px": 50.0, "ts": "t0"},
    )


def test_open_position_tracked_and_exposures_computed():
    p = Portfolio()
    p.open_position(_position(notional_a=10_000.0, notional_b=8_000.0))

    assert p.n_open_positions() == 1
    assert p.gross_exposure() == 18_000.0
    assert p.net_exposure() == 2_000.0


def test_open_position_rejects_duplicate_instrument():
    p = Portfolio()
    p.open_position(_position())
    try:
        p.open_position(_position())
    except ValueError:
        pass
    else:
        assert False, "une 2e ouverture sur le meme instrument aurait du lever"


def test_close_position_updates_pnl_and_equity_curve():
    p = Portfolio()
    p.open_position(_position(instrument_id="ETH-SOL"))

    p.close_position("ETH-SOL", net_pnl=150.0, ts="t1")

    assert p.n_open_positions() == 0
    assert p.realized_pnl == 150.0
    assert p.realized_pnl_by_strategy["pairs_cointegration"] == 150.0
    assert p.equity_curve == [("t1", 150.0)]


def test_positions_for_filters_by_strategy():
    p = Portfolio()
    p.open_position(_position(instrument_id="A-B", strategy="pairs_cointegration"))
    p.open_position(_position(instrument_id="C-D", strategy="other_strategy"))

    assert set(p.positions_for("pairs_cointegration")) == {"A-B"}
    assert set(p.positions_for("other_strategy")) == {"C-D"}


def test_max_drawdown_tracks_worst_dip_from_peak():
    p = Portfolio()
    p.equity_curve = [("t0", 100.0), ("t1", 300.0), ("t2", 50.0), ("t3", 200.0)]

    # pic a 300 avant t2, creux a 50 -> drawdown de -250.
    assert p.max_drawdown() == -250.0


def test_max_drawdown_zero_when_no_trades():
    assert Portfolio().max_drawdown() == 0.0


def test_save_then_load_round_trips_open_position(tmp_path):
    path = tmp_path / "state.json"
    p = Portfolio()
    p.open_position(_position(instrument_id="C-D", notional_a=10_000.0, notional_b=8_300.0))
    p.save(path)

    loaded = Portfolio.load(path)

    assert loaded.n_open_positions() == 1
    pos = loaded.positions["C-D"]
    assert pos.side == 1
    assert pos.notional_a == 10_000.0
    assert pos.notional_b == 8_300.0
    assert pos.entry == {"py": 100.0, "px": 50.0, "ts": "t0"}


def test_save_then_load_round_trips_realized_pnl_and_equity_curve(tmp_path):
    path = tmp_path / "state.json"
    p = Portfolio()
    p.open_position(_position(instrument_id="A-B"))
    p.close_position("A-B", net_pnl=42.5, ts="t1")
    p.save(path)

    loaded = Portfolio.load(path)

    assert loaded.n_open_positions() == 0
    assert loaded.realized_pnl == 42.5
    assert loaded.realized_pnl_by_strategy == {"pairs_cointegration": 42.5}
    assert loaded.equity_curve == [("t1", 42.5)]


def test_load_missing_file_returns_empty_portfolio(tmp_path):
    loaded = Portfolio.load(tmp_path / "does_not_exist.json")

    assert loaded.positions == {}
    assert loaded.realized_pnl == 0.0
    assert loaded.equity_curve == []


def test_save_is_atomic_no_leftover_tmp_file(tmp_path):
    path = tmp_path / "state.json"
    Portfolio().save(path)

    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
