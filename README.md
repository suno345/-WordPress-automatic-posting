# WordPress自動投稿システム

FANZA同人作品のWordPress自動投稿システム。DMM APIから作品情報を取得し、Gemini AIでリライトして自動投稿する軽量で高速なシステムです。

## 🚀 特徴

- **DMM API直接統合**: スクレイピング不要の高速データ取得
- **前倒し投稿システム**: 複数作品発見時の15分間隔前倒し投稿
- **Gemini AI自動リライト**: 商品説明の自然な日本語記事生成
- **セキュリティ強化**: 入力検証、SSL証明書検証、暗号化設定管理
- **軽量設計**: 不要な依存関係を排除した効率的なシステム
- **VPS対応**: 96投稿/日の自動スケジューリング対応

## ディレクトリ構造

```
プロジェクトルート/
├── main.py                 # メインエントリーポイント
├── requirements.txt        # 依存関係
├── config/                 # 設定ファイル
│   ├── config.ini.example  # 設定例
│   ├── config.ini          # 実際の設定ファイル
│   └── config.vps.ini      # VPS用設定
├── src/                    # ソースコード
│   ├── api/                # 外部API関連
│   │   ├── dmm_api.py      # DMM API クライアント
│   │   ├── wordpress_api.py # WordPress API クライアント
│   │   └── gemini_api.py   # Gemini AI API クライアント
│   ├── core/               # コアビジネスロジック
│   │   ├── article_generator.py    # 記事生成
│   │   ├── post_manager.py         # 投稿管理
│   │   ├── auto_posting_system.py  # メインシステム
│   │   ├── post_schedule_manager.py # 前倒し投稿スケジュール
│   │   ├── scheduled_post_executor.py # 予約投稿実行
│   │   └── batch_article_generator.py # バッチ記事生成
│   ├── services/           # システムサービス
│   │   ├── error_handlers.py    # エラーハンドリング
│   │   ├── exceptions.py        # カスタム例外
│   │   ├── resource_manager.py  # リソース管理
│   │   ├── cache_manager.py     # 多層キャッシュシステム
│   │   └── intelligent_error_handler.py # インテリジェントエラー処理
│   ├── security/           # セキュリティ
│   │   ├── input_validator.py   # 入力検証
│   │   └── ssl_certificate_validator.py # SSL証明書検証
│   ├── config/             # 設定管理
│   │   └── secure_config_manager.py # セキュア設定管理
│   ├── database/           # データベース
│   │   └── sqlite_manager.py    # SQLite管理
│   └── utils/              # ユーティリティ
│       ├── constants.py         # 定数定義
│       ├── utils.py             # 汎用関数
│       └── check_swell_blocks.py # SWELL確認スクリプト
├── data/                   # データファイル
│   ├── posted_works.json   # 投稿済み作品リスト (旧形式)
│   ├── posted_works.db     # SQLite投稿履歴データベース
│   ├── scheduled_posts.db  # 予約投稿スケジュールDB
│   └── swell_blocks.json   # SWELLブロック定義
├── docs/                   # ドキュメント
│   ├── 前倒し投稿システム仕様書.md  # 前倒し投稿仕様
│   └── patterns/           # H2見出しパターン
│       ├── パターン1
│       ├── パターン1_装飾版
│       ├── パターン2
│       ├── パターン2_装飾版
│       ├── パターン3
│       └── パターン3_装飾版
├── scripts/                # 実行スクリプト
│   ├── execute_scheduled_posts.py  # 予約投稿実行
│   └── wordpress_auth_diagnostic.py # WordPress認証診断
├── logs/                   # ログファイル
├── tests/                  # テストファイル
│   ├── unit/               # 単体テスト
│   └── integration/        # 結合テスト
└── templates/              # テンプレート
```

## 🔧 セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

セキュリティ強化のため、機密情報は環境変数で管理します：

```bash
# .env ファイルを作成
cat > .env << 'EOF'
# DMM API
DMM_API_ID=your_dmm_api_id
DMM_AFFILIATE_ID=your_affiliate_id

# WordPress
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_PASSWORD=your_application_password

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key
EOF
```

### 3. 設定ファイルの作成

```bash
cp config/config.ini.example config/config.ini
# または VPS用設定
cp config/config.ini.example config/config.vps.ini
```

### 4. 必要なディレクトリの作成

```bash
mkdir -p logs data scripts
```

### 5. データベース初期化

```bash
# SQLiteデータベースを自動作成
python main.py --status
```

## 💻 使用方法

### 通常実行（記事検索・生成・投稿）

```bash
python main.py
```

### VPS環境での実行

```bash
# VPS用設定で実行
python main.py --config config/config.vps.ini --vps-mode

# 予約投稿実行 (cron用)
python scripts/execute_scheduled_posts.py --vps-mode
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

# レビューチェックをスキップ（テスト用）
python main.py --skip-review-check

# WordPress認証診断
python scripts/wordpress_auth_diagnostic.py
```

### VPS cron設定例

```bash
# 15分間隔で予約投稿実行
*/15 * * * * cd /opt/blog-automation && source venv/bin/activate && python scripts/execute_scheduled_posts.py --vps-mode >> logs/cron.log 2>&1

# 1時間おきに新規記事検索・生成
0 * * * * cd /opt/blog-automation && source venv/bin/activate && python main.py --vps-mode >> logs/cron.log 2>&1
```

## ⚡ 主要機能

### 📝 記事生成・投稿
- **DMM API統合**: レビュー情報・商品詳細を直接取得（スクレイピング不要）
- **Gemini AI記事生成**: 商品説明の自然で読みやすい日本語記事へのリライト
- **SWELL対応**: WordPressテーマSWELLのブロック形式で記事生成
- **重複防止**: SQLiteベースの投稿履歴管理
- **構造化記事**: SEO最適化された一貫性のある記事構成

### ⏰ 投稿スケジューリング
- **前倒し投稿システム**: 複数作品発見時の15分間隔前倒し投稿
- **予約投稿実行**: cron対応の自動スケジュール実行
- **96投稿/日対応**: 15分刻みでの効率的な投稿管理
- **スケジュール競合回避**: 既存予約との自動重複チェック

### 🔒 セキュリティ・安定性
- **入力検証**: HTMLサニタイゼーション・XSS対策
- **SSL証明書検証**: 通信セキュリティの強化
- **暗号化設定管理**: 機密情報の安全な保存
- **インテリジェントエラーハンドリング**: 自動復旧機能付きエラー処理

### 🚀 パフォーマンス
- **多層キャッシュシステム**: メモリ・ディスク・時間ベースキャッシュ
- **並列処理**: ThreadPoolExecutorによる高速データ処理
- **軽量設計**: 不要な依存関係を排除（370行コード削減）
- **リソース管理**: メモリリーク防止の適切なリソース管理

## 🏗️ システムアーキテクチャ

### 設計原則
- **軽量・高速**: DMM API直接統合によるスクレイピング不要設計
- **セキュリティファースト**: 多層セキュリティによる機密情報保護
- **モジュラー設計**: 機能ごとの明確な分離と独立性
- **VPS最適化**: 長時間安定動作とリソース効率化
- **拡張性**: 新機能追加に対応した柔軟なアーキテクチャ

### 技術スタック
- **Python 3.8+**: メインプログラミング言語
- **SQLite**: 軽量データベース（投稿履歴・スケジュール管理）
- **DMM API**: 商品情報・レビューデータ取得
- **Gemini AI**: 記事内容の自動生成・リライト
- **WordPress REST API**: 記事投稿・管理
- **環境変数**: セキュアな設定管理

## 📋 自動生成記事の構成

システムが生成する記事は以下の構造化された構成を持ちます：

### 記事タイトル
```
作品タイトル【作者名またはサークル名】
```

### 記事本文構成

#### 1. 導入文
```html
<p>エロ同人サークル「<a href="サークルタグURL">サークル名</a>」のエロマンガです。</p>
```

#### 2. パッケージ画像
```html
<img src="画像URL" alt="作品タイトル" class="aligncenter size-full" />
```

#### 3. 作品紹介文
```html
<p>Gemini AIでリライトされた自然な日本語紹介文</p>
```

#### 4. 作品情報
```html
<p><strong>ページ数：</strong>XX</p>
```

#### 5. ジャンル情報
```html
<p><strong>ジャンル：</strong><a href="ジャンルタグURL">ジャンル1</a>, <a href="ジャンルタグURL">ジャンル2</a></p>
```

#### 6. サンプル画像
```html
<h3>サンプル画像</h3>
<img src="画像URL" alt="作品タイトル サンプル画像" class="aligncenter size-full" />
<!-- DMM APIから取得した全サンプル画像を表示（上限なし） -->
```

#### 7. アフィリエイトボタン（SWELL形式）
```html
<div class="swell-block-button red_ is-style-btn_solid">
  <a href="アフィリエイトURL" class="swell-block-button__link">
    <span>続きを読むにはクリック</span>
  </a>
</div>
```

#### 8. レビュー情報
```html
<h3>レビュー</h3>
<p><strong>評価：</strong>4.5点 (3件)</p>
<blockquote>平均評価: 4.5点</blockquote>
```

#### 9. H2見出し（カスタムパターン）
- `docs/patterns/`からランダム選択される装飾H2見出し
- 作品タイトルとアフィリエイトURLが自動置換

#### 10. 関連作品エリア
```html
<!-- 関連作品はWordPressプラグインで自動表示 -->
```

### タグ・カテゴリ設定
- **タグ**: サークル名、作者名（重複除去）
- **カテゴリ**: DMM APIから取得した全ジャンル

### SEO最適化
- 構造化データ対応
- 適切なalt属性設定
- 内部リンク最適化（タグ・カテゴリリンク）
- SWELL WordPressテーマ完全対応

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. WordPress認証エラー (401 Unauthorized)
```bash
# WordPress認証診断を実行
python scripts/wordpress_auth_diagnostic.py

# 解決方法：
# - WordPressでアプリケーションパスワードを生成
# - 環境変数WORDPRESS_PASSWORDにアプリケーションパスワードを設定
```

#### 2. DMM API接続エラー
```bash
# 接続テストを実行
python main.py --test-connections

# 確認項目：
# - DMM_API_ID の正確性
# - ネットワーク接続
# - API制限状況
```

#### 3. Gemini AI エラー
```bash
# 環境変数を確認
echo $GEMINI_API_KEY

# 解決方法：
# - Google AI StudioでAPIキーを確認
# - 使用量制限をチェック
```

#### 4. 前倒し投稿が動作しない
```bash
# スケジュール状況確認
python scripts/execute_scheduled_posts.py --status --vps-mode

# 確認項目：
# - cron設定の正確性
# - ログファイルのエラー内容
```

### ログの確認

```bash
# 最新ログを監視
tail -f logs/auto_post_$(date +%Y%m%d).log

# エラーログ検索
grep -i error logs/*.log

# cron実行ログ確認
tail -f logs/cron.log
```

## 👨‍💻 開発者向け情報

### パフォーマンス指標

| 項目 | 最適化前 | 最適化後 | 改善率 |
|------|----------|----------|--------|
| レビュー取得速度 | 1-3秒 | 0.01秒 | **200-300倍** |
| コード行数 | 2,500行 | 2,130行 | **15%削減** |
| ライブラリ依存 | 12個 | 7個 | **5個削除** |
| メモリ使用量 | - | **最適化済み** | キャッシュ効率化 |

### 最新のアップデート

- **v1.2.0** (2025-08-01)
  - DMM API直接統合によるスクレイピング廃止
  - 前倒し投稿システム実装
  - セキュリティ強化 (入力検証・SSL検証)
  - SQLite移行・多層キャッシュシステム
  - コードベース大幅軽量化

### テストの実行

```bash
# 単体テスト
python -m pytest tests/unit/

# 結合テスト
python -m pytest tests/integration/

# 全テスト
python -m pytest

# カバレッジ付きテスト
python -m pytest --cov=src
```

### 開発環境のセットアップ

```bash
# 開発用依存関係のインストール
pip install pytest pytest-cov black flake8

# コードフォーマット
black src/ tests/

# リンター実行
flake8 src/ tests/
```

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

---

**⚡ 高速・軽量・セキュア**なWordPress自動投稿システム  
*DMM API統合による次世代同人作品投稿自動化*