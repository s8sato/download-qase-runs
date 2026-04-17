# download-qase-runs

Qase の指定プロジェクトの Test Runs を PDF / CSV 形式でダウンロードするツール。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 使い方

```
python download_qase_runs.py <PROJECT> [--dir DIR] [--pdf] [--csv]
```

> venv をアクティベートした状態で実行してください（`source .venv/bin/activate`）。

| 引数 | 説明 |
|------|------|
| `PROJECT` | Qase プロジェクトキー（例: `SANDBOX`） |
| `--dir DIR` | 保存先ディレクトリ（デフォルト: `./qase/<PROJECT>/runs/`） |
| `--pdf` | PDF レポートをエクスポート |
| `--csv` | CSV レポートをエクスポート |

### 使用例

```bash
# PDF のみ
python download_qase_runs.py SANDBOX --pdf

# PDF と CSV の両方
python download_qase_runs.py SANDBOX --pdf --csv

# 保存先を指定
python download_qase_runs.py SANDBOX --pdf --csv --dir /tmp/qase/
```

## 出力構造

```
DIR/
├── pdf/
│   ├── 1.pdf
│   ├── 2.pdf
│   └── ...
└── csv/
    ├── 1.csv
    ├── 2.csv
    └── ...
```

ファイル名はラン ID です。既存ファイルは上書きされません。

## 認証

初回実行時にブラウザウィンドウが開くので、Qase にログインしてください。  
セッションは `~/.config/download-qase-runs/auth_state.json` に保存され、次回以降は自動的に再利用されます。
