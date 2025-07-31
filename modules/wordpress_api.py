import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import base64

logger = logging.getLogger(__name__)


class WordPressAPI:
    def __init__(self, url: str, username: str, password: str):
        """WordPress REST APIクライアントの初期化"""
        self.site_url = url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (username, password)
        self.headers = {
            'Content-Type': 'application/json',
        }
        
        # Basic認証ヘッダーを追加
        credentials = f"{username}:{password}"
        token = base64.b64encode(credentials.encode()).decode('utf-8')
        self.headers['Authorization'] = f'Basic {token}'
        
    def create_post(self, title: str, content: str, categories: List[int], 
                   tags: List[int], status: str = 'future', 
                   scheduled_date: Optional[datetime] = None) -> Optional[int]:
        """WordPressに記事を投稿"""
        try:
            # 予約投稿の日時設定（デフォルトは翌日）
            if scheduled_date is None:
                scheduled_date = datetime.now() + timedelta(days=1)
            
            post_data = {
                'title': title,
                'content': content,
                'status': status,
                'categories': categories,
                'tags': tags,
                'date': scheduled_date.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 201:
                post_id = response.json().get('id')
                logger.info(f"Successfully created post: {title} (ID: {post_id})")
                return post_id
            else:
                logger.error(f"Failed to create post: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return None
    
    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """カテゴリーを取得または作成"""
        try:
            # 既存のカテゴリーを検索
            response = requests.get(
                f"{self.api_url}/categories",
                params={'search': category_name},
                auth=self.auth
            )
            
            if response.status_code == 200:
                categories = response.json()
                for cat in categories:
                    if cat['name'].lower() == category_name.lower():
                        return cat['id']
            
            # カテゴリーが存在しない場合は作成
            create_response = requests.post(
                f"{self.api_url}/categories",
                json={'name': category_name},
                headers=self.headers,
                auth=self.auth
            )
            
            if create_response.status_code == 201:
                return create_response.json()['id']
            
        except Exception as e:
            logger.error(f"Error handling category: {e}")
        
        return None
    
    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """タグを取得または作成"""
        try:
            # 既存のタグを検索
            response = requests.get(
                f"{self.api_url}/tags",
                params={'search': tag_name},
                auth=self.auth
            )
            
            if response.status_code == 200:
                tags = response.json()
                for tag in tags:
                    if tag['name'].lower() == tag_name.lower():
                        return tag['id']
            
            # タグが存在しない場合は作成
            create_response = requests.post(
                f"{self.api_url}/tags",
                json={'name': tag_name},
                headers=self.headers,
                auth=self.auth
            )
            
            if create_response.status_code == 201:
                return create_response.json()['id']
            
        except Exception as e:
            logger.error(f"Error handling tag: {e}")
        
        return None
    
    def upload_media(self, image_url: str, filename: str) -> Optional[Dict]:
        """画像をWordPressメディアライブラリにアップロード"""
        try:
            # 画像をダウンロード
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                return None
            
            # WordPressにアップロード
            files = {
                'file': (filename, image_response.content, 'image/jpeg')
            }
            
            upload_response = requests.post(
                f"{self.api_url}/media",
                files=files,
                auth=self.auth
            )
            
            if upload_response.status_code == 201:
                media_data = upload_response.json()
                return {
                    'id': media_data['id'],
                    'url': media_data['source_url']
                }
            
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
        
        return None
    
    def get_tag_archive_url(self, tag_name: str) -> str:
        """タグアーカイブページのURLを生成"""
        # WordPressの一般的なタグアーカイブURL形式
        tag_slug = tag_name.lower().replace(' ', '-')
        return f"{self.site_url}/tag/{tag_slug}/"