#!/usr/bin/env python3
"""
WordPress自動投稿システム メインスクリプト
"""
import sys
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.auto_posting_system import AutoPostingSystem
from src.services.exceptions import AutoPostingError, ConfigurationError
from src.config.secure_config_manager import SecureConfigManager


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
    
    return parser.parse_args()


def main():
    """メイン処理"""
    try:
        # コマンドライン引数の解析
        args = parse_arguments()
        
        # VPSモードの場合は設定ファイルを自動変更
        config_file = args.config
        if args.vps_mode:
            config_file = 'config/config.vps.ini'
            print(f"VPSモード: {config_file} を使用")
        
        # システムの初期化
        system = AutoPostingSystem(
            config_file=config_file,
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
        else:
            # 通常の投稿処理
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