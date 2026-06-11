#!/usr/bin/env python3
"""Claude Code Status Line — model, context bar, tokens, cwd.

A custom status line renderer for Claude Code that shows:
  • Model name (cyan)
  • Context usage bar (green/yellow/red)
  • Usage percentage
  • Total token count (white)
  • Working directory (blue, ~-shortened)

Requires Python 3.6+ and NO external dependencies.

Configure in ~/.claude/settings.json:
    "statusLine": {
        "type": "command",
        "command": "python3 /path/to/statusline.py"
    }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


# ---------------------------------------------------------------------------
#  ANSI colour codes
# ---------------------------------------------------------------------------

class _Color:
    CYAN = "01;36"
    WHITE = "01;37"
    BLUE = "01;34"
    GREEN = "01;32"
    YELLOW = "01;33"
    RED = "01;31"


def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _shorten_path(path: str) -> str:
    """Replace $HOME with ~ for a shorter display."""
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


def _format_tokens(n: int) -> str:
    """Human-friendly token count."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n) if n > 0 else "0"


def _progress_bar(pct: int, width: int = 10) -> str:
    """Render a filled/unfilled bar."""
    bar_fill = min(pct // 10, width)
    return "#" * bar_fill + "-" * (width - bar_fill)


def _bar_color(pct: int) -> str:
    if pct >= 60:
        return _Color.RED
    if pct >= 40:
        return _Color.YELLOW
    return _Color.GREEN


# ---------------------------------------------------------------------------
#  Parsing
# ---------------------------------------------------------------------------

def _nested_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Deep dict access without try/except chains."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, {})
    return d if d != {} else default


def parse_input(data: dict, debug: bool = False) -> dict:
    """Extract display fields from the Claude Code status JSON."""
    # Model
    model = "?"
    raw = _nested_get(data, "model")
    if isinstance(raw, dict):
        model = raw.get("display_name") or raw.get("name") or raw.get("id") or "?"
    elif isinstance(raw, str) and raw:
        model = raw
    if model == "?":
        model = os.environ.get("ANTHROPIC_MODEL", "?")

    # Working directory
    cwd = data.get("cwd") or ""
    if not cwd:
        ws = data.get("workspace")
        if isinstance(ws, dict):
            cwd = ws.get("current_dir") or ws.get("root") or ""
    cwd = _shorten_path(cwd)

    # Context window
    cw = data.get("context_window") or {}
    try:
        pct = int(round(float(cw.get("used_percentage", 0))))
    except (TypeError, ValueError):
        pct = 0

    # Token counts (try both nested and flat)
    ti = _nested_get(cw, "total_input_tokens") or data.get("total_input_tokens") or 0
    to = _nested_get(cw, "total_output_tokens") or data.get("total_output_tokens") or 0
    try:
        total_tokens = int(ti) + int(to)
    except (TypeError, ValueError):
        total_tokens = 0

    if debug:
        sys.stderr.write(
            f"[statusline] model={model} cwd={cwd} pct={pct}% "
            f"tokens={total_tokens}\n"
        )

    return {
        "model": model,
        "cwd": cwd,
        "pct": min(pct, 100),
        "tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
#  Render
# ---------------------------------------------------------------------------

def render(info: dict) -> str:
    """Build the one-line status string."""
    bar = _progress_bar(info["pct"])
    bar_colored = _color(_bar_color(info["pct"]), bar)
    ts = _format_tokens(info["tokens"])
    return (
        f"{_color(_Color.CYAN, info['model'])}  "
        f"[{bar_colored}] {info['pct']}%  "
        f"{_color(_Color.WHITE, ts)}  "
        f"{_color(_Color.BLUE, info['cwd'])}"
    )


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claude Code status line renderer",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print parsed fields to stderr for troubleshooting",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()

    try:
        data: dict = json.loads(raw)
    except json.JSONDecodeError:
        print("?", end="", flush=True)
        sys.exit(0)

    info = parse_input(data, debug=args.debug)
    line = render(info)
    print(line, end="", flush=True)


if __name__ == "__main__":
    main()
