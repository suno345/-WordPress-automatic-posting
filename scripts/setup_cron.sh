#!/bin/bash

# VPS用cron設定スクリプト
# 15分間隔で96件/日の自動投稿を設定

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VENV="$PROJECT_ROOT/venv/bin/python"
MAIN_SCRIPT="$PROJECT_ROOT/execute_scheduled_posts.py"
LOG_FILE="$PROJECT_ROOT/logs/cron.log"

echo "=== VPS用cron設定開始 ==="

# ログディレクトリ作成
mkdir -p "$PROJECT_ROOT/logs"

# 現在のcrontab設定を確認
echo "現在のcrontab設定:"
crontab -l 2>/dev/null || echo "crontabが設定されていません"

# 一時ファイル作成
TEMP_CRON=$(mktemp)

# 既存のcrontab設定を保存（存在する場合）
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 既存の同様の設定を削除
sed -i '/vps_auto_posting\.sh/d' "$TEMP_CRON"
sed -i '/blog-automation/d' "$TEMP_CRON"

# 新しいcron設定を追加
cat >> "$TEMP_CRON" << EOF

# WordPress自動投稿システム - 15分間隔実行（96件/日）
# 毎日00:00, 00:15, 00:30, ... 23:45に実行
*/15 * * * * cd $PROJECT_ROOT && $PYTHON_VENV $MAIN_SCRIPT --vps-mode --multiple 1 >> $LOG_FILE 2>&1

# 日次ステータス確認 - 毎日1:00に実行
0 1 * * * cd $PROJECT_ROOT && $PYTHON_VENV $MAIN_SCRIPT --vps-mode --status >> $PROJECT_ROOT/logs/daily_status.log 2>&1

# 週次メンテナンス - 毎週日曜日2:00にGit更新
0 2 * * 0 cd $PROJECT_ROOT && git pull origin main >> $PROJECT_ROOT/logs/git_update.log 2>&1

# 月次バックアップ - 毎月1日3:00にデータベースバックアップ
0 3 1 * * cp $PROJECT_ROOT/data/posts.db $PROJECT_ROOT/data/backup_\$(date +\%Y\%m\%d)_posts.db 2>> $LOG_FILE

EOF

# 新しいcrontab設定を適用
crontab "$TEMP_CRON"
echo "新しいcrontab設定を適用しました:"
crontab -l

# 一時ファイル削除
rm "$TEMP_CRON"

# cron実行確認用テスト
echo ""
echo "=== cron設定確認 ==="
echo "次回実行予定時間の確認:"

# 現在時刻
current_time=$(date '+%Y-%m-%d %H:%M')
echo "現在時刻: $current_time"

# 次の15分刻みの時刻を計算
current_minute=$(date '+%M')
next_quarter=$((((current_minute / 15) + 1) * 15))

if [ $next_quarter -ge 60 ]; then
    next_hour=$(($(date '+%H') + 1))
    next_minute=0
    if [ $next_hour -ge 24 ]; then
        next_hour=0
        next_date=$(date -d 'tomorrow' '+%Y-%m-%d')
    else
        next_date=$(date '+%Y-%m-%d')
    fi
else
    next_hour=$(date '+%H')
    next_minute=$next_quarter
    next_date=$(date '+%Y-%m-%d')
fi

printf "次回実行時刻: %s %02d:%02d\n" "$next_date" "$next_hour" "$next_minute"

# 権限確認
echo ""
echo "=== 権限確認 ==="
if [ -x "$MAIN_SCRIPT" ]; then
    echo "✅ メインスクリプト実行権限: OK"
else
    echo "❌ メインスクリプト実行権限: NG"
    chmod +x "$MAIN_SCRIPT"
    echo "✅ 実行権限を付与しました"
fi

if [ -x "$PYTHON_VENV" ]; then
    echo "✅ Python仮想環境: OK"
else
    echo "❌ Python仮想環境: NG ($PYTHON_VENV)"
    echo "仮想環境の作成が必要です: python3 -m venv venv"
fi

# ディレクトリ権限確認
if [ -w "$PROJECT_ROOT/logs" ]; then
    echo "✅ ログディレクトリ書き込み権限: OK"
else
    echo "❌ ログディレクトリ書き込み権限: NG"
    chmod 755 "$PROJECT_ROOT/logs"
    echo "✅ ログディレクトリ権限を修正しました"
fi

# cron サービス状態確認
echo ""
echo "=== cronサービス状態確認 ==="
if systemctl is-active --quiet cron; then
    echo "✅ cronサービス: 実行中"
elif systemctl is-active --quiet crond; then
    echo "✅ crondサービス: 実行中"
else
    echo "❌ cronサービス: 停止中"
    echo "以下のコマンドでサービスを開始してください:"
    echo "  sudo systemctl start cron"
    echo "  または"
    echo "  sudo systemctl start crond"
fi

# テスト実行
echo ""
echo "=== テスト実行 ==="
echo "スクリプトのテスト実行を行いますか？ (y/N)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "テスト実行中..."
    cd "$PROJECT_ROOT"
    "$PYTHON_VENV" "$MAIN_SCRIPT" --vps-mode --multiple 1
    echo "テスト実行完了"
fi

echo ""
echo "=== 設定完了 ==="
echo "96件/日の自動投稿が15分間隔で実行されます:"
echo "- 実行間隔: 15分 (*/15 * * * *)"
echo "- 1日の実行回数: 96回"
echo "- 1回の投稿数: 1件"
echo ""
echo "ログファイル:"
echo "- cron実行ログ: $LOG_FILE"
echo "- 日次ログ: $PROJECT_ROOT/logs/daily/"
echo "- エラーログ: $PROJECT_ROOT/logs/error/"
echo ""
echo "監視コマンド:"
echo "- リアルタイムログ: tail -f $LOG_FILE"
echo "- 今日の実行状況: cat $PROJECT_ROOT/logs/daily/auto_posting_\$(date +%Y-%m-%d).log"
echo ""
echo "設定完了！"