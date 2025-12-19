from __future__ import annotations

from typing import List

from pydantic import BaseModel

from .manipulator import Manipulator


class Rule(BaseModel):
    description: str
    manipulators: List[Manipulator]

