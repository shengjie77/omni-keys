from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import tomllib

from .ir import RuleIR


class ShortcutFrontend:
    """Parse config (TOML) into platform-agnostic IR rules."""

    def load_toml(self, path: str | Path) -> Dict[str, Any]:
        """Load a TOML config file into a dict."""

        path = Path(path)
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def parse_config(self, config: Dict[str, Any]) -> List[RuleIR]:
        raise NotImplementedError
