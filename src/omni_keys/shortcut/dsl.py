from __future__ import annotations

from typing import Iterable, Mapping

from .ir import Chord, Emit, Hotkey, KeyChord, KeyCode, Modifier, RuleIR


_MODIFIER_TOKENS = {m.value for m in Modifier}


def _normalize_aliases(aliases: Mapping[str, str] | None) -> dict[str, str]:
    if not aliases:
        return {}
    return {str(k).strip().lower(): str(v).strip().lower() for k, v in aliases.items()}


def _tokenize(expr: str, *, step_sep: str, chord_sep: str) -> list[list[str]]:
    expr = expr.strip()
    if not expr:
        raise ValueError("expression is empty")

    steps: list[list[str]] = []
    for raw_step in expr.split(step_sep):
        raw_step = raw_step.strip()
        if not raw_step:
            raise ValueError(f"invalid expression (empty step): {expr!r}")
        tokens = [t.strip() for t in raw_step.split(chord_sep) if t.strip()]
        if not tokens:
            raise ValueError(f"invalid expression (empty chord): {expr!r}")
        steps.append(tokens)
    return steps


def _apply_alias(token: str, *, alias_key: Mapping[str, str], alias_mod: Mapping[str, str]) -> str:
    token = token.strip().lower()
    if token in alias_mod:
        token = alias_mod[token]
    if token in alias_key:
        token = alias_key[token]
    return token


def _split_mods_and_keys(tokens: Iterable[str]) -> tuple[list[KeyCode], set[Modifier]]:
    keys: list[KeyCode] = []
    modifiers: set[Modifier] = set()
    for token in tokens:
        if token in _MODIFIER_TOKENS:
            modifiers.add(Modifier(token))
        else:
            keys.append(KeyCode(token))
    return keys, modifiers


def parse_hotkey(
    expr: str,
    *,
    alias_key: Mapping[str, str] | None = None,
    alias_mod: Mapping[str, str] | None = None,
    step_sep: str = ">",
    chord_sep: str = "+",
) -> Hotkey:
    """Parse DSL hotkey expression into IR Hotkey."""

    alias_key = _normalize_aliases(alias_key)
    alias_mod = _normalize_aliases(alias_mod)

    steps: list[Chord] = []
    for tokens in _tokenize(expr, step_sep=step_sep, chord_sep=chord_sep):
        normalized = [_apply_alias(t, alias_key=alias_key, alias_mod=alias_mod) for t in tokens]
        keys, modifiers = _split_mods_and_keys(normalized)
        if not keys:
            raise ValueError(f"invalid hotkey step (no keys): {tokens!r}")
        steps.append(Chord(keys=keys, modifiers=modifiers))

    return Hotkey(steps=steps)


def parse_keychord(
    expr: str,
    *,
    alias_key: Mapping[str, str] | None = None,
    alias_mod: Mapping[str, str] | None = None,
    chord_sep: str = "+",
) -> KeyChord:
    """Parse DSL emitted chord expression into IR KeyChord."""

    alias_key = _normalize_aliases(alias_key)
    alias_mod = _normalize_aliases(alias_mod)

    tokens = _tokenize(expr, step_sep=",", chord_sep=chord_sep)[0]
    normalized = [_apply_alias(t, alias_key=alias_key, alias_mod=alias_mod) for t in tokens]
    keys, modifiers = _split_mods_and_keys(normalized)
    if len(keys) != 1:
        raise ValueError(f"emit expression must have exactly one key: {expr!r}")

    return KeyChord(key=keys[0], modifiers=modifiers)


def parse_rule_mapping(
    trigger: str,
    emit: str,
    *,
    alias_key: Mapping[str, str] | None = None,
    alias_mod: Mapping[str, str] | None = None,
) -> RuleIR:
    """Parse a (trigger, emit) pair into a RuleIR."""

    hotkey = parse_hotkey(trigger, alias_key=alias_key, alias_mod=alias_mod)
    action = Emit(chord=parse_keychord(emit, alias_key=alias_key, alias_mod=alias_mod))
    return RuleIR(trigger=hotkey, action=action)
