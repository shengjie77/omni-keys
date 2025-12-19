from __future__ import annotations

from pydantic import BaseModel

from .key_code import KeyCode


class FromEvent(BaseModel):
    key_code: KeyCode

