#!/usr/bin/env python3
"""
重複投稿スケジュールのクリーンアップスクリプト
"""
import sys
import json
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.post_schedule_manager import PostScheduleManager


def main():
    """重複スケジュールのクリーンアップを実行"""
    print("🧹 重複投稿スケジュールのクリーンアップを開始します...")
    
    try:
        # スケジュール管理システムを初期化
        schedule_manager = PostScheduleManager()
        
        # 現在の状況を表示
        current_status = schedule_manager.get_schedule_status()
        print(f"📊 現在のスケジュール状況:")
        print(f"   - 予約済み: {current_status['status_breakdown']['scheduled']}件")
        print(f"   - 進行中: {current_status['status_breakdown']['in_progress']}件")
        print(f"   - 期限切れ: {current_status['status_breakdown']['overdue']}件")
        print(f"   - 今日の完了: {current_status['completed_today']}件")
        print(f"   - 今日の失敗: {current_status['failed_today']}件")
        
        # 重複スケジュールのクリーンアップ実行
        cleanup_result = schedule_manager.clean_duplicate_schedules()
        
        if cleanup_result["success"]:
            print(f"\n✅ クリーンアップ完了!")
            print(f"   - 削除前: {cleanup_result['original_count']}件")
            print(f"   - 削除後: {cleanup_result['final_count']}件")
            print(f"   - 削除した重複: {cleanup_result['removed_count']}件")
            print(f"   - 重複作品数: {cleanup_result['duplicates_found']}作品")
            
            if cleanup_result["duplicate_details"]:
                print(f"\n📝 重複作品の詳細:")
                for detail in cleanup_result["duplicate_details"]:
                    print(f"   - 作品ID: {detail['work_id']}")
                    print(f"     総スケジュール数: {detail['total_schedules']}件")
                    print(f"     保持: {detail['kept_schedule']}")
                    print(f"     削除: {', '.join(detail['removed_schedules'])}")
        else:
            print(f"❌ クリーンアップに失敗しました: {cleanup_result['message']}")
            if 'error' in cleanup_result:
                print(f"エラー詳細: {cleanup_result['error']}")
            sys.exit(1)
        
        # クリーンアップ後の状況を表示
        final_status = schedule_manager.get_schedule_status()
        print(f"\n📊 クリーンアップ後のスケジュール状況:")
        print(f"   - 予約済み: {final_status['status_breakdown']['scheduled']}件")
        print(f"   - 進行中: {final_status['status_breakdown']['in_progress']}件")
        print(f"   - 期限切れ: {final_status['status_breakdown']['overdue']}件")
        
    except Exception as e:
        print(f"❌ クリーンアップ中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()