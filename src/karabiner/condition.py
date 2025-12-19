from __future__ import annotations

from pydantic import BaseModel

from .condition_type import ConditionType


# https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/conditions/
class Condition(BaseModel):
    type: ConditionType
    name: str
    value: str

