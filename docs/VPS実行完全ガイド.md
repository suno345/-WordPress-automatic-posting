# VPS実行完全ガイド

## 🎯 **システム概要**

**レビュー条件**: 1件以上のレビュー付き商品対象  
**前倒し投稿**: 複数商品発見時に2分後から15分間隔で即座投稿  
**通常投稿**: 単一商品時は翌日の予定時刻で投稿  

---

## 🚀 **VPS初期セットアップ（完全自動化）**

### **Step 1: プロジェクトのクローンと基本設定**
```bash
# VPSにSSH接続
ssh your_username@your_vps_ip

# プロジェクト用ディレクトリ作成
sudo mkdir -p /opt/blog-automation
sudo chown $USER:$USER /opt/blog-automation
cd /opt/blog-automation

# GitHubからクローン
git clone https://github.com/suno345/-WordPress-automatic-posting.git .

# Python環境セットアップ
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Step 2: 自動初期化実行**
```bash
# VPS初期セットアップスクリプト実行（全自動）
./scripts/vps_setup.sh
```

**このスクリプトが実行する内容**:
- ✅ 必要ディレクトリ自動作成（`data/schedule`, `locks`, `logs`等）
- ✅ 適切な権限設定（ログ755、ロック700、暗号化キー600）
- ✅ 環境変数設定ファイル作成（`.vps_env`）
- ✅ Python環境とネットワーク接続確認
- ✅ 全スクリプトに実行権限付与

---

## 🔐 **WordPress認証設定**

### **Step 3: アプリケーションパスワード作成**
1. **WordPress管理画面にログイン**
   ```
   URL: https://mania-wiki.com/wp-admin
   ユーザー名: automatic
   ```

2. **アプリケーションパスワード生成**
   ```
   ユーザー > プロフィール > 「アプリケーションパスワード」
   → 「新しいアプリケーションパスワード名」: 「VPS自動投稿システム」
   → 「新しいアプリケーションパスワードを追加」をクリック
   ```

3. **設定ファイル更新**
   ```bash
   nano config/config.vps.ini
   # [wordpress]セクションのpasswordを更新
   password = [生成されたアプリケーションパスワード]
   ```

### **Step 4: 認証テスト実行**
```bash
# WordPress認証診断実行
python scripts/wordpress_auth_diagnostic.py
```

**期待される出力**:
```
🎯 診断結果サマリー
実行テスト数: 5
成功テスト数: 5
成功率: 100.0%

🎉 すべてのテストに合格しました！
```

---

## ⏰ **cron設定と運用開始**

### **Step 5: 自動cron設定**
```bash
# cron設定スクリプト実行（全自動）
./scripts/setup_cron.sh
```

**設定される内容**:
- ✅ **15分間隔実行**: `*/15 * * * *` で96回/日
- ✅ **予約投稿実行**: `execute_scheduled_posts.py --vps-mode`
- ✅ **新規記事生成**: `main.py --vps-mode` 毎時0分実行
- ✅ **日次メンテナンス**: ログローテーション、統計レポート
- ✅ **ヘルスチェック**: システム監視とアラート

### **Step 6: システム稼働確認**
```bash
# 接続テスト実行
python main.py --vps-mode --test-connections

# 手動テスト投稿実行
python main.py --vps-mode --verbose

# 予約投稿状況確認
python execute_scheduled_posts.py --status --vps-mode
```

---

## 📊 **新機能：前倒し投稿システム**

### **動作パターン**

#### **パターン1: 単一商品発見時（従来通り）**
```
実行時刻: 15:00
→ 1件のレビュー付き商品発見
→ 翌日 00:XX に投稿予約（通常スケジュール）
```

#### **パターン2: 複数商品発見時（新機能）**
```
実行時刻: 15:00  
→ 3件のレビュー付き商品発見
→ 15:02, 15:17, 15:32 に即座投稿予約（前倒しスケジュール）
```

### **ログ出力例**
```
2025-08-02 15:00:12 - 複数作品発見（3件）- 前倒し投稿を実行します
2025-08-02 15:02:01 - 前倒し投稿スケジュール作成: 3件
2025-08-02 15:02:01 - 投稿予定時刻: 2025-08-02 15:02から15分間隔
```

---

## 🛠️ **運用コマンド集**

### **システム監視**
```bash
# リアルタイムログ監視
tail -f /opt/blog-automation/logs/cron.log

# 今日の投稿状況確認
cat /opt/blog-automation/logs/daily/auto_posting_$(date +%Y-%m-%d).log

# 予約投稿状況確認
python execute_scheduled_posts.py --status --vps-mode

# システム全体状況確認
python main.py --vps-mode --status
```

### **手動操作**
```bash
# 緊急時の手動投稿実行
python execute_scheduled_posts.py --vps-mode

# 最大3件まで連続投稿（遅延回復用）
python execute_scheduled_posts.py --multiple 3 --vps-mode

# 失敗投稿の回復処理
python execute_scheduled_posts.py --recover-failed --vps-mode

# 新規記事検索・生成の手動実行
python main.py --vps-mode --verbose
```

### **メンテナンス**
```bash
# cron設定確認
crontab -l

# システム再起動
sudo systemctl restart cron

# ログ容量確認
du -sh /opt/blog-automation/logs/

# 手動ログローテーション
find /opt/blog-automation/logs -name "*.log" -mtime +7 -delete
```

---

## 📈 **監視とアラート**

### **自動監視項目**
- ✅ **成功率監視**: 90%下回り時アラート
- ✅ **ディスク使用量**: 80%超過時アラート
- ✅ **実行時間監視**: 300秒超過時タイムアウト
- ✅ **連続失敗監視**: 3回連続失敗時アラート

### **ヘルスチェック結果例**
```
過去24時間の成功率: 96.8% (成功: 93, 失敗: 3)
現在のディスク使用率: 45%
予約投稿総数: 12件
次の投稿予定: 2025-08-02 16:00
```

---

## ⚡ **高度な運用設定**

### **環境変数カスタマイズ**
```bash
# ~/.bashrc または /etc/environment に追加
export BLOG_AUTOMATION_ROOT="/opt/blog-automation"
export VPS_MODE="true"
export PYTHON_PATH="/usr/bin/python3"
```

### **systemd サービス化（オプション）**
```bash
# systemd用サービスファイル作成
sudo tee /etc/systemd/system/blog-automation.service << EOF
[Unit]
Description=WordPress Blog Automation System
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/opt/blog-automation
ExecStart=/opt/blog-automation/venv/bin/python execute_scheduled_posts.py --vps-mode
Restart=always
RestartSec=900

[Install]
WantedBy=multi-user.target
EOF

# サービス有効化
sudo systemctl enable blog-automation
sudo systemctl start blog-automation
```

---

## 🔧 **トラブルシューティング**

### **よくある問題と解決方法**

#### **WordPress 401認証エラー**
```bash
# 診断実行
python scripts/wordpress_auth_diagnostic.py

# アプリケーションパスワード再生成
# config/config.vps.iniのパスワード更新
```

#### **Python ModuleNotFoundError**
```bash
# 仮想環境の再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### **権限エラー**
```bash
# 権限の再設定
./scripts/vps_setup.sh
```

#### **ディスク容量不足**
```bash
# 古いログファイル削除
find /opt/blog-automation/logs -name "*.log" -mtime +7 -delete

# 手動ログローテーション
./scripts/log_rotation.sh
```

---

## 🎉 **運用開始確認チェックリスト**

### **初期設定完了確認**
- [ ] ✅ プロジェクトクローン完了
- [ ] ✅ Python仮想環境作成・依存関係インストール完了
- [ ] ✅ VPS初期セットアップスクリプト実行完了
- [ ] ✅ WordPressアプリケーションパスワード設定完了
- [ ] ✅ 認証診断テスト100%合格
- [ ] ✅ cron設定完了

### **システム動作確認**
- [ ] ✅ 手動テスト投稿成功
- [ ] ✅ 予約投稿システム動作確認
- [ ] ✅ ログ出力正常
- [ ] ✅ エラーハンドリング動作確認

### **24時間後確認項目**
- [ ] ✅ 96回のcron実行確認
- [ ] ✅ 投稿成功率90%以上
- [ ] ✅ ログファイルサイズ適正
- [ ] ✅ WordPress予約投稿作成確認

---

## 📞 **サポート情報**

### **ログファイル場所**
- **cron実行ログ**: `/opt/blog-automation/logs/cron.log`
- **日次ログ**: `/opt/blog-automation/logs/daily/`
- **エラーログ**: `/opt/blog-automation/logs/error/`

### **設定ファイル**
- **VPS設定**: `/opt/blog-automation/config/config.vps.ini`
- **環境変数**: `/opt/blog-automation/.vps_env`

### **重要コマンド**
```bash
# 緊急停止
crontab -r

# システム状態確認
python /opt/blog-automation/main.py --vps-mode --status

# 予約投稿状況確認
python /opt/blog-automation/execute_scheduled_posts.py --status --vps-mode
```

---

**🚀 システム準備完了！前倒し投稿機能付きで96件/日の自動投稿開始！**