"""
入力検証・サニタイゼーションシステム - セキュリティ強化
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
import bleach
from urllib.parse import urlparse, parse_qs
import json

logger = logging.getLogger(__name__)


class InputValidator:
    """入力検証・サニタイゼーションシステム"""
    
    # 許可されるHTMLタグ（WordPress投稿用）
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'div', 'span'
    ]
    
    # 許可されるHTML属性
    ALLOWED_HTML_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'div': ['class', 'id'],
        'span': ['class', 'id']
    }
    
    # 危険なパターン
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # スクリプトタグ
        r'javascript:',                # JavaScriptプロトコル
        r'on\w+\s*=',                 # イベントハンドラ
        r'<iframe[^>]*>.*?</iframe>',  # iframe
        r'<object[^>]*>.*?</object>',  # object
        r'<embed[^>]*>',               # embed
        r'<form[^>]*>.*?</form>',      # form
    ]
    
    def __init__(self):
        """バリデーター初期化"""
        logger.info("入力検証システム初期化完了")
    
    def validate_and_sanitize_article_content(self, content: str) -> str:
        """
        記事コンテンツの検証とサニタイゼーション
        
        Args:
            content: 記事コンテンツ
            
        Returns:
            サニタイズされた安全なコンテンツ
        """
        if not content or not isinstance(content, str):
            return ""
        
        try:
            # 1. 危険なパターンの除去
            sanitized = self._remove_dangerous_patterns(content)
            
            # 2. HTMLタグのサニタイゼーション
            sanitized = self._sanitize_html_content(sanitized)
            
            # 3. URLの検証
            sanitized = self._validate_urls_in_content(sanitized)
            
            # 4. 文字エンコーディングの正規化
            sanitized = self._normalize_encoding(sanitized)
            
            # 5. 長さ制限
            sanitized = self._apply_length_limits(sanitized)
            
            logger.debug(f"記事コンテンツをサニタイズしました (元: {len(content)}文字 → 後: {len(sanitized)}文字)")
            
            return sanitized
            
        except Exception as e:
            logger.error(f"記事コンテンツサニタイゼーションエラー: {e}")
            # エラー時は安全な空文字を返す
            return ""
    
    def validate_work_data(self, work_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        作品データの検証とサニタイゼーション
        
        Args:
            work_data: 作品データ
            
        Returns:
            検証済み作品データ
        """
        if not isinstance(work_data, dict):
            raise ValueError("作品データは辞書である必要があります")
        
        validated_data = {}
        
        try:
            # 必須フィールドの検証
            validated_data['work_id'] = self._validate_work_id(work_data.get('work_id'))
            validated_data['title'] = self._sanitize_text_field(work_data.get('title', ''), max_length=200)
            
            # オプションフィールドの検証
            validated_data['author_name'] = self._sanitize_text_field(
                work_data.get('author_name', ''), max_length=100
            )
            validated_data['circle_name'] = self._sanitize_text_field(
                work_data.get('circle_name', ''), max_length=100
            )
            validated_data['description'] = self._sanitize_text_field(
                work_data.get('description', ''), max_length=1000
            )
            
            # URL フィールドの検証
            validated_data['detail_url'] = self._validate_url(work_data.get('detail_url', ''))
            validated_data['affiliate_url'] = self._validate_url(work_data.get('affiliate_url', ''))
            
            # 画像URLの検証
            validated_data['image_urls'] = self._validate_image_urls(
                work_data.get('image_urls', [])
            )
            
            # 数値フィールドの検証
            validated_data['price'] = self._validate_integer(work_data.get('price'), min_val=0)
            validated_data['page_count'] = self._validate_integer(work_data.get('page_count'), min_val=0)
            validated_data['rating'] = self._validate_float(work_data.get('rating'), min_val=0.0, max_val=5.0)
            
            # 日付フィールドの検証
            validated_data['release_date'] = self._sanitize_text_field(
                work_data.get('release_date', ''), max_length=20
            )
            
            # ジャンル・タグの検証
            validated_data['genre'] = self._sanitize_text_field(work_data.get('genre', ''), max_length=50)
            validated_data['tags'] = self._validate_tag_list(work_data.get('tags', []))
            
            # レビューデータの検証
            if 'reviews' in work_data:
                validated_data['reviews'] = self._validate_reviews(work_data['reviews'])
            
            logger.debug(f"作品データを検証しました: {validated_data['title']}")
            
            return validated_data
            
        except Exception as e:
            logger.error(f"作品データ検証エラー: {e}")
            raise ValueError(f"作品データの検証に失敗しました: {e}")
    
    def validate_api_response(self, response_data: Any, expected_type: type = dict) -> Any:
        """
        API応答の検証
        
        Args:
            response_data: API応答データ
            expected_type: 期待されるデータ型
            
        Returns:
            検証済みAPI応答
        """
        if response_data is None:
            raise ValueError("API応答がNullです")
        
        if not isinstance(response_data, expected_type):
            raise TypeError(f"API応答の型が不正です。期待: {expected_type}, 実際: {type(response_data)}")
        
        # JSON の場合の追加検証
        if isinstance(response_data, dict):
            # 深い検証を実行
            validated_response = self._deep_validate_dict(response_data)
            logger.debug("API応答を検証しました")
            return validated_response
        
        return response_data
    
    def _remove_dangerous_patterns(self, content: str) -> str:
        """危険なパターンを除去"""
        for pattern in self.DANGEROUS_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        return content
    
    def _sanitize_html_content(self, content: str) -> str:
        """HTMLコンテンツのサニタイゼーション"""
        return bleach.clean(
            content,
            tags=self.ALLOWED_HTML_TAGS,
            attributes=self.ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
    
    def _validate_urls_in_content(self, content: str) -> str:
        """コンテンツ内のURLを検証"""
        # URLパターンを検索
        url_pattern = r'https?://[^\s<>"\'()]+'
        
        def validate_url_match(match):
            url = match.group(0)
            if self._is_safe_url(url):
                return url
            else:
                logger.warning(f"危険なURLを除去: {url}")
                return "[URLが除去されました]"
        
        return re.sub(url_pattern, validate_url_match, content)
    
    def _is_safe_url(self, url: str) -> bool:
        """URLの安全性をチェック"""
        try:
            parsed = urlparse(url)
            
            # プロトコルチェック
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # ドメインチェック（許可リスト）
            allowed_domains = [
                'dmm.co.jp',
                'al.dmm.co.jp',
                'pics.dmm.co.jp',
                'mania-wiki.com',
                'wordpress.com',
                'gravatar.com'
            ]
            
            domain = parsed.netloc.lower()
            if not any(allowed_domain in domain for allowed_domain in allowed_domains):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _normalize_encoding(self, content: str) -> str:
        """文字エンコーディングの正規化"""
        # HTMLエンティティのデコード
        content = html.unescape(content)
        
        # 制御文字の除去
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return content
    
    def _apply_length_limits(self, content: str, max_length: int = 50000) -> str:
        """長さ制限の適用"""
        if len(content) > max_length:
            logger.warning(f"コンテンツが長すぎるため切り詰めました: {len(content)} → {max_length}")
            return content[:max_length] + "..."
        return content
    
    def _validate_work_id(self, work_id: Any) -> str:
        """作品IDの検証"""
        if not work_id:
            raise ValueError("作品IDが必要です")
        
        work_id_str = str(work_id).strip()
        
        # 英数字、ハイフン、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9_-]+$', work_id_str):
            raise ValueError("作品IDに無効な文字が含まれています")
        
        if len(work_id_str) > 100:
            raise ValueError("作品IDが長すぎます")
        
        return work_id_str
    
    def _sanitize_text_field(self, text: Any, max_length: int = 500) -> str:
        """テキストフィールドのサニタイゼーション"""
        if not text:
            return ""
        
        text_str = str(text).strip()
        
        # HTMLタグの除去
        text_str = re.sub(r'<[^>]+>', '', text_str)
        
        # 制御文字の除去
        text_str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text_str)
        
        # 長さ制限
        if len(text_str) > max_length:
            text_str = text_str[:max_length]
        
        return text_str
    
    def _validate_url(self, url: Any) -> str:
        """URL の検証"""
        if not url:
            return ""
        
        url_str = str(url).strip()
        
        if not self._is_safe_url(url_str):
            logger.warning(f"不正なURLです: {url_str}")
            return ""
        
        return url_str
    
    def _validate_image_urls(self, urls: Any) -> List[str]:
        """画像URLリストの検証"""
        if not urls or not isinstance(urls, (list, tuple)):
            return []
        
        validated_urls = []
        for url in urls[:10]:  # 最大10個まで
            validated_url = self._validate_url(url)
            if validated_url:
                validated_urls.append(validated_url)
        
        return validated_urls
    
    def _validate_integer(self, value: Any, min_val: Optional[int] = None, 
                         max_val: Optional[int] = None) -> Optional[int]:
        """整数値の検証"""
        if value is None or value == "":
            return None
        
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return min_val
            
            if max_val is not None and int_val > max_val:
                return max_val
            
            return int_val
            
        except (ValueError, TypeError):
            return None
    
    def _validate_float(self, value: Any, min_val: Optional[float] = None, 
                       max_val: Optional[float] = None) -> Optional[float]:
        """浮動小数点値の検証"""
        if value is None or value == "":
            return None
        
        try:
            float_val = float(value)
            
            if min_val is not None and float_val < min_val:
                return min_val
            
            if max_val is not None and float_val > max_val:
                return max_val
            
            return float_val
            
        except (ValueError, TypeError):
            return None
    
    def _validate_tag_list(self, tags: Any) -> List[str]:
        """タグリストの検証"""
        if not tags or not isinstance(tags, (list, tuple)):
            return []
        
        validated_tags = []
        for tag in tags[:20]:  # 最大20個まで
            sanitized_tag = self._sanitize_text_field(tag, max_length=50)
            if sanitized_tag and sanitized_tag not in validated_tags:
                validated_tags.append(sanitized_tag)
        
        return validated_tags
    
    def _validate_reviews(self, reviews: Any) -> List[Dict[str, Any]]:
        """レビューデータの検証"""
        if not reviews or not isinstance(reviews, (list, tuple)):
            return []
        
        validated_reviews = []
        for review in reviews[:50]:  # 最大50個まで
            if isinstance(review, dict):
                validated_review = {
                    'rating': self._validate_float(review.get('rating'), 0.0, 5.0),
                    'comment': self._sanitize_text_field(review.get('comment', ''), max_length=1000),
                    'author': self._sanitize_text_field(review.get('author', ''), max_length=100)
                }
                validated_reviews.append(validated_review)
        
        return validated_reviews
    
    def _deep_validate_dict(self, data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """辞書の深い検証"""
        if max_depth <= 0:
            return {}
        
        validated_dict = {}
        
        for key, value in data.items():
            # キーの検証
            safe_key = self._sanitize_text_field(key, max_length=100)
            if not safe_key:
                continue
            
            # 値の検証
            if isinstance(value, dict):
                validated_dict[safe_key] = self._deep_validate_dict(value, max_depth - 1)
            elif isinstance(value, (list, tuple)):
                validated_dict[safe_key] = self._validate_list(value, max_depth - 1)
            elif isinstance(value, str):
                validated_dict[safe_key] = self._sanitize_text_field(value, max_length=10000)
            elif isinstance(value, (int, float, bool)):
                validated_dict[safe_key] = value
            else:
                # その他の型は文字列に変換
                validated_dict[safe_key] = self._sanitize_text_field(str(value), max_length=1000)
        
        return validated_dict
    
    def _validate_list(self, data: List[Any], max_depth: int = 10) -> List[Any]:
        """リストの検証"""
        if max_depth <= 0:
            return []
        
        validated_list = []
        
        for item in data[:100]:  # 最大100要素まで
            if isinstance(item, dict):
                validated_list.append(self._deep_validate_dict(item, max_depth - 1))
            elif isinstance(item, (list, tuple)):
                validated_list.append(self._validate_list(item, max_depth - 1))
            elif isinstance(item, str):
                validated_list.append(self._sanitize_text_field(item, max_length=1000))
            elif isinstance(item, (int, float, bool)):
                validated_list.append(item)
            else:
                validated_list.append(self._sanitize_text_field(str(item), max_length=1000))
        
        return validated_list


# グローバルバリデーターインスタンス
validator = InputValidator()