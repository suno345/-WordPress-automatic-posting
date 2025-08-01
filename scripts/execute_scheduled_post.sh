#!/bin/bash

# 予約投稿実行スクリプト
# 15分毎に予約された投稿を実行

# 設定
PROJECT_ROOT="/opt/blog-automation"
PYTHON_PATH="/usr/bin/python3"
LOG_DIR="$PROJECT_ROOT/logs"
SCHEDULED_LOG="$LOG_DIR/scheduled_posts.log"
LOCK_FILE="/tmp/scheduled_post.lock"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 現在の日時
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY=$(date '+%Y-%m-%d')
CURRENT_TIME=$(date '+%H:%M')

# ログ関数
log_scheduled() {
    echo "[$TIMESTAMP] $1" | tee -a "$SCHEDULED_LOG"
}

# ロック機能（軽量版）
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid=$(cat "$LOCK_FILE")
        if ps -p "$lock_pid" > /dev/null 2>&1; then
            log_scheduled "既に予約投稿実行中です (PID: $lock_pid). スキップします。"
            exit 0  # エラーではなく正常終了
        else
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# ロック解除
release_lock() {
    rm -f "$LOCK_FILE"
}

# 終了時の処理
cleanup() {
    release_lock
}
trap cleanup EXIT

# 軽量システムチェック
quick_system_check() {
    # 重要なファイル・ディレクトリのみチェック
    if [ ! -d "$PROJECT_ROOT" ] || [ ! -f "$PROJECT_ROOT/config/config.vps.ini" ]; then
        log_scheduled "ERROR: 必要なファイル・ディレクトリが見つかりません"
        exit 1
    fi
    
    # ディスク容量の緊急チェック（95%以上で停止）
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
    if [ "$disk_usage" -gt 95 ]; then
        log_scheduled "ERROR: ディスク容量不足 (${disk_usage}%) - 実行を停止"
        exit 1
    fi
}

# 予約投稿実行
execute_scheduled_post() {
    log_scheduled "予約投稿実行開始 - $CURRENT_TIME"
    
    cd "$PROJECT_ROOT" || {
        log_scheduled "ERROR: プロジェクトディレクトリへの移動に失敗"
        exit 1
    }
    
    # Python実行（予約投稿モード）
    local start_time=$(date +%s)
    
    timeout 180 "$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '.')

from src.config.config_manager import ConfigManager
from src.api.wordpress_api import WordPressAPI
from src.core.scheduled_post_executor import ScheduledPostExecutor
from src.core.post_manager import PostManager
import logging

# ログ設定（軽量）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # 設定読み込み
    config = ConfigManager('config/config.vps.ini')
    
    # API クライアント初期化
    wp_api = WordPressAPI(config.wordpress)
    post_manager = PostManager()
    
    # 予約投稿実行システム初期化
    executor = ScheduledPostExecutor(
        wp_api=wp_api,
        config=config,
        post_manager=post_manager
    )
    
    # 予約投稿実行
    result = executor.execute_next_scheduled_post()
    
    # 結果出力
    if result['status'] == 'success':
        print(f'SUCCESS: {result[\"post_info\"][\"title\"]} - 投稿完了 (ID: {result.get(\"post_id\", \"不明\")})')
        print(f'実行時間: {result[\"performance\"].get(\"total_execution_time\", 0):.1f}秒')
    elif result['status'] == 'failed':
        print(f'FAILED: {result.get(\"message\", \"投稿失敗\")}')
        sys.exit(1)
    elif result['status'] == 'exception':
        print(f'ERROR: {result.get(\"error\", \"不明なエラー\")}')
        sys.exit(1)
    elif result['status'] == 'no_action':
        print('NO_ACTION: 実行する予約投稿がありません')
    else:
        print(f'UNKNOWN: 不明な状態 - {result[\"status\"]}')
        
except Exception as e:
    print(f'ERROR: 予約投稿実行中にエラー: {e}')
    sys.exit(1)
" >> "$SCHEDULED_LOG" 2>&1
    
    local exit_code=$?
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))
    
    case $exit_code in
        0)
            log_scheduled "予約投稿実行完了 (実行時間: ${execution_time}秒)"
            update_execution_stats "success"
            ;;
        124)
            log_scheduled "ERROR: 予約投稿実行タイムアウト (180秒超過)"
            update_execution_stats "timeout"
            ;;
        *)
            log_scheduled "ERROR: 予約投稿実行失敗 (終了コード: $exit_code, 実行時間: ${execution_time}秒)"
            update_execution_stats "execution_error"
            
            # 失敗時は次回実行で回復を試行
            schedule_recovery_attempt
            ;;
    esac
    
    return $exit_code
}

# 実行統計更新
update_execution_stats() {
    local result_type="$1"
    local stats_file="$LOG_DIR/scheduled_stats_$TODAY.txt"
    echo "$(date '+%H:%M'): $result_type" >> "$stats_file"
}

# 回復試行のスケジュール
schedule_recovery_attempt() {
    local recovery_file="$PROJECT_ROOT/data/recovery_needed.flag"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Recovery needed" >> "$recovery_file"
    log_scheduled "回復試行をスケジュールしました"
}

# 回復処理実行
execute_recovery_if_needed() {
    local recovery_file="$PROJECT_ROOT/data/recovery_needed.flag"
    
    if [ -f "$recovery_file" ]; then
        log_scheduled "失敗投稿の回復処理実行"
        
        # 複数投稿実行（遅延分の回復）
        "$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '.')

from src.config.config_manager import ConfigManager
from src.api.wordpress_api import WordPressAPI
from src.core.scheduled_post_executor import ScheduledPostExecutor
from src.core.post_manager import PostManager

try:
    config = ConfigManager('config/config.vps.ini')
    wp_api = WordPressAPI(config.wordpress)
    post_manager = PostManager()
    
    executor = ScheduledPostExecutor(
        wp_api=wp_api,
        config=config,
        post_manager=post_manager
    )
    
    # 失敗投稿の回復処理
    recovery_result = executor.recover_failed_posts()
    print(f'RECOVERY: {recovery_result[\"rescheduled_count\"]}件を再スケジュール')
    
    # 複数投稿実行（最大3件）
    multi_result = executor.execute_multiple_posts(3)
    print(f'MULTI_EXEC: 成功{multi_result[\"success_count\"]}件, 失敗{multi_result[\"failed_count\"]}件')
    
except Exception as e:
    print(f'RECOVERY_ERROR: {e}')
" >> "$SCHEDULED_LOG" 2>&1
        
        # 回復処理完了後、フラグファイルを削除
        rm -f "$recovery_file"
        log_scheduled "回復処理完了"
    fi
}

# スケジュール状況の簡易確認
check_schedule_status() {
    # 今日の実行統計
    local stats_file="$LOG_DIR/scheduled_stats_$TODAY.txt"
    if [ -f "$stats_file" ]; then
        local success_count=$(grep -c "success" "$stats_file" 2>/dev/null || echo 0)
        local error_count=$(grep -c -E "(execution_error|timeout)" "$stats_file" 2>/dev/null || echo 0)
        local total_count=$((success_count + error_count))
        
        if [ $total_count -gt 0 ]; then
            local success_rate=$(echo "scale=1; $success_count * 100 / $total_count" | bc -l)
            log_scheduled "今日の実行状況: 成功${success_count}件, 失敗${error_count}件 (成功率: ${success_rate}%)"
            
            # 成功率が80%を下回る場合は警告
            if (( $(echo "$success_rate < 80" | bc -l) )); then
                log_scheduled "WARNING: 成功率が低下しています"
            fi
        fi
    fi
}

# 次回実行時刻の表示
show_next_execution() {
    # 次の15分刻みの時刻を計算
    local current_minute=$(date '+%M')
    local next_minute=$(( ((current_minute / 15) + 1) * 15 ))
    
    if [ $next_minute -ge 60 ]; then
        local next_hour=$(( $(date '+%H') + 1 ))
        next_minute=0
    else
        local next_hour=$(date '+%H')
    fi
    
    if [ $next_hour -ge 24 ]; then
        next_hour=0
        local next_date="明日"
    else
        local next_date="今日"
    fi
    
    printf "次回実行予定: %s %02d:%02d\n" "$next_date" "$next_hour" "$next_minute"
}

# ログローテーション（軽量版）
light_log_rotation() {
    # 実行回数が多いため、1日1回のみローテーション実行
    if [ "$CURRENT_TIME" = "00:00" ]; then
        # 7日以上古いログファイルを削除
        find "$LOG_DIR" -name "scheduled_*.log" -mtime +7 -delete 2>/dev/null
        find "$LOG_DIR" -name "scheduled_stats_*.txt" -mtime +7 -delete 2>/dev/null
    fi
}

# メイン処理
main() {
    # ロック取得
    acquire_lock
    
    # 軽量システムチェック
    quick_system_check
    
    # 回復処理確認・実行
    execute_recovery_if_needed
    
    # 予約投稿実行
    execute_scheduled_post
    local execution_result=$?
    
    # スケジュール状況確認（5分毎）
    local minute=$(date '+%M')
    if [ $((minute % 5)) -eq 0 ]; then
        check_schedule_status
    fi
    
    # ログローテーション（軽量版）
    light_log_rotation
    
    # 次回実行時刻表示（デバッグ用、00分のみ）
    if [ "$minute" = "00" ]; then
        show_next_execution >> "$SCHEDULED_LOG"
    fi
    
    return $execution_result
}

# スクリプト実行
main "$@"