#!/bin/bash

# バッチ記事生成スクリプト
# 深夜2時に1日分の記事を生成し、15分間隔で予約設定

# 設定
PROJECT_ROOT="/opt/blog-automation"
PYTHON_PATH="/usr/bin/python3"
LOG_DIR="$PROJECT_ROOT/logs"
BATCH_LOG="$LOG_DIR/batch_generation.log"
LOCK_FILE="/tmp/batch_generation.lock"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 現在の日時
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY=$(date '+%Y-%m-%d')

# ログ関数
log_batch() {
    echo "[$TIMESTAMP] $1" | tee -a "$BATCH_LOG"
}

# ロック機能
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid=$(cat "$LOCK_FILE")
        if ps -p "$lock_pid" > /dev/null 2>&1; then
            log_batch "既にバッチ生成が実行中です (PID: $lock_pid). 終了します。"
            exit 1
        else
            log_batch "古いロックファイルを削除: $lock_pid"
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

# システムチェック
system_check() {
    log_batch "バッチ生成システムチェック開始"
    
    # プロジェクトディレクトリ存在チェック
    if [ ! -d "$PROJECT_ROOT" ]; then
        log_batch "ERROR: プロジェクトディレクトリが見つかりません: $PROJECT_ROOT"
        exit 1
    fi
    
    # Python実行ファイルチェック
    if [ ! -x "$PYTHON_PATH" ]; then
        log_batch "ERROR: Python実行ファイルが見つかりません: $PYTHON_PATH"
        exit 1
    fi
    
    # VPS設定ファイルチェック
    if [ ! -f "$PROJECT_ROOT/config/config.vps.ini" ]; then
        log_batch "ERROR: VPS設定ファイルが見つかりません"
        exit 1
    fi
    
    # ディスク容量チェック
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
    if [ "$disk_usage" -gt 85 ]; then
        log_batch "WARNING: ディスク使用量が高い: ${disk_usage}%"
    fi
    
    # メモリ使用量チェック
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        log_batch "WARNING: メモリ使用量が高い: ${memory_usage}%"
    fi
    
    log_batch "システムチェック完了"
}

# API接続テスト
api_connectivity_test() {
    log_batch "API接続テスト開始"
    
    # DMM API接続テスト
    if ! curl -s --max-time 10 "https://api.dmm.com/" > /dev/null; then
        log_batch "WARNING: DMM API接続に問題の可能性"
    else
        log_batch "DMM API接続: OK"
    fi
    
    # WordPress API接続テスト
    if ! curl -s --max-time 10 "https://mania-wiki.com/wp-json/wp/v2/" > /dev/null; then
        log_batch "WARNING: WordPress API接続に問題の可能性"
    else
        log_batch "WordPress API接続: OK"
    fi
    
    # Gemini API接続テスト
    if ! curl -s --max-time 10 "https://generativelanguage.googleapis.com/" > /dev/null; then
        log_batch "WARNING: Gemini API接続に問題の可能性"
    else
        log_batch "Gemini API接続: OK"
    fi
    
    log_batch "API接続テスト完了"
}

# バッチ記事生成実行
execute_batch_generation() {
    log_batch "バッチ記事生成実行開始"
    
    cd "$PROJECT_ROOT" || {
        log_batch "ERROR: プロジェクトディレクトリへの移動に失敗"
        exit 1
    }
    
    # Python実行（バッチ生成モード）
    local start_time=$(date +%s)
    
    timeout 3600 "$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '.')

from src.config.config_manager import ConfigManager
from src.api.dmm_api import DMMAPIClient
from src.api.gemini_api import GeminiAPI
from src.core.batch_article_generator import BatchArticleGenerator
from src.core.post_manager import PostManager
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # 設定読み込み
    config = ConfigManager('config/config.vps.ini')
    
    # API クライアント初期化
    dmm_client = DMMAPIClient(config.dmm_api)
    gemini_api = GeminiAPI(config.gemini)
    post_manager = PostManager()
    
    # バッチ生成システム初期化
    batch_generator = BatchArticleGenerator(
        dmm_client=dmm_client,
        gemini_api=gemini_api,
        config=config,
        post_manager=post_manager
    )
    
    # バッチ生成実行
    result = batch_generator.generate_daily_batch()
    
    # 結果出力
    if result.get('articles_generated', 0) > 0:
        print(f'SUCCESS: {result[\"articles_generated\"]}件の記事を生成し、{result.get(\"articles_scheduled\", 0)}件を予約設定しました')
        print(f'成功率: {result.get(\"success_rate\", 0):.1f}%')
        print(f'総実行時間: {result.get(\"total_time\", 0):.1f}秒')
    else:
        print(f'WARNING: 記事生成に失敗しました。エラー: {result.get(\"error\", \"不明\")}')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: バッチ生成中にエラー: {e}')
    sys.exit(1)
" >> "$BATCH_LOG" 2>&1
    
    local exit_code=$?
    local end_time=$(date +%s)
    local execution_time=$((end_time - start_time))
    
    case $exit_code in
        0)
            log_batch "バッチ記事生成完了 (実行時間: ${execution_time}秒)"
            update_success_stats
            ;;
        124)
            log_batch "ERROR: バッチ生成タイムアウト (3600秒超過)"
            update_error_stats "timeout"
            exit 1
            ;;
        *)
            log_batch "ERROR: バッチ記事生成失敗 (終了コード: $exit_code, 実行時間: ${execution_time}秒)"
            update_error_stats "generation_error"
            exit 1
            ;;
    esac
}

# 成功統計更新
update_success_stats() {
    local stats_file="$LOG_DIR/batch_success_$TODAY.txt"
    echo "$(date '+%H:%M'): BATCH_SUCCESS" >> "$stats_file"
}

# エラー統計更新
update_error_stats() {
    local error_type="$1"
    local stats_file="$LOG_DIR/batch_error_$TODAY.txt"
    echo "$(date '+%H:%M'): BATCH_ERROR - $error_type" >> "$stats_file"
}

# 生成後の検証
verify_generation_result() {
    log_batch "生成結果検証開始"
    
    # 予約スケジュールファイルの存在確認
    local schedule_file="$PROJECT_ROOT/data/schedule/post_schedule.json"
    if [ -f "$schedule_file" ]; then
        local scheduled_count=$(cat "$schedule_file" | grep -o '"scheduled"' | wc -l)
        log_batch "予約設定確認: ${scheduled_count}件の投稿が予約されています"
        
        if [ "$scheduled_count" -lt 50 ]; then
            log_batch "WARNING: 予約投稿数が少ない可能性があります"
        fi
    else
        log_batch "WARNING: 予約スケジュールファイルが見つかりません"
    fi
    
    # データディレクトリのサイズ確認
    local data_size=$(du -sh "$PROJECT_ROOT/data" | cut -f1)
    log_batch "データディレクトリサイズ: $data_size"
    
    log_batch "生成結果検証完了"
}

# 次回実行の準備
prepare_next_execution() {
    log_batch "次回実行準備開始"
    
    # 古いバッチログのクリーンアップ（7日以上古い）
    find "$LOG_DIR" -name "batch_*.log" -mtime +7 -delete
    find "$LOG_DIR" -name "batch_success_*.txt" -mtime +7 -delete
    find "$LOG_DIR" -name "batch_error_*.txt" -mtime +7 -delete
    
    # 次回実行時刻の計算と表示
    local next_execution="明日 02:00"
    log_batch "次回バッチ実行予定: $next_execution"
    
    log_batch "次回実行準備完了"
}

# 緊急時のフォールバック処理
emergency_fallback() {
    log_batch "緊急フォールバック処理開始"
    
    # 少数の記事を緊急生成
    "$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '.')

from src.config.config_manager import ConfigManager
from src.api.dmm_api import DMMAPIClient
from src.api.gemini_api import GeminiAPI
from src.core.batch_article_generator import BatchArticleGenerator
from src.core.post_manager import PostManager

try:
    config = ConfigManager('config/config.vps.ini')
    dmm_client = DMMAPIClient(config.dmm_api)
    gemini_api = GeminiAPI(config.gemini)
    post_manager = PostManager()
    
    batch_generator = BatchArticleGenerator(
        dmm_client=dmm_client,
        gemini_api=gemini_api,
        config=config,
        post_manager=post_manager
    )
    
    # 緊急生成（24件）
    result = batch_generator.emergency_generation(24)
    
    if result['success']:
        print(f'EMERGENCY_SUCCESS: {result[\"generated_count\"]}件の緊急記事を生成')
    else:
        print('EMERGENCY_FAILED: 緊急生成も失敗')
        
except Exception as e:
    print(f'EMERGENCY_ERROR: {e}')
" >> "$BATCH_LOG" 2>&1
    
    log_batch "緊急フォールバック処理完了"
}

# メイン処理
main() {
    log_batch "=== バッチ記事生成開始 ==="
    
    # ロック取得
    acquire_lock
    
    # システムチェック
    system_check
    
    # API接続テスト
    api_connectivity_test
    
    # バッチ記事生成実行
    if ! execute_batch_generation; then
        log_batch "通常のバッチ生成に失敗しました。緊急フォールバックを実行します。"
        emergency_fallback
    fi
    
    # 生成結果検証
    verify_generation_result
    
    # 次回実行の準備
    prepare_next_execution
    
    log_batch "=== バッチ記事生成完了 ==="
}

# スクリプト実行
main "$@"