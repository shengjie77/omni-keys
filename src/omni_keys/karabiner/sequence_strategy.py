from __future__ import annotations

import re
from typing import List, Protocol

from omni_keys.shortcut.ir import Emit, RuleIR

from .models.condition import ConditionType, VarCondition
from .models.from_event import AnyKey, FromEvent
from .models.manipulator import DelayedAction, Manipulator
from .models.modifier import Modifier
from .models.modifiers import FromModifiers
from .models.to_event import ToEvent, Variable


class SequenceLoweringStrategy(Protocol):
    """Lower a sequence-style RuleIR into Karabiner manipulators."""

    def lower(self, rule: RuleIR, *, namespace: str) -> List[Manipulator]: ...


class StateMachineStrategy:
    """Default sequence lowering (backend internal)."""

    def __init__(self, *, timeout_ms: int = 1000) -> None:
        self._timeout_ms = timeout_ms

    def lower(self, rule: RuleIR, *, namespace: str) -> List[Manipulator]:
        steps = rule.trigger.steps
        if len(steps) < 2:
            raise ValueError("sequence strategy requires at least 2 steps")
        if not isinstance(rule.action, Emit):
            raise ValueError("sequence strategy only supports Emit action")

        step_ids = [_step_id(step) for step in steps]
        root_var = _prefix_var(step_ids, 1)
        all_vars = _all_vars(step_ids)

        manipulators: list[Manipulator] = []

        # Root step: enter active state + setup timeout cancel
        manipulators.append(
            Manipulator(
                from_=_from_event(steps[0]),
                to=[_set_var(root_var, 1)],
                to_delayed_action=DelayedAction(
                    to_if_invoked=[_set_var(v, 0) for v in all_vars]
                ),
                parameters={
                    "basic.to_delayed_action_delay_milliseconds": self._timeout_ms
                },
            )
        )

        # Intermediate transitions
        for i in range(1, len(steps) - 1):
            from_var = _prefix_var(step_ids, i)
            to_var = _prefix_var(step_ids, i + 1)

            manipulators.append(
                Manipulator(
                    conditions=[
                        VarCondition(type=ConditionType.VARIABLE_IF, name=from_var, value=1),
                    ],
                    from_=_from_event(steps[i]),
                    to=[_set_var(from_var, 0), _set_var(to_var, 1)],
                    to_delayed_action=DelayedAction(
                        to_if_invoked=[_set_var(v, 0) for v in all_vars]
                    ),
                    parameters={
                        "basic.to_delayed_action_delay_milliseconds": self._timeout_ms
                    },
                )
            )

        # Final step: clear state + emit action
        last_var = _prefix_var(step_ids, len(steps) - 1)
        manipulators.append(
            Manipulator(
                conditions=[
                    VarCondition(type=ConditionType.VARIABLE_IF, name=last_var, value=1),
                ],
                from_=_from_event(steps[-1]),
                to=[
                    _set_var(last_var, 0),
                    ToEvent(
                        key_code=rule.action.chord.key,
                        modifiers=_map_modifiers(rule.action.chord.modifiers)
                        if rule.action.chord.modifiers
                        else None,
                    ),
                ],
            )
        )

        # Cancel on wrong key for each active prefix
        for prefix_var in all_vars:
            manipulators.append(
                Manipulator(
                    conditions=[
                        VarCondition(type=ConditionType.VARIABLE_IF, name=prefix_var, value=1),
                    ],
                    from_=FromEvent(any=AnyKey.KEY_CODE),
                    to=[_set_var(v, 0) for v in all_vars],
                )
            )

        return manipulators


def _set_var(name: str, value: int) -> ToEvent:
    return ToEvent(set_variable=Variable(name=name, value=value))


def _from_event(step) -> FromEvent:
    from_mods = None
    if step.modifiers:
        from_mods = FromModifiers(
            mandatory=_map_modifiers(step.modifiers),
            optional=[Modifier.ANY],
        )

    if len(step.keys) == 1:
        return FromEvent(key_code=step.keys[0], modifiers=from_mods)
    return FromEvent(simultaneous=list(step.keys), modifiers=from_mods)


def _step_id(step) -> str:
    parts = [*(m.value for m in sorted(step.modifiers, key=lambda m: m.value)), *step.keys]
    return _sanitize("_".join(parts))


def _prefix_var(step_ids: list[str], length: int) -> str:
    root = step_ids[0]
    if length <= 1:
        return f"seq_{root}_active"
    suffix = "_".join(step_ids[1:length])
    return f"seq_{root}_{suffix}"


def _all_vars(step_ids: list[str]) -> list[str]:
    return [_prefix_var(step_ids, i) for i in range(1, len(step_ids))]


def _sanitize(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")


def _map_modifiers(mods) -> list[Modifier]:
    return [Modifier(mod.value) for mod in sorted(mods, key=lambda m: m.value)]
