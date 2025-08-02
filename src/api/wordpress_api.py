"""
リファクタリング済みWordPress API クライアント
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin

from ..utils.constants import Constants
from ..services.exceptions import WordPressAPIError
from ..utils.utils import retry_on_exception, create_tag_slug, normalize_string
from ..services.resource_manager import SessionMixin


logger = logging.getLogger(__name__)


class WordPressAPI(SessionMixin):
    """WordPress REST API クライアント（リファクタリング版）"""
    
    def __init__(self, url: str, username: str, password: str):
        """
        WordPress REST APIクライアントの初期化
        
        Args:
            url: WordPressサイトのURL
            username: ユーザー名
            password: アプリケーションパスワード
        """
        super().__init__()
        self.site_url = url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/{Constants.WP_API_VERSION}"
        
        # セッション認証の設定
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
        slug: Optional[str] = None,
        featured_image_url: Optional[str] = None
    ) -> Dict[str, Union[bool, int, str]]:
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
            featured_image_url: アイキャッチ画像URL
        
        Returns:
            投稿結果の辞書 (success, post_id, post_url, error)
        
        Raises:
            WordPressAPIError: API呼び出しに失敗した場合
        """
        try:
            # 予約投稿の日時設定
            if scheduled_date is None:
                scheduled_date = datetime.now() + timedelta(days=1)
            
            # アイキャッチ画像のアップロード
            featured_media_id = None
            if featured_image_url:
                media_result = self.upload_media(featured_image_url, f"featured-{slug or 'image'}.jpg")
                if media_result and media_result.get('id'):
                    featured_media_id = media_result['id']
                    logger.info(f"アイキャッチ画像をアップロード: ID {featured_media_id}")
                else:
                    logger.warning(f"アイキャッチ画像のアップロードに失敗: {featured_image_url}")
            
            post_data = {
                'title': title,
                'content': content,
                'status': status,
                'categories': categories,
                'tags': tags,
                'date': scheduled_date.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            
            # アイキャッチ画像IDが取得できた場合は設定
            if featured_media_id:
                post_data['featured_media'] = featured_media_id
            
            # スラッグが指定されている場合は追加
            if slug:
                post_data['slug'] = slug
            
            response = self.session.post(f"{self.api_url}/posts", json=post_data)
            
            if response.status_code == 201:
                post_data_response = response.json()
                post_id = post_data_response.get('id')
                post_url = post_data_response.get('link', '')
                logger.info(f"Successfully created post: {title} (ID: {post_id})")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url
                }
            else:
                error_msg = f"Failed to create post: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error creating post: {e}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error creating post: {e}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
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
            logger.info(f"Downloading image from: {image_url}")
            
            # 画像をダウンロード
            image_response = self.session.get(image_url, timeout=Constants.API_TIMEOUT)
            image_response.raise_for_status()
            
            # Content-Typeを取得
            content_type = image_response.headers.get('content-type', 'image/jpeg')
            logger.info(f"Downloaded image: size={len(image_response.content)} bytes, content-type={content_type}")
            
            # ファイルサイズチェック（例：10MB制限）
            content_length = len(image_response.content)
            if content_length > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Image too large: {content_length} bytes")
                return None
            
            # ファイル名を安全にする（特殊文字除去）
            import re
            safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
            logger.info(f"Using safe filename: {safe_filename}")
            
            # WordPressにアップロード
            files = {
                'file': (safe_filename, image_response.content, content_type)
            }
            
            logger.info(f"Uploading to WordPress: {self.api_url}/media")
            
            # ファイルアップロード時はContent-Typeヘッダーを一時的に削除
            # （requestsが自動的にmultipart/form-dataを設定するため）
            original_content_type = self.session.headers.get('Content-Type')
            if 'Content-Type' in self.session.headers:
                del self.session.headers['Content-Type']
                logger.info("Temporarily removed Content-Type header for file upload")
            
            try:
                upload_response = self.session.post(f"{self.api_url}/media", files=files)
            finally:
                # Content-Typeヘッダーを復元
                if original_content_type:
                    self.session.headers['Content-Type'] = original_content_type
                    logger.info("Restored Content-Type header")
            
            if upload_response.status_code == 201:
                media_data = upload_response.json()
                logger.info(f"Successfully uploaded media: {safe_filename} (ID: {media_data['id']})")
                return {
                    'id': media_data['id'],
                    'url': media_data['source_url']
                }
            else:
                logger.error(f"Failed to upload media: HTTP {upload_response.status_code}")
                logger.error(f"Response body: {upload_response.text[:500]}")
                
                # 権限エラーの場合の詳細情報
                if upload_response.status_code == 401:
                    logger.error("Authentication failed - check WordPress credentials")
                elif upload_response.status_code == 403:
                    logger.error("Permission denied - user may not have media upload privileges")
                
        except Exception as e:
            logger.error(f"Error uploading media from {image_url}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
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
    
    def create_scheduled_post(
        self, 
        title: str, 
        content: str, 
        scheduled_time: datetime,
        categories: List[int] = None,
        tags: List[int] = None,
        **kwargs
    ) -> Dict[str, Union[bool, int, str]]:
        """
        WordPress予約投稿を作成（15分刻み対応）
        
        Args:
            title: 記事タイトル
            content: 記事本文
            scheduled_time: 投稿予定日時
            categories: カテゴリーIDのリスト
            tags: タグIDのリスト
            **kwargs: 追加パラメータ
            
        Returns:
            投稿結果の辞書 (success, post_id, scheduled_time, error)
        """
        try:
            # 15分刻みに調整
            adjusted_time = self._adjust_to_15min_interval(scheduled_time)
            
            # デフォルト値設定
            if categories is None:
                categories = [1]  # 未分類
            if tags is None:
                tags = []
            
            post_data = {
                'title': title,
                'content': content,
                'status': 'future',
                'date': adjusted_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'categories': categories,
                'tags': tags
            }
            
            # 追加パラメータを適用
            if 'slug' in kwargs:
                post_data['slug'] = kwargs['slug']
            if 'excerpt' in kwargs:
                post_data['excerpt'] = kwargs['excerpt']
            
            response = self.session.post(f"{self.api_url}/posts", json=post_data)
            
            if response.status_code == 201:
                post_response = response.json()
                post_id = post_response.get('id')
                post_url = post_response.get('link', '')
                
                logger.info(f"WordPress予約投稿作成成功: {title} (ID: {post_id}, 予定時刻: {adjusted_time.strftime('%Y-%m-%d %H:%M')})")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": post_url,
                    "scheduled_time": adjusted_time.isoformat(),
                    "wordpress_status": "future"
                }
            else:
                error_msg = f"WordPress予約投稿作成失敗: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"WordPress予約投稿作成中にエラー: {e}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_scheduled_posts(self, limit: int = 50) -> List[Dict]:
        """
        予約投稿一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            予約投稿のリスト
        """
        try:
            response = self.session.get(
                f"{self.api_url}/posts",
                params={
                    'status': 'future',
                    'per_page': limit,
                    'orderby': 'date',
                    'order': 'asc'
                }
            )
            
            if response.status_code == 200:
                posts = response.json()
                scheduled_posts = []
                
                for post in posts:
                    scheduled_posts.append({
                        "id": post['id'],
                        "title": post['title']['rendered'],
                        "scheduled_time": post['date'],
                        "status": post['status'],
                        "link": post['link'],
                        "categories": post['categories'],
                        "tags": post['tags']
                    })
                
                logger.info(f"予約投稿取得成功: {len(scheduled_posts)}件")
                return scheduled_posts
            else:
                logger.error(f"予約投稿取得失敗: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"予約投稿取得中にエラー: {e}")
            return []
    
    def find_available_slots(self, base_time: datetime, count: int = 1) -> List[datetime]:
        """
        利用可能な15分刻み投稿枠を検索
        
        Args:
            base_time: 基準時刻
            count: 必要な枠数
            
        Returns:
            利用可能な時刻のリスト
        """
        try:
            # 既存の予約投稿を取得
            scheduled_posts = self.get_scheduled_posts(limit=100)
            occupied_times = set()
            
            for post in scheduled_posts:
                post_time = datetime.fromisoformat(post['scheduled_time'].replace('T', ' ').replace('Z', ''))
                # 15分刻みに丸める
                rounded_time = self._adjust_to_15min_interval(post_time)
                occupied_times.add(rounded_time.strftime('%Y-%m-%d %H:%M'))
            
            # 利用可能な枠を検索
            available_slots = []
            candidate_time = self._adjust_to_15min_interval(base_time)
            
            # 最大1週間先まで検索
            max_search_time = base_time + timedelta(days=7)
            
            while len(available_slots) < count and candidate_time <= max_search_time:
                time_key = candidate_time.strftime('%Y-%m-%d %H:%M')
                
                if time_key not in occupied_times:
                    available_slots.append(candidate_time)
                
                candidate_time += timedelta(minutes=15)
            
            logger.info(f"利用可能な投稿枠: {len(available_slots)}件 (必要: {count}件)")
            return available_slots
            
        except Exception as e:
            logger.error(f"利用可能枠検索中にエラー: {e}")
            return []
    
    def _adjust_to_15min_interval(self, target_time: datetime) -> datetime:
        """
        時刻を15分刻みに調整
        
        Args:
            target_time: 調整対象の時刻
            
        Returns:
            15分刻みに調整された時刻
        """
        # 秒・ミリ秒をリセット
        adjusted = target_time.replace(second=0, microsecond=0)
        
        # 分を15分刻みに調整
        current_minute = adjusted.minute
        remainder = current_minute % 15
        
        if remainder == 0:
            return adjusted
        else:
            # 次の15分刻みに繰り上げ
            minutes_to_add = 15 - remainder
            return adjusted + timedelta(minutes=minutes_to_add)
    
    def delete_scheduled_post(self, post_id: int) -> bool:
        """
        予約投稿を削除
        
        Args:
            post_id: 投稿ID
            
        Returns:
            削除成功時True
        """
        try:
            response = self.session.delete(f"{self.api_url}/posts/{post_id}")
            
            if response.status_code == 200:
                logger.info(f"予約投稿削除成功: ID {post_id}")
                return True
            else:
                logger.error(f"予約投稿削除失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"予約投稿削除中にエラー: {e}")
            return False
    
    def update_scheduled_post_time(self, post_id: int, new_time: datetime) -> bool:
        """
        予約投稿の時刻を変更
        
        Args:
            post_id: 投稿ID
            new_time: 新しい投稿時刻
            
        Returns:
            更新成功時True
        """
        try:
            adjusted_time = self._adjust_to_15min_interval(new_time)
            
            update_data = {
                'date': adjusted_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'status': 'future'
            }
            
            response = self.session.post(f"{self.api_url}/posts/{post_id}", json=update_data)
            
            if response.status_code == 200:
                logger.info(f"予約投稿時刻更新成功: ID {post_id} -> {adjusted_time.strftime('%Y-%m-%d %H:%M')}")
                return True
            else:
                logger.error(f"予約投稿時刻更新失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"予約投稿時刻更新中にエラー: {e}")
            return False