#!/usr/bin/env python3
"""
予約投稿実行スクリプト - 15分間隔実行用
"""
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.scheduled_post_executor import ScheduledPostExecutor
from src.api.wordpress_api import WordPressAPI
from src.core.post_manager import PostManager
from src.config.simple_config_manager import SimpleConfigManager
from src.services.exceptions import AutoPostingError, ConfigurationError

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/scheduled_posts_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='予約投稿実行システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python execute_scheduled_posts.py                # 次の予約投稿を1件実行
  python execute_scheduled_posts.py --multiple 3   # 最大3件まで連続実行
  python execute_scheduled_posts.py --status       # 予約投稿状況を表示
  python execute_scheduled_posts.py --vps-mode     # VPS最適化モードで実行
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config/config.ini',
        help='設定ファイルのパス'
    )
    
    parser.add_argument(
        '--vps-mode',
        action='store_true',
        help='VPS最適化モードで実行（config.vps.iniを自動選択）'
    )
    
    parser.add_argument(
        '--multiple', '-m',
        type=int,
        default=1,
        help='連続実行する最大投稿数（デフォルト: 1）'
    )
    
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='予約投稿状況を表示'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを出力'
    )
    
    parser.add_argument(
        '--recover-failed',
        action='store_true',
        help='失敗した投稿を回復処理'
    )
    
    parser.add_argument(
        '--test-connections',
        action='store_true',
        help='API接続テストを実行'
    )
    
    return parser.parse_args()


def main():
    """メイン処理"""
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # VPSモードの場合は環境変数を設定
        if args.vps_mode:
            # VPSモードを環境変数に設定
            import os
            os.environ['VPS_MODE'] = 'true'
            logger.info("VPSモード: .env設定を使用")
        
        # 詳細ログ設定
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("詳細ログモードを有効化")
        
        # 設定の読み込み（簡素化設定管理）
        config_manager = SimpleConfigManager()
        wp_config = config_manager.wordpress
        
        # WordPress APIクライアントの初期化
        wp_api = WordPressAPI(
            url=wp_config.url,
            username=wp_config.username,
            password=wp_config.password
        )
        
        # 投稿管理システムの初期化
        post_manager = PostManager(config_manager)
        
        # 予約投稿実行システムの初期化
        executor = ScheduledPostExecutor(
            wp_api=wp_api,
            config=config_manager,
            post_manager=post_manager
        )
        
        logger.info("予約投稿実行システム初期化完了")
        
        # 実行モードに応じた処理
        if args.test_connections:
            # API接続テスト
            logger.info("API接続テストを開始")
            test_wordpress_connection(wp_api)
            test_config_access(config_manager)
            logger.info("全ての接続テストが完了しました")
            
        elif args.status:
            # 状況表示
            status = executor.get_execution_status()
            print_status(status)
            
        elif args.recover_failed:
            # 失敗投稿の回復処理
            logger.info("失敗投稿の回復処理を開始")
            result = executor.recover_failed_posts()
            logger.info(f"回復処理完了: {result['rescheduled_count']}件を再スケジュール")
            
        else:
            # 予約投稿実行
            if args.multiple > 1:
                # 複数投稿実行
                logger.info(f"複数予約投稿実行開始 - 最大{args.multiple}件")
                results = executor.execute_multiple_posts(max_posts=args.multiple)
                print_execution_results(results)
            else:
                # 単一投稿実行
                logger.info("次の予約投稿を実行")
                result = executor.execute_next_scheduled_post()
                print_single_execution_result(result)
        
        logger.info("予約投稿実行システム終了")
        
    except ConfigurationError as e:
        logger.error(f"設定エラー: {e}")
        sys.exit(1)
    except AutoPostingError as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(130)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


def print_status(status):
    """予約投稿状況を表示"""
    print("\n" + "="*50)
    print("🕒 予約投稿システム状況")
    print("="*50)
    
    schedule_summary = status["schedule_summary"]
    print(f"予約投稿総数: {schedule_summary['total_scheduled']}件")
    print(f"  - 予約済み: {schedule_summary['status_breakdown']['scheduled']}件")
    print(f"  - 実行中: {schedule_summary['status_breakdown']['in_progress']}件")
    print(f"  - 遅延: {schedule_summary['status_breakdown']['overdue']}件")
    print(f"今日の完了: {schedule_summary['completed_today']}件")
    print(f"今日の失敗: {schedule_summary['failed_today']}件")
    
    next_post = status["next_post"]
    if next_post:
        print(f"\n📅 次の投稿予定:")
        print(f"  タイトル: {next_post['title']}")
        print(f"  予定時刻: {next_post['scheduled_time']}")
        print(f"  遅延: {next_post['delay_minutes']:.1f}分")
        if next_post['is_overdue']:
            print(f"  ⚠️ 予定時刻を過ぎています")
    else:
        print(f"\n📅 実行予定の投稿はありません")
    
    print(f"\n最終更新: {status['last_updated']}")


def print_execution_results(results):
    """複数投稿実行結果を表示"""
    print("\n" + "="*50)
    print("📊 複数投稿実行結果")
    print("="*50)
    
    print(f"実行開始: {results['started_at']}")
    print(f"実行完了: {results['completed_at']}")
    print(f"総実行時間: {results['total_execution_time']:.1f}秒")
    print(f"成功: {results['success_count']}件")
    print(f"失敗: {results['failed_count']}件")
    
    if results['executed_posts']:
        print(f"\n📝 実行詳細:")
        for i, post_result in enumerate(results['executed_posts'], 1):
            status_emoji = "✅" if post_result['status'] == 'success' else "❌"
            print(f"  {i}. {status_emoji} {post_result.get('message', 'N/A')}")


def print_single_execution_result(result):
    """単一投稿実行結果を表示"""
    print("\n" + "="*50)
    print("📊 投稿実行結果")
    print("="*50)
    
    status_emoji = {
        'success': '✅',
        'failed': '❌',
        'exception': '⚠️',
        'no_action': '📭'
    }.get(result['status'], '❓')
    
    print(f"ステータス: {status_emoji} {result['status']}")
    print(f"メッセージ: {result['message']}")
    print(f"実行時刻: {result['execution_time']}")
    
    if result.get('post_info'):
        post_info = result['post_info']
        print(f"\n📝 投稿情報:")
        print(f"  タイトル: {post_info['title']}")
        print(f"  作品ID: {post_info['work_id']}")
        print(f"  予定時刻: {post_info['scheduled_time']}")
        
    if result.get('performance'):
        perf = result['performance']
        print(f"\n⏱️ パフォーマンス:")
        print(f"  総実行時間: {perf.get('total_execution_time', 0):.1f}秒")
        if 'wordpress_post_time' in perf:
            print(f"  WordPress投稿時間: {perf['wordpress_post_time']:.1f}秒")


def test_wordpress_connection(wp_api):
    """WordPress API接続テスト"""
    print("\n🔗 WordPress API接続テスト")
    print("-" * 30)
    
    try:
        # WordPress API接続テスト
        connection_success = wp_api.test_connection()
        if connection_success:
            print("✅ WordPress API接続成功")
            
            # サイト情報も取得してみる
            try:
                site_info = wp_api.get_site_info()
                if site_info:
                    print(f"   サイト名: {site_info.get('name', 'N/A')}")
                    print(f"   サイトURL: {site_info.get('url', 'N/A')}")
                    print(f"   説明: {site_info.get('description', 'N/A')}")
                else:
                    print("   サイト情報: 取得できませんでした")
            except Exception as e:
                print(f"   サイト情報取得エラー: {e}")
        else:
            print("❌ WordPress API接続失敗")
    except Exception as e:
        print(f"❌ WordPress API接続エラー: {e}")


def test_config_access(config_manager):
    """設定アクセステスト"""
    print("\n⚙️ 設定アクセステスト")
    print("-" * 30)
    
    try:
        # WordPress設定テスト
        wp_config = config_manager.wordpress
        print("✅ WordPress設定読み込み成功")
        print(f"   URL: {wp_config.url}")
        print(f"   ユーザー名: {wp_config.username}")
        print(f"   パスワード: {'*' * 8}")
        
        # DMM API設定テスト
        dmm_config = config_manager.dmm_api
        print("✅ DMM API設定読み込み成功")
        print(f"   API ID: {dmm_config.api_id[:8]}...")
        print(f"   アフィリエイトID: {dmm_config.affiliate_id}")
        
        # Gemini API設定テスト
        gemini_config = config_manager.gemini
        print("✅ Gemini API設定読み込み成功")
        print(f"   API Key: {gemini_config.api_key[:8]}...")
        
        # システム設定テスト
        system_config = config_manager.system
        print("✅ システム設定読み込み成功")
        print(f"   VPSモード: {system_config.vps_mode}")
        print(f"   検索制限: {system_config.search_limit}")
        
    except Exception as e:
        print(f"❌ 設定アクセスエラー: {e}")


if __name__ == "__main__":
    main()