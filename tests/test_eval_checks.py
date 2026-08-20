"""Unit tests for evals/checks.py — all pure functions, no API calls."""
from evals.checks import (
    check_cfo_format,
    extract_dollar_figures,
    find_ungrounded_figures,
    stress_scenario,
)

VALID_CFO_OUTPUT = """
## EXECUTIVE SUMMARY
Revenue is on track. Margins are stable.
## Q4 GUIDANCE RECOMMENDATION
- Revenue: $530M-$545M
- EBITDA Margin: 16%-18%
- Key Assumption: NRR expansion continues
## TOP 3 RISKS TO GUIDANCE
1. Deal slippage
2. VP departure
3. EU compliance
## BOARD RECOMMENDATION
MAINTAIN guidance. The data supports the current range.
## DISSENTING VIEW
Cost Analyst's margin concerns are noted but not decisive.
"""


def test_check_cfo_format_passes_on_well_formed_output():
    result = check_cfo_format(VALID_CFO_OUTPUT)
    assert result.ok is True
    assert result.missing_sections == []
    assert result.has_guidance_call is True


def test_check_cfo_format_flags_missing_section():
    broken = VALID_CFO_OUTPUT.replace("## DISSENTING VIEW\n", "")
    result = check_cfo_format(broken)
    assert result.ok is False
    assert "## DISSENTING VIEW" in result.missing_sections


def test_check_cfo_format_flags_missing_guidance_call():
    broken = VALID_CFO_OUTPUT.replace("MAINTAIN guidance.", "The board should decide.")
    result = check_cfo_format(broken)
    assert result.ok is False
    assert result.has_guidance_call is False


def test_extract_dollar_figures_handles_common_formats():
    text = "Revenue was $521,000,000, up from $487M. Deals worth $47M slipped. Q4 target is $2.08 billion."
    figures = extract_dollar_figures(text)
    assert 521_000_000.0 in figures
    assert 487_000_000.0 in figures
    assert 47_000_000.0 in figures
    assert 2_080_000_000.0 in figures


def test_find_ungrounded_figures_matches_known_scenario_values():
    scenario = {"financials": {"revenue_q3_actual": 521_000_000}, "forward_guidance": {}, "macro_context": {}}
    text = "Revenue came in at $521M, right in line with plan."
    assert find_ungrounded_figures(text, scenario) == []


def test_find_ungrounded_figures_flags_invented_numbers():
    scenario = {"financials": {"revenue_q3_actual": 521_000_000}, "forward_guidance": {}, "macro_context": {}}
    text = "Revenue came in at $999M, a huge beat."
    ungrounded = find_ungrounded_figures(text, scenario)
    assert 999_000_000.0 in ungrounded


def test_find_ungrounded_figures_treats_risk_and_opportunity_narrative_figures_as_grounded():
    # Regression test: figures cited only inside risks/opportunities narrative
    # strings (not the numeric dicts) were being flagged as invented even
    # though they're real scenario facts. See agents.py's SAMPLE_SCENARIO for
    # the real-world example this is modeled on.
    scenario = {
        "financials": {},
        "forward_guidance": {},
        "macro_context": {},
        "risks": ["3 enterprise deals ($47M TCV) slipped to Q4 from Q3"],
        "opportunities": ["AI add-on module launched — $8M ARR in first 60 days"],
    }
    text = "The $47M in slipped deals is offset by $8M in new AI ARR."
    assert find_ungrounded_figures(text, scenario) == []


def test_stress_scenario_worsens_inputs_without_mutating_original():
    original = {
        "financials": {"operating_expenses": 100},
        "forward_guidance": {"q4_opex_projected": 100, "q4_revenue_low": 100, "q4_revenue_high": 200},
        "risks": ["existing risk"],
    }
    stressed = stress_scenario(original)

    assert stressed["forward_guidance"]["q4_opex_projected"] > original["forward_guidance"]["q4_opex_projected"]
    assert stressed["forward_guidance"]["q4_revenue_low"] < 100
    assert stressed["financials"]["operating_expenses"] > 100
    assert len(stressed["risks"]) == 2

    # original must be untouched
    assert original["forward_guidance"]["q4_opex_projected"] == 100
    assert original["risks"] == ["existing risk"]
