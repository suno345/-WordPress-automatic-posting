import requests
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..services.resource_manager import SessionMixin

logger = logging.getLogger(__name__)


class DMMAPIClient(SessionMixin):
    def __init__(self, api_id: str, affiliate_id: str = "", request_delay: int = 2):
        """DMM アフィリエイト API クライアント"""
        super().__init__()
        self.api_base_url = "https://api.dmm.com/affiliate/v3"
        self.api_id = api_id
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay
        
    def get_items(self, limit: int = 20, offset: int = 1) -> List[Dict]:
        """商品一覧を取得（新着順の同人コミック）"""
        try:
            time.sleep(self.request_delay)
            
            # 同人コミック作品取得用パラメータ
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'doujin',         # 同人サービス
                'floor': 'digital_doujin',   # 同人フロア
                'hits': limit,
                'offset': offset,
                'sort': 'date',              # 新着順
                'output': 'json',
                'article': 'genre',          # ジャンルフィルタ
                'article_id': '156022'       # 男性向けジャンルID
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
                logger.error(f"API Response: {data}")  # デバッグ用にレスポンス全体をログ出力
                return []
            
            items = data.get('result', {}).get('items', [])
            logger.info(f"Retrieved {len(items)} items from DMM API")
            
            # デバッグ用：最初のアイテムの構造をログ出力
            if items:
                logger.info(f"First item type: {type(items[0])}")
                logger.info(f"First item sample: {str(items[0])[:200]}...")
            
            return items
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error from DMM API: {e}")
            try:
                error_data = e.response.json()
                logger.error(f"Error Response: {error_data}")
            except:
                logger.error(f"Error Response Text: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching items from DMM API: {e}")
            return []
    
    def is_comic_work(self, api_item: Dict) -> bool:
        """コミック作品かどうかを判定"""
        # imageURLのパスにcomicが含まれているかチェック
        if 'imageURL' in api_item and 'large' in api_item['imageURL']:
            image_url = api_item['imageURL']['large']
            if '/comic/' in image_url:
                return True
        
        # ジャンルにコミック関連のものが含まれているかチェック
        if 'iteminfo' in api_item and 'genre' in api_item['iteminfo']:
            for genre in api_item['iteminfo']['genre']:
                genre_name = genre.get('name', '').lower()
                if 'コミック' in genre_name or 'マンガ' in genre_name or '漫画' in genre_name:
                    return True
        
        return True  # デフォルトでは全て通す
    
    def get_reviewed_works(self, target_count: int = 5, max_check: int = 100) -> List[Dict]:
        """レビュー付きの作品を指定数見つけるまで検索"""
        reviewed_works = []
        current_offset = 1
        batch_size = 20
        
        logger.info(f"Searching for {target_count} works with reviews (checking up to {max_check} works)...")
        
        while len(reviewed_works) < target_count and current_offset <= max_check:
            # 新着順で商品を取得
            raw_items = self.get_items(limit=batch_size, offset=current_offset)
            if not raw_items:
                break
                
            # 各商品をチェック
            for item in raw_items:
                if len(reviewed_works) >= target_count:
                    break
                    
                # データ変換とレビューチェック
                work_data = self.convert_to_work_data(item)
                if work_data:  # レビューがある場合のみwork_dataが返される
                    reviewed_works.append(work_data)
                    logger.info(f"Found reviewed work: {work_data['title']} ({len(reviewed_works)}/{target_count})")
            
            current_offset += batch_size
            
        logger.info(f"Found {len(reviewed_works)} works with reviews")
        return reviewed_works
    
    def get_review_info_from_page(self, product_url: str) -> Dict:
        """商品ページからレビュー情報を取得"""
        try:
            time.sleep(self.request_delay)  # リクエスト間隔を保持
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = self.session.get(product_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # レビュー数を取得
            review_count = 0
            review_average = 0.0
            
            # FANZA商品ページのレビュー要素を探す
            review_elements = soup.find_all(['span', 'div'], class_=lambda x: x and 'review' in x.lower())
            
            for element in review_elements:
                text = element.get_text().strip()
                # レビュー数のパターンを探す（例：「レビュー（5件）」）
                if '件' in text and ('レビュー' in text or 'review' in text.lower()):
                    import re
                    numbers = re.findall(r'(\d+)', text)
                    if numbers:
                        review_count = int(numbers[0])
                        break
            
            # 星評価を取得
            star_elements = soup.find_all(['span', 'div'], class_=lambda x: x and ('star' in str(x).lower() or 'rating' in str(x).lower()))
            for element in star_elements:
                if element.get('data-rating') or element.get('data-score'):
                    try:
                        review_average = float(element.get('data-rating') or element.get('data-score'))
                        break
                    except (ValueError, TypeError):
                        continue
            
            return {
                'count': review_count,
                'average': review_average,
                'has_reviews': review_count > 0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get review info from {product_url}: {e}")
            return {'count': 0, 'average': 0.0, 'has_reviews': False}
    
    def convert_to_work_data(self, api_item: Dict) -> Dict:
        """API レスポンスを内部データ形式に変換"""
        try:
            # コミック作品のみを対象とする
            if not self.is_comic_work(api_item):
                return None
            
            # レビュー情報の確認
            # APIレスポンスにレビュー情報が含まれていない場合、商品ページからスクレイピング
            has_reviews = False
            if 'review' in api_item and api_item.get('review', {}).get('count', 0) > 0:
                has_reviews = True
            else:
                # 商品ページからレビュー情報を取得
                product_url = api_item.get('URL', '')
                if product_url:
                    review_info = self.get_review_info_from_page(product_url)
                    has_reviews = review_info['has_reviews']
                    
                    # レビュー情報をapi_itemに追加
                    if has_reviews:
                        api_item['review'] = {
                            'count': review_info['count'],
                            'average': review_info['average']
                        }
            
            # レビューがない作品はスキップ
            if not has_reviews:
                logger.info(f"Skipping work without reviews: {api_item.get('title', 'Unknown')}")
                return None
            # ジャンル情報の抽出
            genres = []
            if 'iteminfo' in api_item and 'genre' in api_item['iteminfo']:
                for genre_item in api_item['iteminfo']['genre']:
                    genres.append(genre_item['name'])
            
            # サンプル画像の抽出
            sample_images = []
            if 'sampleImageURL' in api_item:
                logger.info(f"Sample image data found: {api_item['sampleImageURL']}")
                if 'sample_l' in api_item['sampleImageURL']:
                    if 'image' in api_item['sampleImageURL']['sample_l']:
                        sample_images = api_item['sampleImageURL']['sample_l']['image']
                        logger.info(f"Extracted {len(sample_images)} sample images")
                    else:
                        logger.info("No 'image' key in sample_l")
                else:
                    logger.info("No 'sample_l' key in sampleImageURL")
            else:
                logger.info("No 'sampleImageURL' key in API response")
            
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
                'category': '同人',
                'package_image_url': api_item.get('imageURL', {}).get('large', ''),
                'description': api_item.get('comment', 'この作品の詳細な紹介文は準備中です。'),
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
            logger.error(f"Problematic item: {api_item}")  # デバッグ用
            return None
    
    def _extract_circle_name(self, api_item: Dict) -> str:
        """サークル名を抽出"""
        # iteminfo の maker から抽出
        if 'iteminfo' in api_item and 'maker' in api_item['iteminfo']:
            makers = api_item['iteminfo']['maker']
            if makers and len(makers) > 0:
                return makers[0].get('name', '')
        
        return '不明'
    
    def _extract_author_name(self, api_item: Dict) -> str:
        """作者名を抽出（サークル名と同じ場合が多い）"""
        return self._extract_circle_name(api_item)
    
    def _extract_page_count(self, api_item: Dict) -> str:
        """ページ数を抽出"""
        # volumeフィールドから抽出
        if 'volume' in api_item:
            volume = api_item['volume']
            # 数字だけの場合はページ数として扱う
            if volume.isdigit():
                return f"{volume}ページ"
            else:
                return volume
        return '不明'
    
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