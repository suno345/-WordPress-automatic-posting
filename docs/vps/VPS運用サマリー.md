# VPS運用サマリー - 15分間隔96件投稿システム

## 🎯 **システム概要**

### **投稿スケジュール**
- **実行頻度**: 15分間隔（24時間で96回）
- **実行時刻**: 00:00, 00:15, 00:30, 00:45, ... 23:45
- **1回の投稿数**: 1件
- **1日の目標投稿数**: 96件

### **技術構成**
- **OS**: Ubuntu/CentOS
- **スケジューラー**: cron
- **メイン言語**: Python 3.8+
- **監視**: 自動ヘルスチェック
- **ログ管理**: 日次ローテーション

---

## 📁 **重要ファイル一覧**

### **設定ファイル**
- `config/config.vps.ini` - VPS専用設定（API情報、最適化設定）

### **実行スクリプト**
- `scripts/vps_auto_posting.sh` - メイン投稿スクリプト（15分毎実行）
- `scripts/setup_cron.sh` - cron設定自動化
- `scripts/health_check.sh` - システム監視（毎時実行）
- `scripts/daily_maintenance.sh` - 日次メンテナンス（毎日1時）

### **ドキュメント**
- `docs/VPS導入手順書.md` - 詳細導入手順
- `docs/VPS定期実行設計書.md` - システム設計詳細

---

## ⚙️ **cron設定内容**

```bash
# 15分毎の自動投稿（96回/日）
*/15 * * * * /opt/blog-automation/scripts/vps_auto_posting.sh >> /opt/blog-automation/logs/cron.log 2>&1

# 日次メンテナンス（毎日1時）
0 1 * * * /opt/blog-automation/scripts/daily_maintenance.sh >> /opt/blog-automation/logs/cron.log 2>&1

# ヘルスチェック（毎時）
0 * * * * /opt/blog-automation/scripts/health_check.sh >> /opt/blog-automation/logs/cron.log 2>&1
```

---

## 📊 **監視・統計機能**

### **リアルタイム監視**
- **実行ログ**: `tail -f logs/cron.log`
- **今日の詳細**: `cat logs/daily/auto_posting_$(date +%Y-%m-%d).log`
- **成功数**: `wc -l logs/success_log_$(date +%Y-%m-%d).txt`
- **失敗数**: `wc -l logs/error_log_$(date +%Y-%m-%d).txt`

### **自動統計生成**
- **成功率計算**: 自動的に計算・記録
- **パフォーマンス監視**: 実行時間・リソース使用率
- **アラート機能**: 連続失敗・API制限接近時の通知

---

## 🚀 **VPS導入手順（簡易版）**

### **1. 環境準備**
```bash
# パッケージインストール
sudo apt update && sudo apt install -y python3 python3-pip git cron curl bc jq

# プロジェクトクローン
sudo git clone https://github.com/suno345/-WordPress-automatic-posting.git /opt/blog-automation
sudo chown -R $USER:$USER /opt/blog-automation
```

### **2. Python環境**
```bash
cd /opt/blog-automation
pip3 install -r requirements.txt
```

### **3. 設定編集**
```bash
# VPS用設定ファイルを編集
nano config/config.vps.ini

# 必須項目:
# - WordPress URL/認証情報
# - DMM API情報  
# - Gemini API キー
```

### **4. cron設定**
```bash
# 自動設定実行
./scripts/setup_cron.sh

# または手動設定
crontab -e
# 上記cron設定内容を追加
```

### **5. 動作確認**
```bash
# テスト実行
./scripts/vps_auto_posting.sh

# ログ確認
tail -f logs/cron.log
```

---

## 📈 **成功指標・KPI**

### **目標値**
- **投稿成功率**: 95%以上
- **1日の投稿数**: 90件以上（96件中）
- **平均実行時間**: 3分以内
- **システム稼働率**: 99.5%以上

### **監視項目**
- **API制限回避**: DMM API 1000回/日制限の80%以内
- **エラー発生率**: 5%以下
- **レビューあり記事比率**: 70%以上
- **記事重複率**: 5%以下

---

## 🔧 **トラブルシューティング**

### **よくある問題**

#### **1. cronが動かない**
```bash
# サービス確認・開始
systemctl status cron
sudo systemctl start cron

# 設定確認
crontab -l
```

#### **2. API接続エラー**
```bash
# 接続テスト
curl -s "https://api.dmm.com/"
curl -s "https://mania-wiki.com/wp-json/wp/v2/"

# 設定ファイル確認
cat config/config.vps.ini
```

#### **3. ディスク容量不足**
```bash
# 容量確認
df -h

# 手動クリーンアップ
./scripts/daily_maintenance.sh
```

#### **4. 成功率低下**
```bash
# エラーログ確認
cat logs/error/error_$(date +%Y-%m-%d).log

# 設定調整（request_delay増加）
nano config/config.vps.ini
```

---

## 📝 **運用チェックリスト**

### **日次確認**
- [ ] 成功率が90%以上
- [ ] エラーログに重大な問題なし
- [ ] ディスク使用率80%以下
- [ ] 投稿された記事の品質確認

### **週次確認**
- [ ] システムアップデート確認
- [ ] ログファイルサイズ確認
- [ ] バックアップファイル確認
- [ ] パフォーマンス統計レビュー

### **月次確認**
- [ ] API使用量統計レビュー
- [ ] 設定最適化の検討
- [ ] セキュリティ更新確認
- [ ] システム拡張の検討

---

## 🎊 **運用開始**

以上の設定により、**15分間隔で96件/日の自動投稿システム**が稼働します！

### **最終確認コマンド**
```bash
# 全体状況確認
echo "=== VPS自動投稿システム状況 ==="
echo "設定ファイル: $(ls -la config/config.vps.ini)"
echo "cron設定: $(crontab -l | grep blog-automation | wc -l)件"
echo "今日の投稿: 成功$(wc -l < logs/success_log_$(date +%Y-%m-%d).txt 2>/dev/null || echo 0)件, 失敗$(wc -l < logs/error_log_$(date +%Y-%m-%d).txt 2>/dev/null || echo 0)件"
echo "次回実行: $(date -d '+15 minutes' '+%H:%M')"
```

**96件/日の安定した自動投稿が実現されます！** 🚀