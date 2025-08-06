#!/usr/bin/env python3
"""
WordPress自動投稿システム メインスクリプト
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.auto_posting_system import AutoPostingSystem
from src.services.exceptions import AutoPostingError, ConfigurationError
from src.config.simple_config_manager import SimpleConfigManager


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='WordPress自動投稿システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                          # 通常実行
  python main.py --config config/config.ini # カスタム設定ファイル使用
  python main.py --test-connections       # 接続テストのみ実行
  python main.py --status                 # システム状態表示
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config/config.ini',
        help='設定ファイルのパス (デフォルト: config/config.ini, VPS: config/config.vps.ini)'
    )
    
    parser.add_argument(
        '--vps-mode',
        action='store_true',
        help='VPS最適化モードで実行（config.vps.iniを自動選択）'
    )
    
    parser.add_argument(
        '--test-connections', '-t',
        action='store_true',
        help='接続テストのみ実行'
    )
    
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='システム状態を表示'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを出力'
    )
    
    parser.add_argument(
        '--skip-review-check',
        action='store_true',
        help='レビューチェックをスキップ（テスト用）'
    )
    
    parser.add_argument(
        '--reset-posted-count',
        action='store_true',
        help='投稿カウンターをリセット（次回投稿日時を今日に戻す）'
    )
    
    parser.add_argument(
        '--cleanup-duplicates',
        action='store_true',
        help='重複投稿スケジュールをクリーンアップ'
    )
    
    parser.add_argument(
        '--sync-from-vps',
        action='store_true',
        help='VPS環境から投稿済み作品データを同期'
    )
    
    return parser.parse_args()


def main():
    """メイン処理"""
    import os  # osモジュールを関数の最初でimport
    
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # VPSモードの場合は環境変数を設定
        if args.vps_mode:
            os.environ['VPS_MODE'] = 'true'
            print("VPSモード: .env設定を使用")
        
        # システムの初期化（簡素化設定管理）
        system = AutoPostingSystem(
            config_file=None,  # .envファイルを直接使用
            verbose=args.verbose,
            skip_review_check=getattr(args, 'skip_review_check', False)
        )
        
        # 実行モードに応じた処理
        if args.test_connections:
            success = system.test_connections()
            sys.exit(0 if success else 1)
        elif args.status:
            system.display_status()
            sys.exit(0)
        elif args.reset_posted_count:
            # 投稿カウンターリセット
            print("🔄 投稿カウンターをリセットしています...")
            old_count = system.post_manager.get_posted_count()
            success = system.post_manager.reset_posted_count()
            if success:
                print(f"✅ 投稿カウンターをリセットしました: {old_count}件 → 0件")
                print("📅 次回投稿は翌日0:00から開始されます")
            else:
                print("❌ 投稿カウンターのリセットに失敗しました")
            sys.exit(0 if success else 1)
        elif args.cleanup_duplicates:
            # 重複スケジュールクリーンアップ
            from src.core.post_schedule_manager import PostScheduleManager
            print("🧹 重複投稿スケジュールをクリーンアップしています...")
            schedule_manager = PostScheduleManager()
            cleanup_result = schedule_manager.clean_duplicate_schedules()
            if cleanup_result["success"]:
                print(f"✅ クリーンアップ完了: {cleanup_result['removed_count']}件削除")
                if cleanup_result["duplicates_found"] > 0:
                    print(f"📝 {cleanup_result['duplicates_found']}作品の重複を解消しました")
            else:
                print(f"❌ クリーンアップに失敗しました: {cleanup_result['message']}")
            sys.exit(0 if cleanup_result["success"] else 1)
        elif args.sync_from_vps:
            # VPS環境からデータ同期
            import subprocess
            print("🔄 VPS環境から投稿済み作品データを同期しています...")
            try:
                result = subprocess.run([
                    "python", "sync_from_vps.py"
                ], capture_output=True, text=True)
                
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                
                if result.returncode == 0:
                    print("✅ VPS環境からの同期が完了しました")
                else:
                    print("❌ VPS環境からの同期に失敗しました")
                sys.exit(result.returncode)
            except Exception as e:
                print(f"❌ 同期処理中にエラーが発生: {e}")
                sys.exit(1)
        else:
            # 通常の投稿処理
            vps_mode = os.getenv('VPS_MODE', 'false').lower() == 'true'
            print(f"🚀 main.py実行開始 - VPSモード: {'有効' if vps_mode else '無効'}")
            print(f"📊 処理予定: {system.config.system.max_posts_per_run}件")
            
            success = system.run()
            sys.exit(0 if success else 1)
            
    except ConfigurationError as e:
        print(f"設定エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except AutoPostingError as e:
        print(f"システムエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n処理が中断されました", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"予期しないエラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()