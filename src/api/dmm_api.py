import requests
import time
import logging
import yaml
from typing import Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path

from ..services.resource_manager import SessionMixin

logger = logging.getLogger(__name__)


class DMMAPIClient(SessionMixin):
    def __init__(self, api_id: str, affiliate_id: str = "", request_delay: int = 2, max_workers: int = 3):
        """DMM アフィリエイト API クライアント"""
        super().__init__()
        self.api_base_url = "https://api.dmm.com/affiliate/v3"
        self.api_id = api_id
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay
        self.max_workers = max_workers
        self._review_cache = {}  # レビュー情報キャッシュ
        self._cache_lock = threading.Lock()  # キャッシュアクセス用ロック
        self._load_config()
        
    def _load_config(self) -> None:
        """設定ファイルからレビューパターンを読み込み"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "review_patterns.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                # レビューパターンを読み込み
                review_patterns = config.get('review_patterns', {})
                self.review_patterns = []
                
                # 各カテゴリのパターンを統合
                for category in ['basic', 'modern', 'english', 'fanza_specific']:
                    patterns = review_patterns.get(category, [])
                    for pattern_config in patterns:
                        self.review_patterns.append(pattern_config['pattern'])
                
                # レビューセクション用パターン
                self.review_section_patterns = [
                    pattern_config['pattern'] for pattern_config in 
                    config.get('review_section_patterns', [])
                ]
                
                # レビューなし判定パターン
                self.no_review_indicators = config.get('no_review_indicators', [])
                
                # HTMLセレクタ
                self.html_selectors = config.get('html_selectors', [])
                
                logger.info(f"設定ファイルから{len(self.review_patterns)}個のレビューパターンを読み込みました")
            else:
                logger.warning(f"設定ファイルが見つかりません: {config_path}")
                self._use_default_patterns()
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            self._use_default_patterns()
    
    def _use_default_patterns(self) -> None:
        """デフォルトのレビューパターンを使用"""
        self.review_patterns = [
            r'レビュー\s*[（(]\s*(\d+)\s*件\s*[）)]',
            r'レビュー\s*:\s*(\d+)\s*件',
            r'レビュー\s+(\d+)\s*件',
            r'評価\s*[（(]\s*(\d+)\s*件\s*[）)]',
            r'(\d+)\s*件のレビュー',
            r'(\d+)\s*人がレビュー',
            r'レビュー数\s*[:：]\s*(\d+)',
            r'(\d+)\s+reviews?\b',
        ]
        
        self.review_section_patterns = [
            r'総評価数\s*(\d+)\s*[（(]',
            r'総評価数\s*(\d+)',
            r'平均評価\s*[\d.]+\s*総評価数\s*(\d+)',
            r'(\d+)\s*件のレビュー',
            r'レビュー\s*(\d+)\s*件',
        ]
        
        self.no_review_indicators = [
            'この作品に最初のレビューを書いてみませんか？',
            '最初のレビューを書いて',
            '最初のレビューを投稿'
        ]
        
        self.html_selectors = [
            '.review-list',
            '.review-item',
            '[class*="review-count"]',
            '[class*="rating-count"]',
            '[data-review-count]'
        ]
        
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
    
    def get_review_info_from_page_cached(self, product_url: str) -> Dict:
        """キャッシュ機能付きレビュー情報取得"""
        # キャッシュチェック
        with self._cache_lock:
            if product_url in self._review_cache:
                logger.debug(f"Using cached review info for {product_url}")
                return self._review_cache[product_url]
        
        # キャッシュにない場合は取得
        result = self.get_review_info_from_page(product_url)
        
        # キャッシュに保存
        with self._cache_lock:
            self._review_cache[product_url] = result
        
        return result
    
    def get_review_info_batch(self, product_urls: List[str]) -> Dict[str, Dict]:
        """複数商品のレビュー情報を並列取得"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 並列でレビュー情報を取得
            future_to_url = {
                executor.submit(self.get_review_info_from_page_cached, url): url 
                for url in product_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results[url] = result
                    logger.debug(f"Completed review check for {url}: {result['count']} reviews")
                except Exception as e:
                    logger.error(f"Error checking reviews for {url}: {e}")
                    results[url] = {'count': 0, 'average': 0.0, 'has_reviews': False}
        
        return results
    
    def get_review_info_from_page(self, product_url: str) -> Dict:
        """商品ページからレビュー情報を取得"""
        try:
            time.sleep(self.request_delay)  # リクエスト間隔を保持
            
            # 年齢認証対応のCookie設定
            self.session.cookies.set('age_check_done', '1', domain='.dmm.co.jp')
            self.session.cookies.set('ckcy', '1', domain='.dmm.co.jp')
            
            # より包括的なヘッダー設定
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://www.dmm.co.jp/',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            response = self.session.get(product_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # レビュー数を取得
            review_count = 0
            review_average = 0.0
            
            # FANZA商品ページのレビュー要素を探す（複数パターンで検索）
            import re
            
            # パターン1: レビュー数の直接検索（設定ファイルから読み込み）
            
            # 全テキストを取得して検索
            page_text = soup.get_text()
            for pattern in self.review_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    review_count = int(matches[0])
                    logger.info(f"Found review count using pattern '{pattern}': {review_count}")
                    break
            
            # パターン2: HTML要素から検索（FANZA構造に特化）
            if review_count == 0:
                # FANZA の review_anchor 要素をチェック
                review_section = soup.find(id='review_anchor')
                if review_section:
                    review_text = review_section.get_text()
                    logger.info(f"Review section text: {review_text[:200]}...")
                    
                    # レビューなし判定（設定ファイルから読み込み）
                    if any(indicator in review_text for indicator in self.no_review_indicators):
                        logger.info("No reviews found - first review prompt detected")
                        review_count = 0
                    else:
                        # レビューが存在する場合のパターンを検索（設定ファイルから読み込み）
                        for pattern in self.review_section_patterns:
                            matches = re.findall(pattern, review_text)
                            if matches:
                                review_count = int(matches[0])
                                logger.info(f"Found review count in review section using pattern '{pattern}': {review_count}")
                                break
                
                # さらに他の要素をチェック（設定ファイルから読み込み）
                if review_count == 0:
                    for selector in self.html_selectors:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text().strip()
                            # 数字を含むテキストをチェック
                            numbers = re.findall(r'(\d+)', text)
                            if numbers and any(keyword in text for keyword in ['件', 'レビュー', 'review', '評価']):
                                review_count = int(numbers[0])
                                logger.info(f"Found review count using selector '{selector}': {review_count}")
                                break
                        if review_count > 0:
                            break
            
            # デバッグ: レビューが見つからない場合、ページ内容を少し出力
            if review_count == 0:
                logger.debug(f"No reviews found for {product_url}")
                # ページの一部テキストを確認（デバッグ用）
                sample_text = page_text[:500] if len(page_text) > 500 else page_text
                logger.debug(f"Sample page text: {sample_text}")
            
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
    
    def convert_to_work_data(self, api_item: Dict, skip_review_check: bool = False) -> Dict:
        """API レスポンスを内部データ形式に変換"""
        try:
            # コミック作品のみを対象とする
            if not self.is_comic_work(api_item):
                return None
            
            # レビュー情報の検証
            if not self._validate_reviews(api_item, skip_review_check):
                return None
            
            # 作品データの構築
            return self._build_work_data(api_item)
            
        except Exception as e:
            logger.error(f"Error converting API item to work data: {e}")
            logger.error(f"Problematic item: {api_item}")
            return None
    
    def _validate_reviews(self, api_item: Dict, skip_review_check: bool) -> bool:
        """レビュー情報の検証"""
        try:
            if skip_review_check:
                logger.info(f"Skipping review check for: {api_item.get('title', 'Unknown')}")
                return True
            
            # APIレスポンスにレビュー情報が含まれている場合
            if 'review' in api_item and api_item.get('review', {}).get('count', 0) > 0:
                return True
            
            # 商品ページからレビュー情報を取得
            product_url = api_item.get('URL', '')
            if not product_url:
                logger.warning(f"No product URL found for: {api_item.get('title', 'Unknown')}")
                return False
            
            review_info = self.get_review_info_from_page(product_url)
            has_reviews = review_info['has_reviews']
            
            # レビュー情報をapi_itemに追加
            if has_reviews:
                api_item['review'] = {
                    'count': review_info['count'],
                    'average': review_info['average']
                }
                return True
            
            # レビューがない作品はスキップ
            logger.info(f"Skipping work without reviews: {api_item.get('title', 'Unknown')}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating reviews for {api_item.get('title', 'Unknown')}: {e}")
            return False
    
    def _extract_sample_images(self, api_item: Dict) -> List[str]:
        """サンプル画像の抽出"""
        try:
            if 'sampleImageURL' not in api_item:
                logger.debug("No 'sampleImageURL' key in API response")
                return []
            
            sample_url_data = api_item['sampleImageURL']
            logger.debug(f"Sample image data found: {sample_url_data}")
            
            if 'sample_l' not in sample_url_data:
                logger.debug("No 'sample_l' key in sampleImageURL")
                return []
            
            if 'image' not in sample_url_data['sample_l']:
                logger.debug("No 'image' key in sample_l")
                return []
            
            sample_images = sample_url_data['sample_l']['image']
            logger.info(f"Extracted {len(sample_images)} sample images")
            return sample_images
            
        except Exception as e:
            logger.error(f"Error extracting sample images: {e}")
            return []
    
    def _extract_review_data(self, api_item: Dict) -> List[Dict]:
        """レビューデータの抽出"""
        try:
            if 'review' not in api_item:
                return []
            
            review_data = api_item['review']
            average = review_data.get('average', 0)
            count = review_data.get('count', 0)
            
            return [{
                'rating': f"{average}点 ({count}件)",
                'text': f"平均評価: {average}点"
            }]
            
        except Exception as e:
            logger.error(f"Error extracting review data: {e}")
            return []
    
    def _extract_genres(self, api_item: Dict) -> List[str]:
        """ジャンル情報の抽出"""
        try:
            if 'iteminfo' not in api_item or 'genre' not in api_item['iteminfo']:
                return []
            
            genres = []
            for genre_item in api_item['iteminfo']['genre']:
                genre_name = genre_item.get('name', '')
                if genre_name:
                    genres.append(genre_name)
            
            return genres
            
        except Exception as e:
            logger.error(f"Error extracting genres: {e}")
            return []
    
    def _build_work_data(self, api_item: Dict) -> Dict:
        """作品データの構築"""
        try:
            # 各データ要素を抽出
            genres = self._extract_genres(api_item)
            sample_images = self._extract_sample_images(api_item)
            reviews = self._extract_review_data(api_item)
            affiliate_url = api_item.get('affiliateURL', api_item.get('URL', ''))
            
            # 作品データを構築
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
            logger.error(f"Error building work data: {e}")
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