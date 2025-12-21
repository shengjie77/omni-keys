from __future__ import annotations

from omni_keys.karabiner.backend import KarabinerBackend
from omni_keys.shortcut.ir import Chord, Emit, Hotkey, KeyChord, RuleIR, When
from omni_keys.karabiner.models.condition import VarCondition


def test_leader_hold_and_tap_generated() -> None:
    # A minimal sequence to force leader behavior in backend (f18>w>v)
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"]), Chord(keys=["v"])]),
        action=Emit(chord=KeyChord(key="1")),
        when=When(applications=["com.example.app"]),
    )

    backend = KarabinerBackend()
    out = backend.compile([rule], description="test")

    # Expect leader hold and tap behavior to be present in manipulators
    has_leader_hold = False
    has_leader_tap = False
    for manip in out.manipulators:
        if manip.from_.key_code != "f18":
            continue
        if manip.to_after_key_up is None or manip.to_if_alone is None:
            continue
        # omni.hold set/unset
        if any(
            e.set_variable and e.set_variable.name == "omni.hold" and e.set_variable.value == 1
            for e in (manip.to or [])
        ) and any(
            e.set_variable and e.set_variable.name == "omni.hold" and e.set_variable.value == 0
            for e in manip.to_after_key_up
        ):
            has_leader_hold = True
        # tap enters sequence mode
        if any(
            e.set_variable and e.set_variable.name == "omni.seq" and e.set_variable.value == "seq:f18"
            for e in manip.to_if_alone
        ):
            has_leader_tap = True

    assert has_leader_hold
    assert has_leader_tap


def test_leader_hold_chord_rule() -> None:
    # leader_key+h -> left_arrow
    rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18", "h"])]),
        action=Emit(chord=KeyChord(key="left_arrow")),
    )
    # include a sequence rule so f18 is recognized as leader
    seq_rule = RuleIR(
        trigger=Hotkey(steps=[Chord(keys=["f18"]), Chord(keys=["w"]), Chord(keys=["v"])]),
        action=Emit(chord=KeyChord(key="1")),
    )

    backend = KarabinerBackend()
    out = backend.compile([seq_rule, rule], description="test")

    # Look for a manipulator that triggers on h with omni.hold==1
    found = False
    for manip in out.manipulators:
        if manip.from_.key_code != "h":
            continue
        if not any(
            isinstance(c, VarCondition) and c.name == "omni.hold" and c.value == 1
            for c in manip.conditions
        ):
            continue
        if manip.to and any(e.key_code == "left_arrow" for e in manip.to):
            found = True
            break

    assert found
