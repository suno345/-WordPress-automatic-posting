import requests
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from ..services.resource_manager import SessionMixin
from ..services.cache_manager import get_cache
from ..services.intelligent_error_handler import with_intelligent_retry, handle_api_error, record_api_success

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
        
        # ジャンル情報キャッシュ
        self.genre_cache = {}
        self.male_genre_ids = set()
        self.female_genre_ids = set()
        
        # 多層キャッシュマネージャー
        self.cache_manager = get_cache()
        
        
    
        
    def get_items(self, limit: int = 20, offset: int = 1, use_genre_filter: bool = True) -> List[Dict]:
        """商品一覧を取得（新着順の同人コミック・インテリジェントリトライ付き）"""
        attempt = 1
        last_error = None
        
        while True:
            try:
                time.sleep(self.request_delay)
                
                # 基本パラメータ（同人作品に特化、コミック判定は後処理で実行）
                params = {
                    'api_id': self.api_id,
                    'affiliate_id': self.affiliate_id,
                    'site': 'FANZA',
                    'service': 'doujin',         # 同人サービス
                    'floor': 'digital_doujin',   # 同人フロア
                    'hits': limit,
                    'offset': offset,
                    'sort': 'date',              # 新着順
                    'output': 'json'
                }
                
                # 改善：GenreSearch APIで男性向けジャンルを特定して使用
                if use_genre_filter:
                    # 男性向けコミック作品に特化：ジャンル指定でフィルタ
                    male_genre_ids = self.get_male_genre_ids()
                    if male_genre_ids:
                        # articleをgenreに変更して男性向けジャンルで絞り込み
                        params['article'] = 'genre'
                        params['article_id'] = male_genre_ids[0]  # 最初の男性向けジャンルIDを使用
                        logger.debug(f"男性向けジャンルフィルター適用: {male_genre_ids[0]}")
                    else:
                        # ジャンルIDが取得できない場合は基本パラメータのみ使用
                        logger.info("男性向けジャンルIDが取得できないため、基本検索を使用")
                
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
                if 'article' in params and params['article'] == 'genre':
                    logger.info(f"Retrieved {len(items)} items from DMM API (filtered by male genre: {params.get('article_id', 'unknown')})")
                else:
                    logger.info(f"Retrieved {len(items)} comic items from DMM API (filtered by article_id=comic)")
                
                # デバッグ用：最初のアイテムの構造をログ出力
                if items:
                    logger.info(f"First item type: {type(items[0])}")
                    logger.info(f"First item sample: {str(items[0])[:200]}...")
                
                return items
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP Error from DMM API: {e}")
                last_error = e
                try:
                    error_data = e.response.json()
                    logger.error(f"Error Response: {error_data}")
                except:
                    logger.error(f"Error Response Text: {e.response.text}")
                    
            except Exception as e:
                logger.error(f"Error fetching items from DMM API: {e}")
                last_error = e
                
            # インテリジェントリトライ処理
            if hasattr(self, 'error_handler'):
                delay = self.error_handler.handle_error(last_error, attempt)
                if delay > 0:
                    logger.info(f"Retrying after {delay} seconds (attempt {attempt + 1})")
                    time.sleep(delay)
                    attempt += 1
                    continue
                    
            logger.error(f"Failed to fetch items after {attempt} attempts")
            return []
    
    def is_comic_work(self, api_item: Dict) -> bool:
        """コミック作品のみを判定（ジャンルフィルター使用時も対応）"""
        # imageURLのパスでコミック作品を判定
        if 'imageURL' in api_item and 'large' in api_item['imageURL']:
            image_url = api_item['imageURL']['large']
            
            # コミック作品を識別
            if '/digital/comic/' in image_url:
                return True
            
            # 明確に非コミック系のパスは除外
            excluded_paths = [
                '/digital/game/',      # ゲーム作品
                '/digital/cg/',        # CG集
                '/digital/voice/',     # 音声作品
                '/digital/video/',     # 動画作品
                '/digital/anime/',     # アニメ作品（動画）
                '/digital/novel/',     # ノベル作品
            ]
            
            for excluded_path in excluded_paths:
                if excluded_path in image_url:
                    return False
        
        # ジャンルでコミック作品を判定（GenreSearch使用時の補助判定）
        if 'iteminfo' in api_item and 'genre' in api_item['iteminfo']:
            for genre in api_item['iteminfo']['genre']:
                genre_name = genre.get('name', '')
                
                # コミック系ジャンルを確認
                if any(comic_genre in genre_name for comic_genre in ['コミック', 'マンガ', '漫画']):
                    return True
                
                # 明確に非コミック系ジャンルは除外
                excluded_genres = [
                    'ロールプレイング', 'RPG', 'シミュレーション', 'アクション',
                    '動画・アニメーション', 'ボイス', '音声付き', 'ASMR',
                    '3DCG', 'CG集', 'デジタルノベル', 'ノベル'
                ]
                
                if any(excluded in genre_name for excluded in excluded_genres):
                    return False
        
        # GenreSearch APIで男性向けジャンルを使用している場合、
        # コミック系の可能性が高いため、より寛容な判定
        return True
    
    def _is_male_oriented_work(self, api_item: Dict) -> bool:
        """男性向け作品かどうかを判定（GenreSearch使用時は簡素化）"""
        # GenreSearch APIで既に男性向けジャンルでフィルタしている場合は、
        # 明らかな女性向けキーワードのチェックのみ実行
        
        # タイトルから女性向けキーワードをチェック
        title = api_item.get('title', '')
        female_keywords = ['BL', 'ボーイズラブ', '乙女', '女性向け', 'TL']
        if any(keyword in title for keyword in female_keywords):
            logger.debug(f"女性向けキーワードを含むタイトルとして除外: {title}")
            return False
        
        # GenreSearch APIによる男性向けフィルタを信頼
        return True
    
    def initialize_genre_cache(self) -> bool:
        """ジャンル情報をキャッシュに読み込み（多層キャッシュ活用）"""
        try:
            # まず多層キャッシュから試行
            cached_genre_data = self.cache_manager.get("genre_data", "dmm_api")
            cached_male_ids = self.cache_manager.get("male_genre_ids", "dmm_api")
            cached_female_ids = self.cache_manager.get("female_genre_ids", "dmm_api")
            
            if cached_genre_data and cached_male_ids and cached_female_ids:
                # キャッシュから復元
                self.genre_cache = cached_genre_data
                self.male_genre_ids = set(cached_male_ids)
                self.female_genre_ids = set(cached_female_ids)
                logger.info(f"ジャンル情報をキャッシュから復元: 男性向け{len(self.male_genre_ids)}件, 女性向け{len(self.female_genre_ids)}件")
                return True
            
            logger.info("ジャンル情報がキャッシュにないため、GenreSearch APIから取得開始")
            
            # キャッシュにない場合はGenreSearch APIから取得
            genre_data = self._fetch_genre_list()
            if not genre_data:
                logger.warning("ジャンル情報の取得に失敗しました")
                # フォールバック: デフォルトの男性向けジャンルIDを設定
                logger.info("フォールバック: デフォルト男性向けジャンルIDを設定")
                self.male_genre_ids.add("101")  # 一般的な同人コミックID
                return False
            
            # ジャンル情報を分析してキャッシュに保存
            self._analyze_and_cache_genres(genre_data)
            
            # 男性向けジャンルが見つからない場合のフォールバック
            if not self.male_genre_ids:
                logger.warning("男性向けジャンルが検出されませんでした。デフォルトIDを追加")
                self.male_genre_ids.add("101")  # デフォルトの男性向けジャンルID
            
            # 多層キャッシュに保存（24時間有効）
            self.cache_manager.set("genre_data", self.genre_cache, "dmm_api", ttl_hours=24)
            self.cache_manager.set("male_genre_ids", list(self.male_genre_ids), "dmm_api", ttl_hours=24)
            self.cache_manager.set("female_genre_ids", list(self.female_genre_ids), "dmm_api", ttl_hours=24)
            
            logger.info(f"ジャンル情報キャッシュを初期化: 男性向け{len(self.male_genre_ids)}件, 女性向け{len(self.female_genre_ids)}件")
            return True
            
        except Exception as e:
            logger.error(f"ジャンルキャッシュ初期化エラー: {e}")
            return False
    
    def _fetch_genre_list(self) -> List[Dict]:
        """GenreSearch APIでジャンル一覧を取得"""
        # affiliate_idが空の場合は除外
        params = {
            'api_id': self.api_id,
            'floor_id': '81',  # digital_doujin フロア
            'hits': 500,
            'output': 'json'
        }
        
        if self.affiliate_id:
            params['affiliate_id'] = self.affiliate_id
        
        try:
            logger.info(f"GenreSearch API request with params: {params}")
            response = self.session.get(f"{self.api_base_url}/GenreSearch", params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"GenreSearch API response status: {data.get('result', {}).get('status', 'unknown')}")
            logger.debug(f"GenreSearch API full response: {data}")
            
            status = data.get('result', {}).get('status', 0)
            if status == 200 or status == '200':
                genres = data.get('result', {}).get('genre', [])
                logger.info(f"GenreSearch API returned {len(genres)} genres")
                return genres
            else:
                logger.error(f"GenreSearch API error: {data}")
                return []
                
        except Exception as e:
            logger.error(f"GenreSearch API request failed: {e}")
            return []
    
    def _analyze_and_cache_genres(self, genre_data: List[Dict]) -> None:
        """ジャンル情報を分析してキャッシュに保存"""
        logger.info(f"Analyzing {len(genre_data)} genres for male/female classification")
        
        # 女性向けジャンルのキーワード
        female_keywords = [
            '女性向け', 'BL', 'ボーイズラブ', '乙女', 'TL', 'ティーンズラブ',
            '少女', 'レディース', '恋愛', 'ラブロマンス', '腐女子'
        ]
        
        # 男性向けジャンルのキーワード（拡張版）
        male_keywords = [
            '男性向け', '成人向け', 'アダルト', 'エロ', '青年向け',
            '大人向け', 'R18', '18禁', 'エッチ', 'Hな', 'セックス',
            'オナニー', 'フェラ', 'パイズリ', 'バック', '中出し',
            'ロリ', '巨乳', '美少女', 'JK', '人妻', 'メイド',
            '学園', 'ハーレム', 'NTR', '寝取り', '調教', '凌辱'
        ]
        
        # デフォルト男性向けジャンル（明確な女性向けキーワードがない場合）
        default_male_genres = [
            'コミック', 'マンガ', '漫画', 'CG', 'イラスト', 'アニメ',
            'ゲーム', 'ノベル', '3D', 'フルカラー', 'モノクロ'
        ]
        
        for genre in genre_data:
            genre_id = genre.get('genre_id', '')
            genre_name = genre.get('name', '')
            
            # ジャンル情報をキャッシュに保存
            self.genre_cache[genre_id] = {
                'name': genre_name,
                'ruby': genre.get('ruby', ''),
                'list_url': genre.get('list_url', '')
            }
            
            # 女性向け判定（優先）
            if any(keyword in genre_name for keyword in female_keywords):
                self.female_genre_ids.add(genre_id)
                logger.debug(f"女性向けジャンル登録: {genre_name} (ID: {genre_id})")
            
            # 男性向け判定（明示的キーワード）
            elif any(keyword in genre_name for keyword in male_keywords):
                self.male_genre_ids.add(genre_id)
                logger.debug(f"男性向けジャンル登録: {genre_name} (ID: {genre_id})")
            
            # デフォルト男性向け判定（女性向けキーワードがない場合）
            elif any(keyword in genre_name for keyword in default_male_genres):
                self.male_genre_ids.add(genre_id)
                logger.debug(f"デフォルト男性向けジャンル登録: {genre_name} (ID: {genre_id})")
        
        logger.info(f"Genre analysis complete: 男性向け={len(self.male_genre_ids)}, 女性向け={len(self.female_genre_ids)}")
    
    def get_male_genre_ids(self) -> List[str]:
        """男性向けジャンルIDのリストを取得"""
        if not self.male_genre_ids and not self.genre_cache:
            # キャッシュが空の場合は初期化を試行
            self.initialize_genre_cache()
        
        return list(self.male_genre_ids)
    
    def get_reviewed_works(self, target_count: int = 5, max_check: int = 100) -> List[Dict]:
        """レビュー付きの作品を指定数見つけるまで検索（並行処理版）"""
        reviewed_works = []
        current_offset = 1
        batch_size = 20
        
        logger.info(f"Searching for {target_count} works with reviews (checking up to {max_check} works)...")
        
        while len(reviewed_works) < target_count and current_offset <= max_check:
            # 新着順で商品を取得
            raw_items = self.get_items(limit=batch_size, offset=current_offset)
            if not raw_items:
                break
            
            # 改善：レビューチェックを並行処理で実行
            batch_works = self._process_items_concurrent(raw_items, target_count - len(reviewed_works))
            reviewed_works.extend(batch_works)
            
            if batch_works:
                logger.info(f"Found {len(batch_works)} reviewed works in batch. Total: {len(reviewed_works)}/{target_count}")
            
            current_offset += batch_size
            
        logger.info(f"Found {len(reviewed_works)} works with reviews")
        return reviewed_works
    
    def _process_items_concurrent(self, raw_items: List[Dict], needed_count: int) -> List[Dict]:
        """商品リストを並行処理でデータ変換とレビューチェック"""
        if not raw_items or needed_count <= 0:
            return []
        
        reviewed_works = []
        max_workers = min(5, len(raw_items))  # 最大5並行
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 各商品の処理を並行実行
            future_to_item = {
                executor.submit(self._process_single_item_safe, item): item 
                for item in raw_items
            }
            
            for future in as_completed(future_to_item):
                if len(reviewed_works) >= needed_count:
                    # 必要数に達したら残りの処理をキャンセル
                    for remaining_future in future_to_item:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    break
                
                try:
                    work_data = future.result(timeout=30)  # 30秒タイムアウト
                    if work_data:
                        reviewed_works.append(work_data)
                        logger.debug(f"Concurrent processing found: {work_data['title']}")
                except Exception as e:
                    item = future_to_item[future]
                    logger.warning(f"Error processing item {item.get('title', 'Unknown')}: {e}")
        
        return reviewed_works
    
    def _process_single_item_safe(self, item: Dict) -> Optional[Dict]:
        """単一商品の安全な処理（例外処理付き）"""
        try:
            return self.convert_to_work_data(item)
        except Exception as e:
            logger.warning(f"Error in _process_single_item_safe: {e}")
            return None
    
    
    
    
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
        """レビュー情報の検証（DMM API直接取得版）"""
        try:
            if skip_review_check:
                logger.info(f"Skipping review check for: {api_item.get('title', 'Unknown')}")
                return True
            
            # DMM APIレスポンスから直接レビュー情報を取得
            if 'review' in api_item:
                review_data = api_item['review']
                review_count = review_data.get('count', 0)
                
                if review_count > 0:
                    logger.info(f"Review found via API: {api_item.get('title', 'Unknown')} - {review_count}件")
                    return True
                else:
                    logger.info(f"No reviews found via API: {api_item.get('title', 'Unknown')}")
                    return False
            else:
                # review情報がAPIレスポンスにない場合
                # VPSモード時は作品不足を防ぐためレビューなしでも許可
                import os
                vps_mode = os.getenv('VPS_MODE', 'false').lower() == 'true'
                if vps_mode:
                    logger.info(f"VPSモード: レビューなしでも許可 - {api_item.get('title', 'Unknown')}")
                    return True
                else:
                    logger.info(f"No review data in API response: {api_item.get('title', 'Unknown')}")
                    return False
            
        except Exception as e:
            logger.error(f"Error validating reviews for {api_item.get('title', 'Unknown')}: {e}")
            return False
    
    def _extract_sample_images(self, api_item: Dict) -> List[str]:
        """サンプル画像の抽出（並行検証付き）"""
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
            
            raw_sample_images = sample_url_data['sample_l']['image']
            logger.info(f"Found {len(raw_sample_images)} sample images")
            
            # 改善：画像URLの検証を並行処理で実行
            validated_images = self._validate_image_urls_concurrent(raw_sample_images)
            
            logger.info(f"Validated {len(validated_images)} sample images")
            return validated_images
            
        except Exception as e:
            logger.error(f"Error extracting sample images: {e}")
            return []
    
    def _validate_image_urls_concurrent(self, image_urls: List[str], max_workers: int = 3) -> List[str]:
        """画像URLを並行処理で検証"""
        if not image_urls:
            return []
        
        # 最大5個まで検証（制限を設ける）
        urls_to_check = image_urls[:5]
        validated_urls = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 各URLの検証を並行実行
            future_to_url = {
                executor.submit(self._validate_single_image_url, url): url 
                for url in urls_to_check
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    is_valid = future.result(timeout=10)  # 10秒タイムアウト
                    if is_valid:
                        validated_urls.append(url)
                        logger.debug(f"Image URL validated: {url}")
                    else:
                        logger.debug(f"Image URL invalid: {url}")
                except Exception as e:
                    logger.warning(f"Error validating image URL {url}: {e}")
        
        return validated_urls
    
    def _validate_single_image_url(self, url: str) -> bool:
        """単一画像URLの検証"""
        try:
            # URLの基本的な妥当性チェック
            if not url or not url.startswith(('http://', 'https://')):
                return False
            
            # 画像系の拡張子チェック
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(url.lower().endswith(ext) for ext in valid_extensions):
                # クエリパラメーターがある場合は無視
                if '?' in url:
                    base_url = url.split('?')[0]
                    if not any(base_url.lower().endswith(ext) for ext in valid_extensions):
                        return False
                else:
                    return False
            
            # DMM系のドメインチェック
            dmm_domains = ['dmm.co.jp', 'dmm.com', 'pics.dmm.co.jp', 'doujin-assets.dmm.co.jp']
            if not any(domain in url for domain in dmm_domains):
                logger.debug(f"Non-DMM domain detected: {url}")
                # DMM以外でも有効なURLとして扱う
            
            return True
            
        except Exception as e:
            logger.warning(f"Error in _validate_single_image_url: {e}")
            return False
    
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