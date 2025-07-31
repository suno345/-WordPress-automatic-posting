import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class FANZAScraper:
    def __init__(self, affiliate_id: str = "", request_delay: int = 2):
        self.base_url = "https://www.dmm.co.jp"
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_work_list(self, list_url: str) -> List[str]:
        """作品一覧ページから作品詳細URLリストを取得"""
        work_urls = []
        
        try:
            response = self.session.get(list_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 作品リストのセレクタ（FANZAのHTML構造に応じて調整が必要）
            work_links = soup.select('div.d-item a[href*="/detail/"]')
            
            for link in work_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    work_urls.append(full_url)
            
            logger.info(f"Found {len(work_urls)} works")
            
        except Exception as e:
            logger.error(f"Error getting work list: {e}")
        
        return work_urls
    
    def scrape_work_detail(self, work_url: str) -> Optional[Dict]:
        """作品詳細ページから情報を取得"""
        try:
            time.sleep(self.request_delay)  # リクエスト間隔を守る
            
            response = self.session.get(work_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            work_data = {
                'url': work_url,
                'work_id': self._extract_work_id(work_url),
                'title': self._extract_title(soup),
                'circle_name': self._extract_circle_name(soup),
                'author_name': self._extract_author_name(soup),
                'category': self._extract_category(soup),
                'package_image_url': self._extract_package_image(soup),
                'description': self._extract_description(soup),
                'page_count': self._extract_page_count(soup),
                'genres': self._extract_genres(soup),
                'sample_images': self._extract_sample_images(soup),
                'reviews': self._extract_reviews(soup),
                'affiliate_url': self._generate_affiliate_url(work_url)
            }
            
            logger.info(f"Successfully scraped: {work_data['title']}")
            return work_data
            
        except Exception as e:
            logger.error(f"Error scraping work detail from {work_url}: {e}")
            return None
    
    def _extract_work_id(self, url: str) -> str:
        """URLから作品IDを抽出"""
        # URLパターン: .../detail/=/cid=xxx/
        try:
            parts = url.split('cid=')
            if len(parts) > 1:
                return parts[1].rstrip('/')
        except:
            pass
        return ""
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """作品タイトルを抽出"""
        title_elem = soup.select_one('h1#title, h1.productTitle')
        return title_elem.text.strip() if title_elem else ""
    
    def _extract_circle_name(self, soup: BeautifulSoup) -> str:
        """サークル名を抽出"""
        circle_elem = soup.select_one('a[href*="/list/=/article=maker/"]')
        return circle_elem.text.strip() if circle_elem else ""
    
    def _extract_author_name(self, soup: BeautifulSoup) -> str:
        """作者名を抽出（サークル名と同じ場合が多い）"""
        # FANZAでは作者名が明示的に記載されていない場合があるため、
        # サークル名で代用するか、別の場所から取得
        return self._extract_circle_name(soup)
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """カテゴリを抽出"""
        category_elem = soup.select_one('div.breadcrumb a[href*="/doujin/"]')
        return category_elem.text.strip() if category_elem else "同人"
    
    def _extract_package_image(self, soup: BeautifulSoup) -> str:
        """パッケージ画像URLを抽出"""
        img_elem = soup.select_one('img.package-image, div.package img')
        if img_elem and img_elem.get('src'):
            return urljoin(self.base_url, img_elem['src'])
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """作品紹介文を抽出"""
        desc_elem = soup.select_one('div.summary__txt, div.work-text')
        return desc_elem.text.strip() if desc_elem else ""
    
    def _extract_page_count(self, soup: BeautifulSoup) -> str:
        """ページ数を抽出"""
        # FANZAの仕様に応じて調整が必要
        page_elem = soup.select_one('td:contains("ページ数")')
        if page_elem and page_elem.next_sibling:
            return page_elem.next_sibling.text.strip()
        return ""
    
    def _extract_genres(self, soup: BeautifulSoup) -> List[str]:
        """ジャンルリストを抽出"""
        genres = []
        genre_elems = soup.select('a[href*="/list/=/article=keyword/"]')
        for elem in genre_elems:
            genre = elem.text.strip()
            if genre:
                genres.append(genre)
        return genres
    
    def _extract_sample_images(self, soup: BeautifulSoup) -> List[str]:
        """サンプル画像URLリストを抽出"""
        sample_images = []
        sample_elems = soup.select('div.sample-image img, div.preview img')
        for elem in sample_elems:
            if elem.get('src'):
                sample_images.append(urljoin(self.base_url, elem['src']))
        return sample_images
    
    def _extract_reviews(self, soup: BeautifulSoup) -> List[Dict]:
        """レビュー情報を抽出"""
        reviews = []
        review_elems = soup.select('div.review-item, div.d-review__item')
        
        for elem in review_elems[:3]:  # 最初の3件のみ取得
            review = {
                'rating': '',
                'text': ''
            }
            
            # 評価
            rating_elem = elem.select_one('.d-review__rate, .review-rating')
            if rating_elem:
                review['rating'] = rating_elem.text.strip()
            
            # レビューテキスト
            text_elem = elem.select_one('.d-review__text, .review-text')
            if text_elem:
                review['text'] = text_elem.text.strip()
            
            if review['text']:
                reviews.append(review)
        
        return reviews
    
    def _generate_affiliate_url(self, work_url: str) -> str:
        """アフィリエイトURLを生成"""
        if self.affiliate_id:
            # FANZAのアフィリエイトURL形式に応じて調整
            return f"{work_url}?{self.affiliate_id}"
        return work_url