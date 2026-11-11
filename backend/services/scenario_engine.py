"""
Deterministic scenario and portfolio calculation engine.
No database calls — pure functions only.
"""
import numpy as np
from typing import Optional


def validate_scenario_probabilities(probs: list) -> bool:
    """Return True if probabilities sum to 1.0 within 1e-6 tolerance."""
    if not probs:
        return False
    total = sum(probs)
    return abs(total - 1.0) < 1e-6


def calculate_portfolio_return(weights: list, scenario_returns: list) -> float:
    """
    Calculate portfolio return: sum(w_i * r_i).
    Raises ValueError if lengths differ or weights don't sum to ~1.0.
    """
    if len(weights) != len(scenario_returns):
        raise ValueError("weights and scenario_returns must have same length")
    if not validate_scenario_probabilities(weights):
        raise ValueError(f"Portfolio weights must sum to 1.0; got {sum(weights):.6f}")
    return float(sum(w * r for w, r in zip(weights, scenario_returns)))


def calculate_expected_return(scenario_probs: list, scenario_returns: list) -> float:
    """
    Calculate expected return: sum(p_s * R_s).
    Raises ValueError if probabilities don't sum to 1.0.
    """
    if len(scenario_probs) != len(scenario_returns):
        raise ValueError("scenario_probs and scenario_returns must have same length")
    if not validate_scenario_probabilities(scenario_probs):
        raise ValueError(f"Scenario probabilities must sum to 1.0; got {sum(scenario_probs):.6f}")
    return float(sum(p * r for p, r in zip(scenario_probs, scenario_returns)))


# Sector sensitivities — inputs arrive as fractions after unit normalisation in callers:
#   sovereign_spread: 1.0 = 100 bps OAT-Bund spread widening
#   ecb_rate:         1.0 = 100 bps ECB deposit-rate change
#   eur:              fractional change in EUR vs basket; positive = EUR appreciates
#   energy:           fractional change in energy price; positive = more expensive
#
# Calibration sources:
#   sovereign_spread: 2011 Eurozone crisis (OAT-Bund +200 bps → French banks -25 %)
#   ecb_rate:         2022-23 ECB hiking cycle (+400 bps → RE REITs -40 %, banks +15 %)
#   eur:              1 % EUR appreciation → luxury/industrial exporters -0.4 to -0.6 %
#   energy:           1 % energy price rise → energy producers +0.5-0.6 %, industrials -0.03 to -0.06 %
#
# All values are equity return coefficients per unit of shock (fractional, not percentage).
_SECTOR_SENSITIVITIES = {
    "sovereign_spread": {
        # Per 1.0 (= 100 bps) OAT-Bund spread widening
        "Financials":             -0.12,   # French banks most exposed (funding cost, sovereign holdings)
        "Real Estate":            -0.07,   # Rate-sensitive, domestic funding
        "Utilities":              -0.04,   # Regulated domestic revenues, some rate sensitivity
        "Industrials":            -0.020,  # Global revenues provide partial hedge
        "Consumer Discretionary": -0.018,  # Luxury names are globally diversified
        "Consumer Staples":       -0.015,
        "Healthcare":             -0.015,
        "Information Technology": -0.020,
        "Energy":                 -0.015,  # TotalEnergies — global business
        "Materials":              -0.020,
        "Communication Services": -0.020,
        "default":                -0.020,
    },
    "eur": {
        # Per 1 % EUR appreciation (positive input = EUR stronger)
        # Exporters hurt by EUR strength → negative coefficients
        # Domestic plays mildly benefit → positive coefficients
        "Industrials":            -0.50,   # Airbus, Renault, Safran — high export exposure
        "Consumer Discretionary": -0.45,   # Luxury (LVMH, Hermès, Kering) — >80 % non-EUR revenues
        "Energy":                 -0.15,   # Oil priced in USD; EUR appreciation reduces EUR revenue
        "Materials":              -0.25,   # Global commodities priced in USD
        "Healthcare":             -0.25,   # Sanofi, EssilorLuxottica — large USD/global revenue base
        "Information Technology": -0.20,   # Capgemini, Dassault — global contracts
        "Consumer Staples":       -0.12,   # L'Oréal, Carrefour — mixed domestic/export
        "Financials":             +0.08,   # Domestic; mild benefit from EUR stability/strength
        "Utilities":              +0.05,   # Engie — mostly domestic revenues
        "Real Estate":            +0.03,   # Domestic assets
        "Communication Services": +0.05,   # Orange — predominantly domestic
        "default":                -0.15,
    },
    "ecb_rate": {
        # Per 1.0 (= 100 bps) ECB rate hike
        "Real Estate":            -0.07,   # Unibail — high leverage, long-duration assets
        "Utilities":              -0.05,   # Engie, Veolia — high capex, rate-sensitive
        "Information Technology": -0.04,   # Long-duration growth valuations
        "Communication Services": -0.03,   # Capital-intensive, leveraged
        "Consumer Discretionary": -0.030,  # Discretionary spending, some leverage
        "Consumer Staples":       -0.025,
        "Industrials":            -0.025,
        "Materials":              -0.025,
        "Healthcare":             -0.020,
        "Energy":                 -0.015,
        "Financials":             +0.025,  # Net interest margin benefit for banks
        "default":                -0.030,
    },
    "energy": {
        # Per 1 % increase in energy price (fractional input, e.g. 0.10 = +10 %)
        "Energy":                 +0.60,   # TotalEnergies — direct revenue uplift
        "Utilities":              +0.06,   # Engie — mixed; some generation benefit
        "Materials":              -0.06,   # Energy-intensive: steel, chemicals, glass
        "Industrials":            -0.04,   # Energy is a meaningful input cost
        "Consumer Discretionary": -0.04,   # Airlines, auto — fuel exposure
        "Consumer Staples":       -0.02,   # Food/retail — logistics and packaging costs
        "Real Estate":            -0.02,   # Operating costs
        "Financials":             -0.01,
        "Healthcare":             -0.01,
        "Information Technology": -0.01,
        "Communication Services": -0.01,
        "default":                -0.02,
    },
    "market": {
        "default": 1.0,
    },
    "volatility": {
        "default": -0.5,
    },
}


def _get_sensitivity(shock_type: str, sector: Optional[str], sensitivity_map: Optional[dict]) -> float:
    """Resolve sensitivity: custom map takes precedence over defaults."""
    if sensitivity_map and shock_type in sensitivity_map:
        return float(sensitivity_map[shock_type])
    sector_map = _SECTOR_SENSITIVITIES.get(shock_type, {})
    if sector and sector in sector_map:
        return sector_map[sector]
    return sector_map.get("default", 0.0)


def apply_stress_shocks(holdings: list, shocks: dict) -> dict:
    """
    Apply scenario shocks to a portfolio of holdings.

    holdings: list of dicts with keys:
        symbol (str), weight (float), market_value (float),
        sector (str, optional), sensitivity_map (dict, optional)

    shocks: dict of {shock_type: shock_value}
        - market: fractional return (e.g. -0.10 for -10%)
        - sovereign_spread: basis points (e.g. 100 for +100bps)
        - eur: fractional change (e.g. -0.05 for -5%)
        - ecb_rate: basis points (e.g. 50 for +50bps)
        - energy: fractional change (e.g. 0.20 for +20%)
        - volatility: volatility points (e.g. 10 for +10 vols)

    Returns:
        portfolio_pnl_pct: float
        portfolio_pnl_eur: float
        holding_contributions: list of {symbol, pnl_pct, pnl_eur, sector, weight}
        sector_contributions: list of {sector, pnl_pct, pnl_eur}
    """
    total_value = sum(h.get("market_value", 0.0) for h in holdings)
    if total_value <= 0:
        raise ValueError("Total portfolio market value must be positive")

    # Normalize weights from market_value if weight not supplied or inconsistent
    for h in holdings:
        if "weight" not in h or h["weight"] is None:
            h["weight"] = h.get("market_value", 0.0) / total_value

    holding_contributions = []
    sector_pnl: dict = {}

    for holding in holdings:
        symbol = holding.get("symbol", "UNKNOWN")
        weight = float(holding.get("weight", 0.0))
        market_value = float(holding.get("market_value", 0.0))
        sector = holding.get("sector") or "Unknown"
        sensitivity_map = holding.get("sensitivity_map") or {}
        asset_type = holding.get("asset_type", "equity")

        if asset_type == "cash":
            # Cash has no equity shock sensitivity
            holding_contributions.append({
                "symbol": symbol, "pnl_pct": 0.0, "pnl_eur": 0.0,
                "sector": sector, "weight": weight
            })
            continue

        # Sum up returns from each shock
        total_holding_return = 0.0
        for shock_type, shock_value in shocks.items():
            sensitivity = _get_sensitivity(shock_type, sector, sensitivity_map)
            holding_return = sensitivity * float(shock_value)
            total_holding_return += holding_return

        pnl_eur = market_value * total_holding_return
        holding_contributions.append({
            "symbol": symbol,
            "pnl_pct": round(total_holding_return * 100, 4),
            "pnl_eur": round(pnl_eur, 2),
            "sector": sector,
            "weight": round(weight, 6),
        })

        # Accumulate sector P&L
        if sector not in sector_pnl:
            sector_pnl[sector] = {"pnl_eur": 0.0, "total_value": 0.0}
        sector_pnl[sector]["pnl_eur"] += pnl_eur
        sector_pnl[sector]["total_value"] += market_value

    portfolio_pnl_eur = sum(h["pnl_eur"] for h in holding_contributions)
    portfolio_pnl_pct = portfolio_pnl_eur / total_value if total_value > 0 else 0.0

    sector_contributions = [
        {
            "sector": sector,
            "pnl_eur": round(data["pnl_eur"], 2),
            "pnl_pct": round(data["pnl_eur"] / total_value * 100, 4) if total_value > 0 else 0.0,
        }
        for sector, data in sorted(sector_pnl.items(), key=lambda x: x[1]["pnl_eur"])
    ]

    return {
        "portfolio_pnl_pct": round(portfolio_pnl_pct * 100, 4),
        "portfolio_pnl_eur": round(portfolio_pnl_eur, 2),
        "holding_contributions": sorted(holding_contributions, key=lambda h: h["pnl_eur"]),
        "sector_contributions": sector_contributions,
    }


def run_monte_carlo(
    portfolio_weights: list,
    expected_returns: list,
    volatilities: list,
    n_paths: int = 1000,
    horizon_days: int = 252,
    seed: int = 42,
    correlation_matrix: Optional[list] = None,
) -> dict:
    """
    Run Monte Carlo simulation for portfolio returns.

    Distribution assumption: log-normal daily returns.
    Returns annualized portfolio returns across paths.
    """
    n = len(portfolio_weights)
    if n != len(expected_returns) or n != len(volatilities):
        raise ValueError("portfolio_weights, expected_returns, and volatilities must have same length")

    rng = np.random.default_rng(seed)

    weights = np.array(portfolio_weights, dtype=float)
    mu = np.array(expected_returns, dtype=float)
    sigma = np.array(volatilities, dtype=float)

    if correlation_matrix is not None:
        corr = np.array(correlation_matrix, dtype=float)
    else:
        corr = np.eye(n)

    # Covariance matrix
    sigma_matrix = np.diag(sigma)
    cov = sigma_matrix @ corr @ sigma_matrix

    # Daily parameters
    dt = 1.0 / 252.0
    mu_daily = mu * dt
    cov_daily = cov * dt

    try:
        L = np.linalg.cholesky(cov_daily)
    except np.linalg.LinAlgError:
        # Fall back to diagonal if matrix not positive definite
        cov_daily = np.diag(np.diag(cov_daily))
        cov_daily = cov_daily + np.eye(n) * 1e-8
        L = np.linalg.cholesky(cov_daily)

    # Simulate
    Z = rng.standard_normal((n_paths, horizon_days, n))
    shocks = Z @ L.T  # shape: (n_paths, horizon_days, n)

    # Daily log returns
    daily_log_returns = mu_daily - 0.5 * np.diag(cov_daily) + shocks

    # Portfolio log return over horizon
    portfolio_daily = daily_log_returns @ weights  # (n_paths, horizon_days)
    portfolio_log_return = portfolio_daily.sum(axis=1)  # (n_paths,)
    portfolio_return = np.exp(portfolio_log_return) - 1.0

    portfolio_return_sorted = np.sort(portfolio_return)
    var_95_idx = int(np.floor(0.05 * n_paths))
    var_95 = -float(portfolio_return_sorted[var_95_idx])  # VaR is positive loss
    es_95 = -float(portfolio_return_sorted[:var_95_idx].mean()) if var_95_idx > 0 else var_95

    return {
        "percentile_5": round(float(np.percentile(portfolio_return, 5)), 6),
        "percentile_50": round(float(np.percentile(portfolio_return, 50)), 6),
        "percentile_95": round(float(np.percentile(portfolio_return, 95)), 6),
        "var_95": round(var_95, 6),
        "expected_shortfall_95": round(es_95, 6),
        "all_returns": [round(float(r), 6) for r in portfolio_return.tolist()],
        "methodology": "Monte Carlo log-normal, independent assets unless correlation matrix provided",
        "seed": seed,
        "n_paths": n_paths,
        "horizon_days": horizon_days,
        "disclaimer": "Simulation result only. Not a probability forecast. Assumptions are illustrative.",
    }
