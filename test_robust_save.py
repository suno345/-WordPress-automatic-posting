#!/usr/bin/env python3
"""
強化されたファイル保存機能のテストスクリプト
"""
import sys
import tempfile
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.post_manager import PostManager


def test_robust_save():
    """強化されたファイル保存機能をテスト"""
    print("🧪 強化されたファイル保存機能のテストを開始...")
    
    # テスト用の一時ディレクトリを使用
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_posted_works.json")
        
        # PostManagerをテスト用ファイルで初期化
        post_manager = PostManager(test_file)
        
        print(f"📁 テスト用ファイル: {test_file}")
        print(f"📊 初期投稿済み件数: {post_manager.get_posted_count()}")
        
        # テスト1: 新規作品の追加
        test_work_id = "d_590748"
        print(f"\n🔧 テスト1: {test_work_id}を投稿済みとしてマーク...")
        
        try:
            post_manager.mark_as_posted(test_work_id)
            print("✅ mark_as_posted実行成功")
            
            # 検証
            if post_manager.is_posted(test_work_id):
                print("✅ メモリ上で正しく認識されています")
            else:
                print("❌ メモリ上で認識されていません")
                return False
                
            # ファイルから再読み込みして検証
            post_manager2 = PostManager(test_file)
            if post_manager2.is_posted(test_work_id):
                print("✅ ファイルから正しく読み込まれています")
            else:
                print("❌ ファイルから読み込まれていません")
                return False
                
        except Exception as e:
            print(f"❌ mark_as_posted実行失敗: {e}")
            return False
        
        # テスト2: 重複追加
        print(f"\n🔧 テスト2: 同じ作品を再度追加（重複チェック）...")
        try:
            post_manager.mark_as_posted(test_work_id)
            print("✅ 重複追加が適切に処理されました")
        except Exception as e:
            print(f"❌ 重複追加処理でエラー: {e}")
            return False
        
        # テスト3: 複数作品の追加
        print(f"\n🔧 テスト3: 複数作品の追加...")
        test_works = ["d_643291", "d_639095", "d_642778"]
        
        for work_id in test_works:
            try:
                post_manager.mark_as_posted(work_id)
                print(f"✅ {work_id} 追加成功")
            except Exception as e:
                print(f"❌ {work_id} 追加失敗: {e}")
                return False
        
        # 最終確認
        total_count = post_manager.get_posted_count()
        expected_count = 4  # test_work_id + test_works 3件
        
        print(f"\n📊 最終確認:")
        print(f"   総投稿済み件数: {total_count}")
        print(f"   期待値: {expected_count}")
        
        if total_count == expected_count:
            print("✅ 全テスト成功！強化されたファイル保存機能が正常に動作しています")
            return True
        else:
            print("❌ 件数が一致しません")
            return False


if __name__ == "__main__":
    success = test_robust_save()
    sys.exit(0 if success else 1)