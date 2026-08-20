"""Tests for the LangGraph pipeline in agents.py, run against a FakeLLM so no
real API calls happen. These catch wiring bugs: a node reading/writing the
wrong state keys, the graph terminating early, escalation state not
propagating, message/debate_log accumulation breaking, etc.
"""
import pytest

from agents import SAMPLE_SCENARIO, build_graph, run_debate
from data_loader import SCENARIOS
from tests.conftest import FakeLLM


def make_state(scenario=SAMPLE_SCENARIO):
    return {
        "scenario": scenario,
        "messages": [],
        "revenue_analysis": None,
        "cost_analysis": None,
        "risk_assessment": None,
        "debate_log": [],
        "escalation_triggered": False,
        "escalation_reason": None,
        "final_recommendation": None,
        "phase": "starting",
        "disagreement_score": 0.0,
    }


@pytest.mark.asyncio
async def test_graph_runs_all_five_nodes_and_fills_final_state(fake_llm_factory):
    fake_llm_factory(FakeLLM({
        "Revenue Analyst": "RA says growth is healthy. [METRIC: NRR 108%]",
        "Cost Analyst": "CA disagrees, opex is ramping. [RISK: margin compression]",
        "Chief Risk Officer": "Risk register complete.\nESCALATE: NO",
        "CFO of": "## EXECUTIVE SUMMARY\nAll good.\n## BOARD RECOMMENDATION\nMAINTAIN guidance.",
    }))

    graph = build_graph()
    final_state = await graph.ainvoke(make_state())

    assert final_state["revenue_analysis"] is not None
    assert final_state["cost_analysis"] is not None
    assert final_state["risk_assessment"] is not None
    assert final_state["final_recommendation"] is not None
    assert final_state["phase"] == "complete"

    # 5 nodes each append exactly one message: RA, CA, RA(rebuttal), RO, CFO
    assert len(final_state["messages"]) == 5
    assert [m["agent"] for m in final_state["messages"]] == [
        "Revenue Analyst", "Cost Analyst", "Revenue Analyst", "Risk Officer", "CFO",
    ]

    # revenue_rebuttal_node records exactly one debate_log entry
    assert len(final_state["debate_log"]) == 1
    entry = final_state["debate_log"][0]
    assert entry["ra_position"] == final_state["revenue_analysis"]
    assert entry["ca_challenge"] == final_state["cost_analysis"]


@pytest.mark.asyncio
async def test_escalation_yes_propagates_into_state_and_cfo_sees_it(fake_llm_factory):
    fake_llm_factory(FakeLLM({
        "Revenue Analyst": "RA position.",
        "Cost Analyst": "CA challenge.",
        # RO_SYSTEM instructs the model to end with the ESCALATE line, so the
        # justification is written before it, matching real model output.
        "Chief Risk Officer": "Unresolved margin/revenue conflict.\nESCALATE: YES\n",
        "CFO of": "## EXECUTIVE SUMMARY\nEscalated.",
    }))

    graph = build_graph()
    final_state = await graph.ainvoke(make_state())

    assert final_state["escalation_triggered"] is True
    assert final_state["escalation_reason"] == "Unresolved margin/revenue conflict."
    assert final_state["disagreement_score"] == 0.72

    ro_msg = next(m for m in final_state["messages"] if m["agent"] == "Risk Officer")
    assert ro_msg["flags"] == ["ESCALATE"]


@pytest.mark.asyncio
async def test_escalation_no_leaves_state_clean(fake_llm_factory):
    fake_llm_factory(FakeLLM({
        "Chief Risk Officer": "Risk register.\nESCALATE: NO",
    }))

    graph = build_graph()
    final_state = await graph.ainvoke(make_state())

    assert final_state["escalation_triggered"] is False
    assert final_state["escalation_reason"] is None
    assert final_state["disagreement_score"] == 0.45


@pytest.mark.asyncio
async def test_run_debate_helper_matches_direct_graph_invocation(fake_llm_factory):
    fake_llm_factory(FakeLLM({}))  # every node falls through to the default response

    result = await run_debate(SAMPLE_SCENARIO)

    assert result["phase"] == "complete"
    assert result["final_recommendation"] is not None


@pytest.mark.parametrize("ticker", list(SCENARIOS.keys()))
@pytest.mark.asyncio
async def test_graph_runs_on_every_built_in_scenario(ticker, fake_llm_factory):
    # Regression test: revenue_rebuttal_node used to index
    # scenario['financials']['net_revenue_retention'] directly and hardcode
    # scenario['opportunities'][0]/[1] with TCORP-specific labels. That crashed
    # (KeyError) on REIT1, which has no NRR field at all, and produced
    # nonsensical prompts for MFGCO. Running every real built-in scenario
    # through the full graph catches sector-specific assumptions like this
    # that a single-scenario test (SAMPLE_SCENARIO is TCORP-shaped) can't.
    fake_llm_factory(FakeLLM({
        "Chief Risk Officer": "Risk register.\nESCALATE: NO",
    }))

    graph = build_graph()
    final_state = await graph.ainvoke(make_state(SCENARIOS[ticker]))

    assert final_state["phase"] == "complete"
    assert final_state["final_recommendation"] is not None


@pytest.mark.asyncio
async def test_run_debate_stream_callback_receives_every_message(fake_llm_factory):
    fake_llm_factory(FakeLLM({}))
    received = []

    async def on_message(msg):
        received.append(msg["agent"])

    result = await run_debate(SAMPLE_SCENARIO, stream_callback=on_message)

    assert received == ["Revenue Analyst", "Cost Analyst", "Revenue Analyst", "Risk Officer", "CFO"]
    assert result["phase"] == "complete"
