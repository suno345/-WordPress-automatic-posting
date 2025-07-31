# WordPress自動投稿システム

DMM アフィリエイト API を使用して同人作品情報を取得し、AIを活用してユニークな紹介記事を生成し、WordPressに自動投稿するシステムです。

## 機能

- DMM アフィリエイト API から同人作品情報を自動取得
- 新着順の同人コミックでレビューされている作品を対象
- Gemini APIを使用した紹介文のリライト
- WordPress REST APIを使用した予約投稿
- 重複投稿防止機能
- エラーハンドリングとログ記録

## セットアップ

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. DMM アフィリエイト API の取得
1. [DMM アフィリエイト](https://affiliate.dmm.com/) にアカウント登録
2. API利用申請を行い、API IDを取得

### 3. 設定ファイルの作成
`config.ini.example` を `config.ini` にコピーし、以下の情報を入力：
- DMM API ID（必須）
- DMM アフィリエイト ID（オプション）
- WordPress サイト情報
- Gemini API キー

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
│   ├── dmm_api.py
│   ├── gemini_api.py
│   ├── wordpress_api.py
│   └── article_generator.py
├── data/                # データファイル
│   └── posted_works.json
├── logs/                # ログファイル
└── scripts/             # ユーティリティスクリプト
```