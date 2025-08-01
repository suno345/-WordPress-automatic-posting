# VPSへのGit経由移管手順書

## 🎯 **移管概要**

**目標**: ローカルで動作確認済みのWordPress自動投稿システムをVPSに移管し、15分間隔での定期実行を開始

---

## 📋 **移管前チェックリスト**

### ✅ **ローカル動作確認**
- [x] 接続テスト成功
- [x] 記事生成・投稿テスト成功  
- [x] 15分間隔スケジューリング動作確認
- [x] セキュリティ改善実装完了

### ✅ **Git準備**
- [x] 最新コードをGitHubにプッシュ済み
- [x] 環境変数設定例（.env.example）準備済み
- [x] VPS用設定ファイル（config.vps.ini）準備済み

---

## 🖥️ **VPS側での移管手順**

### **Step 1: VPSへSSH接続**
```bash
# VPSにSSH接続
ssh your_username@your_vps_ip

# 作業ディレクトリの作成
sudo mkdir -p /opt/blog-automation
sudo chown $USER:$USER /opt/blog-automation
cd /opt/blog-automation
```

### **Step 2: 必要パッケージのインストール**
```bash
# Python 3.8以上のインストール確認
python3 --version

# pipの更新
sudo apt update
sudo apt install -y python3-pip python3-venv git curl

# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate

# 仮想環境の有効化確認
which python
```

### **Step 3: GitHubからコードをクローン**
```bash
# リポジトリのクローン
git clone https://github.com/suno345/-WordPress-automatic-posting.git .

# ブランチの確認
git branch -v

# 最新の状態に更新
git pull origin main
```

### **Step 4: Python依存関係のインストール**
```bash
# 仮想環境の有効化
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# インストール確認
pip list
```

### **Step 5: 環境変数の設定**
```bash
# 環境変数ファイルの作成
cp .env.example .env

# セキュアな権限設定
chmod 600 .env

# 環境変数の編集
nano .env
```

#### **設定内容例**:
```bash
# WordPress設定
WORDPRESS_URL=https://mania-wiki.com
WORDPRESS_USERNAME=automatic
WORDPRESS_PASSWORD=your_secure_password

# DMM API設定
DMM_API_ID=your_dmm_api_id
DMM_AFFILIATE_ID=your_dmm_affiliate_id

# Gemini API設定
GEMINI_API_KEY=your_gemini_api_key

# VPS最適化設定
VPS_MODE=true
LOG_LEVEL=INFO
MAX_POSTS_PER_RUN=1
SEARCH_LIMIT=200
REQUEST_DELAY=3.0
```

### **Step 6: ディレクトリ構造の準備**
```bash
# データディレクトリの作成
mkdir -p data logs

# 権限設定
chmod 755 data logs

# 設定ファイルの確認
ls -la config/

# VPS設定ファイルの存在確認
cat config/config.vps.ini
```

### **Step 7: 接続テストの実行**
```bash
# 仮想環境の有効化
source venv/bin/activate

# VPSモードでの接続テスト
python main.py --vps-mode --test-connections

# システム状態の確認
python main.py --vps-mode --status
```

### **Step 8: 手動テスト実行**
```bash
# 1回だけテスト実行
python main.py --vps-mode --verbose

# ログの確認
tail -f logs/auto_posting_*.log
```

---

## ⏰ **cron設定（定期実行）**

### **Step 9: cron設定ファイルの準備**
```bash
# cron設定用スクリプトの実行権限付与
chmod +x scripts/setup_cron.sh
chmod +x scripts/vps_auto_posting.sh

# cron設定の実行
./scripts/setup_cron.sh
```

### **Step 10: cron動作確認**
```bash
# cron設定の確認
crontab -l

# 出力例:
# */15 * * * * /opt/blog-automation/scripts/vps_auto_posting.sh >> /opt/blog-automation/logs/cron.log 2>&1

# cronサービスの状態確認
sudo systemctl status cron

# 手動でcronスクリプトテスト
./scripts/vps_auto_posting.sh
```

---

## 📊 **監視・ログ確認**

### **リアルタイムログ監視**
```bash
# メインログの監視
tail -f logs/auto_posting_$(date +%Y%m%d).log

# cronログの監視
tail -f logs/cron.log

# エラーログの確認
grep -i error logs/auto_posting_*.log
```

### **WordPress投稿確認**
```bash
# 最新の投稿確認用コマンド
python main.py --vps-mode --status

# 投稿履歴ファイルの確認
cat data/posted_works.json
```

---

## 🔧 **トラブルシューティング**

### **よくある問題と解決方法**

#### **1. 環境変数が読み込まれない**
```bash
# .envファイルの確認
cat .env

# 権限の確認
ls -la .env

# 手動での環境変数設定
export WORDPRESS_PASSWORD="your_password"
```

#### **2. Python依存関係エラー**
```bash
# 仮想環境の再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### **3. cron実行エラー**
```bash
# cronログの詳細確認
tail -50 logs/cron.log

# 手動実行でのデバッグ
cd /opt/blog-automation
source venv/bin/activate
python main.py --vps-mode --verbose
```

#### **4. ディスク容量不足**
```bash
# ディスク使用量確認
df -h

# ログローテーション設定
sudo logrotate -f /etc/logrotate.conf
```

---

## 📈 **運用開始後の確認事項**

### **初日の確認項目**
- [ ] 15分間隔でcronが正常実行されている
- [ ] WordPressに予約投稿が作成されている  
- [ ] エラーログに問題がない
- [ ] 投稿時刻が正確（00:00, 00:15, 00:30...）

### **1週間後の確認項目**
- [ ] 96記事/日のペースで投稿されている
- [ ] ログファイルサイズが適切
- [ ] システムリソース使用量が正常
- [ ] 重複投稿が発生していない

### **継続的な監視**
```bash
# 日次統計確認スクリプト
./scripts/daily_maintenance.sh

# 週次ヘルスチェック
./scripts/health_check.sh
```

---

## 🎉 **移管完了確認**

### **成功の指標**
1. ✅ **cron実行**: 15分間隔で正常実行
2. ✅ **投稿生成**: 予約投稿が正確な時刻で作成
3. ✅ **ログ出力**: エラーなしで動作
4. ✅ **リソース**: CPU・メモリ使用量が正常範囲

### **最終確認コマンド**
```bash
# 総合ステータス確認
python main.py --vps-mode --status

# 最近24時間のログサマリー
grep -c "投稿完了" logs/auto_posting_$(date +%Y%m%d).log

# cron実行回数確認（1日=96回）
grep -c "WordPress自動投稿システム開始" logs/auto_posting_$(date +%Y%m%d).log
```

**移管完了！15分間隔96記事/日の自動投稿システムが稼働開始 🚀**