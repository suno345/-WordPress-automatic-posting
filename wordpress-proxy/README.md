# DMM画像プロキシシステム

## 概要
DMM APIから取得した画像をWordPressサイト経由で配信するプロキシシステムです。
Referrer PolicyやHotlink Protectionによる外部参照制限を回避します。

## インストール方法

### 1. プロキシファイルのアップロード
```bash
# WordPressのルートディレクトリにアップロード
cp dmm-image-proxy.php /path/to/wordpress/
```

### 2. パーミッション設定
```bash
chmod 644 dmm-image-proxy.php
mkdir /path/to/wordpress/cache
chmod 755 /path/to/wordpress/cache
```

### 3. .htaccessの設定（オプション）
```apache
# WordPressのルートディレクトリの.htaccessに追加
<Files "dmm-image-proxy.php">
    <RequireAll>
        Require all granted
    </RequireAll>
</Files>

# キャッシュディレクトリを保護
<Directory "cache">
    Deny from all
</Directory>
```

## 使用方法

### Python（ArticleGenerator）での使用
```python
# 自動的にプロキシURLに変換されます
article_generator = ArticleGenerator(wp_api, proxy_base_url="https://your-site.com/dmm-image-proxy.php")
```

### 手動でのプロキシURL生成
```python
import base64
import urllib.parse

original_url = "https://doujin-assets.dmm.co.jp/digital/comic/example.jpg"
encoded_url = base64.b64encode(original_url.encode('utf-8')).decode('utf-8')
proxy_url = f"https://your-site.com/dmm-image-proxy.php?url={urllib.parse.quote(encoded_url)}"
```

## セキュリティ機能

### 1. ドメイン制限
- `doujin-assets.dmm.co.jp`
- `pics.dmm.co.jp`
- `doujin-assets.dmm.com`
- `pics.dmm.com`

### 2. MIMEタイプ検証
- `image/jpeg`
- `image/png`
- `image/gif`
- `image/webp`

### 3. セキュリティヘッダー
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

### 4. キャッシュシステム
- 24時間のファイルキャッシュ
- MD5ハッシュによるファイル名生成
- 自動的な期限切れ処理

## トラブルシューティング

### 画像が表示されない場合
1. プロキシファイルのパーミッションを確認
2. キャッシュディレクトリの書き込み権限を確認
3. エラーログを確認

### パフォーマンス問題
1. キャッシュディレクトリの容量を確認
2. 古いキャッシュファイルを定期的に削除

### セキュリティ監査
1. 許可ドメインリストを定期的に見直し
2. アクセスログを監視
3. 不正利用の検出

## メンテナンス

### キャッシュクリア
```bash
# 古いキャッシュファイルを削除（7日以上古いファイル）
find /path/to/wordpress/cache -name "*.cache" -mtime +7 -delete
```

### ログ監視
```bash
# エラーログの確認
tail -f /var/log/apache2/error.log | grep "DMM Image Proxy"
```

## 更新履歴
- v1.0: 初期リリース
- セキュリティ機能追加
- キャッシュシステム実装
- エラーハンドリング強化