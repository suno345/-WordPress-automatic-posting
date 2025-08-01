#!/bin/bash

# ヘルスチェックスクリプト
# システムの健全性を監視

PROJECT_ROOT="/opt/blog-automation"
LOG_DIR="$PROJECT_ROOT/logs"
HEALTH_LOG="$LOG_DIR/health_check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ログ関数
log_health() {
    echo "[$TIMESTAMP] $1" >> "$HEALTH_LOG"
}

# API接続チェック
api_connectivity_check() {
    local dmm_api_status="OK"
    local wordpress_api_status="OK"
    local gemini_api_status="OK"
    
    # DMM API接続テスト
    if ! curl -s --max-time 10 "https://api.dmm.com/" > /dev/null; then
        dmm_api_status="NG"
    fi
    
    # WordPress API接続テスト
    if ! curl -s --max-time 10 "https://mania-wiki.com/wp-json/wp/v2/" > /dev/null; then
        wordpress_api_status="NG"
    fi
    
    # Gemini API接続テスト（軽量なテスト）
    if ! curl -s --max-time 10 "https://generativelanguage.googleapis.com/" > /dev/null; then
        gemini_api_status="NG"
    fi
    
    log_health "API接続状況 - DMM: $dmm_api_status, WordPress: $wordpress_api_status, Gemini: $gemini_api_status"
    
    if [[ "$dmm_api_status" == "NG" ]] || [[ "$wordpress_api_status" == "NG" ]] || [[ "$gemini_api_status" == "NG" ]]; then
        return 1
    fi
    return 0
}

# システムリソースチェック
system_resource_check() {
    # CPU使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    # メモリ使用率
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    
    # ディスク使用率
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
    
    log_health "システムリソース - CPU: ${cpu_usage}%, メモリ: ${memory_usage}%, ディスク: ${disk_usage}%"
    
    # 閾値チェック
    local alert=false
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_health "WARNING: CPU使用率が高い: ${cpu_usage}%"
        alert=true
    fi
    
    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        log_health "WARNING: メモリ使用率が高い: ${memory_usage}%"
        alert=true
    fi
    
    if [ "$disk_usage" -gt 80 ]; then
        log_health "WARNING: ディスク使用率が高い: ${disk_usage}%"
        alert=true
    fi
    
    if [ "$alert" = true ]; then
        return 1
    fi
    return 0
}

# プロセス監視
process_monitoring() {
    # Python プロセス数確認
    local python_processes=$(pgrep -f "main.py" | wc -l)
    
    # ロックファイル確認
    local lock_file_exists=false
    if [ -f "/tmp/blog_automation.lock" ]; then
        lock_file_exists=true
        local lock_pid=$(cat "/tmp/blog_automation.lock")
        if ! ps -p "$lock_pid" > /dev/null 2>&1; then
            log_health "WARNING: 古いロックファイルを検出: PID $lock_pid"
            rm -f "/tmp/blog_automation.lock"
            lock_file_exists=false
        fi
    fi
    
    log_health "プロセス監視 - Pythonプロセス数: $python_processes, ロックファイル: $lock_file_exists"
}

# ログファイル分析
log_analysis() {
    local today=$(date '+%Y-%m-%d')
    local success_log="$LOG_DIR/success_log_$today.txt"
    local error_log="$LOG_DIR/error_log_$today.txt"
    
    local success_count=0
    local error_count=0
    
    if [ -f "$success_log" ]; then
        success_count=$(wc -l < "$success_log")
    fi
    
    if [ -f "$error_log" ]; then
        error_count=$(wc -l < "$error_log")
    fi
    
    local total_count=$((success_count + error_count))
    local success_rate=0
    
    if [ $total_count -gt 0 ]; then
        success_rate=$(echo "scale=1; $success_count * 100 / $total_count" | bc -l)
    fi
    
    log_health "今日の実行状況 - 成功: $success_count, 失敗: $error_count, 成功率: ${success_rate}%"
    
    # 成功率が90%を下回る場合は警告
    if [ $total_count -gt 10 ] && (( $(echo "$success_rate < 90" | bc -l) )); then
        log_health "WARNING: 成功率が低い: ${success_rate}%"
        return 1
    fi
    
    return 0
}

# キャッシュ状態チェック
cache_status_check() {
    local cache_dir="$PROJECT_ROOT/cache"
    local cache_file_count=0
    local cache_size=0
    
    if [ -d "$cache_dir" ]; then
        cache_file_count=$(find "$cache_dir" -type f | wc -l)
        cache_size=$(du -sh "$cache_dir" | cut -f1)
    fi
    
    log_health "キャッシュ状況 - ファイル数: $cache_file_count, サイズ: $cache_size"
}

# 設定ファイル整合性チェック
config_integrity_check() {
    local config_file="$PROJECT_ROOT/config/config.vps.ini"
    local config_status="OK"
    
    if [ ! -f "$config_file" ]; then
        config_status="NG - ファイル不存在"
    elif [ ! -r "$config_file" ]; then
        config_status="NG - 読み取り権限なし"
    else
        # 必須項目の存在確認
        if ! grep -q "^\[wordpress\]" "$config_file" || \
           ! grep -q "^\[dmm_api\]" "$config_file" || \
           ! grep -q "^\[gemini\]" "$config_file"; then
            config_status="NG - 必須セクション不足"
        fi
    fi
    
    log_health "設定ファイル状況: $config_status"
    
    if [[ "$config_status" != "OK" ]]; then
        return 1
    fi
    return 0
}

# アラート送信（将来の拡張用）
send_alert() {
    local message="$1"
    local severity="$2"
    
    # 現在はログのみ、将来的にSlack/メール通知を追加可能
    log_health "ALERT [$severity]: $message"
    
    # 重要なアラートの場合は別ファイルにも記録
    if [ "$severity" = "CRITICAL" ]; then
        echo "[$TIMESTAMP] $message" >> "$LOG_DIR/critical_alerts.log"
    fi
}

# メイン処理
main() {
    log_health "=== ヘルスチェック開始 ==="
    
    local overall_status="HEALTHY"
    local checks_failed=0
    
    # API接続チェック
    if ! api_connectivity_check; then
        overall_status="WARNING"
        ((checks_failed++))
        send_alert "API接続に問題があります" "WARNING"
    fi
    
    # システムリソースチェック
    if ! system_resource_check; then
        overall_status="WARNING"
        ((checks_failed++))
        send_alert "システムリソースの使用率が高いです" "WARNING"
    fi
    
    # プロセス監視
    process_monitoring
    
    # ログファイル分析
    if ! log_analysis; then
        overall_status="WARNING"
        ((checks_failed++))
        send_alert "実行成功率が低下しています" "WARNING"
    fi
    
    # キャッシュ状態チェック
    cache_status_check
    
    # 設定ファイル整合性チェック
    if ! config_integrity_check; then
        overall_status="CRITICAL"
        ((checks_failed++))
        send_alert "設定ファイルに問題があります" "CRITICAL"
    fi
    
    # 総合判定
    if [ $checks_failed -gt 2 ]; then
        overall_status="CRITICAL"
        send_alert "複数のヘルスチェックが失敗しました (失敗数: $checks_failed)" "CRITICAL"
    fi
    
    log_health "=== ヘルスチェック完了 - 総合状況: $overall_status ==="
    
    # 終了コード設定
    case $overall_status in
        "HEALTHY") exit 0 ;;
        "WARNING") exit 1 ;;
        "CRITICAL") exit 2 ;;
    esac
}

# スクリプト実行
main "$@"