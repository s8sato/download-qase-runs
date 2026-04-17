Qase の 指定 Project の Test Runs を PDF / CSV 形式でダウンロードするツール
を以下に従って生成すること

- 仕様
  - 入力
    - Qaseのプロジェクト名（以降、PROJECTとする）
    - ダウンロード先のディレクトリパス（以降、DIRとする）
      - デフォルト： ./qase/runs/PROJECT/
    - PDFをダウンロードするフラグ
    - CSVをダウンロードするフラグ
  - 出力
    - https://app.qase.io/run/PROJECT 以下の全てのRunsにわたって
      - 入力にPDFフラグがある場合はPDFをエクスポートして DIR/pdf/ 以下に保存
      - 入力にCSVフラグがある場合はCSVをエクスポートして DIR/csv/ 以下に保存
      - ただし、既存のファイルは上書きしない
- 使用推奨ライブラリ
  - Playwright Python
- 注意事項
  - このツールの用法を簡潔に記したREADMEを作成すること
  - ページネーションに注意
    - 1ページしかない場合、 https://app.qase.io/run/PROJECT?page=1 は404となる
      - この場合の正しいURLは https://app.qase.io/run/PROJECT
    - 最大ページ数を超えてpageを指定すると最大ページにリダイレクトされる
  - 以下にアクセスして動作テストすること
    - https://app.qase.io/run/SANDBOX
- 参考情報
  - Run詳細ページのURLサンプル
    - https://app.qase.io/run/SANDBOX/dashboard/2
      - エクスポート用ボタンのselectorは次のとおり
        - #react-aria8061714511-\:ri4\: