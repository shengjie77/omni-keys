from __future__ import annotations

from typing import Iterable

from omni_keys.karabiner.backend import KarabinerBackend
from omni_keys.karabiner.models.condition import AppCondition, ConditionType, VarCondition
from omni_keys.karabiner.models.to_event import Variable
from omni_keys.shortcut.ir import Chord, Emit, Hotkey, KeyChord, Modifier, RuleIR, When


def _find_app_condition(conditions: Iterable[object]) -> AppCondition | None:
    for cond in conditions:
        if isinstance(cond, AppCondition):
            return cond
    return None


def _find_var_condition(conditions: Iterable[object], name: str) -> VarCondition | None:
    for cond in conditions:
        if isinstance(cond, VarCondition) and cond.name == name:
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


def _has_modifiers(events, expected: set[str]) -> bool:
    for event in events:
        if event.modifiers is None:
            continue
        actual = {getattr(mod, "value", mod) for mod in event.modifiers}
        if actual == expected:
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

    # Expect at least root + final, with extra cancel/timeout rules allowed.
    assert len(out.manipulators) >= 2

    root = out.manipulators[0]
    assert root.from_.key_code == "f18"
    assert root.to is not None
    assert _has_set_variable(root.to, name="seq_f18_active", value=1)

    app_cond = _find_app_condition(root.conditions)
    assert app_cond is not None
    assert app_cond.type == ConditionType.APPLICATION_IF
    assert app_cond.bundle_identifiers == ["com.example.app"]

    final = next(m for m in out.manipulators if m.from_.key_code == "w")
    assert final.to is not None

    var_cond = _find_var_condition(final.conditions, "seq_f18_active")
    assert var_cond is not None
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

    # Expect at least root + mid + final, with extra cancel/timeout rules allowed.
    assert len(out.manipulators) >= 3

    root = out.manipulators[0]
    assert root.from_.key_code == "f18"
    assert root.to is not None
    assert _has_set_variable(root.to, name="seq_f18_active", value=1)

    mid = next(m for m in out.manipulators if m.from_.key_code == "w")
    assert mid.to is not None
    assert _has_set_variable(mid.to, name="seq_f18_active", value=0)
    assert _has_set_variable(mid.to, name="seq_f18_w", value=1)

    var_cond = _find_var_condition(mid.conditions, "seq_f18_active")
    assert var_cond is not None

    final = next(m for m in out.manipulators if m.from_.key_code == "v")
    assert final.to is not None
    assert _has_set_variable(final.to, name="seq_f18_w", value=0)
    assert _has_key_code(final.to, "2")


def test_backend_includes_modifiers() -> None:
    rule = RuleIR(
        trigger=Hotkey(
            steps=[
                Chord(keys=["h"], modifiers={Modifier.RIGHT_COMMAND, Modifier.RIGHT_SHIFT})
            ]
        ),
        action=Emit(
            chord=KeyChord(key="left_arrow", modifiers={Modifier.COMMAND, Modifier.SHIFT})
        ),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    manip = out.manipulators[0]
    assert manip.from_.modifiers is not None
    assert set(manip.from_.modifiers.mandatory or []) == {
        Modifier.RIGHT_COMMAND,
        Modifier.RIGHT_SHIFT,
    }

    assert manip.to is not None
    assert _has_modifiers(manip.to, {"command", "shift"})


def test_backend_sequence_cancel_on_wrong_key() -> None:
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"]), Chord(keys=["v"])]),
        action=Emit(chord=KeyChord(key="2")),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    # Expect cancel manipulators when prefix active and any other key pressed.
    has_root_cancel = False
    has_mid_cancel = False
    for manip in out.manipulators:
        if manip.from_.any is None:
            continue
        if manip.to is None:
            continue

        if _find_var_condition(manip.conditions, "seq_f18_active"):
            if _has_set_variable(manip.to, name="seq_f18_active", value=0) and _has_set_variable(
                manip.to, name="seq_f18_w", value=0
            ):
                has_root_cancel = True

        if _find_var_condition(manip.conditions, "seq_f18_w"):
            if _has_set_variable(manip.to, name="seq_f18_active", value=0) and _has_set_variable(
                manip.to, name="seq_f18_w", value=0
            ):
                has_mid_cancel = True

    assert has_root_cancel
    assert has_mid_cancel


def test_backend_sequence_timeout_clears_state() -> None:
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"]), Chord(keys=["v"])]),
        action=Emit(chord=KeyChord(key="2")),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    # Expect a delayed action with a timeout that clears all root-related states.
    has_timeout_clear = False
    for manip in out.manipulators:
        delayed = getattr(manip, "to_delayed_action", None)
        params = getattr(manip, "parameters", None)
        if delayed is None or params is None:
            continue
        if "basic.to_delayed_action_delay_milliseconds" not in params:
            continue
        invoked = getattr(delayed, "to_if_invoked", None)
        if invoked is None:
            continue
        if _has_set_variable(invoked, name="seq_f18_active", value=0) and _has_set_variable(
            invoked, name="seq_f18_w", value=0
        ):
            has_timeout_clear = True

    assert has_timeout_clear
