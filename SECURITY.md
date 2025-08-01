# セキュリティガイドライン

## 機密情報の管理

### 設定ファイルの運用

#### 本番環境の認証情報
実際の認証情報は以下のファイルで管理し、**絶対にGitにコミットしないでください**：

- `config/config.ini` - ローカル開発用設定
- `config/config.vps.ini` - VPS環境用設定

#### テンプレートファイル
設定の構造を示すテンプレートファイル：
- `config/config.ini.example` - 設定ファイルのテンプレート

### 必要な認証情報

#### Google Gemini API
1. [Google AI Studio](https://aistudio.google.com/app/apikey) でAPIキーを生成
2. `config/config.ini` の `[gemini]` セクションに設定
```ini
[gemini]
api_key = YOUR_ACTUAL_GEMINI_API_KEY
```

#### WordPress認証
1. WordPressダッシュボード > ユーザー > プロフィール
2. アプリケーションパスワードを生成
3. `config/config.ini` の `[wordpress]` セクションに設定
```ini
[wordpress]
url = https://your-site.com
username = your_username
password = YOUR_APP_PASSWORD
```

#### DMM API
1. [DMM アフィリエイト](https://affiliate.dmm.com/)でAPI IDを取得
2. `config/config.ini` の `[dmm_api]` セクションに設定
```ini
[dmm_api]
api_id = YOUR_DMM_API_ID
affiliate_id = YOUR_AFFILIATE_ID
```

## セキュリティ対策

### 履歴の確認
機密情報がコミットされていないか定期的にチェック：
```bash
# 機密情報の検索
git log -p --all -S "api_key" -S "password"
```

### .gitignore の維持
以下のパターンが確実に除外されることを確認：
- `config/config.ini`
- `config/config.vps.ini`
- すべての `.env*` ファイル
- 認証関連のファイル

### 緊急時の対応

#### APIキーが漏洩した場合
1. **即座に無効化**: 各サービスでAPIキーを無効化
2. **新しいキー生成**: 新しいAPIキーを生成
3. **履歴の書き換え**: `git filter-repo` で履歴から削除
4. **強制プッシュ**: GitHub履歴を更新

#### 実行コマンド例
```bash
# 履歴から機密情報を削除
git filter-repo --force --replace-text <(echo "OLD_API_KEY==>***REMOVED***")

# GitHubに強制プッシュ
git remote add origin https://github.com/USERNAME/REPO.git
git push --force origin main
```

## 開発環境のセットアップ

1. リポジトリをクローン
2. `config/config.ini.example` を `config/config.ini` にコピー
3. 実際の認証情報を設定
4. `.gitignore` により `config/config.ini` は自動的に除外

## 定期的なセキュリティチェック

### 月次チェックリスト
- [ ] APIキーの有効期限確認
- [ ] 不要なアクセス権限の削除
- [ ] ログファイルの機密情報チェック
- [ ] 依存パッケージの脆弱性確認

### 年次チェックリスト
- [ ] 全APIキーのローテーション
- [ ] アクセス権限の全面見直し
- [ ] セキュリティ設定の更新

---

**重要**: このファイル自体には機密情報を記載しないでください。テンプレートとプロセスのみを記載しています。