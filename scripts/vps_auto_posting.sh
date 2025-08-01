#!/bin/bash

# VPS自動投稿実行スクリプト
# 15分間隔で1記事投稿（96件/日）

# 設定
PROJECT_ROOT="/opt/blog-automation"
PYTHON_PATH="/usr/bin/python3"
CONFIG_FILE="config/config.vps.ini"
LOG_DIR="$PROJECT_ROOT/logs"
DAILY_LOG_DIR="$LOG_DIR/daily"
ERROR_LOG_DIR="$LOG_DIR/error"
LOCK_FILE="/tmp/blog_automation.lock"

# ログディレクトリ作成
mkdir -p "$DAILY_LOG_DIR" "$ERROR_LOG_DIR"

# 現在の日時
CURRENT_DATE=$(date '+%Y-%m-%d')
CURRENT_TIME=$(date '+%H:%M')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ログファイルパス
DAILY_LOG="$DAILY_LOG_DIR/auto_posting_$CURRENT_DATE.log"
ERROR_LOG="$ERROR_LOG_DIR/error_$CURRENT_DATE.log"
CRON_LOG="$LOG_DIR/cron.log"

# ロック機能
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid=$(cat "$LOCK_FILE")
        if ps -p "$lock_pid" > /dev/null 2>&1; then
            echo "[$TIMESTAMP] 既に実行中です (PID: $lock_pid). スキップします。" >> "$CRON_LOG"
            exit 1
        else
            echo "[$TIMESTAMP] 古いロックファイルを削除: $lock_pid" >> "$CRON_LOG"
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

# ログ関数
log_info() {
    echo "[$TIMESTAMP] INFO: $1" | tee -a "$DAILY_LOG" "$CRON_LOG"
}

log_error() {
    echo "[$TIMESTAMP] ERROR: $1" | tee -a "$ERROR_LOG" "$CRON_LOG"
}

log_success() {
    echo "[$TIMESTAMP] SUCCESS: $1" | tee -a "$DAILY_LOG" "$CRON_LOG"
}

# システムチェック
system_check() {
    log_info "システムチェック開始"
    
    # プロジェクトディレクトリ存在チェック
    if [ ! -d "$PROJECT_ROOT" ]; then
        log_error "プロジェクトディレクトリが見つかりません: $PROJECT_ROOT"
        exit 1
    fi
    
    # 設定ファイル存在チェック
    if [ ! -f "$PROJECT_ROOT/$CONFIG_FILE" ]; then
        log_error "設定ファイルが見つかりません: $PROJECT_ROOT/$CONFIG_FILE"
        exit 1
    fi
    
    # Python実行ファイルチェック
    if [ ! -x "$PYTHON_PATH" ]; then
        log_error "Python実行ファイルが見つかりません: $PYTHON_PATH"
        exit 1
    fi
    
    # ネットワーク接続チェック
    if ! ping -c 1 google.com &> /dev/null; then
        log_error "ネットワーク接続に問題があります"
        exit 1
    fi
    
    log_info "システムチェック完了"
}

# ディスク容量チェック
disk_check() {
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
    local threshold=80
    
    if [ "$disk_usage" -gt "$threshold" ]; then
        log_error "ディスク使用量が閾値を超過: ${disk_usage}% > ${threshold}%"
        return 1
    fi
    
    log_info "ディスク使用量: ${disk_usage}%"
    return 0
}

# メイン実行関数
execute_posting() {
    log_info "自動投稿実行開始 - $CURRENT_TIME"
    
    cd "$PROJECT_ROOT" || {
        log_error "プロジェクトディレクトリへの移動に失敗"
        exit 1
    }
    
    # Python実行（VPSモード）
    local start_time=$(date +%s)
    
    timeout 300 "$PYTHON_PATH" main.py --vps-mode >> "$DAILY_LOG" 2>> "$ERROR_LOG"
    local exit_code=$?
    
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))
    
    case $exit_code in
        0)
            log_success "記事投稿完了 (実行時間: ${execution_time}秒)"
            update_success_stats
            ;;
        124)
            log_error "実行タイムアウト (300秒超過)"
            update_error_stats "timeout"
            ;;
        *)
            log_error "記事投稿失敗 (終了コード: $exit_code, 実行時間: ${execution_time}秒)"
            update_error_stats "execution_error"
            ;;
    esac
    
    return $exit_code
}

# 成功統計更新
update_success_stats() {
    local stats_file="$LOG_DIR/daily_stats_$CURRENT_DATE.json"
    local hour=$(date '+%H')
    
    # JSON統計ファイル更新（簡易版）
    echo "$(date '+%H:%M'): SUCCESS" >> "$LOG_DIR/success_log_$CURRENT_DATE.txt"
}

# エラー統計更新
update_error_stats() {
    local error_type="$1"
    local stats_file="$LOG_DIR/daily_stats_$CURRENT_DATE.json"
    
    echo "$(date '+%H:%M'): ERROR - $error_type" >> "$LOG_DIR/error_log_$CURRENT_DATE.txt"
}

# ログローテーション
log_rotation() {
    # 7日以上古いログファイルを削除
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete
    find "$DAILY_LOG_DIR" -name "*.log" -mtime +7 -delete
    find "$ERROR_LOG_DIR" -name "*.log" -mtime +7 -delete
}

# ヘルスチェック
health_check() {
    local health_file="$LOG_DIR/health_status.json"
    local current_hour=$(date '+%H')
    
    # 1時間に1回ヘルスチェック実行
    if [ "$current_hour" -eq "$(date -d '1 hour ago' '+%H')" ]; then
        log_info "ヘルスチェック実行"
        
        # 過去24時間の成功率計算
        local success_count=$(find "$LOG_DIR" -name "success_log_*.txt" -mtime -1 -exec wc -l {} + | tail -n1 | awk '{print $1}')
        local error_count=$(find "$LOG_DIR" -name "error_log_*.txt" -mtime -1 -exec wc -l {} + | tail -n1 | awk '{print $1}')
        local total_count=$((success_count + error_count))
        
        if [ "$total_count" -gt 0 ]; then
            local success_rate=$(echo "scale=2; $success_count * 100 / $total_count" | bc -l)
            log_info "過去24時間の成功率: ${success_rate}% (成功: $success_count, 失敗: $error_count)"
            
            # 成功率が90%を下回る場合はアラート
            if (( $(echo "$success_rate < 90" | bc -l) )); then
                log_error "成功率が低下しています: ${success_rate}%"
            fi
        fi
    fi
}

# メイン処理
main() {
    log_info "=== VPS自動投稿実行開始 ==="
    
    # ロック取得
    acquire_lock
    
    # システムチェック
    system_check
    
    # ディスク容量チェック
    if ! disk_check; then
        log_error "ディスク容量不足のため実行を中止"
        exit 1
    fi
    
    # 自動投稿実行
    execute_posting
    local result=$?
    
    # ログローテーション（1日1回、0時に実行）
    if [ "$(date '+%H:%M')" = "00:00" ]; then
        log_info "日次メンテナンス実行"
        log_rotation
    fi
    
    # ヘルスチェック
    health_check
    
    log_info "=== VPS自動投稿実行完了 ==="
    
    return $result
}

# スクリプト実行
main "$@"