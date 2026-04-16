#!/usr/bin/env python3
"""Claude Code のセッション JSONL を user/assistant 交互の Markdown に変換する。

使い方:
    python3 jsonl_to_md.py <session.jsonl> [-o output.md]
    python3 jsonl_to_md.py <session.jsonl>            # 同じ場所に .md を出力
    python3 jsonl_to_md.py <dir>                       # ディレクトリ内の全 jsonl を変換
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# 本文として表示しない「制御的」ユーザーメッセージの検出
SKIP_PREFIXES = (
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<local-command-caveat>",
)


def fmt_text(text: str) -> str:
    """Markdown として問題の少ない整形にする(末尾改行の統一など)。"""
    return text.rstrip() + "\n"


def render_tool_use(block: dict[str, Any]) -> str:
    name = block.get("name", "?")
    inp = block.get("input", {})
    try:
        inp_str = json.dumps(inp, ensure_ascii=False, indent=2)
    except Exception:
        inp_str = str(inp)
    return (
        f"> **ツール呼び出し: `{name}`**\n\n"
        f"```json\n{inp_str}\n```\n"
    )


def render_tool_result(block: dict[str, Any]) -> str:
    content = block.get("content")
    is_error = block.get("is_error") or False
    header = "> **ツール結果" + ("（エラー）" if is_error else "") + "**"

    if isinstance(content, str):
        body = content
    elif isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                elif c.get("type") == "image":
                    parts.append("[画像省略]")
                else:
                    parts.append(json.dumps(c, ensure_ascii=False))
            else:
                parts.append(str(c))
        body = "\n".join(parts)
    else:
        body = json.dumps(content, ensure_ascii=False)

    # 長すぎる結果は折り畳む
    if len(body) > 2000:
        body = body[:2000] + "\n...(省略)..."

    return f"{header}\n\n```\n{body}\n```\n"


def extract_blocks(msg_content: Any) -> list[dict[str, Any]]:
    if isinstance(msg_content, str):
        return [{"type": "text", "text": msg_content}]
    if isinstance(msg_content, list):
        return [c for c in msg_content if isinstance(c, dict)]
    return []


def render_user(record: dict[str, Any]) -> str | None:
    msg = record.get("message", {})
    blocks = extract_blocks(msg.get("content"))

    text_parts: list[str] = []
    tool_results: list[str] = []

    for b in blocks:
        t = b.get("type")
        if t == "text":
            text = b.get("text", "")
            if not text.strip():
                continue
            if text.strip().startswith(SKIP_PREFIXES):
                continue
            text_parts.append(text)
        elif t == "tool_result":
            tool_results.append(render_tool_result(b))
        elif t == "image":
            text_parts.append("[画像添付]")

    if not text_parts and not tool_results:
        return None

    out = ["## 👤 User\n"]
    if text_parts:
        out.append(fmt_text("\n\n".join(text_parts)))
    if tool_results:
        out.append("\n".join(tool_results))
    return "\n".join(out) + "\n"


def render_assistant(record: dict[str, Any]) -> str | None:
    msg = record.get("message", {})
    blocks = extract_blocks(msg.get("content"))

    parts: list[str] = []
    for b in blocks:
        t = b.get("type")
        if t == "text":
            text = b.get("text", "")
            if text.strip():
                parts.append(fmt_text(text))
        elif t == "thinking":
            thinking = b.get("thinking", "")
            if thinking.strip():
                parts.append(
                    "<details><summary>🧠 thinking</summary>\n\n"
                    + fmt_text(thinking)
                    + "\n</details>\n"
                )
        elif t == "tool_use":
            parts.append(render_tool_use(b))

    if not parts:
        return None

    return "## 🤖 Claude\n\n" + "\n".join(parts) + "\n"


def convert(jsonl_path: Path, out_path: Path) -> None:
    chunks: list[str] = [f"# Session: {jsonl_path.stem}\n"]
    last_role: str | None = None

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = record.get("type")
            rendered: str | None = None
            if t == "user":
                rendered = render_user(record)
                role = "user"
            elif t == "assistant":
                rendered = render_assistant(record)
                role = "assistant"
            else:
                continue

            if rendered is None:
                continue

            # 同じロールが連続した場合は区切り線で軽く分ける
            if last_role == role:
                chunks.append("\n---\n")
            chunks.append(rendered)
            last_role = role

    out_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"✅ {jsonl_path} -> {out_path}")


OUTPUT_ROOT = Path("./projects").resolve()


def decide_output_path(jsonl_path: Path, source_dir: Path | None) -> Path:
    """出力先を ./projects/<プロジェクト名>/<uuid>.md に決定する。

    source_dir が与えられた場合(ディレクトリ変換時)はその名前をプロジェクト名に、
    単体ファイル指定時は親ディレクトリ名を使う。
    """
    project_name = (source_dir or jsonl_path.parent).name
    out_dir = OUTPUT_ROOT / project_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / (jsonl_path.stem + ".md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Code JSONL -> Markdown")
    parser.add_argument("path", help="変換対象の .jsonl ファイル、またはディレクトリ")
    parser.add_argument(
        "-o",
        "--output",
        help="出力先を明示指定 (ファイル変換時のみ有効。省略時は ./projects/<プロジェクト名>/ に保存)",
    )
    args = parser.parse_args()

    target = Path(args.path).expanduser()
    if not target.exists():
        print(f"パスが存在しません: {target}", file=sys.stderr)
        return 1

    if target.is_dir():
        files = sorted(target.glob("*.jsonl"))
        if not files:
            print("jsonl ファイルが見つかりません", file=sys.stderr)
            return 1
        for f in files:
            convert(f, decide_output_path(f, target))
    else:
        if args.output:
            out = Path(args.output).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
        else:
            out = decide_output_path(target, None)
        convert(target, out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
