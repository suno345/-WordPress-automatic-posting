#!/bin/bash
# VPS クイックデプロイスクリプト
# Git経由でのワンコマンドデプロイ

set -e

print_status() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

echo "🚀 WordPress自動投稿システム クイックデプロイ"
echo "============================================="

# 引数チェック
if [ $# -eq 0 ]; then
    print_error "使用方法: ./scripts/quick_deploy.sh <GitリポジトリURL>"
    echo "例: ./scripts/quick_deploy.sh https://github.com/username/doujin-blog-automation.git"
    exit 1
fi

REPO_URL="$1"
PROJECT_NAME=$(basename "$REPO_URL" .git)
PROJECT_PATH="$HOME/$PROJECT_NAME"

print_info "リポジトリURL: $REPO_URL"
print_info "プロジェクト名: $PROJECT_NAME"
print_info "インストール先: $PROJECT_PATH"

# 既存プロジェクトの確認
if [ -d "$PROJECT_PATH" ]; then
    print_info "既存プロジェクトが見つかりました。更新します..."
    cd "$PROJECT_PATH"
    git pull origin main
    print_status "プロジェクト更新完了"
else
    print_info "新規プロジェクトをクローンします..."
    cd "$HOME"
    git clone "$REPO_URL"
    print_status "プロジェクトクローン完了"
fi

cd "$PROJECT_PATH"

# セットアップスクリプト実行
print_info "VPSセットアップを実行中..."
chmod +x scripts/vps_setup.sh
./scripts/vps_setup.sh

print_status "クイックデプロイ完了！"
echo ""
echo "次の手順:"
echo "1. .envファイルを編集してAPI情報を設定"
echo "   cd $PROJECT_PATH"
echo "   nano .env"
echo ""
echo "2. 接続テスト実行"
echo "   source venv/bin/activate"
echo "   python main.py --vps-mode --test-connections"
echo ""
echo "3. cron設定"
echo "   crontab -e"
echo "   # scripts/cron_template.txt の内容を参考に設定"
echo ""
echo "4. 自動投稿開始"
echo "   python execute_scheduled_posts.py --vps-mode --multiple 3"