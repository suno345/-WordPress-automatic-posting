#!/usr/bin/env python3
"""
簡素化版テストスクリプト - .env直接参照
config.ini系列を使わずに環境変数のみで動作
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .envファイルを手動で読み込み（python-dotenvを使わない簡素版）
def load_env_file(env_path=".env"):
    """簡素版 .env読み込み"""
    env_file = Path(env_path)
    if not env_file.exists():
        print(f"❌ {env_path} が見つかりません")
        return False
    
    try:
        with env_file.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ {env_path} 読み込み完了")
        return True
    except Exception as e:
        print(f"❌ {env_path} 読み込みエラー: {e}")
        return False

def test_dmm_api():
    """DMM API簡素版テスト"""
    print("🎯 DMM API簡素版テスト開始...")
    
    try:
        from src.api.dmm_api import DMMAPIClient
        
        # 環境変数から直接取得
        api_id = os.getenv('DMM_API_ID')
        affiliate_id = os.getenv('DMM_AFFILIATE_ID')
        
        if not api_id or not affiliate_id:
            print("❌ DMM API設定が不足")
            print(f"DMM_API_ID: {'設定済み' if api_id else '未設定'}")
            print(f"DMM_AFFILIATE_ID: {'設定済み' if affiliate_id else '未設定'}")
            return False
        
        print(f"DMM_API_ID: {api_id}")
        print(f"DMM_AFFILIATE_ID: {affiliate_id}")
        
        # DMMクライアント初期化（環境変数直接指定）
        dmm_client = DMMAPIClient(api_id, affiliate_id)
        
        # 作品取得テスト
        print("作品取得テスト中...")
        items = dmm_client.get_items(limit=3, offset=1, use_genre_filter=True)
        print(f"取得アイテム数: {len(items)}")
        
        if items:
            for i, item in enumerate(items, 1):
                title = item.get('title', '不明')
                content_id = item.get('content_id', '不明')
                print(f"  {i}. {title} (ID: {content_id})")
            print("✅ DMM API テスト成功")
            return True
        else:
            print("❌ 作品取得に失敗")
            return False
            
    except Exception as e:
        print(f"❌ DMM API テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gemini_api():
    """Gemini API簡素版テスト"""
    print("\n🎯 Gemini API簡素版テスト開始...")
    
    try:
        from src.api.gemini_api import GeminiAPI
        
        # 環境変数から直接取得
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            print("❌ GEMINI_API_KEY が未設定")
            return False
        
        print(f"Gemini APIキー: {api_key[:10]}...")
        
        # Geminiクライアント初期化
        gemini_api = GeminiAPI(api_key=api_key)
        
        # テスト記事生成
        test_title = "テスト作品タイトル"
        test_description = "これはテスト用の作品説明文です。DMM APIから取得した作品情報をもとに記事を生成します。"
        
        print("記事生成テスト中...")
        article = gemini_api.rewrite_description(
            title=test_title,
            original_description=test_description
        )
        
        if article:
            print(f"✅ 記事生成成功: {len(article)}文字")
            print(f"記事プレビュー: {article[:100]}...")
            return True
        else:
            print("❌ 記事生成失敗")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("=" * 50)
    print("🚀 簡素化版API統合テスト")
    print("=" * 50)
    
    # .env読み込み
    if not load_env_file():
        print("❌ 環境変数読み込み失敗")
        return False
    
    # 環境変数確認
    print("\n📋 環境変数確認:")
    required_vars = ['DMM_API_ID', 'DMM_AFFILIATE_ID', 'GEMINI_API_KEY']
    for var in required_vars:
        value = os.getenv(var)
        status = f"設定済み ({value[:10]}...)" if value else "未設定"
        print(f"  {var}: {status}")
    
    # APIテスト実行
    dmm_success = test_dmm_api()
    gemini_success = test_gemini_api()
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    print(f"DMM API: {'✅ 成功' if dmm_success else '❌ 失敗'}")
    print(f"Gemini API: {'✅ 成功' if gemini_success else '❌ 失敗'}")
    
    if dmm_success and gemini_success:
        print("\n🎉 全テスト成功！記事生成システム正常動作")
        return True
    else:
        print("\n⚠️ 一部テストに失敗しました")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)