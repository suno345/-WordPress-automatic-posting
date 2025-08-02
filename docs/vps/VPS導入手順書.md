# VPS導入手順書

## 🎯 **導入概要**

15分間隔で96件/日の自動投稿を実現するVPSシステムの導入手順

### **実行スケジュール**
- **頻度**: 15分間隔（1日96回）
- **時間**: 00:00, 00:15, 00:30, ... 23:45
- **投稿数**: 1件/実行

---

## 🔧 **1. VPSサーバー準備**

### **推奨スペック**
- **OS**: Ubuntu 20.04 LTS / CentOS 8
- **CPU**: 1vCPU以上
- **メモリ**: 1GB以上
- **ストレージ**: 20GB以上
- **ネットワーク**: 安定した接続

### **初期設定**
```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# 必要パッケージインストール
sudo apt install -y python3 python3-pip git cron curl bc jq

# タイムゾーン設定（日本時間）
sudo timedatectl set-timezone Asia/Tokyo
```

---

## 📥 **2. プロジェクトクローン**

```bash
# プロジェクトディレクトリ作成
sudo mkdir -p /opt/blog-automation
sudo chown $USER:$USER /opt/blog-automation

# GitHubからクローン
cd /opt
sudo git clone https://github.com/suno345/-WordPress-automatic-posting.git blog-automation

# 所有者変更
sudo chown -R $USER:$USER /opt/blog-automation
```

---

## 🐍 **3. Python環境セットアップ**

```bash
cd /opt/blog-automation

# Python依存関係インストール
pip3 install -r requirements.txt

# 仮想環境作成（推奨）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ **4. 設定ファイル編集**

```bash
# VPS用設定ファイルを編集
nano config/config.vps.ini
```

**重要な設定項目**:
```ini
[wordpress]
url = https://your-blog.com          # あなたのブログURL
username = automatic                 # WordPress ユーザー名
password = your-app-password         # アプリケーションパスワード

[dmm_api]
api_id = your-dmm-api-id            # DMM API ID
affiliate_id = your-affiliate-id     # アフィリエイトID

[gemini]
api_key = your-gemini-api-key       # Gemini API キー

[settings]
max_posts_per_run = 1               # 1回の実行で1記事
search_limit = 200                  # 検索範囲を拡大
request_delay = 3                   # API制限対策
vps_mode = true                     # VPS最適化ON
```

---

## 🗂️ **5. ディレクトリ構造作成**

```bash
cd /opt/blog-automation

# 必要ディレクトリ作成
mkdir -p logs/daily logs/error backups cache data

# 権限設定
chmod 755 logs cache data backups
chmod 644 config/config.vps.ini
chmod +x scripts/*.sh
```

---

## ⏰ **6. cron設定**

### **自動設定（推奨）**
```bash
cd /opt/blog-automation
./scripts/setup_cron.sh
```

### **手動設定**
```bash
# crontabを編集
crontab -e

# 以下を追加
*/15 * * * * /opt/blog-automation/scripts/vps_auto_posting.sh >> /opt/blog-automation/logs/cron.log 2>&1
0 1 * * * /opt/blog-automation/scripts/daily_maintenance.sh >> /opt/blog-automation/logs/cron.log 2>&1
0 * * * * /opt/blog-automation/scripts/health_check.sh >> /opt/blog-automation/logs/cron.log 2>&1
```

---

## 🧪 **7. 動作テスト**

### **手動実行テスト**
```bash
cd /opt/blog-automation

# 1回だけ実行してテスト
./scripts/vps_auto_posting.sh

# ログ確認
tail -f logs/cron.log
```

### **設定確認**
```bash
# cron設定確認
crontab -l

# cronサービス状態確認
systemctl status cron

# 次回実行時刻確認
date
```

---

## 📊 **8. 監視・運用**

### **リアルタイム監視**
```bash
# 実行ログをリアルタイム表示
tail -f /opt/blog-automation/logs/cron.log

# 今日の実行状況確認
cat /opt/blog-automation/logs/daily/auto_posting_$(date +%Y-%m-%d).log
```

### **統計確認**
```bash
# 今日の成功・失敗数
wc -l /opt/blog-automation/logs/success_log_$(date +%Y-%m-%d).txt
wc -l /opt/blog-automation/logs/error_log_$(date +%Y-%m-%d).txt

# ヘルスチェック結果
tail -20 /opt/blog-automation/logs/health_check.log
```

### **手動メンテナンス**
```bash
# 日次メンテナンス手動実行
./scripts/daily_maintenance.sh

# ヘルスチェック手動実行
./scripts/health_check.sh
```

---

## 🚨 **9. トラブルシューティング**

### **よくある問題と対処法**

#### **問題1: cronが実行されない**
```bash
# cronサービス確認
systemctl status cron

# cronサービス開始
sudo systemctl start cron
sudo systemctl enable cron

# cron設定確認
crontab -l
```

#### **問題2: Python実行エラー**
```bash
# Pythonパス確認
which python3

# 依存関係再インストール
cd /opt/blog-automation
pip3 install -r requirements.txt --upgrade
```

#### **問題3: API接続エラー**
```bash
# ネットワーク接続確認
ping google.com

# API接続テスト
curl -s "https://api.dmm.com/"
curl -s "https://mania-wiki.com/wp-json/wp/v2/"
```

#### **問題4: ディスク容量不足**
```bash
# ディスク使用量確認
df -h

# 古いログ削除
find /opt/blog-automation/logs -name "*.log" -mtime +7 -delete

# 手動メンテナンス実行
./scripts/daily_maintenance.sh
```

#### **問題5: 重複投稿**
```bash
# posted_works.json確認
cat /opt/blog-automation/data/posted_works.json

# キャッシュクリア
rm -rf /opt/blog-automation/cache/*
```

---

## 📈 **10. パフォーマンス最適化**

### **高負荷時の対策**
```bash
# 設定ファイル調整
nano config/config.vps.ini

# 以下の値を調整
request_delay = 5        # API間隔を延長
max_workers = 1          # 並行処理数を削減
search_limit = 100       # 検索範囲を縮小
```

### **成功率向上の設定**
```bash
# リトライ設定強化
retry_attempts = 5
retry_delay = 120

# 検索範囲拡大
max_search_extend = 1000
```

---

## 🔒 **11. セキュリティ設定**

### **ファイル権限強化**
```bash
# 設定ファイルの権限制限
chmod 600 config/config.vps.ini

# スクリプトファイルの権限
chmod 755 scripts/*.sh

# ログディレクトリの権限
chmod 755 logs
```

### **定期的なセキュリティ更新**
```bash
# システム更新用cronを追加
echo "0 3 * * 0 apt update && apt upgrade -y" | sudo crontab -
```

---

## 📊 **12. 成功指標の確認**

### **目標値**
- **投稿成功率**: 95%以上
- **1日の投稿数**: 90件以上（96件中）
- **平均実行時間**: 3分以内
- **API制限回避**: 制限の80%以内

### **監視コマンド**
```bash
# 今日の成績確認
echo "成功: $(wc -l < logs/success_log_$(date +%Y-%m-%d).txt 2>/dev/null || echo 0)"
echo "失敗: $(wc -l < logs/error_log_$(date +%Y-%m-%d).txt 2>/dev/null || echo 0)"

# 週間サマリー
for i in {0..6}; do
  date=$(date -d "$i days ago" +%Y-%m-%d)
  success=$(wc -l < logs/success_log_$date.txt 2>/dev/null || echo 0)
  echo "$date: $success件"
done
```

---

## 🎉 **導入完了**

以上の手順で、15分間隔96件/日の自動投稿システムが稼働開始します！

### **確認事項**
- ✅ cronが15分間隔で実行されている
- ✅ ログが正常に出力されている  
- ✅ 記事が正常に投稿されている
- ✅ エラー率が10%以下である

### **運用開始後の週次確認**
1. **成功率確認** - 90%以上維持
2. **ログ確認** - エラーパターンの分析
3. **リソース確認** - CPU・メモリ・ディスク使用率
4. **記事品質確認** - 投稿された記事の品質

**安定した96件/日の自動投稿が実現されます！** 🚀