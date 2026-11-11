import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.scenario_engine import (
    validate_scenario_probabilities,
    calculate_portfolio_return,
    calculate_expected_return,
    apply_stress_shocks,
    run_monte_carlo,
)


# --- validate_scenario_probabilities ---

def test_valid_probabilities():
    assert validate_scenario_probabilities([0.35, 0.25, 0.25, 0.15]) is True


def test_invalid_probabilities_sum_too_high():
    assert validate_scenario_probabilities([0.5, 0.5, 0.5, 0.5]) is False


def test_invalid_probabilities_sum_too_low():
    assert validate_scenario_probabilities([0.1, 0.1, 0.1, 0.1]) is False


def test_valid_two_probabilities():
    assert validate_scenario_probabilities([0.6, 0.4]) is True


def test_empty_probabilities():
    assert validate_scenario_probabilities([]) is False


# --- calculate_portfolio_return ---

def test_portfolio_return_balanced():
    result = calculate_portfolio_return([0.5, 0.5], [0.1, -0.1])
    assert abs(result - 0.0) < 1e-9


def test_portfolio_return_weighted():
    result = calculate_portfolio_return([0.6, 0.4], [0.2, -0.1])
    expected = 0.6 * 0.2 + 0.4 * (-0.1)  # 0.12 - 0.04 = 0.08
    assert abs(result - expected) < 1e-9


def test_portfolio_return_all_positive():
    result = calculate_portfolio_return([0.5, 0.5], [0.1, 0.2])
    assert abs(result - 0.15) < 1e-9


def test_portfolio_return_raises_on_bad_weights():
    with pytest.raises(ValueError, match="sum to 1.0"):
        calculate_portfolio_return([0.6, 0.6], [0.1, 0.1])


def test_portfolio_return_raises_on_length_mismatch():
    with pytest.raises(ValueError):
        calculate_portfolio_return([0.5, 0.5], [0.1])


# --- calculate_expected_return ---

def test_expected_return_calculation():
    probs = [0.35, 0.25, 0.25, 0.15]
    returns = [0.05, -0.10, -0.05, -0.15]
    result = calculate_expected_return(probs, returns)
    expected = 0.35 * 0.05 + 0.25 * (-0.10) + 0.25 * (-0.05) + 0.15 * (-0.15)
    assert abs(result - expected) < 1e-9


def test_expected_return_raises_bad_probs():
    with pytest.raises(ValueError):
        calculate_expected_return([0.5, 0.5, 0.5], [0.1, 0.1, 0.1])


# --- apply_stress_shocks ---

def _make_holdings(total=1_000_000):
    return [
        {"symbol": "BNP.PA", "weight": 0.3, "market_value": 300_000, "sector": "Financials", "asset_type": "equity"},
        {"symbol": "TTE.PA", "weight": 0.4, "market_value": 400_000, "sector": "Energy", "asset_type": "equity"},
        {"symbol": "CASH", "weight": 0.3, "market_value": 300_000, "sector": None, "asset_type": "cash"},
    ]


def test_market_shock_negative_pnl():
    holdings = _make_holdings()
    result = apply_stress_shocks(holdings, {"market": -0.10})
    assert result["portfolio_pnl_pct"] < 0, "Negative market shock should produce negative P&L"
    assert result["portfolio_pnl_eur"] < 0


def test_market_shock_zero():
    holdings = _make_holdings()
    result = apply_stress_shocks(holdings, {"market": 0.0})
    assert abs(result["portfolio_pnl_pct"]) < 1e-9


def test_cash_holding_unaffected_by_market_shock():
    holdings = _make_holdings()
    result = apply_stress_shocks(holdings, {"market": -0.20})
    cash_contrib = next((h for h in result["holding_contributions"] if h["symbol"] == "CASH"), None)
    assert cash_contrib is not None
    assert cash_contrib["pnl_pct"] == 0.0


def test_sovereign_spread_shock_financials():
    holdings = [
        {"symbol": "BNP.PA", "weight": 1.0, "market_value": 1_000_000, "sector": "Financials", "asset_type": "equity"},
    ]
    result = apply_stress_shocks(holdings, {"sovereign_spread": 100})
    # Financials sensitivity: -0.015 per bps, so 100bps = -1.5 (150% loss) which is -15 pnl_pct
    assert result["portfolio_pnl_pct"] < 0


def test_energy_shock_positive_for_energy_sector():
    holdings = [
        {"symbol": "TTE.PA", "weight": 1.0, "market_value": 1_000_000, "sector": "Energy", "asset_type": "equity"},
    ]
    result = apply_stress_shocks(holdings, {"energy": 0.20})
    assert result["portfolio_pnl_pct"] > 0, "Energy sector benefits from higher energy prices"


def test_multiple_shocks():
    holdings = _make_holdings()
    result = apply_stress_shocks(holdings, {"market": -0.10, "sovereign_spread": 50})
    assert "portfolio_pnl_pct" in result
    assert "holding_contributions" in result
    assert len(result["holding_contributions"]) == 3


def test_empty_shocks():
    holdings = _make_holdings()
    result = apply_stress_shocks(holdings, {})
    assert abs(result["portfolio_pnl_pct"]) < 1e-9


def test_stress_shocks_raises_zero_value():
    with pytest.raises(ValueError):
        apply_stress_shocks([], {"market": -0.10})


# --- run_monte_carlo ---

def test_monte_carlo_reproducible():
    weights = [0.5, 0.5]
    returns = [0.07, 0.08]
    vols = [0.20, 0.25]
    r1 = run_monte_carlo(weights, returns, vols, n_paths=100, seed=42)
    r2 = run_monte_carlo(weights, returns, vols, n_paths=100, seed=42)
    assert r1["percentile_50"] == r2["percentile_50"]
    assert r1["var_95"] == r2["var_95"]


def test_monte_carlo_different_seeds():
    weights = [0.5, 0.5]
    returns = [0.07, 0.08]
    vols = [0.20, 0.25]
    r1 = run_monte_carlo(weights, returns, vols, n_paths=100, seed=42)
    r2 = run_monte_carlo(weights, returns, vols, n_paths=100, seed=99)
    assert r1["percentile_50"] != r2["percentile_50"]


def test_monte_carlo_var_positive():
    weights = [0.5, 0.5]
    returns = [0.07, 0.08]
    vols = [0.20, 0.25]
    result = run_monte_carlo(weights, returns, vols, n_paths=500, seed=42)
    assert result["var_95"] > 0, "VaR should be a positive loss measure"


def test_monte_carlo_percentile_ordering():
    weights = [0.5, 0.5]
    returns = [0.07, 0.08]
    vols = [0.20, 0.25]
    result = run_monte_carlo(weights, returns, vols, n_paths=500, seed=42)
    assert result["percentile_5"] <= result["percentile_50"] <= result["percentile_95"]


def test_monte_carlo_returns_count():
    weights = [1.0]
    returns = [0.07]
    vols = [0.20]
    result = run_monte_carlo(weights, returns, vols, n_paths=200, seed=42)
    assert len(result["all_returns"]) == 200
