from __future__ import annotations

from omni_keys.karabiner.backend import KarabinerBackend
from omni_keys.shortcut.ir import Chord, Emit, Hotkey, KeyChord, RuleIR, When


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
        # leader_hold set/unset
        if any(
            e.set_variable and e.set_variable.name == "leader_hold" and e.set_variable.value == 1
            for e in (manip.to or [])
        ) and any(
            e.set_variable and e.set_variable.name == "leader_hold" and e.set_variable.value == 0
            for e in manip.to_after_key_up
        ):
            has_leader_hold = True
        # tap enters sequence mode
        if any(
            e.set_variable and e.set_variable.name == "seq_f18_active" and e.set_variable.value == 1
            for e in manip.to_if_alone
        ):
            has_leader_tap = True

    assert has_leader_hold
    assert has_leader_tap
