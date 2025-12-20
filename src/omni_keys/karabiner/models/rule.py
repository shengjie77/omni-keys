from __future__ import annotations

from typing import List

from pydantic import BaseModel

from .manipulator import Manipulator


class Rule(BaseModel):
    """Karabiner top-level rule model."""

    description: str
    manipulators: List[Manipulator]

