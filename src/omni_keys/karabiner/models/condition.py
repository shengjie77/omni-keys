from __future__ import annotations

from enum import Enum
from typing import Literal, List, Union

from pydantic import BaseModel

type Condition = Union[VarCondition, AppCondition]

class ConditionType(str, Enum):
    """Karabiner condition type."""
    APPLICATION_IF = 'frontmost_application_if'
    VARIABLE_IF = 'variable_if'


class BaseCondition(BaseModel):
    """Karabiner condition model."""

    type: ConditionType


class VarCondition(BaseCondition):
    type: Literal[ConditionType.VARIABLE_IF]
    name: str
    value: str | int | bool


class AppCondition(BaseCondition):
    type: Literal[ConditionType.APPLICATION_IF]
    bundle_identifiers: List[str]

