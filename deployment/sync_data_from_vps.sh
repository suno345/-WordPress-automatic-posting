#!/bin/bash
# VPS環境からローカル環境へのデータ同期スクリプト

# 設定
VPS_HOST="member1@your-vps-ip"  # 実際のVPS情報に置き換えてください
VPS_PROJECT_PATH="/home/member1/wordpress-auto-posting"
LOCAL_PROJECT_PATH="$(dirname "$(realpath "$0")")/.."

echo "🔄 VPS環境からデータ同期を開始..."

# VPSから投稿済み作品データを取得
echo "📥 投稿済み作品データを取得中..."
scp "${VPS_HOST}:${VPS_PROJECT_PATH}/data/posted_works.json" "${LOCAL_PROJECT_PATH}/data/posted_works.json.vps"

if [ $? -eq 0 ]; then
    echo "✅ VPS投稿済みデータ取得完了"
    
    # バックアップ作成
    if [ -f "${LOCAL_PROJECT_PATH}/data/posted_works.json" ]; then
        cp "${LOCAL_PROJECT_PATH}/data/posted_works.json" "${LOCAL_PROJECT_PATH}/data/posted_works.json.backup.$(date +%Y%m%d_%H%M%S)"
        echo "📁 ローカルデータをバックアップしました"
    fi
    
    # VPSデータで置き換え
    mv "${LOCAL_PROJECT_PATH}/data/posted_works.json.vps" "${LOCAL_PROJECT_PATH}/data/posted_works.json"
    echo "✅ ローカルデータをVPS版で更新完了"
    
    # 投稿済み件数確認
    posted_count=$(python3 -c "
import json
with open('${LOCAL_PROJECT_PATH}/data/posted_works.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(len(data.get('posted_work_ids', [])))
")
    echo "📊 同期後の投稿済み作品数: ${posted_count}件"
    
else
    echo "❌ VPSからのデータ取得に失敗しました"
    exit 1
fi

# VPSからスケジュール関連データも同期（オプション）
echo ""
echo "📅 スケジュール関連データも同期しますか？(y/N)"
read -r sync_schedule

if [[ $sync_schedule =~ ^[Yy]$ ]]; then
    echo "📥 スケジュール関連データを同期中..."
    
    # completed_posts.json
    scp "${VPS_HOST}:${VPS_PROJECT_PATH}/data/schedule/completed_posts.json" "${LOCAL_PROJECT_PATH}/data/schedule/"
    
    # failed_posts.json
    scp "${VPS_HOST}:${VPS_PROJECT_PATH}/data/schedule/failed_posts.json" "${LOCAL_PROJECT_PATH}/data/schedule/"
    
    # post_schedule.json（現在の予約状況）
    scp "${VPS_HOST}:${VPS_PROJECT_PATH}/data/schedule/post_schedule.json" "${LOCAL_PROJECT_PATH}/data/schedule/"
    
    echo "✅ スケジュール関連データ同期完了"
fi

echo ""
echo "🎯 同期完了！重複投稿問題が解決されました"
echo "📋 確認方法:"
echo "  python test_posted_check.py"
echo ""
echo "⏰ 定期同期の推奨:"
echo "  このスクリプトを定期的に実行することで、VPSとローカルの整合性を保てます"