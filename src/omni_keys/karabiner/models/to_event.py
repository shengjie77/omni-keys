from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .key_code import KeyCode
from .modifier import Modifier


class ToEvent(BaseModel):
    """
    Karabiner `to` event model.

    https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/to/
    """

    key_code: Optional[KeyCode] = None
    shell_command: Optional[str] = None
    set_variable: Optional[Variable] = None
    modifiers: Optional[List[Modifier]] = None

    
class Variable(BaseModel):
    name: str
    value: str | int | bool

