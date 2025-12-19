from __future__ import annotations

from .ir import Hotkey, KeyChord, RuleIR


def parse_hotkey(expr: str) -> Hotkey:
    """Parse DSL hotkey expression into IR Hotkey."""

    raise NotImplementedError


def parse_keychord(expr: str) -> KeyChord:
    """Parse DSL emitted chord expression into IR KeyChord."""

    raise NotImplementedError


def parse_rule_mapping(trigger: str, emit: str) -> RuleIR:
    """Parse a (trigger, emit) pair into a RuleIR."""

    raise NotImplementedError

