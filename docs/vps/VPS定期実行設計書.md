# VPS定期実行システム設計書

## 📋 **実行要件**

### **投稿スケジュール**
- **投稿数**: 96件/日
- **実行間隔**: 15分刻み（24時間で96回実行）
- **1回の投稿数**: 1件/実行
- **実行時間**: 00:00, 00:15, 00:30, 00:45, ... 23:45

### **技術的要件**
- **プラットフォーム**: VPS（Ubuntu/CentOS想定）
- **スケジューラー**: cron
- **Python**: 3.8以上
- **ログ管理**: 日次ローテーション
- **エラーハンドリング**: 失敗時の再試行

## 🕐 **実行スケジュール詳細**

### **1日の実行パターン**
```
00:00 → 記事1投稿
00:15 → 記事2投稿
00:30 → 記事3投稿
...
23:30 → 記事95投稿
23:45 → 記事96投稿
```

### **cron設定**
```bash
# 15分毎に実行（1日96回）
*/15 * * * * /path/to/vps_auto_posting.sh >> /path/to/logs/cron.log 2>&1
```

## 🔧 **システム構成**

### **ディレクトリ構造**
```
/opt/blog-automation/
├── app/                    # アプリケーションコード
├── config/                 # 設定ファイル
│   ├── config.vps.ini     # VPS専用設定
│   └── config.local.ini   # ローカル設定（gitignore）
├── logs/                   # ログファイル
│   ├── daily/             # 日次ログ
│   └── error/             # エラーログ
├── scripts/               # 実行スクリプト
│   ├── vps_auto_posting.sh
│   ├── setup_cron.sh
│   └── health_check.sh
├── data/                  # データファイル
└── cache/                 # キャッシュディレクトリ
```

## 📊 **パフォーマンス考慮事項**

### **API制限対策**
- **DMM API**: 1日1000回制限 → 96回実行で余裕
- **WordPress API**: 制限なし（自サーバー）
- **Gemini API**: 1日制限内で運用

### **サーバーリソース**
- **CPU**: 低負荷（記事生成時のみ高負荷）
- **メモリ**: 512MB以上推奨
- **ディスク**: ログ・キャッシュ用に1GB以上
- **ネットワーク**: 安定した接続必須

## 🛡️ **信頼性・監視**

### **エラーハンドリング**
- **API障害**: 3回リトライ後スキップ
- **ネットワーク障害**: 指数バックオフでリトライ
- **記事不足**: 検索範囲拡大で対応

### **監視項目**
- **実行成功率**: 90%以上維持
- **API応答時間**: 平均5秒以内
- **投稿品質**: レビューありの記事比率
- **エラー発生頻度**: 1日10件以下

### **アラート設定**
- **連続失敗**: 3回連続失敗でメール通知
- **API制限**: 制限近接でSlack通知
- **ディスク容量**: 80%超過で警告

## 🔄 **運用フロー**

### **日次メンテナンス**
```bash
# 自動実行（cronで設定）
0 0 * * * /opt/blog-automation/scripts/daily_maintenance.sh
```

1. **ログローテーション**
2. **キャッシュクリーンアップ**
3. **統計レポート生成**
4. **ヘルスチェック実行**

### **週次メンテナンス**
```bash
# 毎週日曜日 2:00実行
0 2 * * 0 /opt/blog-automation/scripts/weekly_maintenance.sh
```

1. **システムアップデート確認**
2. **ログアーカイブ**
3. **パフォーマンス分析**
4. **設定最適化**

## 📈 **スケーリング計画**

### **段階的拡張**
1. **Phase 1**: 96件/日（現在の目標）
2. **Phase 2**: 144件/日（10分間隔）
3. **Phase 3**: 288件/日（5分間隔）

### **制約事項**
- **API制限**: DMM 1000回/日が上限
- **サーバー負荷**: 記事生成処理のCPU使用率
- **WordPress**: 大量投稿時のパフォーマンス

## 🚀 **デプロイ手順**

### **1. サーバー準備**
```bash
# 必要パッケージインストール
sudo apt update
sudo apt install python3 python3-pip git cron

# プロジェクトクローン
cd /opt
sudo git clone https://github.com/suno345/-WordPress-automatic-posting.git blog-automation
```

### **2. 環境設定**
```bash
# Python依存関係インストール
cd /opt/blog-automation
sudo pip3 install -r requirements.txt

# 設定ファイル作成
sudo cp config/config.ini config/config.vps.ini
# config.vps.ini を編集
```

### **3. cron設定**
```bash
# cron設定を追加
sudo crontab -e
# */15 * * * * /opt/blog-automation/scripts/vps_auto_posting.sh
```

### **4. 権限設定**
```bash
# 実行権限付与
sudo chmod +x scripts/*.sh
sudo chown -R www-data:www-data /opt/blog-automation
```

## 📝 **設定例**

### **config.vps.ini**
```ini
[wordpress]
url = https://your-blog.com
username = automatic
password = your-secure-password

[dmm_api]
api_id = your-dmm-api-id
affiliate_id = your-affiliate-id

[gemini]
api_key = your-gemini-api-key

[system]
log_level = INFO
max_posts_per_run = 1        # VPS用: 1記事/実行
retry_attempts = 3
request_delay = 2.0
cache_enabled = true
vps_mode = true              # VPS最適化フラグ
```

## 🎯 **成功指標**

### **KPI目標**
- **投稿成功率**: 95%以上
- **平均実行時間**: 3分以内
- **API制限回避**: 制限の80%以内で運用
- **サーバー稼働率**: 99.5%以上

### **品質指標**
- **レビューあり記事比率**: 70%以上
- **記事の重複率**: 5%以下
- **画像表示成功率**: 95%以上
- **SEO最適化記事比率**: 90%以上

このシステムにより、安定した96件/日の自動投稿を実現します！