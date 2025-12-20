from __future__ import annotations

from typing import List

from omni_keys.shortcut.ir import Emit, RuleIR

from .models.condition import AppCondition, ConditionType
from .models.from_event import FromEvent
from .models.manipulator import Manipulator
from .models.modifier import Modifier
from .models.modifiers import FromModifiers
from .models.rule import Rule
from .models.to_event import ToEvent
from .sequence_strategy import StateMachineStrategy


class KarabinerBackend:
    """Compile IR rules into Karabiner JSON models."""

    def __init__(self) -> None:
        self._sequence_strategy = StateMachineStrategy()

    def compile(self, rules: List[RuleIR], *, description: str) -> Rule:
        manipulators: List[Manipulator] = []

        for rule in rules:
            rule_manips: List[Manipulator]
            if len(rule.trigger.steps) > 1:
                rule_manips = self._sequence_strategy.lower(rule, namespace="default")
            else:
                rule_manips = [self._lower_chord(rule)]

            if rule.when and rule.when.applications:
                app_cond = AppCondition(
                    type=ConditionType.APPLICATION_IF,
                    bundle_identifiers=list(rule.when.applications),
                )
                for manip in rule_manips:
                    manip.conditions.append(app_cond)

            manipulators.extend(rule_manips)

        return Rule(description=description, manipulators=manipulators)

    @staticmethod
    def _lower_chord(rule: RuleIR) -> Manipulator:
        step = rule.trigger.steps[0]
        if not isinstance(rule.action, Emit):
            raise ValueError("only Emit action is supported")

        from_mods = None
        if step.modifiers:
            from_mods = FromModifiers(
                mandatory=_map_modifiers(step.modifiers),
                optional=[Modifier.ANY],
            )

        if len(step.keys) == 1:
            from_event = FromEvent(key_code=step.keys[0], modifiers=from_mods)
        else:
            from_event = FromEvent(simultaneous=list(step.keys), modifiers=from_mods)

        to_mods = _map_modifiers(rule.action.chord.modifiers) if rule.action.chord.modifiers else None
        to_event = ToEvent(key_code=rule.action.chord.key, modifiers=to_mods)
        return Manipulator(from_=from_event, to=[to_event])


def _map_modifiers(mods) -> list[Modifier]:
    return [Modifier(mod.value) for mod in sorted(mods, key=lambda m: m.value)]
