#!/usr/bin/env python3
"""
d_590748重複投稿問題のデバッグスクリプト
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
from src.config.simple_config_manager import SimpleConfigManager


def debug_post_manager_initialization():
    """PostManager初期化のデバッグ"""
    print("=== PostManager初期化デバッグ ===")
    
    # 1. main.pyと同じ方法でPostManagerを初期化（config_file=None）
    print("\n1. main.py方式でPostManagerを初期化:")
    try:
        # AutoPostingSystemでの初期化を模倣
        post_manager_main = PostManager()  # デフォルト引数
        print(f"  ファイルパス: {post_manager_main.posted_works_file}")
        print(f"  投稿済み件数: {post_manager_main.get_posted_count()}件")
        print(f"  d_590748判定: {'投稿済み' if post_manager_main.is_posted('d_590748') else '未投稿'}")
    except Exception as e:
        print(f"  エラー: {e}")
    
    # 2. execute_scheduled_posts.py方式でPostManagerを初期化
    print("\n2. execute_scheduled_posts.py方式でPostManagerを初期化:")
    try:
        post_manager_scheduled = PostManager()  # 明示的にデフォルト引数
        print(f"  ファイルパス: {post_manager_scheduled.posted_works_file}")
        print(f"  投稿済み件数: {post_manager_scheduled.get_posted_count()}件")
        print(f"  d_590748判定: {'投稿済み' if post_manager_scheduled.is_posted('d_590748') else '未投稿'}")
    except Exception as e:
        print(f"  エラー: {e}")
    
    # 3. ファイルパス確認
    print("\n3. ファイルパス詳細確認:")
    try:
        # プロジェクトルート計算
        test_root = Path(__file__).parent.parent.parent
        expected_file = test_root / "data" / "posted_works.json"
        
        print(f"  現在の作業ディレクトリ: {os.getcwd()}")
        print(f"  スクリプト実行位置: {Path(__file__).parent}")
        print(f"  計算されたプロジェクトルート: {test_root}")
        print(f"  期待されるファイルパス: {expected_file}")
        print(f"  ファイルの存在: {expected_file.exists()}")
        
        if expected_file.exists():
            print(f"  ファイルサイズ: {expected_file.stat().st_size} bytes")
    except Exception as e:
        print(f"  エラー: {e}")


def debug_work_filtering():
    """作品フィルタリング処理のデバッグ"""
    print("\n=== 作品フィルタリング処理デバッグ ===")
    
    try:
        post_manager = PostManager()
        
        # テスト用の作品ID（d_590748を含む）
        test_work_ids = [
            "d_590748",    # 投稿済みのはず
            "d_999999",    # 存在しないID（未投稿）
            "d_123456",    # 存在しないID（未投稿）
        ]
        
        print(f"テスト対象ID: {test_work_ids}")
        
        # 1. 個別のis_posted()チェック
        print("\n1. 個別投稿済み判定:")
        for work_id in test_work_ids:
            is_posted = post_manager.is_posted(work_id)
            print(f"  {work_id}: {'投稿済み' if is_posted else '未投稿'}")
        
        # 2. filter_unposted_works()チェック
        print("\n2. filter_unposted_works()結果:")
        unposted_ids = post_manager.filter_unposted_works(test_work_ids)
        print(f"  未投稿作品: {unposted_ids}")
        
        # 3. posted_worksセットの内容確認
        print(f"\n3. posted_worksセット確認:")
        print(f"  セットサイズ: {len(post_manager.posted_works)}")
        print(f"  d_590748がセット内に存在: {'d_590748' in post_manager.posted_works}")
        
        # 4. セット内の類似IDを検索
        print(f"\n4. d_590748類似IDの検索:")
        similar_ids = [work_id for work_id in post_manager.posted_works if '590748' in work_id]
        print(f"  '590748'を含むID: {similar_ids}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


def debug_environment_variables():
    """環境変数の確認"""
    print("\n=== 環境変数確認 ===")
    
    vps_mode = os.getenv('VPS_MODE', 'false').lower() == 'true'
    print(f"VPS_MODE: {os.getenv('VPS_MODE', 'なし')} → {vps_mode}")
    
    # その他の重要な環境変数
    important_vars = [
        'WORDPRESS_URL',
        'WORDPRESS_USERNAME', 
        'DMM_API_ID',
        'DMM_AFFILIATE_ID',
        'GEMINI_API_KEY'
    ]
    
    for var in important_vars:
        value = os.getenv(var, 'なし')
        # パスワードやキーは一部のみ表示
        if 'PASSWORD' in var or 'KEY' in var or 'API_ID' in var:
            display_value = value[:8] + '...' if value != 'なし' and len(value) > 8 else value
        else:
            display_value = value
        print(f"{var}: {display_value}")


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='d_590748重複投稿問題デバッグ')
    parser.add_argument('--vps-mode', action='store_true', help='VPSモードで実行')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # VPSモードの設定
    if args.vps_mode:
        os.environ['VPS_MODE'] = 'true'
        print("🔍 VPSモードを有効化")
    
    print("🔍 d_590748重複投稿問題デバッグ開始")
    
    debug_environment_variables()
    debug_post_manager_initialization()
    debug_work_filtering()
    
    print("\n🔍 デバッグ完了")