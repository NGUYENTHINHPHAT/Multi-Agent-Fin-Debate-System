"""Tests for data_loader.py — pre-built scenarios and the EDGAR scenario builder.

These are pure/data tests: no network calls (fetch_real_scenario/fetch_edgar_facts
are intentionally not exercised here — they need the real SEC EDGAR API).
"""
from data_loader import SCENARIOS, build_edgar_scenario, get_scenario_by_ticker

REQUIRED_TOP_LEVEL_KEYS = {
    "company", "period", "next_period", "context", "data_source",
    "financials", "forward_guidance", "macro_context", "risks", "opportunities",
}


def test_scenarios_has_the_three_expected_tickers():
    assert set(SCENARIOS.keys()) == {"TCORP", "MFGCO", "REIT1"}


def test_every_scenario_has_required_top_level_shape():
    for ticker, scenario in SCENARIOS.items():
        missing = REQUIRED_TOP_LEVEL_KEYS - scenario.keys()
        assert not missing, f"{ticker} is missing keys: {missing}"
        assert isinstance(scenario["risks"], list) and scenario["risks"]
        assert isinstance(scenario["opportunities"], list) and scenario["opportunities"]


def test_get_scenario_by_ticker_is_case_insensitive():
    assert get_scenario_by_ticker("tcorp") == SCENARIOS["TCORP"]
    assert get_scenario_by_ticker("TCORP") == SCENARIOS["TCORP"]


def test_get_scenario_by_ticker_unknown_returns_none():
    assert get_scenario_by_ticker("NOPE") is None


def _edgar_quarterly_unit(end: str, start: str, val: int, filed: str = "2024-01-01"):
    return {"form": "10-Q", "start": start, "end": end, "val": val, "fp": "Q3", "filed": filed}


def _fake_edgar_facts():
    # 5 quarters of revenue so build_edgar_scenario can compute YoY growth
    # (prior_yr = revenue_data[4]).
    revenue_units = [
        _edgar_quarterly_unit("2024-09-30", "2024-07-01", 550_000_000),
        _edgar_quarterly_unit("2024-06-30", "2024-04-01", 530_000_000),
        _edgar_quarterly_unit("2024-03-31", "2024-01-01", 510_000_000),
        _edgar_quarterly_unit("2023-12-31", "2023-10-01", 500_000_000),
        _edgar_quarterly_unit("2023-09-30", "2023-07-01", 500_000_000),  # prior-year comp
    ]
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": revenue_units}},
                "OperatingExpenses": {"units": {"USD": [
                    _edgar_quarterly_unit("2024-09-30", "2024-07-01", 400_000_000),
                ]}},
            }
        }
    }


def test_build_edgar_scenario_computes_growth_and_guidance():
    scenario = build_edgar_scenario("ACME", "Acme Corp", _fake_edgar_facts(), fed_rate=5.0)

    assert scenario is not None
    assert scenario["company"] == "Acme Corp (NASDAQ/NYSE: ACME)"
    assert scenario["financials"]["revenue_q3_actual"] == 550_000_000
    # (550M - 500M) / 500M * 100 = 10.0
    assert scenario["financials"]["revenue_growth_yoy"] == 10.0
    assert scenario["macro_context"]["fed_funds_rate"] == 5.0
    # forward guidance is derived from rev_current, not hardcoded
    assert scenario["forward_guidance"]["q4_revenue_low"] == int(550_000_000 * 0.97)
    assert scenario["forward_guidance"]["q4_revenue_high"] == int(550_000_000 * 1.05)


def test_build_edgar_scenario_returns_none_without_revenue_data():
    facts = {"facts": {"us-gaap": {}}}
    assert build_edgar_scenario("ACME", "Acme Corp", facts) is None
