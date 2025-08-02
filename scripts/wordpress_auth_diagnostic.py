#!/usr/bin/env python3
"""
WordPress認証診断スクリプト
"""
import sys
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.secure_config_manager import SecureConfigManager

class WordPressAuthDiagnostic:
    """WordPress認証診断クラス"""
    
    def __init__(self):
        # 設定ファイルから直接読み込み
        import configparser
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.vps.ini')
        config.read(config_path)
        
        self.site_url = config.get('wordpress', 'url').rstrip('/')
        self.username = config.get('wordpress', 'username')
        self.password = config.get('wordpress', 'password')
        
        # REST API URL
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        
        print(f"診断対象サイト: {self.site_url}")
        print(f"ユーザー名: {self.username}")
        print(f"パスワード: {'*' * len(self.password)}")
        print("-" * 50)
    
    def run_full_diagnostic(self):
        """完全な診断を実行"""
        print("🔍 WordPress認証診断開始\n")
        
        results = {
            "basic_connection": self.test_basic_connection(),
            "rest_api_discovery": self.test_rest_api_discovery(),
            "authentication": self.test_authentication(),
            "user_permissions": self.test_user_permissions(),
            "post_creation_capability": self.test_post_creation_capability()
        }
        
        self.print_diagnostic_summary(results)
        return results
    
    def test_basic_connection(self):
        """基本的な接続テスト"""
        print("1️⃣ 基本接続テスト")
        
        try:
            response = requests.get(self.site_url, timeout=10)
            if response.status_code == 200:
                print("✅ サイトへの基本接続: 成功")
                return {"success": True, "status_code": response.status_code}
            else:
                print(f"❌ サイトへの基本接続: 失敗 (ステータス: {response.status_code})")
                return {"success": False, "status_code": response.status_code}
        except Exception as e:
            print(f"❌ サイトへの基本接続: エラー - {e}")
            return {"success": False, "error": str(e)}
    
    def test_rest_api_discovery(self):
        """REST API検出テスト"""
        print("\n2️⃣ REST API検出テスト")
        
        try:
            # WordPress REST API ルートをテスト
            response = requests.get(f"{self.site_url}/wp-json", timeout=10)
            if response.status_code == 200:
                api_info = response.json()
                print("✅ REST API検出: 成功")
                print(f"   - WordPress バージョン: {api_info.get('description', 'Unknown')}")
                print(f"   - API 認証方式: {', '.join(api_info.get('authentication', ['Unknown']))}")
                return {"success": True, "api_info": api_info}
            else:
                print(f"❌ REST API検出: 失敗 (ステータス: {response.status_code})")
                return {"success": False, "status_code": response.status_code}
        except Exception as e:
            print(f"❌ REST API検出: エラー - {e}")
            return {"success": False, "error": str(e)}
    
    def test_authentication(self):
        """認証テスト"""
        print("\n3️⃣ 認証テスト")
        
        try:
            # 認証が必要なエンドポイント /users/me をテスト
            response = requests.get(
                f"{self.api_url}/users/me",
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print("✅ 認証テスト: 成功")
                print(f"   - ユーザーID: {user_data.get('id')}")
                print(f"   - 表示名: {user_data.get('name')}")
                print(f"   - 役割: {', '.join(user_data.get('roles', ['Unknown']))}")
                return {"success": True, "user_data": user_data}
            elif response.status_code == 401:
                print("❌ 認証テスト: 認証失敗 (401 Unauthorized)")
                print("   💡 考えられる原因:")
                print("      - パスワードが間違っている")
                print("      - アプリケーションパスワードが必要")
                print("      - Basic認証が無効化されている")
                return {"success": False, "status_code": 401, "auth_error": True}
            else:
                print(f"❌ 認証テスト: 失敗 (ステータス: {response.status_code})")
                print(f"   - レスポンス: {response.text[:200]}")
                return {"success": False, "status_code": response.status_code}
        except Exception as e:
            print(f"❌ 認証テスト: エラー - {e}")
            return {"success": False, "error": str(e)}
    
    def test_user_permissions(self):
        """ユーザー権限テスト"""
        print("\n4️⃣ ユーザー権限テスト")
        
        try:
            # カテゴリ一覧取得（読み取り権限）
            response = requests.get(
                f"{self.api_url}/categories",
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code == 200:
                categories = response.json()
                print(f"✅ カテゴリ読み取り: 成功 ({len(categories)}件取得)")
                
                # 投稿一覧取得（読み取り権限）
                posts_response = requests.get(
                    f"{self.api_url}/posts",
                    auth=(self.username, self.password),
                    params={"per_page": 1},
                    timeout=10
                )
                
                if posts_response.status_code == 200:
                    print("✅ 投稿読み取り: 成功")
                    return {"success": True, "read_permissions": True}
                else:
                    print(f"❌ 投稿読み取り: 失敗 (ステータス: {posts_response.status_code})")
                    return {"success": False, "read_permissions": False}
            else:
                print(f"❌ 権限テスト: 失敗 (ステータス: {response.status_code})")
                return {"success": False, "status_code": response.status_code}
        except Exception as e:
            print(f"❌ 権限テスト: エラー - {e}")
            return {"success": False, "error": str(e)}
    
    def test_post_creation_capability(self):
        """投稿作成機能テスト"""
        print("\n5️⃣ 投稿作成機能テスト")
        
        try:
            # テスト投稿データ
            test_post = {
                "title": f"認証診断テスト - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "content": "これは認証診断のテスト投稿です。作成後すぐに削除されます。",
                "status": "draft",  # 下書きで作成
                "categories": [1]   # 未分類カテゴリ
            }
            
            # テスト投稿作成
            response = requests.post(
                f"{self.api_url}/posts",
                json=test_post,
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 201:
                post_data = response.json()
                post_id = post_data["id"]
                print(f"✅ テスト投稿作成: 成功 (ID: {post_id})")
                
                # 作成したテスト投稿を削除
                delete_response = requests.delete(
                    f"{self.api_url}/posts/{post_id}",
                    auth=(self.username, self.password),
                    timeout=10
                )
                
                if delete_response.status_code == 200:
                    print("✅ テスト投稿削除: 成功")
                else:
                    print(f"⚠️ テスト投稿削除: 失敗 (手動で削除してください: ID {post_id})")
                
                return {"success": True, "post_creation": True, "test_post_id": post_id}
            elif response.status_code == 401:
                print("❌ テスト投稿作成: 認証エラー (401)")
                print("   💡 WordPress管理画面でアプリケーションパスワードを確認してください")
                return {"success": False, "status_code": 401, "auth_error": True}
            elif response.status_code == 403:
                print("❌ テスト投稿作成: 権限不足 (403)")
                print("   💡 ユーザーに投稿作成権限がありません")
                return {"success": False, "status_code": 403, "permission_error": True}
            else:
                print(f"❌ テスト投稿作成: 失敗 (ステータス: {response.status_code})")
                print(f"   - レスポンス: {response.text[:200]}")
                return {"success": False, "status_code": response.status_code, "response": response.text[:200]}
        except Exception as e:
            print(f"❌ テスト投稿作成: エラー - {e}")
            return {"success": False, "error": str(e)}
    
    def print_diagnostic_summary(self, results):
        """診断結果サマリーを出力"""
        print("\n" + "="*50)
        print("🎯 診断結果サマリー")
        print("="*50)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result.get("success", False))
        
        print(f"実行テスト数: {total_tests}")
        print(f"成功テスト数: {passed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 すべてのテストに合格しました！")
            print("WordPress認証は正常に動作しています。")
        else:
            print(f"\n⚠️ {total_tests - passed_tests}個のテストが失敗しました。")
            
            # 失敗の種類に応じた解決方法を提示
            auth_result = results.get("authentication", {})
            post_result = results.get("post_creation_capability", {})
            
            if auth_result.get("auth_error"):
                print("\n🔧 推奨解決方法:")
                print("1. WordPress管理画面にログイン")
                print("2. ユーザー > プロフィール に移動")
                print("3. 「アプリケーションパスワード」を新規作成")
                print("4. 生成されたパスワードを.envファイルのWORDPRESS_PASSWORDに設定")
            
            if post_result.get("permission_error"):
                print("\n🔧 権限関連の解決方法:")
                print("1. WordPress管理画面で対象ユーザーの役割を確認")
                print("2. 「編集者」以上の権限を付与")
                print("3. プラグインによる権限制限がないか確認")

def main():
    """メイン実行関数"""
    diagnostic = WordPressAuthDiagnostic()
    results = diagnostic.run_full_diagnostic()
    
    # 診断完了
    print(f"\n✨ 診断完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results

if __name__ == "__main__":
    main()