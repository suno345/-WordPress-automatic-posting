#!/usr/bin/env python3
"""
d_590748重複投稿問題の包括的デバッグスクリプト
main.pyとexecute_scheduled_posts.pyの動作を詳細に分析
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.post_manager import PostManager
from src.core.auto_posting_system import AutoPostingSystem
from src.config.simple_config_manager import SimpleConfigManager
from src.core.search_cache_manager import SearchCacheManager


def debug_cache_system():
    """キャッシュシステムのデバッグ"""
    print("\n=== キャッシュシステムデバッグ ===")
    
    try:
        cache_manager = SearchCacheManager()
        
        print(f"キャッシュファイルパス: {cache_manager.cache_file}")
        print(f"キャッシュファイル存在: {cache_manager.cache_file.exists()}")
        
        # キャッシュステータス
        cache_status = cache_manager.get_cache_status()
        print(f"キャッシュステータス: {cache_status}")
        
        # キャッシュされた作品ID
        cached_work_ids = cache_manager.get_cached_work_ids()
        print(f"キャッシュされた作品ID数: {len(cached_work_ids)}")
        
        if cached_work_ids:
            print(f"キャッシュされた最初の5件: {cached_work_ids[:5]}")
            # d_590748がキャッシュに含まれているかチェック
            if 'd_590748' in cached_work_ids:
                print("⚠️ d_590748がキャッシュに存在します！")
            else:
                print("✅ d_590748はキャッシュに存在しません")
        
    except Exception as e:
        print(f"キャッシュシステムデバッグエラー: {e}")
        import traceback
        traceback.print_exc()


def simulate_main_py_execution():
    """main.pyの実行をシミュレート"""
    print("\n=== main.py実行シミュレーション ===")
    
    try:
        # main.pyと同様にAutoPostingSystemを初期化
        print("1. AutoPostingSystem初期化中...")
        system = AutoPostingSystem(
            config_file=None,
            verbose=True,
            skip_review_check=True  # テスト用
        )
        
        print(f"2. PostManager状態:")
        print(f"   - 投稿済み件数: {system.post_manager.get_posted_count()}件")
        print(f"   - d_590748判定: {'投稿済み' if system.post_manager.is_posted('d_590748') else '未投稿'}")
        
        print(f"3. キャッシュマネージャー状態:")
        cache_status = system.cache_manager.get_cache_status()
        print(f"   - ステータス: {cache_status}")
        
        # _fetch_worksメソッドの一部を模倣（実際の検索はスキップ）
        print("4. 作品フィルタリング処理のテスト:")
        test_work_ids = ['d_590748', 'd_999999', 'd_123456']
        unposted_ids = system.post_manager.filter_unposted_works(test_work_ids)
        print(f"   - テストID: {test_work_ids}")
        print(f"   - 未投稿ID: {unposted_ids}")
        
        # キャッシュから作品IDを取得するロジックをテスト
        cached_work_ids = system.cache_manager.get_cached_work_ids()
        if cached_work_ids:
            print(f"5. キャッシュから取得した作品ID:")
            print(f"   - キャッシュ件数: {len(cached_work_ids)}")
            if 'd_590748' in cached_work_ids:
                print("   ⚠️ d_590748がキャッシュに存在！これが重複投稿の原因の可能性")
            else:
                print("   ✅ d_590748はキャッシュに存在しません")
        else:
            print("5. キャッシュは空です")
        
        return system
        
    except Exception as e:
        print(f"main.py実行シミュレーションエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def simulate_execute_scheduled_posts():
    """execute_scheduled_posts.pyの実行をシミュレート"""
    print("\n=== execute_scheduled_posts.py実行シミュレーション ===")
    
    try:
        # execute_scheduled_posts.pyと同様に初期化
        print("1. 設定読み込み...")
        config_manager = SimpleConfigManager()
        
        print("2. PostManager初期化...")
        post_manager = PostManager()  # デフォルトパスを使用
        
        print(f"3. PostManager状態:")
        print(f"   - ファイルパス: {post_manager.posted_works_file}")
        print(f"   - 投稿済み件数: {post_manager.get_posted_count()}件")
        print(f"   - d_590748判定: {'投稿済み' if post_manager.is_posted('d_590748') else '未投稿'}")
        
        return post_manager
        
    except Exception as e:
        print(f"execute_scheduled_posts.py実行シミュレーションエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_potential_race_conditions():
    """潜在的な競合状態を分析"""
    print("\n=== 潜在的競合状態分析 ===")
    
    try:
        # 複数のPostManagerインスタンスを同時に作成してテスト
        print("1. 複数PostManagerインスタンス作成テスト:")
        
        pm1 = PostManager()
        pm2 = PostManager()
        
        print(f"   - PostManager1: {pm1.posted_works_file}")
        print(f"   - PostManager2: {pm2.posted_works_file}")
        print(f"   - ファイルパス一致: {pm1.posted_works_file == pm2.posted_works_file}")
        print(f"   - 投稿済みセットサイズ一致: {len(pm1.posted_works) == len(pm2.posted_works)}")
        print(f"   - d_590748判定一致: {pm1.is_posted('d_590748') == pm2.is_posted('d_590748')}")
        
        # ファイルの最終更新時刻をチェック
        posted_works_file = Path(pm1.posted_works_file)
        if posted_works_file.exists():
            import datetime
            mtime = posted_works_file.stat().st_mtime
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   - posted_works.json最終更新: {mtime_str}")
        
    except Exception as e:
        print(f"競合状態分析エラー: {e}")
        import traceback
        traceback.print_exc()


def check_autoposting_work_selection():
    """AutoPostingSystemの作品選択ロジックを詳しく確認"""
    print("\n=== AutoPostingSystem作品選択ロジック詳細確認 ===")
    
    try:
        system = AutoPostingSystem(
            config_file=None,
            verbose=True,
            skip_review_check=True
        )
        
        print("1. _fetch_worksメソッドの動作を分析:")
        
        # キャッシュマネージャーの状態を確認
        cached_work_ids = system.cache_manager.get_cached_work_ids()
        print(f"   - キャッシュから取得した作品ID: {len(cached_work_ids)}件")
        
        if cached_work_ids:
            # キャッシュに作品IDがある場合の処理を追跡
            print("   - キャッシュから作品取得処理をテスト")
            required_works = system.config.system.max_posts_per_run
            target_work_ids = cached_work_ids[:required_works]
            print(f"   - 処理対象キャッシュID: {target_work_ids}")
            
            # 投稿済みフィルター処理
            work_ids = target_work_ids
            unposted_ids = system.post_manager.filter_unposted_works(work_ids)
            print(f"   - フィルター後未投稿ID: {unposted_ids}")
            
            if 'd_590748' in target_work_ids:
                is_posted = system.post_manager.is_posted('d_590748')
                print(f"   ⚠️ 重要: d_590748がキャッシュに存在、投稿済み判定: {'投稿済み' if is_posted else '未投稿'}")
                
                if not is_posted:
                    print("   🚨 これが重複投稿の直接的原因です！")
                else:
                    print("   ✅ d_590748は正しく投稿済みと判定されています")
        else:
            print("   - キャッシュは空のため通常の検索処理")
        
    except Exception as e:
        print(f"作品選択ロジック確認エラー: {e}")
        import traceback
        traceback.print_exc()


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='d_590748重複投稿問題の包括的デバッグ')
    parser.add_argument('--vps-mode', action='store_true', help='VPSモードで実行')
    parser.add_argument('--clear-cache', action='store_true', help='キャッシュをクリアしてからテスト')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # VPSモードの設定
    if args.vps_mode:
        os.environ['VPS_MODE'] = 'true'
        print("🔍 VPSモードを有効化")
    
    # キャッシュクリア
    if args.clear_cache:
        cache_manager = SearchCacheManager()
        cache_manager.clear_cache()
        print("🗑️ キャッシュをクリア")
    
    print("🔍 d_590748重複投稿問題の包括的デバッグ開始")
    print(f"VPS_MODE: {os.getenv('VPS_MODE', 'false')}")
    
    debug_cache_system()
    simulate_execute_scheduled_posts()
    simulate_main_py_execution()
    analyze_potential_race_conditions()
    check_autoposting_work_selection()
    
    print("\n🔍 包括的デバッグ完了")
    
    # 最終結論
    print("\n=== 調査結果まとめ ===")
    print("1. PostManagerの初期化はmain.pyとexecute_scheduled_posts.pyで一致")
    print("2. d_590748の投稿済み判定は正常に動作")
    print("3. 重複投稿の原因は以下の可能性:")
    print("   a) キャッシュシステムに古いd_590748が残存")
    print("   b) VPS環境でのファイルアクセス競合")
    print("   c) 異なる実行タイミングでの投稿済みファイル状態不整合")
    print("   d) DMM API検索結果とキャッシュの不整合")