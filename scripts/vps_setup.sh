#!/bin/bash
# VPS環境セットアップスクリプト - Git連携版
# 使用方法: chmod +x scripts/vps_setup.sh && ./scripts/vps_setup.sh

set -e  # エラー時に停止

# 色付きエコー関数
print_status() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

# プロジェクトルートを現在のディレクトリに設定
PROJECT_ROOT="$(pwd)"
PYTHON_PATH="/usr/bin/env python3"

echo "🚀 WordPress自動投稿システム VPSセットアップ開始"
echo "=================================================="

# システム情報表示
print_info "システム情報:"
echo "  OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')"
echo "  Python: $(python3 --version)"
echo "  Git: $(git --version)"
echo "  現在位置: $PROJECT_ROOT"
echo ""

# 必要ディレクトリの作成
print_info "必要なディレクトリを作成中..."
mkdir -p logs data backups

print_status "ディレクトリ作成完了"

# Python仮想環境作成
print_info "Python仮想環境をセットアップ中..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "仮想環境作成完了"
else
    print_info "仮想環境は既に存在します"
fi

# 仮想環境有効化
source venv/bin/activate
print_status "仮想環境有効化完了"

# 依存関係インストール
print_info "Python依存関係をインストール中..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "依存関係インストール完了"

# 実行権限付与
print_info "実行権限を設定中..."
chmod +x main.py
chmod +x execute_scheduled_posts.py
chmod +x scripts/wordpress_auth_diagnostic.py
print_status "実行権限設定完了"

# .envファイル確認
print_info ".envファイルを確認中..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_info ".env.example から .env を作成しました"
        echo ""
        print_error "重要: .envファイルに実際のAPI情報を設定してください"
        echo "編集コマンド: nano .env"
        echo ""
    else
        print_error ".env.example ファイルが見つかりません"
        exit 1
    fi
else
    print_status ".envファイル確認済み"
fi

# .envファイル権限設定
chmod 600 .env
print_status ".envファイル権限設定完了 (600)"

# 接続テスト準備
print_info "システム接続テストの準備完了"
echo ""
echo "次のステップ:"
echo "1. .envファイルに実際のAPI情報を設定"
echo "   nano .env"
echo ""
echo "2. 接続テスト実行"
echo "   python main.py --vps-mode --test-connections"
echo ""
echo "3. WordPress認証診断"
echo "   python scripts/wordpress_auth_diagnostic.py"
echo ""
echo "4. cron設定"
echo "   crontab -e"
echo ""

# cron設定例を表示
print_info "cron設定例（実際のパスに修正してください）:"
echo "現在のパス: $PROJECT_ROOT"
echo ""
echo "crontab -e で以下を追加:"
echo "# 15分間隔で自動投稿実行"
echo "*/15 * * * * $PROJECT_ROOT/venv/bin/python $PROJECT_ROOT/execute_scheduled_posts.py --vps-mode --multiple 3 >> $PROJECT_ROOT/logs/cron.log 2>&1"
echo ""
echo "# 毎日0時にシステム状況確認"
echo "0 0 * * * $PROJECT_ROOT/venv/bin/python $PROJECT_ROOT/execute_scheduled_posts.py --vps-mode --status >> $PROJECT_ROOT/logs/daily_status.log 2>&1"
echo ""
echo "# 毎週日曜日3時にGit更新"
echo "0 3 * * 0 cd $PROJECT_ROOT && git pull origin main >> $PROJECT_ROOT/logs/git_update.log 2>&1"
echo ""

print_status "VPSセットアップ完了！"
echo "=================================================="