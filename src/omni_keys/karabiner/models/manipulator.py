from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .condition import Condition
from .from_event import FromEvent
from .to_event import ToEvent


class DelayedAction(BaseModel):
    to_if_invoked: Optional[List[ToEvent]] = None
    to_if_canceled: Optional[List[ToEvent]] = None


class Manipulator(BaseModel):
    """Karabiner manipulator model."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = "basic"
    conditions: List[Condition] = Field(default_factory=list)
    from_: FromEvent = Field(alias="from")
    to: Optional[List[ToEvent]] = None
    to_after_key_up: Optional[List[ToEvent]] = None
    to_if_alone: Optional[List[ToEvent]] = None
    to_delayed_action: Optional[DelayedAction] = None
    parameters: Optional[Dict[str, int]] = None
