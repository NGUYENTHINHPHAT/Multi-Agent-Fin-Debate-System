"""Pure eval checks for debate output — no API calls, no I/O.

These are heuristics, not ground truth: groundedness in particular will have
false positives (an agent legitimately doing arithmetic on two real figures
produces a third number that won't appear verbatim in the scenario). Treat
flagged figures as "worth a human glance," not an automatic fail — that's why
run_evals.py doesn't hard-fail the run on groundedness alone, only on format
compliance.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── CFO output format compliance ─────────────────────────────────────────────
REQUIRED_CFO_SECTIONS = [
    "## EXECUTIVE SUMMARY",
    "## Q4 GUIDANCE RECOMMENDATION",
    "## TOP 3 RISKS TO GUIDANCE",
    "## BOARD RECOMMENDATION",
    "## DISSENTING VIEW",
]
VALID_GUIDANCE_CALLS = ("MAINTAIN", "RAISE", "LOWER")


@dataclass
class FormatCheckResult:
    ok: bool
    missing_sections: list[str] = field(default_factory=list)
    has_guidance_call: bool = False

    @property
    def summary(self) -> str:
        if self.ok:
            return "PASS"
        problems = []
        if self.missing_sections:
            problems.append(f"missing sections: {self.missing_sections}")
        if not self.has_guidance_call:
            problems.append(f"no {VALID_GUIDANCE_CALLS} call found in BOARD RECOMMENDATION")
        return "FAIL — " + "; ".join(problems)


def check_cfo_format(cfo_output: str) -> FormatCheckResult:
    """Checks the CFO's output against the exact structure mandated by CFO_SYSTEM
    in agents.py. This is a hard, deterministic check — the system prompt gives
    the model an explicit template, so drift here means the model isn't
    following instructions (or the template needs updating)."""
    missing = [s for s in REQUIRED_CFO_SECTIONS if s not in cfo_output]
    has_call = any(call in cfo_output.upper() for call in VALID_GUIDANCE_CALLS)
    return FormatCheckResult(ok=not missing and has_call, missing_sections=missing, has_guidance_call=has_call)


# ── Groundedness ──────────────────────────────────────────────────────────────
_DOLLAR_FIGURE_RE = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s?(million|billion|M|B|K)?\b", re.IGNORECASE
)
_SUFFIX_MULTIPLIER = {"k": 1_000, "m": 1_000_000, "million": 1_000_000, "b": 1_000_000_000, "billion": 1_000_000_000}


def extract_dollar_figures(text: str) -> list[float]:
    """Pulls every $-prefixed number out of free text and normalizes it to raw
    dollars (so "$521M" and "$521,000,000" both become 521000000.0)."""
    figures = []
    for number_str, suffix in _DOLLAR_FIGURE_RE.findall(text):
        try:
            value = float(number_str.replace(",", ""))
        except ValueError:
            continue
        multiplier = _SUFFIX_MULTIPLIER.get(suffix.lower(), 1)
        figures.append(value * multiplier)
    return figures


def _known_numeric_values(scenario: dict) -> list[float]:
    values = []
    for section in ("financials", "forward_guidance", "macro_context"):
        for v in scenario.get(section, {}).values():
            if isinstance(v, (int, float)):
                values.append(float(v))
    # risks/opportunities are narrative strings that often carry their own real
    # figures, e.g. "3 enterprise deals ($47M TCV) slipped to Q4" — those are
    # legitimate scenario facts too, just not in the numeric dicts above.
    for section in ("risks", "opportunities"):
        for item in scenario.get(section, []):
            if isinstance(item, str):
                values.extend(extract_dollar_figures(item))
    return values


def find_ungrounded_figures(text: str, scenario: dict, tolerance: float = 0.03) -> list[float]:
    """Returns $ figures mentioned in `text` that don't approximately match any
    numeric value in the scenario's financials/forward_guidance/macro_context.
    A non-empty result is a hint the model may be inventing numbers, not proof."""
    known = _known_numeric_values(scenario)
    ungrounded = []
    for figure in extract_dollar_figures(text):
        if not any(abs(figure - k) / max(abs(k), 1.0) < tolerance for k in known):
            ungrounded.append(figure)
    return ungrounded


# ── Escalation calibration ────────────────────────────────────────────────────
def stress_scenario(scenario: dict) -> dict:
    """Returns a deep-enough copy of `scenario` mutated to look clearly worse —
    opex inflated, guidance range compressed, and a severe new risk appended —
    so we can check whether the Risk Officer's ESCALATE decision actually
    responds to input severity rather than defaulting to one answer."""
    import copy
    stressed = copy.deepcopy(scenario)
    fwd = stressed["forward_guidance"]
    for key in ("q4_opex_projected",):
        if key in fwd:
            fwd[key] = int(fwd[key] * 1.35)
    for key in ("q4_revenue_low", "q4_revenue_high"):
        if key in fwd:
            fwd[key] = int(fwd[key] * 0.85)
    stressed["risks"] = list(stressed.get("risks", [])) + [
        "URGENT: Largest customer (14% of revenue) issued formal churn notice this week",
    ]
    fin = stressed.get("financials", {})
    if "operating_expenses" in fin:
        fin["operating_expenses"] = int(fin["operating_expenses"] * 1.2)
    return stressed
