from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .condition import Condition
from .from_event import FromEvent
from .to_event import ToEvent


class Manipulator(BaseModel):
    """Karabiner manipulator model."""

    type: str = "basic"
    conditions: List[Condition] = Field(default_factory=list)
    from_: FromEvent = Field(alias="from")
    to: Optional[List[ToEvent]] = None
    to_after_key_up: Optional[List[ToEvent]] = None
    to_if_alone: Optional[List[ToEvent]] = None

