from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from .condition import Condition
from .from_event import FromEvent


class Manipulator(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conditions: List[Condition]
    from_: FromEvent = Field(alias="from")

