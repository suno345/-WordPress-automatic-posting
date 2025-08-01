#!/usr/bin/env python3
"""
15分刻み前倒し投稿システムのテストスクリプト
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.post_schedule_manager import PostScheduleManager

def create_test_articles(count: int):
    """テスト用記事データを作成"""
    articles = []
    for i in range(count):
        article = {
            "work_data": {
                "work_id": f"test_work_{i+1}",
                "title": f"テスト作品{i+1}",
                "circle_name": f"テストサークル{i+1}",
                "author_name": f"テスト作者{i+1}",
                "description": f"これはテスト用の作品{i+1}です。"
            },
            "rewritten_description": f"リライトされたテスト説明文{i+1}",
            "article_content": f"完全なテスト記事内容{i+1}"
        }
        articles.append(article)
    return articles

def test_advance_schedule():
    """前倒し投稿スケジュールのテスト"""
    print("=== 15分刻み前倒し投稿システムテスト ===")
    print(f"現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # スケジュール管理システム初期化（設定なしでテスト）
    schedule_manager = PostScheduleManager()
    
    print(f"\n1. 現在の投稿状況確認")
    status = schedule_manager.get_schedule_status()
    print(f"予約投稿総数: {status['total_scheduled']}件")
    print(f"今日の完了: {status['completed_today']}件")
    
    remaining_slots = schedule_manager._get_remaining_daily_slots()
    print(f"今日の残り枠: {remaining_slots}件")
    
    print(f"\n2. 15分刻み空き枠確認テスト")
    available_slots = schedule_manager._calculate_next_15min_slots(3, remaining_slots)
    print(f"利用可能な15分刻み枠: {len(available_slots)}件")
    for i, slot in enumerate(available_slots):
        print(f"  {i+1}. {slot.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\n3. 前倒し投稿スケジュール作成テスト")
    test_articles = create_test_articles(3)
    
    try:
        schedule_info = schedule_manager.create_advance_schedule(test_articles)
        
        print(f"スケジュール作成結果:")
        print(f"  タイプ: {schedule_info['type']}")
        print(f"  記事数: {schedule_info['total_articles']}件")
        print(f"  残り日次枠: {schedule_info['remaining_daily_slots']}件")
        print(f"  使用枠:")
        for slot in schedule_info['slots_used']:
            print(f"    - {slot}")
        
        print(f"\n4. スケジュール状況確認")
        updated_status = schedule_manager.get_schedule_status()
        print(f"更新後予約投稿総数: {updated_status['total_scheduled']}件")
        
        if updated_status['next_posts']:
            print(f"次の投稿予定:")
            for post in updated_status['next_posts'][:3]:
                print(f"  - {post['post_time']}: {post['title']} (優先度: {post['priority']})")
        
        print(f"\n✅ テスト完了")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        raise

def test_slot_occupation_check():
    """時刻重複チェックテスト"""
    print(f"\n=== 時刻重複チェックテスト ===")
    
    schedule_manager = PostScheduleManager()
    
    # 現在時刻から次の15分刻み時刻を計算
    now = datetime.now()
    next_quarter = now.replace(second=0, microsecond=0)
    minutes_to_next = (15 - now.minute % 15) % 15
    if minutes_to_next == 0:
        minutes_to_next = 15
    next_quarter += timedelta(minutes=minutes_to_next)
    
    print(f"次の15分刻み時刻: {next_quarter.strftime('%Y-%m-%d %H:%M')}")
    
    # 重複チェック
    is_occupied = schedule_manager._is_slot_occupied(next_quarter)
    print(f"時刻占有状況: {'占有済み' if is_occupied else '空き'}")
    
    # 今後5つの15分刻み時刻をチェック
    print(f"\n今後の15分刻み時刻占有状況:")
    for i in range(5):
        check_time = next_quarter + timedelta(minutes=15 * i)
        occupied = schedule_manager._is_slot_occupied(check_time)
        status = "占有済み" if occupied else "空き"
        print(f"  {check_time.strftime('%H:%M')}: {status}")

def main():
    """メインテスト実行"""
    try:
        print("15分刻み前倒し投稿システムテスト開始")
        
        test_advance_schedule()
        test_slot_occupation_check()
        
        print(f"\n🎉 全テスト完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()