#!/usr/bin/env python3
"""
WordPress自動投稿システム メインスクリプト（リファクタリング版）
"""
import sys
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.auto_posting_system import AutoPostingSystem
from modules.exceptions import AutoPostingError, ConfigurationError


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='WordPress自動投稿システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main_refactored.py                    # 通常実行
  python main_refactored.py --config custom.ini # カスタム設定ファイル使用
  python main_refactored.py --test-connections  # 接続テストのみ実行
  python main_refactored.py --status           # システム状態表示
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config.ini',
        help='設定ファイルのパス (デフォルト: config.ini)'
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
        help='詳細ログを表示'
    )
    
    return parser.parse_args()


def run_main_process(system: AutoPostingSystem) -> int:
    """メインの投稿処理を実行"""
    try:
        result = system.run()
        
        print(f"✅ 処理完了:")
        print(f"   - 処理対象作品: {result['processed']}件")
        print(f"   - 投稿成功: {result['posted']}件")
        print(f"   - 総投稿数: {result['total_posted']}件")
        
        return 0 if result['posted'] > 0 else 1
        
    except AutoPostingError as e:
        print(f"❌ 投稿処理エラー: {e}")
        return 1
    except Exception as e:
        print(f"💥 予期しないエラー: {e}")
        return 2


def run_connection_test(system: AutoPostingSystem) -> int:
    """接続テストを実行"""
    try:
        print("🔍 API接続テストを実行中...")
        results = system.test_connections()
        
        all_ok = True
        for service, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {service.upper()}: {'OK' if status else 'NG'}")
            if not status:
                all_ok = False
        
        if all_ok:
            print("🎉 全ての接続テストが成功しました！")
            return 0
        else:
            print("⚠️  一部の接続テストが失敗しました。設定を確認してください。")
            return 1
            
    except Exception as e:
        print(f"❌ 接続テストエラー: {e}")
        return 1


def show_system_status(system: AutoPostingSystem) -> int:
    """システム状態を表示"""
    try:
        print("📊 システム状態:")
        status = system.get_system_status()
        
        # 設定概要
        config = status['config_summary']
        print(f"   WordPress URL: {config['wordpress_url']}")
        print(f"   WordPress User: {config['wordpress_username']}")
        print(f"   DMM API ID: {config['dmm_api_id']}")
        print(f"   Gemini API: {'設定済み' if config['has_gemini_key'] else '未設定'}")
        print(f"   ログレベル: {config['log_level']}")
        print(f"   最大投稿数/回: {config['max_posts_per_run']}")
        
        # 投稿統計
        print(f"   総投稿数: {status['posted_count']}件")
        print(f"   H2パターン数: {status['h2_patterns_count']}個")
        
        # 接続状態
        print("   接続状態:")
        for service, connected in status['connection_tests'].items():
            status_icon = "🟢" if connected else "🔴"
            print(f"     {status_icon} {service.upper()}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 状態表示エラー: {e}")
        return 1


def main():
    """メイン関数"""
    args = parse_arguments()
    
    try:
        # システム初期化
        print("🚀 WordPress自動投稿システムを初期化中...")
        system = AutoPostingSystem(config_file=args.config)
        
        # 実行モードに応じて処理を分岐
        if args.test_connections:
            return run_connection_test(system)
        elif args.status:
            return show_system_status(system)
        else:
            return run_main_process(system)
            
    except ConfigurationError as e:
        print(f"⚙️  設定エラー: {e}")
        print("設定ファイル（config.ini）を確認してください。")
        return 3
    except KeyboardInterrupt:
        print("\n⏹️  ユーザーによって中断されました。")
        return 130
    except Exception as e:
        print(f"💥 初期化エラー: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 4


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)