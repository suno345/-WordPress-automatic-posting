#!/bin/bash

# VPS用15分間隔cron設定ワンライナー
# 使用方法: ssh member1@your-vps-ip "bash -s" < VPS_CRON_SETUP.sh

echo "=== VPS 15分間隔cron設定 開始 ==="

# プロジェクトルートディレクトリを自動検出
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$PROJECT_ROOT/execute_scheduled_posts.py" ]; then
    # wordpressディレクトリ内を想定
    PROJECT_ROOT="/opt/wordpress-auto-posting"
    if [ ! -f "$PROJECT_ROOT/execute_scheduled_posts.py" ]; then
        PROJECT_ROOT="/home/$(whoami)/wordpress-auto-posting"
    fi
fi

PYTHON_VENV="$PROJECT_ROOT/venv/bin/python"
MAIN_SCRIPT="$PROJECT_ROOT/execute_scheduled_posts.py"
LOG_FILE="$PROJECT_ROOT/logs/cron.log"

echo "プロジェクトルート: $PROJECT_ROOT"

# ログディレクトリ作成
mkdir -p "$PROJECT_ROOT/logs"

# 実行権限付与
chmod +x "$MAIN_SCRIPT"

# 一時ファイル作成
TEMP_CRON=$(mktemp)

# 既存のcrontab設定を保存
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 既存の設定を削除（重複防止）
sed -i '/execute_scheduled_posts\.py/d' "$TEMP_CRON"
sed -i '/wordpress-auto-posting/d' "$TEMP_CRON"

# 新しいcron設定を追加
cat >> "$TEMP_CRON" << EOF

# WordPress自動投稿システム - 15分間隔実行
*/15 * * * * cd $PROJECT_ROOT && $PYTHON_VENV $MAIN_SCRIPT --vps-mode --multiple 1 >> $LOG_FILE 2>&1

# 日次ステータス確認 - 毎日1:00
0 1 * * * cd $PROJECT_ROOT && $PYTHON_VENV $MAIN_SCRIPT --vps-mode --status >> $PROJECT_ROOT/logs/daily_status.log 2>&1

# 週次Git更新 - 毎週日曜日2:00
0 2 * * 0 cd $PROJECT_ROOT && git pull origin main >> $PROJECT_ROOT/logs/git_update.log 2>&1

EOF

# crontab設定を適用
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "✅ 15分間隔cron設定完了"
echo ""
echo "設定内容:"
crontab -l | grep -E "(execute_scheduled_posts|#.*WordPress)"
echo ""
echo "次回実行時間:"
current_minute=$(date '+%M')
next_quarter=$((((current_minute / 15) + 1) * 15))
if [ $next_quarter -ge 60 ]; then
    next_hour=$(($(date '+%H') + 1))
    next_minute=0
    if [ $next_hour -ge 24 ]; then
        next_hour=0
        next_date=$(date -d 'tomorrow' '+%Y-%m-%d' 2>/dev/null || date -v+1d '+%Y-%m-%d')
    else
        next_date=$(date '+%Y-%m-%d')
    fi
else
    next_hour=$(date '+%H')
    next_minute=$next_quarter
    next_date=$(date '+%Y-%m-%d')
fi
printf "次回実行: %s %02d:%02d\n" "$next_date" "$next_hour" "$next_minute"

echo ""
echo "監視コマンド:"
echo "- リアルタイムログ: tail -f $LOG_FILE"
echo "- 今日のログ: tail -f $PROJECT_ROOT/logs/scheduled_posts_\$(date +%Y%m%d).log"
echo "- cron動作確認: crontab -l"

# テスト実行
echo ""
echo "テスト実行を行いますか？ (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "テスト実行中..."
    cd "$PROJECT_ROOT"
    "$PYTHON_VENV" "$MAIN_SCRIPT" --vps-mode --multiple 1
    echo "✅ テスト実行完了"
fi

echo ""
echo "=== 設定完了 ==="
echo "96件/日の自動投稿が15分間隔で実行されます"