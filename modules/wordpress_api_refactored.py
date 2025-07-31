"""
リファクタリング済みWordPress API クライアント
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin

from .constants import Constants
from .exceptions import WordPressAPIError
from .utils import retry_on_exception, create_tag_slug, normalize_string


logger = logging.getLogger(__name__)


class WordPressAPI:
    """WordPress REST API クライアント（リファクタリング版）"""
    
    def __init__(self, url: str, username: str, password: str):
        """
        WordPress REST APIクライアントの初期化
        
        Args:
            url: WordPressサイトのURL
            username: ユーザー名
            password: アプリケーションパスワード
        """
        self.site_url = url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/{Constants.WP_API_VERSION}"
        
        # Sessionオブジェクトを使用してHTTP接続を再利用
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
        self.session.timeout = Constants.API_TIMEOUT
        
        # キャッシュ用辞書
        self._category_cache: Dict[str, int] = {}
        self._tag_cache: Dict[str, int] = {}
        
        logger.info(f"WordPress API client initialized for: {self.site_url}")
    
    def __enter__(self):
        """コンテキストマネージャーのエントリ"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了時にセッションをクローズ"""
        self.session.close()
    
    @retry_on_exception(max_retries=Constants.MAX_RETRIES)
    def create_post(
        self, 
        title: str, 
        content: str, 
        categories: List[int], 
        tags: List[int], 
        status: str = 'future', 
        scheduled_date: Optional[datetime] = None,
        slug: Optional[str] = None
    ) -> Optional[int]:
        """
        WordPressに記事を投稿
        
        Args:
            title: 記事タイトル
            content: 記事本文
            categories: カテゴリーIDのリスト
            tags: タグIDのリスト
            status: 投稿ステータス
            scheduled_date: 予約投稿日時
            slug: URLスラッグ（商品IDなど）
        
        Returns:
            投稿ID、失敗時はNone
        
        Raises:
            WordPressAPIError: API呼び出しに失敗した場合
        """
        try:
            # 予約投稿の日時設定
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
            
            # スラッグが指定されている場合は追加
            if slug:
                post_data['slug'] = slug
            
            response = self.session.post(f"{self.api_url}/posts", json=post_data)
            
            if response.status_code == 201:
                post_id = response.json().get('id')
                logger.info(f"Successfully created post: {title} (ID: {post_id})")
                return post_id
            else:
                error_msg = f"Failed to create post: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise WordPressAPIError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error creating post: {e}"
            logger.error(error_msg)
            raise WordPressAPIError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating post: {e}"
            logger.error(error_msg)
            raise WordPressAPIError(error_msg)
    
    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        カテゴリーを取得または作成
        
        Args:
            category_name: カテゴリー名
        
        Returns:
            カテゴリーID、失敗時はNone
        """
        normalized_name = normalize_string(category_name)
        
        # キャッシュチェック
        if normalized_name in self._category_cache:
            return self._category_cache[normalized_name]
        
        category_id = self._get_or_create_taxonomy_term('categories', normalized_name)
        
        if category_id:
            self._category_cache[normalized_name] = category_id
        
        return category_id
    
    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """
        タグを取得または作成
        
        Args:
            tag_name: タグ名
        
        Returns:
            タグID、失敗時はNone
        """
        normalized_name = normalize_string(tag_name)
        
        # キャッシュチェック
        if normalized_name in self._tag_cache:
            return self._tag_cache[normalized_name]
        
        tag_id = self._get_or_create_taxonomy_term('tags', normalized_name)
        
        if tag_id:
            self._tag_cache[normalized_name] = tag_id
        
        return tag_id
    
    def _get_or_create_taxonomy_term(self, taxonomy: str, term_name: str) -> Optional[int]:
        """
        タクソノミータームの取得または作成（共通処理）
        
        Args:
            taxonomy: タクソノミー名（'categories' または 'tags'）
            term_name: ターム名
        
        Returns:
            ターID、失敗時はNone
        """
        try:
            # 既存のタームを検索
            response = self.session.get(
                f"{self.api_url}/{taxonomy}",
                params={'search': term_name, 'per_page': 50}
            )
            
            if response.status_code == 200:
                terms = response.json()
                for term in terms:
                    if term['name'].lower() == term_name.lower():
                        return term['id']
            
            # タームが存在しない場合は作成
            create_response = self.session.post(
                f"{self.api_url}/{taxonomy}",
                json={'name': term_name}
            )
            
            if create_response.status_code == 201:
                term_id = create_response.json()['id']
                logger.info(f"Created new {taxonomy[:-1]}: {term_name} (ID: {term_id})")
                return term_id
            else:
                logger.warning(f"Failed to create {taxonomy[:-1]}: {term_name}")
            
        except Exception as e:
            logger.error(f"Error handling {taxonomy[:-1]} '{term_name}': {e}")
        
        return None
    
    def upload_media(self, image_url: str, filename: str) -> Optional[Dict[str, Union[int, str]]]:
        """
        画像をWordPressメディアライブラリにアップロード
        
        Args:
            image_url: 画像URL
            filename: ファイル名
        
        Returns:
            アップロード結果の辞書、失敗時はNone
        """
        try:
            # 画像をダウンロード
            image_response = self.session.get(image_url, timeout=Constants.API_TIMEOUT)
            image_response.raise_for_status()
            
            # ファイルサイズチェック（例：10MB制限）
            content_length = len(image_response.content)
            if content_length > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Image too large: {content_length} bytes")
                return None
            
            # WordPressにアップロード
            files = {
                'file': (filename, image_response.content, 'image/jpeg')
            }
            
            upload_response = self.session.post(f"{self.api_url}/media", files=files)
            
            if upload_response.status_code == 201:
                media_data = upload_response.json()
                logger.info(f"Successfully uploaded media: {filename}")
                return {
                    'id': media_data['id'],
                    'url': media_data['source_url']
                }
            else:
                logger.error(f"Failed to upload media: {upload_response.status_code}")
            
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
        
        return None
    
    def get_tag_archive_url(self, tag_name: str) -> str:
        """
        タグアーカイブページのURLを生成
        
        Args:
            tag_name: タグ名
        
        Returns:
            タグアーカイブURL
        """
        tag_slug = create_tag_slug(tag_name)
        return urljoin(self.site_url, f'/tag/{tag_slug}/')
    
    def test_connection(self) -> bool:
        """
        WordPress APIへの接続テスト
        
        Returns:
            接続成功時True、失敗時False
        """
        try:
            response = self.session.get(f"{self.api_url}/users/me")
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Connected as user: {user_data.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"Connection test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False
    
    def get_site_info(self) -> Optional[Dict[str, str]]:
        """
        サイト情報を取得
        
        Returns:
            サイト情報の辞書、失敗時はNone
        """
        try:
            response = self.session.get(f"{self.site_url}/wp-json")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting site info: {e}")
        
        return None