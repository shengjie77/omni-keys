from __future__ import annotations

from enum import Enum
from typing import List, Optional, Set

from pydantic import BaseModel


class Modifier(str, Enum):
    """Frontend (platform-agnostic) modifier tokens; must distinguish left/right."""


class KeyCode(str):
    """Frontend (platform-agnostic) key token."""


class Chord(BaseModel):
    """One trigger step: simultaneous keys (+ optional modifiers)."""

    keys: List[KeyCode]
    modifiers: Set[Modifier] = set()


class Hotkey(BaseModel):
    """Trigger hotkey: 1 step = chord, N steps = sequence."""

    steps: List[Chord]


class KeyChord(BaseModel):
    """The emitted key chord (one key + optional modifiers)."""

    key: KeyCode
    modifiers: Set[Modifier] = set()


class Action(BaseModel):
    """Base type for rule actions."""


class Emit(Action):
    """Emit a key chord."""

    chord: KeyChord


class When(BaseModel):
    """User-visible conditions (e.g., frontmost apps, modes)."""


class RuleIR(BaseModel):
    """Frontend IR rule: trigger -> action, optionally gated by when."""

    trigger: Hotkey
    action: Action
    when: Optional[When] = None

