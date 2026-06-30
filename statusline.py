#!/usr/bin/env python3
"""Claude Code Status Line — model, context bar, tokens, cwd.

A custom status line renderer for Claude Code that shows:
  • Model name (cyan)
  • Context usage bar (green/yellow/red)
  • Usage percentage
  • Total token count (white)
  • Session cost — auto-detects DeepSeek pricing (magenta)
  • Working directory (blue, ~-shortened)

Pricing is self-calculated from token counts × provider rates, so it works
accurately with any API provider. DeepSeek Flash/Pro are auto-detected;
set STATUSLINE_INPUT_PRICE / STATUSLINE_OUTPUT_PRICE / STATUSLINE_CURRENCY
env vars for other providers.

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
    MAGENTA = "01;35"


# ---------------------------------------------------------------------------
#  Pricing — DeepSeek (RMB per 1M tokens, cache miss)
# ---------------------------------------------------------------------------

# https://api-docs.deepseek.com/quick_start/pricing
_DEEPSEEK_PRICES = {
    "flash": {"input": 1.0, "output": 2.0},   # V4-Flash
    "pro":   {"input": 3.0, "output": 6.0},   # V4-Pro
}


def _get_pricing(model: str) -> tuple[float, float, str]:
    """Return (input_¥_per_1M, output_¥_per_1M, currency_symbol).

    Priority: env vars > DeepSeek auto-detect > Claude Code fallback.
    """
    input_env = os.environ.get("STATUSLINE_INPUT_PRICE")
    output_env = os.environ.get("STATUSLINE_OUTPUT_PRICE")
    if input_env and output_env:
        try:
            currency = os.environ.get("STATUSLINE_CURRENCY", "¥")
            return float(input_env), float(output_env), currency
        except ValueError:
            pass

    model_lower = model.lower()
    for key, prices in _DEEPSEEK_PRICES.items():
        if key in model_lower:
            return prices["input"], prices["output"], "¥"

    # Unknown model — fall back to Claude Code's built-in cost
    return 0, 0, "$"


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


def _format_cost(cost: float, currency: str) -> str:
    """Human-friendly cost string (¥ or $)."""
    if cost <= 0:
        return f"{currency}0"
    if cost < 0.01:
        return f"<{currency}0.01"
    return f"{currency}{cost:.2f}"


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

    # Session cost — self-calculated from tokens for accuracy with any provider.
    # Claude Code's built-in total_cost_usd uses Anthropic pricing; we compute
    # our own via DeepSeek rates (or env-var overrides) instead.
    input_price, output_price, currency = _get_pricing(model)
    try:
        ti_int = int(ti)
        to_int = int(to)
    except (TypeError, ValueError):
        ti_int = to_int = 0

    if input_price > 0 or output_price > 0:
        # Self-calculated from token counts + provider pricing
        cost_val = (ti_int / 1_000_000) * input_price + (to_int / 1_000_000) * output_price
    else:
        # Fallback: use Claude Code's built-in cost (for Anthropic models)
        cost = data.get("cost")
        if isinstance(cost, dict):
            try:
                cost_val = float(cost.get("total_cost_usd", 0))
            except (TypeError, ValueError):
                cost_val = 0.0
        else:
            cost_val = 0.0
        currency = "$"

    if debug:
        sys.stderr.write(
            f"[statusline] model={model} cwd={cwd} pct={pct}% "
            f"tokens={total_tokens} cost={currency}{cost_val:.4f}\n"
        )

    return {
        "model": model,
        "cwd": cwd,
        "pct": min(pct, 100),
        "tokens": total_tokens,
        "cost_val": cost_val,
        "currency": currency,
    }


# ---------------------------------------------------------------------------
#  Render
# ---------------------------------------------------------------------------

def render(info: dict) -> str:
    """Build the one-line status string."""
    bar = _progress_bar(info["pct"])
    bar_colored = _color(_bar_color(info["pct"]), bar)
    ts = _format_tokens(info["tokens"])
    cs = _format_cost(info["cost_val"], info["currency"])
    return (
        f"{_color(_Color.CYAN, info['model'])}  "
        f"[{bar_colored}] {info['pct']}%  "
        f"{_color(_Color.WHITE, ts)}  "
        f"{_color(_Color.MAGENTA, cs)}  "
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
