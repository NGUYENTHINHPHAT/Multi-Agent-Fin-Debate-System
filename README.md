---
title: Multi-Agent Finance Debate System
emoji: 🏦
colorFrom: purple
colorTo: green
sdk: gradio
sdk_version: 6.14.0
python_version: '3.13'
app_file: app.py
pinned: true
license: mit
short_description: LangGraph multi-agent financial debate system
tags:
  - finance
  - langgraph
  - multi-agent
  - llm
  - portfolio
---

# 🏦 Multi-Agent Finance Debate System

**🚀 [Live Demo](https://huggingface.co/spaces/PhatNguyen39/Multi-Agent-Fin-Debate-System)**

A production-grade demo of a **LangGraph multi-agent system** where four AI agents debate a quarterly financial forecast and produce a board-ready CFO recommendation.

## Architecture

```
Q3 Scenario Input
       │
       ▼
┌─────────────────┐    Phase 1: Independent Analysis
│ Revenue Analyst │ ──► Defends revenue projections with NRR, pipeline data
└────────┬────────┘
         │
         ▼
┌─────────────────┐    Phase 2: Adversarial Cross-Examination  
│  Cost Analyst   │ ──► Challenges assumptions, flags margin compression
└────────┬────────┘
         │ (Revenue Analyst rebuts)
         ▼
┌─────────────────┐    Phase 3: Risk Escalation Audit
│  Risk Officer   │ ──► Scores risks, decides ESCALATE: YES/NO
└────────┬────────┘
         │
         ▼
┌─────────────────┐    Phase 4: Board Synthesis
│      CFO        │ ──► Structured recommendation: MAINTAIN/RAISE/LOWER
└─────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | Anthropic Claude (claude-3-5-haiku) |
| UI | [Gradio](https://gradio.app) |
| State Management | LangGraph `TypedDict` with `Annotated` reducers |
| Data | SEC EDGAR API (free) + synthetic composites |

## Available Scenarios

| Scenario | Sector | Key Tension |
|----------|--------|-------------|
| TechCorp Inc. (SaaS) | Enterprise Software | Growth vs. macro headwinds |
| ManufactureCo Holdings | Industrial | Margin compression vs. backlog strength |
| PropTrust REIT | Commercial Real Estate | Office vacancy vs. industrial opportunity |

## Real Data Integration

```python
# SEC EDGAR — Free, no API key
import httpx
CIK = "0001108524"  # Any public company CIK
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
resp = httpx.get(url, headers={"User-Agent": "your-app your@email.com"})
facts = resp.json()
# Contains all GAAP metrics from 10-Q/10-K filings going back 10+ years
```

## Local Setup

```bash
git clone https://huggingface.co/spaces/PhatNguyen39/Multi-Agent-Fin-Debate-System
cd Multi-Agent-Fin-Debate-System
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

python app.py
# → http://localhost:7860
```

## Testing & Evaluation

This is an LLM system, so "correct" has two different meanings — the *code*
can be correct (the graph is wired right, state flows through cleanly) while
the *model output* is still low-quality (wrong format, invented numbers,
an escalation call that ignores the input). Each gets its own layer:

| | Unit tests (`tests/`) | Evals (`evals/`) |
|---|---|---|
| Checks | Graph wiring, state accumulation, escalation string-parsing, EDGAR data parsing | CFO output format, groundedness of cited $ figures, escalation calibration |
| Anthropic API calls | None — mocked | Yes, real calls |
| Cost | Free | Small $ cost per run |
| Speed | <1s, 24 tests | Minutes (depends on `--repeats`) |
| Runs in CI | ✅ every push/PR (`.github/workflows/test.yml`), gates the HF deploy | ❌ manual only |
| Command | `pytest -v` | `python -m evals.run_evals` |

### Unit tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

`tests/conftest.py` patches `agents.get_llm` with a `FakeLLM` that returns
scripted responses keyed off which agent's system prompt is asking, so the
whole 5-node LangGraph pipeline (`agents.py`) runs deterministically without
touching the network. This is what catches wiring bugs: a node reading the
wrong state key, a message not accumulating, the escalation flag not
propagating to the CFO.

`smoke_test.py` (repo root) is a separate, manual script — not part of
pytest — that runs one full debate against the *real* API, useful for
eyeballing output after a prompt change:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python smoke_test.py
```

### Evals

Unit tests can't tell you if the CFO's output is actually *good* — that
requires real model output. `evals/run_evals.py` runs all 3 scenarios
against the live API and grades the result:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m evals.run_evals --stress --repeats 2
```

| Check | Type | What it means |
|---|---|---|
| **Format compliance** | Hard — fails the run | Does the CFO's output contain every required section (`## EXECUTIVE SUMMARY`, `## Q4 GUIDANCE RECOMMENDATION`, `## TOP 3 RISKS TO GUIDANCE`, `## BOARD RECOMMENDATION`, `## DISSENTING VIEW`) plus an explicit MAINTAIN/RAISE/LOWER call? |
| **Groundedness** | Soft signal | Do the `$` figures each agent cites actually appear in the scenario's financials, or look invented? Flags outliers for a human to check, not a hard fail — an agent doing legitimate arithmetic on two real numbers can trip this. |
| **Escalation calibration** | Soft signal, `--stress` only | `--stress` runs a deliberately worsened variant of each scenario (opex +35%, guidance range compressed, a severe new risk appended) alongside the baseline. The stress variant should escalate at least as often — if it doesn't, the Risk Officer isn't actually tracking input severity. |

Real captured output (`python -m evals.run_evals --stress`, `claude-haiku-4-5`, 6 runs):
```
Running TCORP/baseline...
  → FORMAT OK, escalated=True, 51.6s, ungrounded=47
Running TCORP/stress...
  → FORMAT OK, escalated=True, 51.8s, ungrounded=22
Running MFGCO/baseline...
  → FORMAT OK, escalated=True, 45.4s, ungrounded=8
Running MFGCO/stress...
  → FORMAT OK, escalated=True, 45.9s, ungrounded=15
Running REIT1/baseline...
  → FORMAT OK, escalated=True, 46.7s, ungrounded=10
Running REIT1/stress...
  → FORMAT OK, escalated=True, 51.5s, ungrounded=18

Wrote evals/results/20260820T061408Z.json
6 runs, 0 format failures.
Escalation rate — baseline: 3, stress: 3 (expect stress >= baseline; if not, escalation isn't tracking severity)
```

Results are written to `evals/results/*.json` (gitignored — local run
artifacts, not fixtures, since output is stochastic). The check functions
themselves (`evals/checks.py`) are pure and have no API dependency, so
they're covered by `tests/test_eval_checks.py` and run in CI even though the
end-to-end eval run doesn't.

**What this first real run found:**
- **Format compliance was perfect** (6/6) — the CFO reliably follows its template.
- **Escalation didn't discriminate** — every baseline *and* every stress variant
  escalated (3/3 vs 3/3). At `n=1` per variant this isn't statistically
  meaningful (`--repeats` gives a real rate), but taken at face value it
  suggests the Risk Officer may be biased toward escalating regardless of
  input severity, worth a closer look at `RO_SYSTEM` in `agents.py`.
- **Groundedness flagged 8–47 figures per run.** Spot-checking a sample: some
  are the model doing legitimate arithmetic on real inputs (e.g. projecting
  a number from a real growth rate), which the heuristic can't distinguish
  from invented specifics — that's exactly why this check is a soft signal,
  not a gate. Worth a manual read of a transcript before trusting it further.
- **This run also caught two real crash bugs**, both the same shape: two
  nodes assumed TCORP-shaped data (`financials['net_revenue_retention']`
  indexed directly, and a hardcoded `forward_guidance['fy2024_revenue_target']`
  key) and crashed with `KeyError` on `REIT1`, which uses different metrics
  (no NRR; guides on FFO/share instead of revenue). Both are fixed now
  (`agents.py`, `revenue_rebuttal_node` / `cfo_synthesis_node`), and
  `tests/test_agents_graph.py::test_graph_runs_on_every_built_in_scenario` is
  a parametrized regression test across all 3 built-in scenarios so a future
  scenario-specific-field bug like this fails fast and free in `pytest`,
  instead of only surfacing on a real, paid eval run.
- **`escalation_reason` was silently blank on all 6/6 real escalations.**
  `RO_SYSTEM` tells the model to end its response with the `ESCALATE:
  YES/NO` line, so the actual justification is the text *before* it —
  `parse_escalation()` was looking at the line *after* instead, which on
  real output was just the empty string left by the response's own
  trailing newline. Every escalation the CFO/board saw was missing its
  "why." Fixed in `agents.py` (`parse_escalation` now looks backward for
  the nearest non-blank line first), with a named regression test
  (`tests/test_escalation.py::test_escalate_reason_is_not_the_trailing_blank_line`).

### Current status (as of the last real run, 2026-08-20)

| Item | Status |
|---|---|
| Format compliance | ✅ Verified live — 6/6 |
| REIT1 crash bugs (NRR / fy-target KeyErrors) | ✅ Fixed and verified live — re-run after the fix completed all 6/6 |
| `escalation_reason` blank-string bug | 🔧 Fixed, verified only against a synthetic reproduction of the real output shape — **not yet re-confirmed against a live API call** |
| Escalation calibration (does it actually track severity?) | ⚠️ Unresolved — the one live run escalated 3/3 baseline and 3/3 stress, which doesn't discriminate, but `n=1` per variant isn't statistically meaningful either way |
| Groundedness heuristic (8–47 flags/run) | ⚠️ Unresolved — flagged figures haven't been manually read against the transcripts to sort legitimate derived numbers from actual hallucination |

The last two rows need either `--repeats` (for a real escalation rate) or a
manual transcript read (for groundedness) to resolve — both require another
live run against the Anthropic API, which hasn't been done since the fixes
above landed. Until then, treat escalation calibration and output
groundedness as open questions, not verified behavior.

## Design Patterns Demonstrated

- **Supervisor-less multi-agent pipeline** — each agent has a single responsibility
- **Adversarial debate architecture** — structured disagreement surfaced via CA cross-examination
- **Escalation routing** — Risk Officer acts as a conditional router
- **Structured LLM output** — CFO uses strict format templates for board-ready output
- **State accumulation** — LangGraph `Annotated[List, operator.add]` for message history

---
