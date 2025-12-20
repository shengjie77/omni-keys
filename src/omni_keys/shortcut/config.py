from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class AliasConfig(BaseModel):
    key: Dict[str, str] = Field(default_factory=dict)
    mod: Dict[str, str] = Field(default_factory=dict)


class RuleConfig(BaseModel):
    trigger: str
    emit: str


class WhenGroupConfig(BaseModel):
    applications: List[str]
    rule: List[RuleConfig] = Field(default_factory=list)


class Config(BaseModel):
    version: int | None = None
    description: str | None = None
    alias: AliasConfig = Field(default_factory=AliasConfig)
    rule: List[RuleConfig] = Field(default_factory=list)
    when: List[WhenGroupConfig] = Field(default_factory=list)
