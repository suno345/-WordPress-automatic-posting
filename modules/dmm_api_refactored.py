"""
リファクタリング済みDMM API クライアント
"""
import requests
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

from .constants import Constants, DefaultValues
from .exceptions import DMMAPIError
from .utils import safe_get_nested, retry_on_exception


logger = logging.getLogger(__name__)


class DMMAPIClient:
    """DMM アフィリエイト API クライアント（リファクタリング版）"""
    
    def __init__(self, api_id: str, affiliate_id: str = "", request_delay: int = None):
        """
        DMM アフィリエイト API クライアントの初期化
        
        Args:
            api_id: DMM API ID
            affiliate_id: DMM アフィリエイト ID
            request_delay: リクエスト間の待機時間（秒）
        """
        self.api_base_url = Constants.DMM_API_BASE_URL
        self.api_id = api_id
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay or Constants.REQUEST_DELAY
        
        # SessionオブジェクトでHTTP接続を効率化
        self.session = requests.Session()
        self.session.timeout = Constants.API_TIMEOUT
        
        # ログの初期設定完了フラグ
        self._structure_logged = False
        
        logger.info(f"DMM API client initialized with API ID: {api_id[:10]}...")
    
    def __enter__(self):
        """コンテキストマネージャーのエントリ"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了時にセッションをクローズ"""
        self.session.close()
    
    @retry_on_exception(max_retries=Constants.MAX_RETRIES)
    def get_items(self, limit: int = 20, offset: int = 1) -> List[Dict]:
        """
        商品一覧を取得（新着順の同人コミック、レビューあり）
        
        Args:
            limit: 取得件数
            offset: オフセット
        
        Returns:
            商品リスト
        
        Raises:
            DMMAPIError: API呼び出しに失敗した場合
        """
        try:
            time.sleep(self.request_delay)
            
            params = self._build_api_params(limit, offset)
            
            response = self.session.get(f"{self.api_base_url}/ItemList", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # APIステータスチェック
            result_status = safe_get_nested(data, 'result', 'status')
            if result_status != 200:
                error_msg = safe_get_nested(data, 'result', 'message', default='Unknown error')
                raise DMMAPIError(f"DMM API Error: {error_msg}")
            
            items = safe_get_nested(data, 'result', 'items', default=[])
            logger.info(f"Retrieved {len(items)} items from DMM API")
            
            # 初回のみデータ構造をログ出力
            if items and not self._structure_logged:
                self._log_data_structure(items[0])
                self._structure_logged = True
            
            return items
            
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP Error from DMM API: {e}"
            logger.error(error_msg)
            raise DMMAPIError(error_msg)
        except Exception as e:
            error_msg = f"Error fetching items from DMM API: {e}"
            logger.error(error_msg)
            raise DMMAPIError(error_msg)
    
    def _build_api_params(self, limit: int, offset: int) -> Dict[str, str]:
        """API リクエストパラメータを構築"""
        params = {
            'api_id': self.api_id,
            'site': Constants.DMM_SITE,
            'service': Constants.DMM_SERVICE,
            'floor': Constants.DMM_FLOOR,
            'hits': str(limit),
            'offset': str(offset),
            'sort': 'date',
            'output': 'json',
            'article': 'genre',
            'article_id': Constants.DMM_GENRE_ID
        }
        
        # affiliate_idが設定されている場合のみ追加
        if self.affiliate_id:
            params['affiliate_id'] = self.affiliate_id
        
        return params
    
    def _log_data_structure(self, sample_item: Dict) -> None:
        """データ構造のログ出力（初回のみ）"""
        sample_images_count = len(safe_get_nested(
            sample_item, 'sampleImageURL', 'sample_l', 'image', default=[]
        ))
        
        logger.info(f"Sample data structure - Images: {sample_images_count}, "
                   f"Content ID: {sample_item.get('content_id', 'N/A')}")
    
    def is_comic_work(self, api_item: Dict) -> bool:
        """
        コミック作品かどうかを判定
        
        Args:
            api_item: API レスポンスアイテム
        
        Returns:
            コミック作品の場合True
        """
        # imageURLのパスにcomicが含まれているかチェック
        image_url = safe_get_nested(api_item, 'imageURL', 'large')
        if image_url and '/comic/' in image_url:
            return True
        
        # ジャンルにコミック関連のものが含まれているかチェック
        genres = safe_get_nested(api_item, 'iteminfo', 'genre', default=[])
        for genre in genres:
            genre_name = genre.get('name', '').lower()
            if any(keyword in genre_name for keyword in ['コミック', 'マンガ', '漫画']):
                return True
        
        return True  # デフォルトでは全て通す
    
    def convert_to_work_data(self, api_item: Dict) -> Optional[Dict]:
        """
        API レスポンスを内部データ形式に変換
        
        Args:
            api_item: API レスポンスアイテム
        
        Returns:
            変換された作品データ、変換失敗時はNone
        """
        try:
            # コミック作品のみを対象とする
            if not self.is_comic_work(api_item):
                return None
            
            work_data = {
                'url': api_item.get('URL', ''),
                'work_id': api_item.get('content_id', ''),
                'title': api_item.get('title', ''),
                'circle_name': self._extract_circle_name(api_item),
                'author_name': self._extract_author_name(api_item),
                'category': DefaultValues.DEFAULT_CATEGORY,
                'package_image_url': safe_get_nested(api_item, 'imageURL', 'large', default=''),
                'description': api_item.get('comment', DefaultValues.DEFAULT_DESCRIPTION),
                'page_count': self._extract_page_count(api_item),
                'genres': self._extract_genres(api_item),
                'sample_images': self._extract_sample_images(api_item),
                'reviews': self._extract_reviews(api_item),
                'affiliate_url': api_item.get('affiliateURL', api_item.get('URL', '')),
                'price': safe_get_nested(api_item, 'prices', 'price', default=''),
                'release_date': api_item.get('date', '')
            }
            
            return work_data
            
        except Exception as e:
            logger.error(f"Error converting API item to work data: {e}")
            return None
    
    def _extract_genres(self, api_item: Dict) -> List[str]:
        """ジャンル情報の抽出"""
        genres = []
        genre_items = safe_get_nested(api_item, 'iteminfo', 'genre', default=[])
        
        for genre_item in genre_items:
            if isinstance(genre_item, dict) and 'name' in genre_item:
                genres.append(genre_item['name'])
        
        return genres
    
    def _extract_sample_images(self, api_item: Dict) -> List[str]:
        """サンプル画像の抽出"""
        sample_images = safe_get_nested(
            api_item, 'sampleImageURL', 'sample_l', 'image', default=[]
        )
        
        # リストが返されることを保証
        if not isinstance(sample_images, list):
            return []
        
        return sample_images
    
    def _extract_reviews(self, api_item: Dict) -> List[Dict[str, str]]:
        """レビュー情報の抽出"""
        reviews = []
        review_data = api_item.get('review')
        
        if review_data:
            average = review_data.get('average', 0)
            count = review_data.get('count', 0)
            reviews.append({
                'rating': f"{average}点 ({count}件)",
                'text': f"平均評価: {average}点"
            })
        
        return reviews
    
    def _extract_circle_name(self, api_item: Dict) -> str:
        """サークル名を抽出"""
        makers = safe_get_nested(api_item, 'iteminfo', 'maker', default=[])
        
        if makers and len(makers) > 0:
            return makers[0].get('name', DefaultValues.CIRCLE_NAME_UNKNOWN)
        
        return DefaultValues.CIRCLE_NAME_UNKNOWN
    
    def _extract_author_name(self, api_item: Dict) -> str:
        """作者名を抽出（サークル名と同じ場合が多い）"""
        return self._extract_circle_name(api_item)
    
    def _extract_page_count(self, api_item: Dict) -> str:
        """ページ数を抽出"""
        volume = api_item.get('volume', '')
        
        if volume and volume.isdigit():
            return f"{volume}ページ"
        elif volume:
            return volume
        
        return DefaultValues.PAGE_COUNT_UNKNOWN
    
    def get_work_detail(self, content_id: str) -> Optional[Dict]:
        """
        特定の作品の詳細情報を取得
        
        Args:
            content_id: コンテンツID
        
        Returns:
            作品詳細データ、失敗時はNone
        """
        try:
            time.sleep(self.request_delay)
            
            params = {
                'api_id': self.api_id,
                'cid': content_id,
                'output': 'json'
            }
            
            if self.affiliate_id:
                params['affiliate_id'] = self.affiliate_id
            
            response = self.session.get(f"{self.api_base_url}/ItemList", params=params)
            response.raise_for_status()
            
            data = response.json()
            items = safe_get_nested(data, 'result', 'items', default=[])
            
            if items:
                return self.convert_to_work_data(items[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching work detail for {content_id}: {e}")
            return None