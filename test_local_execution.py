#!/usr/bin/env python3
"""
ローカル本番環境テスト用スクリプト
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.auto_posting_system import AutoPostingSystem


def setup_test_environment():
    """テスト環境の設定"""
    print("=== ローカル本番環境テスト ===")
    print(f"実行時刻: {datetime.now()}")
    
    # 環境変数の確認
    required_env_vars = [
        'WORDPRESS_URL',
        'WORDPRESS_USERNAME', 
        'WORDPRESS_PASSWORD',
        'DMM_API_ID',
        'DMM_AFFILIATE_ID',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 以下の環境変数が設定されていません:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n環境変数を設定してから実行してください。")
        return False
    
    print("✅ 環境変数設定確認完了")
    return True


def show_schedule_preview():
    """投稿スケジュール予測を表示"""
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"\n📅 投稿スケジュール予測:")
    print(f"現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"予約投稿時刻: {tomorrow.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"投稿日: {tomorrow.strftime('%Y年%m月%d日')}")


def run_test_execution():
    """テスト実行"""
    try:
        print("\n🚀 システム初期化中...")
        
        # VPSモードで実行（config.vps.ini使用）
        system = AutoPostingSystem(
            config_file='config/config.vps.ini',
            verbose=True,
            skip_review_check=False
        )
        
        print("\n🔗 接続テスト実行中...")
        connection_results = system.test_connections()
        
        all_connected = True
        for service, status in connection_results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {service}: {status_icon}")
            if not status:
                all_connected = False
        
        if not all_connected:
            print("❌ 接続テストに失敗しました。設定を確認してください。")
            return False
        
        print("\n📊 システム状態:")
        system.display_status()
        
        # 実際に実行するか確認
        print(f"\n⚠️  この実行により以下が行われます:")
        print(f"   - DMM APIから作品データを取得")
        print(f"   - 男性向けコミック作品をフィルタリング")
        print(f"   - Gemini APIで紹介文をリライト")
        print(f"   - WordPressに予約投稿を作成")
        
        # 明日の投稿時刻を表示
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"   - 投稿予約時刻: {tomorrow.strftime('%Y年%m月%d日 %H:%M')}")
        
        response = input(f"\n実行しますか？ (y/N): ")
        if response.lower() != 'y':
            print("テストを中止しました。")
            return False
        
        print(f"\n🔄 メイン処理実行中...")
        result = system.run()
        
        print(f"\n✅ テスト実行完了!")
        print(f"📈 実行結果:")
        print(f"   - 処理した作品数: {result['processed']}件")
        print(f"   - 投稿した記事数: {result['posted']}件")
        print(f"   - 総投稿数: {result['total_posted']}件")
        
        if result['posted'] > 0:
            print(f"\n🎯 WordPressで予約投稿を確認してください:")
            print(f"   - WordPress管理画面 → 投稿 → 予約投稿")
            print(f"   - 投稿時刻: {tomorrow.strftime('%Y年%m月%d日 %H:%M')}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False


def show_vps_simulation():
    """VPS運用シミュレーション説明"""
    print(f"\n🖥️  VPS運用シミュレーション:")
    print(f"   cron設定: */15 * * * * (15分間隔)")
    
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"\n📅 今日VPSで実行した場合の投稿スケジュール例:")
    for i in range(6):  # 6回分のスケジュール例
        execution_time = now.replace(minute=(now.minute // 15) * 15 + i * 15, second=0, microsecond=0)
        if execution_time.minute >= 60:
            execution_time = execution_time + timedelta(hours=1)
            execution_time = execution_time.replace(minute=execution_time.minute % 60)
        
        post_time = tomorrow + timedelta(minutes=i * 15)
        
        print(f"   {i+1}回目実行 {execution_time.strftime('%H:%M')} → 投稿予約 {post_time.strftime('%m/%d %H:%M')}")


def main():
    """メイン処理"""
    if not setup_test_environment():
        sys.exit(1)
    
    show_schedule_preview()
    show_vps_simulation()
    
    # テスト実行
    success = run_test_execution()
    
    if success:
        print(f"\n🎉 ローカルテストが正常に完了しました!")
        print(f"   VPS環境でも同様に動作します。")
        sys.exit(0)
    else:
        print(f"\n❌ テストに失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()