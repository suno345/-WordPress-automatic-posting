# WordPress自動投稿システム

FANZAの同人作品をWordPressに自動投稿するシステムです。

## ディレクトリ構造

```
プロジェクトルート/
├── main.py                 # メインエントリーポイント
├── requirements.txt        # 依存関係
├── config/                 # 設定ファイル
│   ├── config.ini.example  # 設定例
│   └── config.ini          # 実際の設定ファイル
├── src/                    # ソースコード
│   ├── api/                # 外部API関連
│   │   ├── dmm_api.py      # DMM API クライアント
│   │   ├── wordpress_api.py # WordPress API クライアント
│   │   └── gemini_api.py   # Gemini AI API クライアント
│   ├── core/               # コアビジネスロジック
│   │   ├── article_generator.py # 記事生成
│   │   ├── post_manager.py      # 投稿管理
│   │   └── auto_posting_system.py # メインシステム
│   ├── services/           # システムサービス
│   │   ├── error_handlers.py    # エラーハンドリング
│   │   ├── exceptions.py        # カスタム例外
│   │   ├── resource_manager.py  # リソース管理
│   │   └── security_utils.py    # セキュリティ
│   ├── utils/              # ユーティリティ
│   │   ├── constants.py         # 定数定義
│   │   ├── utils.py             # 汎用関数
│   │   └── check_swell_blocks.py # SWELL確認スクリプト
│   └── config/             # 設定管理
│       └── config_manager.py    # 設定管理クラス
├── data/                   # データファイル
│   ├── posted_works.json   # 投稿済み作品リスト
│   └── swell_blocks.json   # SWELLブロック定義
├── docs/                   # ドキュメント
│   └── patterns/           # H2見出しパターン
│       ├── パターン1
│       ├── パターン1_装飾版
│       ├── パターン2
│       ├── パターン2_装飾版
│       ├── パターン3
│       └── パターン3_装飾版
├── logs/                   # ログファイル
├── tests/                  # テストファイル
│   ├── unit/               # 単体テスト
│   └── integration/        # 結合テスト
└── templates/              # テンプレート
```

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの作成

```bash
cp config/config.ini.example config/config.ini
```

設定ファイル (`config/config.ini`) を編集して、各種APIキーとWordPress情報を設定してください。

### 3. 必要なディレクトリの作成

```bash
mkdir -p logs data
```

## 使用方法

### 通常実行

```bash
python main.py
```

### コマンドラインオプション

```bash
# カスタム設定ファイルを使用
python main.py --config config/custom.ini

# 接続テストのみ実行
python main.py --test-connections

# システム状態を表示
python main.py --status

# 詳細ログを出力
python main.py --verbose
```

## 機能

- **自動記事生成**: Gemini AIを使用した記事の自動生成
- **投稿管理**: 重複投稿の防止と投稿履歴管理
- **エラーハンドリング**: 統一されたエラー処理システム
- **セキュリティ**: 機密情報の安全な取り扱い
- **リソース管理**: メモリリーク防止のためのリソース管理
- **ログ管理**: 詳細なログ記録とエラー追跡

## アーキテクチャ

このシステムは以下の設計原則に基づいています：

- **モジュラーアーキテクチャ**: 機能ごとの明確な分離
- **依存性注入**: テスタブルで柔軟な設計
- **エラーファースト**: 堅牢なエラーハンドリング
- **セキュリティファースト**: 機密情報の適切な保護
- **SOLID原則**: 保守性の高いコード設計

## トラブルシューティング

### よくある問題

1. **設定エラー**: `config/config.ini` の設定を確認してください
2. **API接続エラー**: ネットワーク接続とAPIキーを確認してください
3. **パス関連エラー**: ディレクトリ構造が正しいか確認してください

### ログの確認

```bash
tail -f logs/auto_post_$(date +%Y%m%d).log
```

## 開発者向け情報

### テストの実行

```bash
# 単体テスト
python -m pytest tests/unit/

# 結合テスト
python -m pytest tests/integration/

# 全テスト
python -m pytest
```

### 開発環境のセットアップ

```bash
# 開発用依存関係のインストール
pip install -r requirements-dev.txt

# プリコミットフックの設定
pre-commit install
```

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。