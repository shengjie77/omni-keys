from __future__ import annotations

from enum import Enum


class Modifier(str, Enum):
    """Karabiner modifier token (backend target model)."""

    ANY = "any"

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
