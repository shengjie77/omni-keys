from __future__ import annotations

from typing import List, Set

from omni_keys.shortcut.ir import Emit, RuleIR

from .models.condition import AppCondition, ConditionType, VarCondition
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
        leader_keys = _collect_leader_keys(rules)

        for rule in rules:
            rule_manips: List[Manipulator]
            if len(rule.trigger.steps) > 1:
                rule_manips = self._sequence_strategy.lower(rule, namespace="default")
            else:
                rule_manips = [self._lower_chord(rule, leader_keys)]

            if rule.when and rule.when.applications:
                app_cond = AppCondition(
                    type=ConditionType.APPLICATION_IF,
                    bundle_identifiers=list(rule.when.applications),
                )
                for manip in rule_manips:
                    if _is_leader_hold_manip(manip):
                        continue
                    manip.conditions.append(app_cond)

            manipulators.extend(rule_manips)

        return Rule(description=description, manipulators=manipulators)

    @staticmethod
    def _lower_chord(rule: RuleIR, leader_keys: Set[str]) -> Manipulator:
        step = rule.trigger.steps[0]
        if not isinstance(rule.action, Emit):
            raise ValueError("only Emit action is supported")

        if len(step.keys) == 1:
            from_event = FromEvent(
                key_code=step.keys[0],
                modifiers=_from_modifiers(step.modifiers),
            )
            to_event = ToEvent(
                key_code=rule.action.chord.key,
                modifiers=_map_modifiers(rule.action.chord.modifiers)
                if rule.action.chord.modifiers
                else None,
            )
            return Manipulator(from_=from_event, to=[to_event])

        # leader_key + key chord
        if len(step.keys) == 2 and not step.modifiers:
            leader = next((k for k in step.keys if k in leader_keys), None)
            if leader is None:
                raise ValueError("multi-key chord requires a leader key from a sequence")
            other = next(k for k in step.keys if k != leader)
            from_event = FromEvent(key_code=other)
            to_event = ToEvent(
                key_code=rule.action.chord.key,
                modifiers=_map_modifiers(rule.action.chord.modifiers)
                if rule.action.chord.modifiers
                else None,
            )
            return Manipulator(
                conditions=[
                    VarCondition(
                        type=ConditionType.VARIABLE_IF,
                        name="leader_hold",
                        value=1,
                    )
                ],
                from_=from_event,
                to=[to_event],
            )

        raise ValueError("simultaneous keys are not supported in chord triggers")


def _from_modifiers(mods) -> FromModifiers | None:
    if not mods:
        return None
    return FromModifiers(
        mandatory=_map_modifiers(mods),
        optional=[Modifier.ANY],
    )


def _map_modifiers(mods) -> list[Modifier]:
    return [Modifier(mod.value) for mod in sorted(mods, key=lambda m: m.value)]


def _collect_leader_keys(rules: List[RuleIR]) -> Set[str]:
    leaders: Set[str] = set()
    for rule in rules:
        if len(rule.trigger.steps) < 2:
            continue
        step0 = rule.trigger.steps[0]
        if len(step0.keys) != 1 or step0.modifiers:
            continue
        leaders.add(step0.keys[0])
    return leaders


def _is_leader_hold_manip(manip: Manipulator) -> bool:
    if not manip.to_after_key_up:
        return False
    if not manip.to:
        return False
    if not manip.to_if_alone:
        return False

    def _has_set_var(events, name: str, value: int) -> bool:
        return any(
            e.set_variable
            and e.set_variable.name == name
            and e.set_variable.value == value
            for e in events
        )

    return _has_set_var(manip.to, "leader_hold", 1) and _has_set_var(
        manip.to_after_key_up, "leader_hold", 0
    )
