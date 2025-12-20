from __future__ import annotations

from typing import Any, Dict

from .models.rule import Rule


def compile_toml_config(config: Dict[str, Any]) -> Rule:
    """End-to-end compilation: TOML config dict -> Karabiner Rule model."""

    raise NotImplementedError

