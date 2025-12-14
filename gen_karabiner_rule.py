from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


_MODIFIER_ALIASES: dict[str, str] = {
    "command": "left_command",
    "cmd": "left_command",
    "shift": "left_shift",
    "option": "left_option",
    "opt": "left_option",
    "alt": "left_option",
    "control": "left_control",
    "ctrl": "left_control",
}


@dataclass(frozen=True)
class Shortcut:
    key_code: str
    modifiers: tuple[str, ...] = ()


def _set_var(name: str, value: int) -> dict[str, Any]:
    return {"set_variable": {"name": name, "value": value}}


def _var_if(name: str, value: int = 1) -> dict[str, Any]:
    return {"type": "variable_if", "name": name, "value": value}


def _frontmost_app_if(bundle_identifiers: Sequence[str]) -> dict[str, Any]:
    return {"type": "frontmost_application_if", "bundle_identifiers": list(bundle_identifiers)}


def _basic_manipulator(
    *,
    from_key: str,
    to: Sequence[Mapping[str, Any]],
    conditions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    manipulator: dict[str, Any] = {
        "type": "basic",
        "from": {"key_code": from_key, "modifiers": {"optional": ["any"]}},
        "to": list(to),
    }
    if conditions:
        manipulator["conditions"] = list(conditions)
    return manipulator


def _sanitize_token(token: str) -> str:
    token = token.strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token)
    token = re.sub(r"_+", "_", token).strip("_")
    return token or "x"


def _parse_sequence(sequence: str) -> tuple[str, ...]:
    parts = [p.strip().lower() for p in sequence.split(">")]
    parts = [p for p in parts if p]
    if len(parts) < 2:
        raise ValueError(f"sequence must have >= 2 keys, got: {sequence!r}")
    return tuple(parts)


def _parse_shortcut(shortcut: str) -> Shortcut:
    parts = [p.strip().lower() for p in shortcut.split("+")]
    parts = [p for p in parts if p]
    if not parts:
        raise ValueError("shortcut is empty")

    key = parts[-1]
    modifiers: list[str] = []
    for mod in parts[:-1]:
        mapped = _MODIFIER_ALIASES.get(mod)
        if not mapped:
            raise ValueError(f"unsupported modifier: {mod!r} (from {shortcut!r})")
        modifiers.append(mapped)

    return Shortcut(key_code=key, modifiers=tuple(modifiers))


def _iter_rule_items(rules: Any) -> Iterable[tuple[str, str]]:
    if isinstance(rules, dict):
        yield from rules.items()
        return
    if isinstance(rules, list):
        for item in rules:
            if not isinstance(item, dict):
                raise TypeError(f"rules list items must be objects, got: {type(item).__name__}")
            yield from item.items()
        return
    raise TypeError(f"rules must be an object or list of objects, got: {type(rules).__name__}")


def _build_rule(
    *,
    description: str,
    applications: Sequence[str] | None,
    mappings: Sequence[tuple[tuple[str, ...], Shortcut]],
) -> dict[str, Any]:
    # Group by leader key (sequence[0]).
    by_leader: dict[str, list[tuple[tuple[str, ...], Shortcut]]] = {}
    for sequence, shortcut in mappings:
        by_leader.setdefault(sequence[0], []).append((sequence, shortcut))

    manipulators: list[dict[str, Any]] = []
    app_condition = _frontmost_app_if(applications) if applications else None

    for leader_key in sorted(by_leader.keys()):
        leader_id = _sanitize_token(leader_key)
        leader_active_var = f"seq_{leader_id}_active"

        sequences = by_leader[leader_key]
        # Disallow ambiguous "one sequence is prefix of another".
        seq_set = {seq for (seq, _) in sequences}
        for seq in seq_set:
            for i in range(2, len(seq)):
                if seq[:i] in seq_set:
                    raise ValueError(f"ambiguous sequences: {seq[:i]!r} is a prefix of {seq!r}")

        prefix_vars: dict[tuple[str, ...], str] = {}
        for seq, _ in sequences:
            tail = seq[1:]
            for i in range(1, len(tail)):
                prefix = tail[:i]
                if prefix not in prefix_vars:
                    prefix_vars[prefix] = f"seq_{leader_id}_{'_'.join(_sanitize_token(p) for p in prefix)}"

        # Leader: tap to arm sequence mode (sticky until consumed).
        leader_conditions: list[dict[str, Any]] = []
        if app_condition:
            leader_conditions.append(app_condition)

        reset_prefix_vars = [_set_var(name, 0) for name in sorted(prefix_vars.values())]
        manipulators.append(
            {
                "type": "basic",
                "from": {"key_code": leader_key, "modifiers": {"optional": ["any"]}},
                "conditions": leader_conditions if leader_conditions else None,
                "to": [_set_var(leader_active_var, 1), *reset_prefix_vars],
            }
        )
        if manipulators[-1].get("conditions") is None:
            manipulators[-1].pop("conditions", None)

        # leader>key (length==2)
        single_step: dict[str, Shortcut] = {}
        for seq, shortcut in sequences:
            tail = seq[1:]
            if len(tail) == 1:
                key = tail[0]
                if key in single_step and single_step[key] != shortcut:
                    raise ValueError(f"conflicting mappings for {leader_key!r}>{key!r}")
                single_step[key] = shortcut

        for key, shortcut in sorted(single_step.items()):
            conditions = [_var_if(leader_active_var, 1)]
            if app_condition:
                conditions.append(app_condition)
            manipulators.append(
                _basic_manipulator(
                    from_key=key,
                    conditions=conditions,
                    to=[
                        _set_var(leader_active_var, 0),
                        {"key_code": shortcut.key_code, "modifiers": list(shortcut.modifiers)},
                    ],
                )
            )

        # First transition after leader for multi-step sequences (length>=3).
        first_steps: dict[str, str] = {}
        for seq, _ in sequences:
            tail = seq[1:]
            if len(tail) < 2:
                continue
            first = tail[0]
            first_var = prefix_vars[(first,)]
            if first in first_steps and first_steps[first] != first_var:
                raise RuntimeError("internal error: inconsistent prefix vars")
            first_steps[first] = first_var

        for first_key, first_var in sorted(first_steps.items()):
            conditions = [_var_if(leader_active_var, 1)]
            if app_condition:
                conditions.append(app_condition)
            manipulators.append(
                _basic_manipulator(
                    from_key=first_key,
                    conditions=conditions,
                    to=[_set_var(leader_active_var, 0), _set_var(first_var, 1)],
                )
            )

        # Intermediate transitions (prefix -> next_prefix) for sequences length>=4.
        transitions: dict[tuple[tuple[str, ...], str], tuple[str, str]] = {}
        # Key: (prev_prefix, next_key) -> (prev_var, next_var)
        for seq, _ in sequences:
            tail = seq[1:]
            if len(tail) < 3:
                continue
            for i in range(1, len(tail) - 1):
                prev_prefix = tail[:i]
                next_key = tail[i]
                next_prefix = tail[: i + 1]
                prev_var = prefix_vars[prev_prefix]
                next_var = prefix_vars[next_prefix]
                transitions[(prev_prefix, next_key)] = (prev_var, next_var)

        for (prev_prefix, next_key), (prev_var, next_var) in sorted(
            transitions.items(), key=lambda x: (x[0][0], x[0][1])
        ):
            conditions = [_var_if(prev_var, 1)]
            if app_condition:
                conditions.append(app_condition)
            manipulators.append(
                _basic_manipulator(
                    from_key=next_key,
                    conditions=conditions,
                    to=[_set_var(prev_var, 0), _set_var(next_var, 1)],
                )
            )

        # Final actions (last key triggers shortcut).
        finals: dict[tuple[tuple[str, ...], str], tuple[str, Shortcut]] = {}
        # Key: (prev_prefix, last_key) -> (prev_var, shortcut)
        for seq, shortcut in sequences:
            tail = seq[1:]
            if len(tail) < 2:
                continue
            prev_prefix = tail[:-1]
            last_key = tail[-1]
            prev_var = prefix_vars[prev_prefix]
            key = (prev_prefix, last_key)
            if key in finals and finals[key][1] != shortcut:
                raise ValueError(f"conflicting mappings for {leader_key!r}>{'>'.join(tail)!r}")
            finals[key] = (prev_var, shortcut)

        for (prev_prefix, last_key), (prev_var, shortcut) in sorted(
            finals.items(), key=lambda x: (x[0][0], x[0][1])
        ):
            conditions = [_var_if(prev_var, 1)]
            if app_condition:
                conditions.append(app_condition)
            manipulators.append(
                _basic_manipulator(
                    from_key=last_key,
                    conditions=conditions,
                    to=[
                        _set_var(prev_var, 0),
                        {"key_code": shortcut.key_code, "modifiers": list(shortcut.modifiers)},
                    ],
                )
            )

    return {"description": description, "manipulators": manipulators}


def generate_karabiner_rule(config_path: str, out_path: str) -> None:
    """
    Read a shortcut config json and generate a Karabiner "rule" json (description+manipulators).

    Config schema (see keyboard.json):
    - description: optional str, copied to output rule "description"
    - applications: optional list[str] (bundle id regexes), applied as frontmost_application_if
    - rules: dict[str, str] or list[dict[str, str]]
      - key: "f18>w>v" style sequence
      - value: "command+shift+option+1" style shortcut
    """
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    applications = config.get("applications")
    if applications is not None:
        if not isinstance(applications, list) or not all(isinstance(x, str) for x in applications):
            raise TypeError("applications must be a list of strings")

    raw_rules = config.get("rules")
    if raw_rules is None:
        raise KeyError("missing required field: rules")

    mappings: list[tuple[tuple[str, ...], Shortcut]] = []
    for seq_str, shortcut_str in _iter_rule_items(raw_rules):
        if not isinstance(seq_str, str) or not isinstance(shortcut_str, str):
            raise TypeError("rules keys/values must be strings")
        mappings.append((_parse_sequence(seq_str), _parse_shortcut(shortcut_str)))

    description_value = config.get("description")
    if description_value is None:
        description = f"Generated from {os.path.basename(config_path)}"
    elif isinstance(description_value, str):
        description = description_value
    else:
        raise TypeError("description must be a string")

    rule = _build_rule(description=description, applications=applications, mappings=mappings)
    Path(out_path).write_text(json.dumps(rule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    import sys

    argv = sys.argv[1:]
    if len(argv) == 4 and argv[0] == "config" and argv[2] == "out":
        generate_karabiner_rule(argv[1], argv[3])
        raise SystemExit(0)

    parser = argparse.ArgumentParser(description="Generate Karabiner rule json from a shortcut config json.")
    parser.add_argument("config", nargs="?", help="Shortcut config json path (e.g. keyboard.json)")
    parser.add_argument("out", nargs="?", help="Output Karabiner rule json path")
    parser.add_argument("--config", dest="config_flag", help="Shortcut config json path (e.g. keyboard.json)")
    parser.add_argument("--out", dest="out_flag", help="Output Karabiner rule json path")

    raw = parser.parse_args()

    config_path = raw.config_flag or raw.config
    out_path = raw.out_flag or raw.out

    if not config_path or not out_path:
        parser.error("expected config and out paths (e.g. keyboard.json out.json)")

    generate_karabiner_rule(config_path, out_path)
