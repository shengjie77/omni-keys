from __future__ import annotations

from typing import Any, Dict, List

from .ir import RuleIR


class ShortcutFrontend:
    """Parse config (TOML) into platform-agnostic IR rules."""

    def parse_config(self, config: Dict[str, Any]) -> List[RuleIR]:
        raise NotImplementedError

