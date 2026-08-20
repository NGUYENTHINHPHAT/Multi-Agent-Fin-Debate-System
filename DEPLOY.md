# 🚀 Deployment Guide

## How deployment works

This repo auto-deploys to a Hugging Face Space on every push to `main`:

```
push to main → .github/workflows/test.yml (pytest) → .github/workflows/deploy-hf.yml (git push to the HF Space)
```

`deploy-hf.yml`'s `sync-to-hub` job depends on the `test` job (`needs: test`),
so a failing test suite blocks the deploy — broken code can't reach the
Space automatically.

## One-time setup

Already done for the live Space — this is here for forking or setting up
a new one from scratch.

1. **Create the Space** — https://huggingface.co/new-space, SDK: **Gradio**.
   Note its URL: `https://huggingface.co/spaces/<hf-username>/<space-name>`.

2. **Generate an HF access token** — https://huggingface.co/settings/tokens
   → New token → Write access (or a fine-grained token scoped to write on
   just that Space).

3. **Add it as a GitHub Actions secret on this repo** — repo → Settings →
   Secrets and variables → Actions → New repository secret → name
   `HF_TOKEN`, value the token from step 2.

4. **Point `deploy-hf.yml` at your Space** (only needed if deploying
   somewhere other than the existing target):
   ```yaml
   git push https://<anything>:${HF_TOKEN}@huggingface.co/spaces/<hf-username>/<space-name> main
   ```
   The username before the `:` is just a placeholder for git's basic-auth
   URL format — HF authenticates by the token, not that name, so it doesn't
   need to match any particular account. This is also why the deploy still
   works from a different GitHub account than the one the Space itself
   lives under: GitHub hosting and HF Space ownership are independent
   credentials.

5. **Add the app's runtime secret on the Space itself** (not a GitHub
   secret — the app reads this at runtime, not at deploy time): Space →
   Settings → Repository Secrets → `ANTHROPIC_API_KEY`.

That's it — every push to `main` that passes tests re-syncs the Space. No
manual push to the Space needed day to day.

## Manual deploy (bypassing the Action)

```bash
git remote add hf https://huggingface.co/spaces/<hf-username>/<space-name>
git push hf main
```

## Local Development

```bash
pip install -r requirements.txt

# .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

python app.py
# → http://localhost:7860
```

For running the test suite and evals, see [Testing & Evaluation in the
README](README.md#testing--evaluation).

## Possible Extensions

1. **Streaming to a custom frontend** — `app.py` already streams node-by-node via `graph.astream()` for the Gradio UI; a dedicated FastAPI/SSE backend would let a non-Gradio frontend consume the same stream
2. **Memory across quarters** — LangGraph persistence lets agents remember Q1/Q2 positions
3. **Human-in-the-loop** — LangGraph `interrupt()` to let a human CFO approve the escalation decision
4. **Red team mode** — a 5th agent playing bear-case adversary for stress testing
5. **Backtesting** — run the debate on historical quarters and compare the AI recommendation vs. actual results

## File Structure

```
Multi-Agent-Fin-System/
├── app.py                     # Gradio UI — HF Spaces entry point
├── agents.py                  # LangGraph graph + all agent nodes
├── data_loader.py             # Scenarios + SEC EDGAR integration
├── demo_data.py                # Pre-recorded transcript for the "Load Demo" button (no API key needed)
├── live_data_walkthrough.ipynb # Notebook walking through the SEC EDGAR integration
├── requirements.txt
├── requirements-dev.txt        # + pytest, for running tests/evals locally
├── smoke_test.py                # Manual one-off debate against the real API (not part of pytest)
├── tests/                       # Mocked pytest suite — see README
├── evals/                       # Real-API eval harness — see README
├── README.md                    # HF Spaces README (shown on the Space page)
├── DEPLOY.md                    # This file
└── .github/workflows/
    ├── test.yml                   # Runs pytest on every push/PR
    └── deploy-hf.yml               # Syncs main to the HF Space after tests pass
```
