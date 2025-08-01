#!/bin/bash

# 日次メンテナンススクリプト
# 毎日1時に実行

PROJECT_ROOT="/opt/blog-automation"
LOG_DIR="$PROJECT_ROOT/logs"
MAINTENANCE_LOG="$LOG_DIR/maintenance.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY=$(date '+%Y-%m-%d')
YESTERDAY=$(date -d 'yesterday' '+%Y-%m-%d')

# ログ関数
log_maintenance() {
    echo "[$TIMESTAMP] $1" | tee -a "$MAINTENANCE_LOG"
}

# ログローテーション
log_rotation() {
    log_maintenance "ログローテーション開始"
    
    # 7日以上古いログファイルを削除
    local deleted_count=0
    
    # 各ログディレクトリの古いファイルを削除
    for log_pattern in "daily/*.log" "error/*.log" "*.log"; do
        while IFS= read -r -d '' file; do
            rm "$file"
            ((deleted_count++))
        done < <(find "$LOG_DIR" -name "$log_pattern" -mtime +7 -type f -print0)
    done
    
    log_maintenance "ログローテーション完了 - 削除ファイル数: $deleted_count"
}

# キャッシュクリーンアップ
cache_cleanup() {
    log_maintenance "キャッシュクリーンアップ開始"
    
    local cache_dir="$PROJECT_ROOT/cache"
    local cleaned_size=0
    
    if [ -d "$cache_dir" ]; then
        # 1日以上古いキャッシュファイルを削除
        local old_cache_files=$(find "$cache_dir" -type f -mtime +1)
        if [ -n "$old_cache_files" ]; then
            cleaned_size=$(echo "$old_cache_files" | xargs du -ch | tail -n1 | cut -f1)
            echo "$old_cache_files" | xargs rm -f
        fi
        
        # 空のディレクトリを削除
        find "$cache_dir" -type d -empty -delete
    fi
    
    log_maintenance "キャッシュクリーンアップ完了 - 削除サイズ: $cleaned_size"
}

# 統計レポート生成
generate_daily_stats() {
    log_maintenance "統計レポート生成開始"
    
    local stats_file="$LOG_DIR/daily_stats_$TODAY.json"
    local success_log="$LOG_DIR/success_log_$YESTERDAY.txt"
    local error_log="$LOG_DIR/error_log_$YESTERDAY.txt"
    
    local success_count=0
    local error_count=0
    
    # 昨日の実行結果を集計
    if [ -f "$success_log" ]; then
        success_count=$(wc -l < "$success_log")
    fi
    
    if [ -f "$error_log" ]; then
        error_count=$(wc -l < "$error_log")
    fi
    
    local total_count=$((success_count + error_count))
    local success_rate=0
    
    if [ $total_count -gt 0 ]; then
        success_rate=$(echo "scale=2; $success_count * 100 / $total_count" | bc -l)
    fi
    
    # JSON形式で統計を保存
    cat > "$stats_file" << EOF
{
    "date": "$YESTERDAY",
    "total_executions": $total_count,
    "successful_posts": $success_count,
    "failed_posts": $error_count,
    "success_rate": $success_rate,
    "target_posts": 96,
    "achievement_rate": $(echo "scale=2; $success_count * 100 / 96" | bc -l)
}
EOF
    
    log_maintenance "統計レポート生成完了 - 昨日の成功率: ${success_rate}%"
    
    # 成功率が90%を下回る場合は警告
    if [ $total_count -gt 10 ] && (( $(echo "$success_rate < 90" | bc -l) )); then
        log_maintenance "WARNING: 昨日の成功率が低い: ${success_rate}%"
    fi
    
    # 目標達成率をチェック（96件中何件投稿できたか）
    local achievement_rate=$(echo "scale=1; $success_count * 100 / 96" | bc -l)
    log_maintenance "昨日の目標達成率: ${achievement_rate}% ($success_count/96件)"
}

# システム情報収集
collect_system_info() {
    log_maintenance "システム情報収集開始"
    
    local system_info_file="$LOG_DIR/system_info_$TODAY.txt"
    
    {
        echo "=== システム情報 - $TODAY ==="
        echo "OS情報:"
        uname -a
        echo ""
        echo "ディスク使用量:"
        df -h "$PROJECT_ROOT"
        echo ""
        echo "メモリ使用量:"
        free -h
        echo ""
        echo "CPU情報:"
        top -bn1 | head -n5
        echo ""
        echo "プロセス一覧:"
        ps aux | grep -E "(python|main.py)" | grep -v grep
        echo ""
        echo "ネットワーク接続:"
        netstat -tuln | grep LISTEN | head -10
        echo ""
    } > "$system_info_file"
    
    log_maintenance "システム情報収集完了"
}

# データベース最適化（将来の拡張用）
optimize_database() {
    log_maintenance "データベース最適化開始"
    
    # 現在はファイルベースなので、posted_works.jsonの最適化のみ
    local posted_works_file="$PROJECT_ROOT/data/posted_works.json"
    
    if [ -f "$posted_works_file" ]; then
        local original_size=$(stat -f%z "$posted_works_file" 2>/dev/null || stat -c%s "$posted_works_file")
        
        # JSONファイルの整形（圧縮）
        if command -v jq >/dev/null 2>&1; then
            jq -c . "$posted_works_file" > "${posted_works_file}.tmp" && \
            mv "${posted_works_file}.tmp" "$posted_works_file"
            
            local new_size=$(stat -f%z "$posted_works_file" 2>/dev/null || stat -c%s "$posted_works_file")
            local saved_bytes=$((original_size - new_size))
            
            log_maintenance "データベース最適化完了 - 削減サイズ: ${saved_bytes}バイト"
        else
            log_maintenance "jqが利用できないため、データベース最適化をスキップ"
        fi
    fi
}

# バックアップ作成
create_backup() {
    log_maintenance "バックアップ作成開始"
    
    local backup_dir="$PROJECT_ROOT/backups"
    local backup_file="$backup_dir/backup_$TODAY.tar.gz"
    
    mkdir -p "$backup_dir"
    
    # 重要なファイルをバックアップ
    tar -czf "$backup_file" \
        -C "$PROJECT_ROOT" \
        config/ \
        data/ \
        src/ \
        scripts/ \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        2>/dev/null
    
    if [ -f "$backup_file" ]; then
        local backup_size=$(du -h "$backup_file" | cut -f1)
        log_maintenance "バックアップ作成完了 - サイズ: $backup_size"
        
        # 7日以上古いバックアップを削除
        find "$backup_dir" -name "backup_*.tar.gz" -mtime +7 -delete
    else
        log_maintenance "ERROR: バックアップ作成に失敗"
    fi
}

# セキュリティチェック
security_check() {
    log_maintenance "セキュリティチェック開始"
    
    local security_issues=0
    
    # ファイル権限チェック
    local config_perms=$(stat -f%Mp%Lp "$PROJECT_ROOT/config/" 2>/dev/null || stat -c%a "$PROJECT_ROOT/config/")
    if [ "$config_perms" != "755" ] && [ "$config_perms" != "750" ]; then
        log_maintenance "WARNING: 設定ディレクトリの権限が適切でない: $config_perms"
        ((security_issues++))
    fi
    
    # 設定ファイル内の機密情報チェック
    if grep -q "password.*=" "$PROJECT_ROOT/config/config.vps.ini" 2>/dev/null; then
        local config_file_perms=$(stat -f%Mp%Lp "$PROJECT_ROOT/config/config.vps.ini" 2>/dev/null || stat -c%a "$PROJECT_ROOT/config/config.vps.ini")
        if [ "$config_file_perms" != "600" ] && [ "$config_file_perms" != "640" ]; then
            log_maintenance "WARNING: 設定ファイルの権限が適切でない: $config_file_perms"
            ((security_issues++))
        fi
    fi
    
    log_maintenance "セキュリティチェック完了 - 発見された問題: $security_issues件"
}

# メイン処理
main() {
    log_maintenance "=== 日次メンテナンス開始 ==="
    
    # 各メンテナンス処理を実行
    log_rotation
    cache_cleanup
    generate_daily_stats
    collect_system_info
    optimize_database
    create_backup
    security_check
    
    # 総合サマリー
    local log_size=$(du -sh "$LOG_DIR" | cut -f1)
    local cache_size=$(du -sh "$PROJECT_ROOT/cache" 2>/dev/null | cut -f1 || echo "0B")
    
    log_maintenance "=== 日次メンテナンス完了 ==="
    log_maintenance "現在の状況 - ログサイズ: $log_size, キャッシュサイズ: $cache_size"
}

# スクリプト実行
main "$@"