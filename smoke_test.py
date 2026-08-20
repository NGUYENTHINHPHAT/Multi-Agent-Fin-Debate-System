"""Manual smoke test: runs one full debate against the REAL Anthropic API.

Not part of the automated pytest suite (see tests/) — this makes live LLM
calls, costs a small amount of API credit, and needs ANTHROPIC_API_KEY set.
Use it to eyeball that the end-to-end pipeline still produces sane output
after changing a prompt or the graph wiring.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python smoke_test.py
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

from agents import run_debate
from data_loader import SCENARIOS

load_dotenv()


async def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set — export it before running this smoke test.")
        sys.exit(1)

    result = await run_debate(SCENARIOS["TCORP"])

    print("\n" + "=" * 60)
    print("FINAL CFO RECOMMENDATION")
    print("=" * 60)
    print(result["final_recommendation"])
    print("\n" + "=" * 60)
    print(f"Escalated: {result['escalation_triggered']} ({result.get('escalation_reason')})")
    print(f"Messages exchanged: {len(result['messages'])}")


if __name__ == "__main__":
    asyncio.run(main())
