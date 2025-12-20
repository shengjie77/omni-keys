from __future__ import annotations

from typing import Iterable

from omni_keys.karabiner.backend import KarabinerBackend
from omni_keys.karabiner.models.condition import AppCondition, ConditionType, VarCondition
from omni_keys.karabiner.models.to_event import Variable
from omni_keys.shortcut.ir import Chord, Emit, Hotkey, KeyChord, RuleIR, When


def _find_app_condition(conditions: Iterable[object]) -> AppCondition | None:
    for cond in conditions:
        if isinstance(cond, AppCondition):
            return cond
    return None


def _find_var_condition(conditions: Iterable[object]) -> VarCondition | None:
    for cond in conditions:
        if isinstance(cond, VarCondition):
            return cond
    return None


def _has_set_variable(events, *, name: str, value: int) -> bool:
    for event in events:
        if event.set_variable is None:
            continue
        if isinstance(event.set_variable, Variable):
            if event.set_variable.name == name and event.set_variable.value == value:
                return True
    return False


def _has_key_code(events, key_code: str) -> bool:
    for event in events:
        if event.key_code == key_code:
            return True
    return False


def test_backend_sequence_two_step() -> None:
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"])]),
        action=Emit(chord=KeyChord(key="1")),
        when=When(applications=["com.example.app"]),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    assert len(out.manipulators) == 2

    root = out.manipulators[0]
    assert root.from_.key_code == "f18"
    assert root.to is not None
    assert _has_set_variable(root.to, name="seq_f18_active", value=1)

    app_cond = _find_app_condition(root.conditions)
    assert app_cond is not None
    assert app_cond.type == ConditionType.APPLICATION_IF
    assert app_cond.bundle_identifiers == ["com.example.app"]

    final = out.manipulators[1]
    assert final.from_.key_code == "w"
    assert final.to is not None

    var_cond = _find_var_condition(final.conditions)
    assert var_cond is not None
    assert var_cond.name == "seq_f18_active"
    assert var_cond.value == 1

    assert _has_set_variable(final.to, name="seq_f18_active", value=0)
    assert _has_key_code(final.to, "1")


def test_backend_sequence_three_step() -> None:
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"]), Chord(keys=["v"])]),
        action=Emit(chord=KeyChord(key="2")),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    assert len(out.manipulators) == 3

    root = out.manipulators[0]
    assert root.from_.key_code == "f18"
    assert root.to is not None
    assert _has_set_variable(root.to, name="seq_f18_active", value=1)

    mid = out.manipulators[1]
    assert mid.from_.key_code == "w"
    assert mid.to is not None
    assert _has_set_variable(mid.to, name="seq_f18_active", value=0)
    assert _has_set_variable(mid.to, name="seq_f18_w", value=1)

    var_cond = _find_var_condition(mid.conditions)
    assert var_cond is not None
    assert var_cond.name == "seq_f18_active"

    final = out.manipulators[2]
    assert final.from_.key_code == "v"
    assert final.to is not None
    assert _has_set_variable(final.to, name="seq_f18_w", value=0)
    assert _has_key_code(final.to, "2")
