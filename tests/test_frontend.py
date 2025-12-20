from __future__ import annotations

from pathlib import Path

from omni_keys.shortcut.frontend import ShortcutFrontend
from omni_keys.shortcut.ir import Emit


def _norm_mods(modifiers) -> set[str]:
    return {getattr(mod, "value", mod) for mod in modifiers}


def test_parse_config_basic() -> None:
    path = Path(__file__).with_name("test_keys.toml")
    frontend = ShortcutFrontend()
    config = frontend.load_toml(path)
    rules = frontend.parse_config(config)

    assert len(rules) == 2

    # leader_key+h has no implicit when
    chord_rule = next(r for r in rules if len(r.trigger.steps) == 1)
    assert chord_rule.when is None

    # leader_key>w>v uses when group and should inherit applications
    seq_rule = next(r for r in rules if len(r.trigger.steps) == 3)

    assert isinstance(seq_rule.action, Emit)
    assert seq_rule.action.chord.key == "1"
    assert _norm_mods(seq_rule.action.chord.modifiers) == {"command", "shift", "option"}

    assert seq_rule.when is not None
    assert getattr(seq_rule.when, "applications", None) == [
        "^com\\.jetbrains\\.",
        "^com\\.google\\.android\\.studio$",
    ]
