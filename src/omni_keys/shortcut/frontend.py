from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import tomllib

from .config import Config
from .dsl import parse_rule_mapping
from .ir import RuleIR, When


class ShortcutFrontend:
    """Parse config (TOML) into platform-agnostic IR rules."""

    def load_toml(self, path: str | Path) -> Dict[str, Any]:
        """Load a TOML config file into a dict."""

        path = Path(path)
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def parse_config(self, config: Dict[str, Any]) -> List[RuleIR]:
        cfg = Config.model_validate(config)

        alias_key = cfg.alias.key
        alias_mod = cfg.alias.mod
        global_apps = cfg.when.applications if cfg.when else None

        rules: List[RuleIR] = []
        for rule in cfg.rule:
            parsed = parse_rule_mapping(
                rule.trigger,
                rule.emit,
                alias_key=alias_key,
                alias_mod=alias_mod,
            )

            rule_apps = rule.when.applications if rule.when else None
            applications = rule_apps if rule_apps is not None else global_apps
            if applications is not None:
                parsed.when = When(applications=applications)

            rules.append(parsed)

        return rules
