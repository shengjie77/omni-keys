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

    assert len(rules) == 1
    rule = rules[0]

    # Trigger: leader_key>w>v -> f18>w>v
    steps = rule.trigger.steps
    assert [step.keys for step in steps] == [["f18"], ["w"], ["v"]]
    assert all(len(step.modifiers) == 0 for step in steps)

    # Action: cmd+shift+opt+1 -> command+shift+option+1
    assert isinstance(rule.action, Emit)
    assert rule.action.chord.key == "1"
    assert _norm_mods(rule.action.chord.modifiers) == {"command", "shift", "option"}

    # Global when should be applied to rule
    assert rule.when is not None
    assert getattr(rule.when, "applications", None) == [
        "^com\\.jetbrains\\.",
        "^com\\.google\\.android\\.studio$",
    ]
