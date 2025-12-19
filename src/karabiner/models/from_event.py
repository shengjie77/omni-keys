from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .key_code import KeyCode
from .modifiers import FromModifiers


class FromEvent(BaseModel):
    """Karabiner `from` event model (key_code or simultaneous)."""

    key_code: Optional[KeyCode] = None
    simultaneous: Optional[List[KeyCode]] = None
    modifiers: Optional[FromModifiers] = None

