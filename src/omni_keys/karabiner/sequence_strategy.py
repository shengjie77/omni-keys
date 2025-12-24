from __future__ import annotations

import re
from typing import List, Protocol

from omni_keys.shortcut.ir import Emit, RuleIR

from .models.condition import ConditionType, VarCondition
from .models.from_event import FromEvent
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
        self._hold_var = "omni.hold"
        self._seq_var = "omni.seq"
        self._seq_idle = "idle"

    def lower(self, rule: RuleIR, *, namespace: str) -> List[Manipulator]:
        steps = rule.trigger.steps
        if len(steps) < 2:
            raise ValueError("sequence strategy requires at least 2 steps")
        if not isinstance(rule.action, Emit):
            raise ValueError("sequence strategy only supports Emit action")

        step_ids = [_step_id(step) for step in steps]
        root_state = _seq_state(step_ids, 0)

        manipulators: list[Manipulator] = []

        # Leader behavior: hold for chord, tap to enter sequence + timeout cancel
        manipulators.append(
            Manipulator(
                from_=_leader_from_event(steps[0]),
                to=[_set_var(self._hold_var, 1)],
                to_after_key_up=[_set_var(self._hold_var, 0)],
                to_if_alone=[
                    _set_var(self._seq_var, root_state),
                ],
                to_delayed_action=DelayedAction(
                    to_if_invoked=[_set_var(self._seq_var, self._seq_idle)]
                ),
                parameters={
                    "basic.to_delayed_action_delay_milliseconds": self._timeout_ms
                },
            )
        )

        # Intermediate transitions
        for i in range(1, len(steps) - 1):
            from_state = _seq_state(step_ids, i - 1)
            to_state = _seq_state(step_ids, i)

            manipulators.append(
                Manipulator(
                    conditions=[
                        VarCondition(
                            type=ConditionType.VARIABLE_IF,
                            name=self._seq_var,
                            value=from_state,
                        ),
                    ],
                    from_=_from_event(steps[i]),
                    to=[_set_var(self._seq_var, to_state)],
                    to_delayed_action=DelayedAction(
                        to_if_invoked=[_set_var(self._seq_var, self._seq_idle)]
                    ),
                    parameters={
                        "basic.to_delayed_action_delay_milliseconds": self._timeout_ms
                    },
                )
            )

            if i == 1:
                manipulators.append(
                    Manipulator(
                        conditions=[
                            VarCondition(
                                type=ConditionType.VARIABLE_IF,
                                name=self._hold_var,
                                value=1,
                            ),
                        ],
                        from_=_from_event(steps[i]),
                        to=[_set_var(self._seq_var, to_state)],
                        to_delayed_action=DelayedAction(
                            to_if_invoked=[_set_var(self._seq_var, self._seq_idle)]
                        ),
                        parameters={
                            "basic.to_delayed_action_delay_milliseconds": self._timeout_ms
                        },
                    )
                )

        # Final step: clear state + emit action
        manipulators.append(
            Manipulator(
                conditions=[
                    VarCondition(
                        type=ConditionType.VARIABLE_IF,
                        name=self._seq_var,
                        value=_seq_state(step_ids, len(steps) - 2),
                    ),
                ],
                from_=_from_event(steps[-1]),
                to=[
                    _set_var(self._seq_var, self._seq_idle),
                    ToEvent(
                        key_code=rule.action.chord.key,
                        modifiers=_map_modifiers(rule.action.chord.modifiers)
                        if rule.action.chord.modifiers
                        else None,
                    ),
                ],
            )
        )

        if len(steps) == 2:
            manipulators.append(
                Manipulator(
                    conditions=[
                        VarCondition(
                            type=ConditionType.VARIABLE_IF,
                            name=self._hold_var,
                            value=1,
                        ),
                    ],
                    from_=_from_event(steps[-1]),
                    to=[
                        _set_var(self._seq_var, self._seq_idle),
                        ToEvent(
                            key_code=rule.action.chord.key,
                            modifiers=_map_modifiers(rule.action.chord.modifiers)
                            if rule.action.chord.modifiers
                            else None,
                        ),
                    ],
                )
            )

        return manipulators


def _set_var(name: str, value: str | int) -> ToEvent:
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


def _leader_from_event(step) -> FromEvent:
    if step.modifiers:
        return _from_event(step)

    from_mods = FromModifiers(mandatory=[], optional=[Modifier.ANY])
    if len(step.keys) == 1:
        return FromEvent(key_code=step.keys[0], modifiers=from_mods)
    return FromEvent(simultaneous=list(step.keys), modifiers=from_mods)


def _step_id(step) -> str:
    parts = [*(m.value for m in sorted(step.modifiers, key=lambda m: m.value)), *step.keys]
    return _sanitize("_".join(parts))


def _seq_state(step_ids: list[str], prefix_len: int) -> str:
    root = step_ids[0]
    if prefix_len <= 0:
        return f"seq:{root}"
    suffix = ":".join(step_ids[1 : prefix_len + 1])
    return f"seq:{root}:{suffix}"


def _sanitize(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")


def _map_modifiers(mods) -> list[Modifier]:
    return [Modifier(mod.value) for mod in sorted(mods, key=lambda m: m.value)]
