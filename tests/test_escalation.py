"""Unit tests for agents.parse_escalation — the fragile string-matching logic
that decides whether the Risk Officer escalates a debate to the board.

RO_SYSTEM instructs the model to end its response with the ESCALATE line, so
these are written against that real shape: justification text *before* the
decision, which is also what a real eval run against the live API showed
(escalation_reason came back "" on 6/6 real escalations before this fix,
because the old forward-looking logic grabbed the empty string left by the
response's trailing newline instead).
"""
from agents import parse_escalation


def test_escalate_yes_prefers_reason_from_line_before_the_decision():
    content = (
        "Risk register:\n"
        "- Margin compression: LIKELIHOOD High, IMPACT 4\n"
        "This creates material disagreement on Q4 opex assumptions.\n"
        "ESCALATE: YES\n"
    )
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "This creates material disagreement on Q4 opex assumptions."


def test_escalate_reason_is_not_the_trailing_blank_line():
    # Regression test for the real bug: content.split('\n') on a string ending
    # in '\n' yields a trailing "" element. The old "line after ESCALATE"
    # logic picked that up as the reason on every real run, since RO_SYSTEM
    # tells the model to put ESCALATE: YES/NO last.
    content = "Enterprise deal slippage remains the top concern.\nESCALATE: YES\n"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Enterprise deal slippage remains the top concern."
    assert reason != ""


def test_escalate_no():
    content = "Risk register looks manageable.\nESCALATE: NO\n"
    escalate, reason = parse_escalation(content)
    assert escalate is False
    assert reason is None


def test_escalate_missing_entirely_defaults_to_no():
    content = "The analysts broadly agree on Q4 guidance."
    escalate, reason = parse_escalation(content)
    assert escalate is False
    assert reason is None


def test_escalate_is_case_insensitive():
    content = "Severe margin risk identified.\nescalate: yes\n"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Severe margin risk identified."


def test_escalate_falls_back_to_text_after_decision_if_nothing_precedes_it():
    # If a future prompt tweak puts the ESCALATE line first, the reason
    # should still be recoverable from what follows.
    content = "ESCALATE: YES\nRationale: severe tail risk detected.\n"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Rationale: severe tail risk detected."


def test_escalate_yes_with_no_surrounding_text_falls_back_to_generic_reason():
    content = "ESCALATE: YES"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Material disagreement on Q4 assumptions"


def test_escalate_reason_skips_blank_lines():
    content = "Real justification here.\n\n\nESCALATE: YES\n\n\n"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Real justification here."


def test_escalate_no_does_not_false_positive_on_partial_match():
    # "escalate" appears without "yes" nearby — must not be misread as escalation.
    content = "We considered whether to escalate but decided ESCALATE: NO is appropriate."
    escalate, reason = parse_escalation(content)
    assert escalate is False
    assert reason is None
