from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .key_code import KeyCode
from .modifier import Modifier


class ToEvent(BaseModel):
    """Karabiner `to` event model."""

    key_code: Optional[KeyCode] = None
    modifiers: Optional[List[Modifier]] = None

