# VPS定期実行デプロイガイド

## 概要
WordPress自動投稿システムをVPS環境でGit経由でデプロイし、cron定期実行する手順です。

## 前提条件
- Ubuntu/CentOS等のLinux VPS
- Python 3.8以上がインストール済み
- Git がインストール済み
- 必要なAPIキー・認証情報が準備済み

## 1. VPS環境でのGitクローン

### リポジトリクローン
```bash
# VPSにSSHログイン
ssh user@your-vps-ip

# ホームディレクトリに移動
cd ~

# リポジトリをクローン
git clone https://github.com/your-username/doujin-blog-automation.git

# プロジェクトディレクトリに移動
cd doujin-blog-automation
```

### 権限設定
```bash
# 実行権限を付与
chmod +x execute_scheduled_posts.py
chmod +x main.py
chmod +x scripts/wordpress_auth_diagnostic.py
```

## 2. Python環境構築

### 仮想環境作成
```bash
# 仮想環境作成
python3 -m venv venv

# 仮想環境有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### システムパッケージ（必要に応じて）
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv git

# CentOS/RHEL
sudo yum update
sudo yum install python3-pip python3-venv git
```

## 3. .env ファイル設定

### .envファイル作成
```bash
# .env.example をコピー
cp .env.example .env

# エディタで編集
nano .env
```

### .env設定内容
```bash
# WordPress設定（実際の値に置き換えてください）
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_PASSWORD=your_application_password

# DMM API設定
DMM_API_ID=your_dmm_api_id
DMM_AFFILIATE_ID=your_affiliate_id

# Gemini AI設定
GEMINI_API_KEY=your_gemini_api_key
```

### セキュリティ設定
```bash
# .envファイルの権限を制限
chmod 600 .env

# .envファイルがGitにコミットされないことを確認
git status
# .env が表示されないことを確認
```

## 4. 初期テスト実行

### 接続テスト
```bash
# 仮想環境が有効化されていることを確認
source venv/bin/activate

# VPSモードで接続テスト
python main.py --vps-mode --test-connections
```

### WordPress認証診断
```bash
# WordPress認証の詳細診断
python scripts/wordpress_auth_diagnostic.py
```

### 予約投稿状況確認
```bash
# 現在の予約投稿状況を確認
python execute_scheduled_posts.py --vps-mode --status
```

## 5. cron設定（15分間隔実行）

### crontab編集
```bash
# crontabを編集
crontab -e
```

### cron設定内容
```bash
# WordPress自動投稿システム - 15分間隔実行
# 毎日15分刻みで96回実行（24時間 × 4回/時間 = 96回）
*/15 * * * * /home/your-username/doujin-blog-automation/venv/bin/python /home/your-username/doujin-blog-automation/execute_scheduled_posts.py --vps-mode --multiple 3 >> /home/your-username/doujin-blog-automation/logs/cron.log 2>&1

# 毎日0時にシステム状況をログ出力
0 0 * * * /home/your-username/doujin-blog-automation/venv/bin/python /home/your-username/doujin-blog-automation/execute_scheduled_posts.py --vps-mode --status >> /home/your-username/doujin-blog-automation/logs/daily_status.log 2>&1

# 毎週日曜日3時にGitプル（自動更新）
0 3 * * 0 cd /home/your-username/doujin-blog-automation && git pull origin main >> /home/your-username/doujin-blog-automation/logs/git_update.log 2>&1
```

### パス設定の注意点
**重要**: 上記の `/home/your-username/doujin-blog-automation` は実際のパスに置き換えてください：

```bash
# 現在のパスを確認
pwd
# 例: /home/ubuntu/doujin-blog-automation

# 実際のユーザー名を確認
whoami
# 例: ubuntu
```

## 6. ログディレクトリ作成

### ログディレクトリ準備
```bash
# ログディレクトリ作成
mkdir -p logs

# ログファイルの権限設定
touch logs/cron.log
touch logs/daily_status.log
touch logs/git_update.log
chmod 644 logs/*.log
```

## 7. 動作確認

### 手動実行テスト
```bash
# 仮想環境有効化
source venv/bin/activate

# VPSモードで1回実行
python execute_scheduled_posts.py --vps-mode

# 複数投稿テスト（最大3件）
python execute_scheduled_posts.py --vps-mode --multiple 3
```

### cron動作確認
```bash
# cron設定確認
crontab -l

# cronサービス状態確認
sudo systemctl status cron  # Ubuntu/Debian
sudo systemctl status crond  # CentOS/RHEL

# ログ確認
tail -f logs/cron.log
```

## 8. 監視・メンテナンス

### ログローテーション設定
```bash
# logrotate設定ファイル作成
sudo nano /etc/logrotate.d/doujin-blog-automation
```

```
/home/your-username/doujin-blog-automation/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 your-username your-username
}
```

### 定期メンテナンススクリプト
```bash
# メンテナンススクリプト作成
nano scripts/maintenance.sh
```

```bash
#!/bin/bash
# 定期メンテナンススクリプト

cd /home/your-username/doujin-blog-automation

# Git更新
git pull origin main

# Python依存関係更新
source venv/bin/activate
pip install -r requirements.txt --upgrade

# システム状況確認
python execute_scheduled_posts.py --vps-mode --status

echo "Maintenance completed: $(date)"
```

## 9. トラブルシューティング

### よくある問題と解決方法

#### 1. 権限エラー
```bash
# Python実行権限確認
ls -la execute_scheduled_posts.py
chmod +x execute_scheduled_posts.py
```

#### 2. 仮想環境エラー
```bash
# 仮想環境再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. cron実行されない
```bash
# cronログ確認
sudo tail -f /var/log/cron    # CentOS
sudo tail -f /var/log/syslog  # Ubuntu

# cron再起動
sudo systemctl restart cron   # Ubuntu
sudo systemctl restart crond  # CentOS
```

#### 4. 環境変数読み込みエラー
```bash
# .envファイル確認
cat .env

# 権限確認
ls -la .env

# パス確認
pwd
which python3
```

## 10. セキュリティ考慮事項

### ファイアウォール設定
```bash
# 必要最小限のポート開放のみ
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### 定期バックアップ
```bash
# データベースバックアップ
# crontabに追加
0 2 * * * cp /home/your-username/doujin-blog-automation/data/posts.db /home/your-username/backups/posts_$(date +\%Y\%m\%d).db
```

### ログ監視
```bash
# 異常ログの監視
# crontabに追加
0 1 * * * grep -i "error\|failed\|exception" /home/your-username/doujin-blog-automation/logs/*.log | mail -s "Auto Posting System Errors" your-email@example.com
```

## 11. パフォーマンス最適化

### システムリソース監視
```bash
# リソース使用量確認
htop
df -h
free -h

# Python プロセス確認
ps aux | grep python
```

### ログサイズ管理
```bash
# 大きくなったログファイルの確認
du -sh logs/*

# 古いログの自動削除
# crontabに追加
0 4 * * * find /home/your-username/doujin-blog-automation/logs -name "*.log" -mtime +30 -delete
```

---

## 実行コマンド例

### 即座に開始する場合
```bash
# VPSにSSHログイン後
cd ~/doujin-blog-automation
source venv/bin/activate
python execute_scheduled_posts.py --vps-mode --multiple 3
```

### システム状況確認
```bash
python execute_scheduled_posts.py --vps-mode --status
```

### 緊急停止が必要な場合
```bash
# cronを一時停止
crontab -e
# 該当行をコメントアウト（先頭に#を追加）

# 実行中プロセス確認・停止
ps aux | grep execute_scheduled_posts
kill [PID]
```

この設定により、VPS環境で15分間隔での自動投稿システムが継続動作します。