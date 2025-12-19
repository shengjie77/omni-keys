from __future__ import annotations

from pydantic import BaseModel

from .condition_type import ConditionType


class Condition(BaseModel):
    """Karabiner condition model."""

    type: ConditionType

