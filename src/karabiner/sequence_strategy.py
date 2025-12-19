from __future__ import annotations

from typing import List, Protocol

from src.shortcut.ir import RuleIR

from .models.manipulator import Manipulator


class SequenceLoweringStrategy(Protocol):
    """Lower a sequence-style RuleIR into Karabiner manipulators."""

    def lower(self, rule: RuleIR, *, namespace: str) -> List[Manipulator]: ...


class StateMachineStrategy:
    """Default sequence lowering (backend internal)."""

    def lower(self, rule: RuleIR, *, namespace: str) -> List[Manipulator]:
        raise NotImplementedError

