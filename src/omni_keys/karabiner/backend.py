from __future__ import annotations

from typing import List

from omni_keys.shortcut.ir import RuleIR

from .models.rule import Rule
from .sequence_strategy import StateMachineStrategy


class KarabinerBackend:
    """Compile IR rules into Karabiner JSON models."""

    def __init__(self) -> None:
        self._sequence_strategy = StateMachineStrategy()

    def compile(self, rules: List[RuleIR], *, description: str) -> Rule:
        raise NotImplementedError
