#!/usr/bin/env python3
"""
投稿済みチェック機能のテストスクリプト
"""
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.post_manager import PostManager


def test_posted_check():
    """投稿済みチェック機能をテスト"""
    print("📋 投稿済みチェック機能のテストを開始...")
    
    # PostManagerを初期化
    post_manager = PostManager()
    
    # 投稿済み作品数を確認
    total_count = post_manager.get_posted_count()
    print(f"📊 総投稿済み作品数: {total_count}件")
    
    # d_590748の投稿済み状況をテスト
    test_work_id = "d_590748"
    is_posted = post_manager.is_posted(test_work_id)
    
    print(f"\n🔍 テスト対象: {test_work_id}")
    print(f"投稿済み判定: {'✅ Yes' if is_posted else '❌ No'}")
    
    if is_posted:
        print("✅ d_590748は正常に投稿済みとして認識されています")
    else:
        print("❌ d_590748が投稿済みとして認識されていません！")
        
        # posted_works.jsonの内容を直接確認
        print("\n📄 posted_works.jsonの内容確認:")
        if hasattr(post_manager, 'posted_works'):
            print(f"投稿済みセット内容数: {len(post_manager.posted_works)}")
            if test_work_id in post_manager.posted_works:
                print("✅ セット内に存在します")
            else:
                print("❌ セット内に存在しません")
                # 類似IDがあるかチェック
                similar_ids = [work_id for work_id in post_manager.posted_works if '590748' in work_id]
                if similar_ids:
                    print(f"類似ID: {similar_ids}")
    
    # 複数の作品IDでテスト
    test_ids = ["d_590748", "d_643291", "d_639095", "d_642778", "d_635602"]
    print(f"\n🔄 複数作品での投稿済みチェックテスト:")
    
    for work_id in test_ids:
        is_posted = post_manager.is_posted(work_id)
        status = "✅ 投稿済み" if is_posted else "❌ 未投稿"
        print(f"  {work_id}: {status}")
    
    # filter_unposted_worksのテスト
    print(f"\n🔍 filter_unposted_worksテスト:")
    unposted_works = post_manager.filter_unposted_works(test_ids)
    print(f"入力: {test_ids}")
    print(f"未投稿: {unposted_works}")


if __name__ == "__main__":
    test_posted_check()