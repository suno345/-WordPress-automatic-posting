import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common import exceptions as selenium_exceptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class FANZAScraper:
    def __init__(self, affiliate_id: str = "", request_delay: int = 2, use_selenium: bool = True):
        self.base_url = "https://www.dmm.co.jp"
        self.affiliate_id = affiliate_id
        self.request_delay = request_delay
        self.use_selenium = use_selenium
        self.driver = None
        
        # requests session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        if self.use_selenium:
            self._setup_selenium_driver()
    
    def _setup_selenium_driver(self):
        """Seleniumドライバーのセットアップ"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # ヘッドレスモード
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # WebDriverManagerを使用してChromeDriverを自動管理
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # bot検知対策
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.implicitly_wait(10)
            logger.info("Selenium WebDriver initialized successfully with ChromeDriverManager")
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            logger.info("Falling back to requests-only mode")
            self.use_selenium = False
    
    def _handle_age_verification(self):
        """年齢認証ページの自動処理"""
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            logger.debug(f"Current URL: {current_url}")
            logger.debug(f"Page source contains '年齢確認': {'年齢確認' in page_source}")
            logger.debug(f"Page source contains 'age': {'age' in page_source.lower()}")
            
            # 年齢認証ページかどうかを確認
            if ("age" in current_url.lower() or 
                "年齢確認" in page_source or 
                "18歳以上" in page_source or
                "age_check" in page_source or
                "ageCheck" in page_source):
                
                logger.info("Age verification page detected, handling automatically")
                
                # より多くのセレクタパターンを試行
                age_confirm_selectors = [
                    'input[value*="はい"]',
                    'button[value*="はい"]',
                    'input[value*="yes"]',
                    'button[value*="yes"]',
                    'a[href*="age_check_done"]',
                    'a[href*="ageCheck"]',
                    '.age-check-yes',
                    '#age-check-yes',
                    'input[type="submit"][value*="はい"]',
                    'input[type="button"][value*="はい"]',
                    'a:contains("はい")',
                    'button:contains("はい")',
                    'a:contains("18歳以上")',
                    'button:contains("18歳以上")',
                    'form input[type="submit"]',
                    'form button[type="submit"]',
                ]
                
                clicked = False
                for selector in age_confirm_selectors:
                    try:
                        logger.debug(f"Trying selector: {selector}")
                        
                        # CSSセレクタとXPathの両方を試行
                        elements = []
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        except:
                            pass
                        
                        if not elements and "contains" in selector:
                            # XPathに変換して試行
                            xpath_selector = selector.replace(':contains("', '[contains(text(), "').replace('")', '")]')
                            try:
                                elements = self.driver.find_elements(By.XPATH, f"//{xpath_selector}")
                            except:
                                pass
                        
                        if elements:
                            element = elements[0]
                            logger.info(f"Found age verification element with selector: {selector}")
                            
                            # スクロールして要素を見える位置に移動
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(1)
                            
                            # クリック試行
                            try:
                                element.click()
                            except:
                                # JavaScriptでクリック
                                self.driver.execute_script("arguments[0].click();", element)
                            
                            logger.info(f"Clicked age verification button with selector: {selector}")
                            clicked = True
                            time.sleep(3)  # ページ遷移待機
                            break
                            
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not clicked:
                    logger.warning("Could not find or click age verification button")
                    # HTMLソースの一部をログ出力（デバッグ用）
                    html_snippet = page_source[:1000] if len(page_source) > 1000 else page_source
                    logger.debug(f"HTML snippet: {html_snippet}")
                else:
                    # ページが更新されるまで待機
                    try:
                        WebDriverWait(self.driver, 15).until(
                            lambda driver: driver.current_url != current_url
                        )
                        logger.info("Age verification completed successfully")
                    except selenium_exceptions.TimeoutException:
                        logger.warning("Age verification: Page did not redirect as expected")
            else:
                logger.debug("No age verification page detected")
                
        except Exception as e:
            logger.warning(f"Age verification handling failed: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def __del__(self):
        """デストラクタでドライバーを閉じる"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def get_work_list(self, list_url: str) -> List[str]:
        """作品一覧ページから作品詳細URLリストを取得"""
        work_urls = []
        
        if self.use_selenium and self.driver:
            return self._get_work_list_selenium(list_url)
        else:
            return self._get_work_list_requests(list_url)
    
    def _get_work_list_selenium(self, list_url: str) -> List[str]:
        """Seleniumを使用した作品一覧取得"""
        work_urls = []
        
        try:
            logger.info(f"Accessing URL with Selenium: {list_url}")
            self.driver.get(list_url)
            
            # 年齢認証ページの処理
            self._handle_age_verification()
            
            # ページが完全に読み込まれるまで待機
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(3)  # 動的コンテンツの読み込み待機
            
            # 複数のセレクタパターンを試行
            work_link_selectors = [
                'div.d-item a[href*="/detail/"]',  # 既存のセレクタ
                'a[href*="/dc/doujin/-/detail/"]',  # より具体的なパス
                'div.tmb a[href*="/detail/"]',  # サムネイル内のリンク
                'div.list-item a[href*="/detail/"]',  # リストアイテム内のリンク
                '.item a[href*="/detail/"]',  # 汎用アイテムクラス
                'a[href*="cid="]',  # cid パラメータを含むリンク
            ]
            
            for selector in work_link_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        for element in elements:
                            href = element.get_attribute('href')
                            if href and href not in work_urls:
                                work_urls.append(href)
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # HTMLソースを取得してBeautifulSoupでも試行
            if not work_urls:
                html_source = self.driver.page_source
                soup = BeautifulSoup(html_source, 'lxml')
                
                # より多くのセレクタパターンを試行
                additional_selectors = [
                    'a[href*="/detail/"]',
                    'a[href*="cid="]',
                    'div[class*="item"] a',
                    'div[class*="tmb"] a',
                    'ul li a[href*="/dc/"]',
                ]
                
                for selector in additional_selectors:
                    work_links = soup.select(selector)
                    for link in work_links:
                        href = link.get('href')
                        if href and '/detail/' in href and href not in work_urls:
                            full_url = urljoin(self.base_url, href)
                            work_urls.append(full_url)
                    
                    if work_urls:
                        logger.info(f"Found links with BeautifulSoup selector: {selector}")
                        break
            
            logger.info(f"Found {len(work_urls)} works")
            
        except Exception as e:
            logger.error(f"Error getting work list with Selenium: {e}")
            # フォールバックとしてrequests方式を試行
            return self._get_work_list_requests(list_url)
        
        return work_urls
    
    def _get_work_list_requests(self, list_url: str) -> List[str]:
        """requestsを使用した作品一覧取得（フォールバック）"""
        work_urls = []
        
        try:
            response = self.session.get(list_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 複数のセレクタパターンを試行
            work_link_selectors = [
                'div.d-item a[href*="/detail/"]',
                'a[href*="/dc/doujin/-/detail/"]',
                'div.tmb a[href*="/detail/"]',
                'div.list-item a[href*="/detail/"]',
                '.item a[href*="/detail/"]',
                'a[href*="cid="]',
                'a[href*="/detail/"]',
            ]
            
            for selector in work_link_selectors:
                work_links = soup.select(selector)
                if work_links:
                    logger.info(f"Found {len(work_links)} links with selector: {selector}")
                    for link in work_links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            work_urls.append(full_url)
                    break
            
            logger.info(f"Found {len(work_urls)} works with requests")
            
        except Exception as e:
            logger.error(f"Error getting work list with requests: {e}")
        
        return work_urls
    
    def scrape_work_detail(self, work_url: str) -> Optional[Dict]:
        """作品詳細ページから情報を取得"""
        if self.use_selenium and self.driver:
            return self._scrape_work_detail_selenium(work_url)
        else:
            return self._scrape_work_detail_requests(work_url)
    
    def _scrape_work_detail_selenium(self, work_url: str) -> Optional[Dict]:
        """Seleniumを使用した作品詳細取得"""
        try:
            time.sleep(self.request_delay)  # リクエスト間隔を守る
            
            logger.info(f"Accessing work detail with Selenium: {work_url}")
            self.driver.get(work_url)
            
            # 年齢認証ページの処理
            self._handle_age_verification()
            
            # ページが完全に読み込まれるまで待機
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # 動的コンテンツの読み込み待機
            
            # HTMLソースを取得してBeautifulSoupで解析
            html_source = self.driver.page_source
            soup = BeautifulSoup(html_source, 'lxml')
            
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
            
            logger.info(f"Successfully scraped with Selenium: {work_data['title']}")
            return work_data
            
        except Exception as e:
            logger.error(f"Error scraping work detail with Selenium from {work_url}: {e}")
            # フォールバックとしてrequests方式を試行
            return self._scrape_work_detail_requests(work_url)
    
    def _scrape_work_detail_requests(self, work_url: str) -> Optional[Dict]:
        """requestsを使用した作品詳細取得（フォールバック）"""
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
            
            logger.info(f"Successfully scraped with requests: {work_data['title']}")
            return work_data
            
        except Exception as e:
            logger.error(f"Error scraping work detail with requests from {work_url}: {e}")
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
        title_selectors = [
            'h1#title',
            'h1.productTitle',
            'h1[id*="title"]',
            'h1.ttl',
            '.productTitle',
            'h1.work-title',
            '.title h1',
            'h1',  # 最後の手段として汎用的なh1タグ
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.text.strip():
                return title_elem.text.strip()
        
        return ""
    
    def _extract_circle_name(self, soup: BeautifulSoup) -> str:
        """サークル名を抽出"""
        circle_selectors = [
            'a[href*="/list/=/article=maker/"]',
            'a[href*="article=maker"]',
            '.maker a',
            '.circle-name a',
            '.brand a',
            'td:contains("サークル名") + td a',
            'td:contains("ブランド名") + td a',
            'a[href*="/circle/"]',
            'a[href*="/brand/"]',
        ]
        
        for selector in circle_selectors:
            circle_elem = soup.select_one(selector)
            if circle_elem and circle_elem.text.strip():
                return circle_elem.text.strip()
        
        return ""
    
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
        image_selectors = [
            'img.package-image',
            'div.package img',
            '.productImg img',
            '.jacket img',
            '.main-image img',
            '.package img',
            'img[src*="jacket"]',
            'img[src*="package"]',
            'img[src*="main"]',
            '.work-image img',
            '.thumbnail img',
        ]
        
        for selector in image_selectors:
            img_elem = soup.select_one(selector)
            if img_elem and img_elem.get('src'):
                src = img_elem['src']
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(self.base_url, src)
                return src
        
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """作品紹介文を抽出"""
        desc_selectors = [
            'div.summary__txt',
            'div.work-text',
            '.summary',
            '.description',
            '.work-description',
            '.intro',
            '.synopsis',
            'div[class*="summary"]',
            'div[class*="description"]',
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem and desc_elem.text.strip():
                return desc_elem.text.strip()
        
        return ""
    
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