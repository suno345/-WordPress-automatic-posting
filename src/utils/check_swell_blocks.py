#!/usr/bin/env python3
"""
SWELLブロック情報取得スクリプト
WordPressサイトからSWELLで利用可能なブロック情報を取得
"""
import requests
import json
from typing import Dict, List, Optional


def get_swell_block_types(site_url: str, username: str, password: str) -> Optional[Dict]:
    """
    WordPress REST APIからブロックタイプ情報を取得
    
    Args:
        site_url: WordPressサイトURL
        username: ユーザー名
        password: アプリケーションパスワード
    
    Returns:
        ブロックタイプ情報の辞書
    """
    try:
        # WordPress REST APIのブロックタイプエンドポイント
        api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/block-types"
        
        response = requests.get(api_url, auth=(username, password))
        response.raise_for_status()
        
        block_types = response.json()
        
        # SWELLブロックのみをフィルタ
        swell_blocks = {}
        for block_name, block_info in block_types.items():
            if 'swell' in block_name.lower() or 'swell' in str(block_info).lower():
                swell_blocks[block_name] = block_info
        
        return swell_blocks
        
    except Exception as e:
        print(f"ブロック情報取得エラー: {e}")
        return None


def get_theme_info(site_url: str, username: str, password: str) -> Optional[Dict]:
    """
    現在のテーマ情報を取得
    """
    try:
        api_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/themes"
        
        response = requests.get(api_url, auth=(username, password))
        response.raise_for_status()
        
        themes = response.json()
        
        # アクティブなテーマを検索
        active_theme = None
        for theme in themes:
            if theme.get('status') == 'active':
                active_theme = theme
                break
        
        return active_theme
        
    except Exception as e:
        print(f"テーマ情報取得エラー: {e}")
        return None


def main():
    """メイン処理"""
    # 設定ファイルから情報を読み込み
    import configparser
    import os
    
    config_file = '../config.ini'
    if not os.path.exists(config_file):
        print("config.iniが見つかりません")
        return
    
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    site_url = config.get('wordpress', 'url')
    username = config.get('wordpress', 'username')
    password = config.get('wordpress', 'password')
    
    print(f"🔍 WordPressサイト情報を調査中: {site_url}")
    
    # テーマ情報取得
    theme_info = get_theme_info(site_url, username, password)
    if theme_info:
        print(f"📋 アクティブテーマ: {theme_info.get('name', 'Unknown')}")
        print(f"   バージョン: {theme_info.get('version', 'Unknown')}")
    
    # SWELLブロック情報取得
    print("\n🎨 SWELLブロック情報を取得中...")
    swell_blocks = get_swell_block_types(site_url, username, password)
    
    if swell_blocks:
        print(f"✅ {len(swell_blocks)}個のSWELLブロックを発見:")
        for block_name, block_info in swell_blocks.items():
            print(f"   - {block_name}")
            if isinstance(block_info, dict) and 'title' in block_info:
                print(f"     タイトル: {block_info['title']}")
    else:
        print("❌ SWELLブロックが見つかりませんでした")
    
    # 結果をJSONファイルに保存
    output_file = '../data/swell_blocks.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    result = {
        'site_url': site_url,
        'theme_info': theme_info,
        'swell_blocks': swell_blocks,
        'timestamp': '2025-07-31'
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 結果を保存: {output_file}")


if __name__ == "__main__":
    main()