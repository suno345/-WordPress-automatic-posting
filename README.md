# WordPress自動投稿システム

FANZAの同人作品情報を元に、AIを活用してユニークな紹介記事を生成し、WordPressに自動投稿するシステムです。

## 機能

- FANZAから同人作品情報を自動取得
- Gemini APIを使用した紹介文のリライト
- WordPress REST APIを使用した予約投稿
- 重複投稿防止機能
- エラーハンドリングとログ記録

## セットアップ

1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

2. 設定ファイルの作成
`config.ini.example` を `config.ini` にコピーし、必要な情報を入力してください。

3. cronジョブの設定
```bash
crontab -e
# 以下を追加（15分ごとに実行）
*/15 * * * * /usr/bin/python3 /path/to/main.py
```

## 使用方法

手動実行:
```bash
python main.py
```

## ディレクトリ構造

```
.
├── main.py              # メインスクリプト
├── config.ini           # 設定ファイル（要作成）
├── requirements.txt     # 依存関係
├── modules/             # 各種モジュール
│   ├── fanza_scraper.py
│   ├── gemini_api.py
│   ├── wordpress_api.py
│   └── article_generator.py
├── data/                # データファイル
│   └── posted_works.json
├── logs/                # ログファイル
└── scripts/             # ユーティリティスクリプト
```