from __future__ import annotations

from pathlib import Path
import argparse

from omni_keys.shortcut.frontend import ShortcutFrontend

from .backend import KarabinerBackend


def compile_toml_config(in_path: str | Path, out_path: str | Path, *, indent: int | None = 2) -> None:
    """End-to-end compilation: TOML file -> Karabiner Rule JSON file."""

    in_path = Path(in_path)
    out_path = Path(out_path)

    frontend = ShortcutFrontend()
    config = frontend.load_toml(in_path)
    rules = frontend.parse_config(config)
    description = str(config.get("description", ""))

    backend = KarabinerBackend()
    rule = backend.compile(rules, description=description)

    json_str = rule.model_dump_json(indent=indent, by_alias=True, exclude_none=True)
    out_path.write_text(json_str + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Karabiner rule json from shortcut config toml."
    )
    parser.add_argument("config", help="Shortcut config toml path (e.g. keyboard.toml)")
    parser.add_argument("out", help="Output Karabiner rule json path")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2)")

    args = parser.parse_args(argv)
    compile_toml_config(args.config, args.out, indent=args.indent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
