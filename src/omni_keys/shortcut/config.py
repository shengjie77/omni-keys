from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class AliasConfig(BaseModel):
    key: Dict[str, str] = Field(default_factory=dict)
    mod: Dict[str, str] = Field(default_factory=dict)


class WhenConfig(BaseModel):
    applications: List[str] | None = None


class RuleConfig(BaseModel):
    trigger: str
    emit: str
    when: WhenConfig | None = None


class Config(BaseModel):
    version: int | None = None
    description: str | None = None
    when: WhenConfig | None = None
    alias: AliasConfig = Field(default_factory=AliasConfig)
    rule: List[RuleConfig] = Field(default_factory=list)
