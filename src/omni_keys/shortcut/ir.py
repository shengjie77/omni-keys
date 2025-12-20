from __future__ import annotations

from enum import Enum
from typing import List, Optional, Set, TypeAlias

from pydantic import BaseModel, Field


class Modifier(str, Enum):
    """Frontend (platform-agnostic) modifier tokens; must distinguish left/right."""

    COMMAND = "command"
    CONTROL = "control"
    OPTION = "option"
    SHIFT = "shift"
    FN = "fn"
    CAPS_LOCK = "caps_lock"

    LEFT_COMMAND = "left_command"
    LEFT_CONTROL = "left_control"
    LEFT_OPTION = "left_option"
    LEFT_SHIFT = "left_shift"

    RIGHT_COMMAND = "right_command"
    RIGHT_CONTROL = "right_control"
    RIGHT_OPTION = "right_option"
    RIGHT_SHIFT = "right_shift"


KeyCode: TypeAlias = str


class Chord(BaseModel):
    """One trigger step: simultaneous keys (+ optional modifiers)."""

    keys: List[KeyCode]
    modifiers: Set[Modifier] = Field(default_factory=set)


class Hotkey(BaseModel):
    """Trigger hotkey: 1 step = chord, N steps = sequence."""

    steps: List[Chord]


class KeyChord(BaseModel):
    """The emitted key chord (one key + optional modifiers)."""

    key: KeyCode
    modifiers: Set[Modifier] = Field(default_factory=set)


class Action(BaseModel):
    """Base type for rule actions."""


class Emit(Action):
    """Emit a key chord."""

    chord: KeyChord


class When(BaseModel):
    """User-visible conditions (e.g., frontmost apps, modes)."""

    applications: Optional[List[str]] = None


class RuleIR(BaseModel):
    """Frontend IR rule: trigger -> action, optionally gated by when."""

    trigger: Hotkey
    action: Action
    when: Optional[When] = None
