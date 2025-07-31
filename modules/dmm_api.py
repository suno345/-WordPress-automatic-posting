import requests
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class DMMAPIClient:
    def __init__(self, api_id: str, affiliate_id: str = "", request_delay: int = 2):
        """DMM アフィリエイト API クライアント"""
        self.api_base_url = "https://api.dmm.com/affiliate/v3"
        self.api_id = api_id
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay
        self.session = requests.Session()
        
    def get_items(self, limit: int = 20, offset: int = 1) -> List[Dict]:
        """商品一覧を取得（新着順の同人コミック、レビューあり）"""
        try:
            time.sleep(self.request_delay)
            
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'doujin',
                'floor': 'doujin-comic',
                'hits': limit,
                'offset': offset,
                'sort': 'date',  # 新着順
                'output': 'json',
                'review_average': '3.0'  # レビュー平均3.0以上（レビューがある商品）
            }
            
            # affiliate_idが空の場合は除外
            if not self.affiliate_id:
                del params['affiliate_id']
            
            response = self.session.get(
                f"{self.api_base_url}/ItemList",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('result', {}).get('status') != 200:
                logger.error(f"API Error: {data.get('result', {}).get('message', 'Unknown error')}")
                return []
            
            items = data.get('result', {}).get('items', [])
            logger.info(f"Retrieved {len(items)} items from DMM API")
            
            return items
            
        except Exception as e:
            logger.error(f"Error fetching items from DMM API: {e}")
            return []
    
    def convert_to_work_data(self, api_item: Dict) -> Dict:
        """API レスポンスを内部データ形式に変換"""
        try:
            # ジャンル情報の抽出
            genres = []
            if 'genre' in api_item:
                for genre_item in api_item['genre']:
                    genres.append(genre_item['name'])
            
            # サンプル画像の抽出
            sample_images = []
            if 'sampleImageURL' in api_item:
                sample_images = list(api_item['sampleImageURL'].values())
            
            # レビュー情報の抽出
            reviews = []
            if 'review' in api_item:
                review_data = api_item['review']
                reviews.append({
                    'rating': f"{review_data.get('average', 0)}点 ({review_data.get('count', 0)}件)",
                    'text': f"平均評価: {review_data.get('average', 0)}点"
                })
            
            # アフィリエイトURL生成
            affiliate_url = api_item.get('affiliateURL', api_item.get('URL', ''))
            
            work_data = {
                'url': api_item.get('URL', ''),
                'work_id': api_item.get('content_id', ''),
                'title': api_item.get('title', ''),
                'circle_name': self._extract_circle_name(api_item),
                'author_name': self._extract_author_name(api_item),
                'category': '同人コミック',
                'package_image_url': api_item.get('imageURL', {}).get('large', ''),
                'description': api_item.get('comment', ''),
                'page_count': self._extract_page_count(api_item),
                'genres': genres,
                'sample_images': sample_images,
                'reviews': reviews,
                'affiliate_url': affiliate_url,
                'price': api_item.get('prices', {}).get('price', ''),
                'release_date': api_item.get('date', '')
            }
            
            return work_data
            
        except Exception as e:
            logger.error(f"Error converting API item to work data: {e}")
            return None
    
    def _extract_circle_name(self, api_item: Dict) -> str:
        """サークル名を抽出"""
        # iteminfo から作者情報を取得
        if 'iteminfo' in api_item:
            for info in api_item['iteminfo']:
                if info.get('name') == 'サークル':
                    return info.get('value', '')
                elif info.get('name') == '作者':
                    return info.get('value', '')
        
        # 作者情報から抽出
        if 'author' in api_item:
            for author in api_item['author']:
                return author.get('name', '')
        
        return ''
    
    def _extract_author_name(self, api_item: Dict) -> str:
        """作者名を抽出（サークル名と同じ場合が多い）"""
        return self._extract_circle_name(api_item)
    
    def _extract_page_count(self, api_item: Dict) -> str:
        """ページ数を抽出"""
        if 'iteminfo' in api_item:
            for info in api_item['iteminfo']:
                if info.get('name') == 'ページ数':
                    return info.get('value', '')
        return ''
    
    def get_work_detail(self, content_id: str) -> Optional[Dict]:
        """特定の作品の詳細情報を取得"""
        try:
            time.sleep(self.request_delay)
            
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'cid': content_id,
                'output': 'json'
            }
            
            if not self.affiliate_id:
                del params['affiliate_id']
            
            response = self.session.get(
                f"{self.api_base_url}/ItemList",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('result', {}).get('items', [])
            
            if items:
                return self.convert_to_work_data(items[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching work detail for {content_id}: {e}")
            return None