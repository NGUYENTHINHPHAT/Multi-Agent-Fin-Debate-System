"""Unit tests for agents.parse_escalation — the fragile string-matching logic
that decides whether the Risk Officer escalates a debate to the board.
"""
from agents import parse_escalation


def test_escalate_yes_captures_reason_from_next_line():
    content = (
        "Risk register:\n"
        "- Margin compression: LIKELIHOOD High, IMPACT 4\n"
        "ESCALATE: YES\n"
        "Reason: Material disagreement on Q4 opex assumptions.\n"
    )
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Reason: Material disagreement on Q4 opex assumptions."


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
    content = "risk assessment complete.\nescalate: yes\nsevere margin risk\n"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "severe margin risk"


def test_escalate_yes_as_last_line_falls_back_to_generic_reason():
    content = "Risk register:\n- Some risk\nESCALATE: YES"
    escalate, reason = parse_escalation(content)
    assert escalate is True
    assert reason == "Material disagreement on Q4 assumptions"


def test_escalate_no_does_not_false_positive_on_partial_match():
    # "escalate" appears without "yes" nearby — must not be misread as escalation.
    content = "We considered whether to escalate but decided ESCALATE: NO is appropriate."
    escalate, reason = parse_escalation(content)
    assert escalate is False
    assert reason is None
