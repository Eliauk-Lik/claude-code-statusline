# Claude Code Status Line

> A custom status line for [Claude Code](https://claude.ai/code) — shows model name, context usage bar, token count, session cost, and current working directory.

[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📸 Preview

![Screenshot](screenshot.png)

- **Model name** — cyan
- **Context bar** — green (0–40%), yellow (40–60%), red (60–100%)
- **Percentage** — context usage %
- **Tokens** — total input + output tokens
- **Cost** — self-calculated from tokens × provider rates (magenta)
- **Working dir** — blue, `~`-shortened

### 💰 Cost Calculation

The script calculates session cost from actual token counts, NOT from Claude
Code's built-in `total_cost_usd` (which assumes Anthropic pricing).

| Provider | Auto-detection | Default pricing |
|----------|---------------|-----------------|
| DeepSeek V4-Pro | model name contains `pro` | ¥3/M input, ¥6/M output |
| DeepSeek V4-Flash | model name contains `flash` | ¥1/M input, ¥2/M output |
| Anthropic | fallback | uses Claude Code's built-in cost |
| Custom | env var override | see below |

**Custom provider?** Set these environment variables:

```bash
export STATUSLINE_INPUT_PRICE=1.5    # ¥ per 1M input tokens
export STATUSLINE_OUTPUT_PRICE=3.0  # ¥ per 1M output tokens
export STATUSLINE_CURRENCY="$"       # default: ¥
```

---

## 🚀 Installation

```bash
# 1. Download the script
curl -Lo ~/.claude/statusline.py \
  https://raw.githubusercontent.com/Eliauk-Lik/claude-code-statusline/main/statusline.py

# 2. Add to ~/.claude/settings.json:
```

Add this to your `~/.claude/settings.json` (or project `.claude/settings.local.json`):

```json
"statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py"
}
```

No restart needed — the status line updates immediately.

---

## 🧪 Debug

If the status line shows `?` or something looks wrong:

```bash
python3 ~/.claude/statusline.py --debug
```

Debug info is written to stderr so it won't interfere with the status output.  
You can also inspect what data Claude Code passes by checking the sample JSON: run the script once with debug, or capture stdin directly:

```bash
# Save the JSON payload Claude Code sends
# (this requires running inside a Claude Code session)
```

---

## ⚙️ How It Works

Claude Code passes a JSON payload to the configured `statusLine` command via stdin every time the status refreshes. This script:

1. Reads and parses the JSON from stdin
2. Extracts: model name, context usage %, input/output tokens, working directory
3. Renders them as a single coloured line → stdout

The `statusLine` config in `settings.json` tells Claude Code to pipe its status JSON to this script and display the output.

---

## 📄 License

[MIT](LICENSE)

---

## 💡 Also See

- [Claude Code settings reference](https://docs.anthropic.com/en/docs/claude-code/settings)
- [Custom status lines](https://docs.anthropic.com/en/docs/claude-code/customization#custom-status-lines)

---

## 🇨🇳 中文说明

**Claude Code 状态栏插件** — 在终端底部显示模型名、上下文使用量进度条、Token 数、费用和工作目录。

### 安装

```bash
# 1. 下载脚本
curl -Lo ~/.claude/statusline.py \
  https://raw.githubusercontent.com/Eliauk-Lik/claude-code-statusline/main/statusline.py

# 2. 在 ~/.claude/settings.json 中添加：
```

```json
"statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py"
}
```

### 显示效果

![截图](screenshot.png)

| 元素 | 颜色 | 说明 |
|------|------|------|
| 模型名 | 青色 | 当前使用的模型 |
| 进度条 `[#—]` | 绿/黄/红 | 0–40% 绿, 40–60% 黄, 60–100% 红 |
| 百分比 | 跟随进度条 | 上下文窗口使用率 |
| Token 数 | 白色 | 输入 + 输出总计（自动缩略：1.2k / 3.4M） |
| 费用 | 品红色 | 根据 token 数 × 模型价格自己算，不是 Claude Code 内置的（那个按 Anthropic 价格算，不准） |
| 工作目录 | 蓝色 | ~ 简化的当前路径 |

### 费用计算

自己根据实际 token 消耗 × 提供商定价计算费用，不依赖 Claude Code 内置的 `total_cost_usd`（它按 Anthropic 模型价格算，第三方 API 不准）。

| 提供商 | 自动识别 | 默认价格 |
|--------|---------|----------|
| DeepSeek V4-Pro | 模型名含 `pro` | ¥3/百万输入, ¥6/百万输出 |
| DeepSeek V4-Flash | 模型名含 `flash` | ¥1/百万输入, ¥2/百万输出 |
| Anthropic | 兜底 | 用 Claude Code 内置 cost |
| 自定义 | 环境变量覆盖 | 见下方 |

**自定义定价**（其他 API 提供商）：

```bash
export STATUSLINE_INPUT_PRICE=1.5   # 每百万输入 token 价格
export STATUSLINE_OUTPUT_PRICE=3.0 # 每百万输出 token 价格
export STATUSLINE_CURRENCY="$"     # 货币符号，默认 ¥
```

### 调试

```bash
python3 ~/.claude/statusline.py --debug
```

输出不正常的 `?` 时加 `--debug` 查看 parsed 字段值。
