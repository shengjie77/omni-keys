from __future__ import annotations

from typing import List, Optional
from enum import Enum

from pydantic import BaseModel

from .key_code import KeyCode
from .modifiers import FromModifiers


class FromEvent(BaseModel):
    """Karabiner `from` event model (key_code or simultaneous)."""

    key_code: Optional[KeyCode] = None
    any: Optional[AnyKey] = None
    simultaneous: Optional[List[KeyCode]] = None
    modifiers: Optional[FromModifiers] = None

class AnyKey(str, Enum):
    """
    https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/from/any/
    """

    KEY_CODE = 'key_code'
    CONSUMER_KEY_CODE = 'consumer_key_code'
    POINTING_BUTTON = 'pointing_button'
