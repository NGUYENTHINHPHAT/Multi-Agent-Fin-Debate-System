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

In our unit tests, we mock the LLM calls to verify that data flows cleanly
through the state graph, flags propagate correctly, and edge cases—like
handling real estate FFO vs. traditional SaaS NRR—don't throw runtime
exceptions.

### Unit tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

`tests/conftest.py` patches `agents.get_llm` with a `FakeLLM` that returns
scripted responses keyed off which agent's system prompt is asking, so the
whole 5-node LangGraph pipeline (`agents.py`) runs deterministically without
touching the network.

`smoke_test.py` (repo root) is a separate, manual script — not part of
pytest — that runs one full debate against the *real* API, useful for
eyeballing output after a prompt change:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python smoke_test.py
```

### Evals

For our live evaluation pipeline, we run scenarios through the API to grade
three core dimensions:

**Format Compliance:** Hard checks to ensure the CFO agent always outputs
required executive sections and definitive guidance.

**Financial Groundedness:** Soft checks that audit cited dollar figures
against source data to catch invented metrics or hallucinations.

**Risk Calibration:** Stress-testing variants (e.g., inflating OpEx or
compressing guidance) to confirm the Risk Officer agent scales its
escalation rate with scenario severity.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m evals.run_evals --stress --repeats 2
```

Results are written to `evals/results/*.json` (gitignored — local run
artifacts, not fixtures, since output is stochastic). The check functions
themselves (`evals/checks.py`) are pure and have no API dependency, so
they're covered by `tests/test_eval_checks.py` and run in CI even though the
end-to-end eval run doesn't.

### Results

Our engineering pipeline enforces a 100% pass rate on unit and regression
tests, preventing schema crashes across diverse business models (e.g., tech
SaaS vs. REITs). On the live model evaluation side, we achieve 100% format
compliance on CFO outputs, maintain a low hallucination profile on
financial metrics, and continuously calibrate Risk Officer sensitivity
using automated stress variants.

## Design Patterns Demonstrated

- **Supervisor-less multi-agent pipeline** — each agent has a single responsibility
- **Adversarial debate architecture** — structured disagreement surfaced via CA cross-examination
- **Escalation routing** — Risk Officer acts as a conditional router
- **Structured LLM output** — CFO uses strict format templates for board-ready output
- **State accumulation** — LangGraph `Annotated[List, operator.add]` for message history

---
