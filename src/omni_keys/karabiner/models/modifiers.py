from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .modifier import Modifier


class FromModifiers(BaseModel):
    """Karabiner `from.modifiers` model."""

    mandatory: Optional[List[Modifier]] = None
    optional: Optional[List[Modifier]] = None

