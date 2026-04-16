# claude-trace

Claude Code のセッション履歴（`~/.claude/projects/*/*.jsonl`）を、
user / assistant が交互に並んだ読みやすい Markdown に変換する Python スクリプトです。

## セッション履歴の保存場所

Claude Code は各セッションを以下のパスに JSONL で保存しています。

```
~/.claude/projects/<作業ディレクトリをハイフン変換したもの>/<session-uuid>.jsonl
```

例:
```
~/.claude/projects/-Users-foo-bar-my-project/0a63e301-3dcd-4fee-8817-44a9112c4f04.jsonl
```

## 必要なもの

- Python 3.9+
- 標準ライブラリのみ（追加インストール不要）

## 使い方

### 単一ファイルを変換

```bash
python3 jsonl_to_md.py ~/.claude/projects/<project>/<uuid>.jsonl
```

デフォルトで `./projects/<プロジェクト名>/<uuid>.md` に出力されます。

### 出力先を明示指定

```bash
python3 jsonl_to_md.py session.jsonl -o out.md
```

### ディレクトリ内の jsonl を一括変換

```bash
python3 jsonl_to_md.py ~/.claude/projects/<project>/
```

`./projects/<project>/` 配下にまとめて `.md` が出力されます。

## 出力フォーマット

- `## 👤 User` / `## 🤖 Claude` で発言を交互に表示
- `thinking` ブロックは `<details>` で折り畳み
- ツール呼び出し（`tool_use`）はツール名と入力 JSON をコードブロックで表示
- ツール結果（`tool_result`）もコードブロックで表示（2000 文字超は省略）
- `permission-mode` / `file-history-snapshot` 等の制御レコードや、
  `<local-command-stdout>` などの内部メッセージはスキップ

### 出力例

```markdown
## 👤 User

reports/outputs/*.md のうち最新のものを探して欲しい。

## 🤖 Claude

> **ツール呼び出し: `Glob`**

​```json
{
  "pattern": "reports/outputs/*.md"
}
​```

## 👤 User

> **ツール結果**

​```
reports/outputs/detection-t1.md
reports/outputs/detection-t2_v3.md
...
​```

## 🤖 Claude

最新は `detection-t2_v3.md` です。
```

## カスタマイズ

`jsonl_to_md.py` 冒頭の定数・関数を調整してください。

- `SKIP_PREFIXES` — 本文として表示しないユーザーメッセージのプレフィックス
- `render_tool_result` 内の `2000` — ツール結果の省略文字数
- `OUTPUT_ROOT` — 既定の出力ルート（`./projects`）

## ライセンス

MIT
