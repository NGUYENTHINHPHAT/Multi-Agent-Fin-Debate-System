"""Real-API eval runner: runs the debate pipeline against live Anthropic calls
and checks output quality. NOT part of pytest/CI — costs API credits and
network access. Run manually after changing a prompt, node, or the graph.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m evals.run_evals                     # all 3 scenarios, baseline only
    python -m evals.run_evals --scenarios TCORP    # just one
    python -m evals.run_evals --stress             # also run a worsened variant
                                                    # of each scenario, to check
                                                    # escalation responds to severity
    python -m evals.run_evals --repeats 3          # repeat each run N times
                                                    # (LLM output is stochastic)

Exit code is non-zero if any run fails CFO format compliance (a hard signal:
the model isn't following its explicit output template). Groundedness and
escalation-calibration findings are printed but don't fail the run — they're
heuristics for a human to skim, not ground truth.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from agents import build_graph
from data_loader import SCENARIOS
from evals.checks import check_cfo_format, find_ungrounded_figures, stress_scenario

load_dotenv()


def make_initial_state(scenario: dict) -> dict:
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


async def run_one(scenario_key: str, scenario: dict, variant: str) -> dict:
    graph = build_graph()
    start = time.monotonic()
    final_state = await graph.ainvoke(make_initial_state(scenario))
    elapsed = time.monotonic() - start

    cfo_output = final_state["final_recommendation"] or ""
    format_result = check_cfo_format(cfo_output)

    groundedness = {
        agent_key: find_ungrounded_figures(final_state.get(agent_key) or "", scenario)
        for agent_key in ("revenue_analysis", "cost_analysis", "risk_assessment")
    }
    groundedness["final_recommendation"] = find_ungrounded_figures(cfo_output, scenario)

    return {
        "scenario": scenario_key,
        "variant": variant,
        "elapsed_seconds": round(elapsed, 1),
        "format_check": {
            "ok": format_result.ok,
            "missing_sections": format_result.missing_sections,
            "has_guidance_call": format_result.has_guidance_call,
        },
        "escalation_triggered": final_state["escalation_triggered"],
        "escalation_reason": final_state["escalation_reason"],
        "disagreement_score": final_state["disagreement_score"],
        "ungrounded_figures": {k: v for k, v in groundedness.items() if v},
    }


async def main_async(args: argparse.Namespace) -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set — export it before running evals.")
        return 1

    scenario_keys = args.scenarios or list(SCENARIOS.keys())
    unknown = set(scenario_keys) - set(SCENARIOS.keys())
    if unknown:
        print(f"Unknown scenario(s): {unknown}. Available: {list(SCENARIOS.keys())}")
        return 1

    runs = []
    for key in scenario_keys:
        variants = [("baseline", SCENARIOS[key])]
        if args.stress:
            variants.append(("stress", stress_scenario(SCENARIOS[key])))

        for variant_name, scenario in variants:
            for repeat in range(args.repeats):
                label = f"{key}/{variant_name}" + (f"#{repeat+1}" if args.repeats > 1 else "")
                print(f"Running {label}...", flush=True)
                result = await run_one(key, scenario, variant_name)
                runs.append(result)
                print(f"  → {result['format_check']['ok'] and 'FORMAT OK' or 'FORMAT FAIL'}, "
                      f"escalated={result['escalation_triggered']}, "
                      f"{result['elapsed_seconds']}s, "
                      f"ungrounded={sum(len(v) for v in result['ungrounded_figures'].values())}")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
    }

    os.makedirs("evals/results", exist_ok=True)
    out_path = f"evals/results/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nWrote {out_path}")

    format_failures = [r for r in runs if not r["format_check"]["ok"]]
    print(f"\n{len(runs)} runs, {len(format_failures)} format failures.")
    if args.stress:
        baseline_escalations = sum(1 for r in runs if r["variant"] == "baseline" and r["escalation_triggered"])
        stress_escalations = sum(1 for r in runs if r["variant"] == "stress" and r["escalation_triggered"])
        print(f"Escalation rate — baseline: {baseline_escalations}, stress: {stress_escalations} "
              f"(expect stress >= baseline; if not, escalation isn't tracking severity)")

    for r in format_failures:
        print(f"  FORMAT FAIL: {r['scenario']}/{r['variant']}: {r['format_check']['missing_sections']}")

    return 1 if format_failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", nargs="+", help="Scenario tickers to run (default: all)")
    parser.add_argument("--repeats", type=int, default=1, help="Repeat each run N times (default: 1)")
    parser.add_argument("--stress", action="store_true", help="Also run a worsened variant of each scenario")
    args = parser.parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
