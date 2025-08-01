"""
リファクタリング済み記事生成クラス
"""
import random
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

from ..utils.constants import Constants, DefaultValues
from ..services.exceptions import FileOperationError
from ..utils.utils import safe_get_nested


logger = logging.getLogger(__name__)


class H2PatternManager:
    """H2見出しパターン管理クラス"""
    
    def __init__(self, patterns_dir: str = None):
        """
        H2パターンマネージャーの初期化
        
        Args:
            patterns_dir: パターンファイルが格納されているディレクトリ
        """
        if patterns_dir is None:
            # 新しいディレクトリ構造に対応
            project_root = Path(__file__).parent.parent.parent
            patterns_dir = project_root / "docs" / "patterns"
        
        self.patterns_dir = Path(patterns_dir)
        self._patterns = self._load_patterns()
        
        logger.info(f"Loaded {len(self._patterns)} H2 patterns from {self.patterns_dir}")
    
    def _load_patterns(self) -> List[str]:
        """H2パターンを起動時に一度だけ読み込み"""
        patterns = []
        
        for i in range(1, 4):  # パターン1-3
            # 装飾版を優先的に読み込み
            decorated_pattern_file = self.patterns_dir / f'パターン{i}_装飾版'
            standard_pattern_file = self.patterns_dir / f'パターン{i}'
            
            pattern_file = decorated_pattern_file if decorated_pattern_file.exists() else standard_pattern_file
            
            try:
                if pattern_file.exists():
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            patterns.append(content)
                            logger.debug(f"Loaded pattern {i}")
                        else:
                            logger.warning(f"Pattern file {i} is empty")
                else:
                    logger.warning(f"Pattern file {pattern_file} not found")
                    
            except Exception as e:
                logger.error(f"Failed to load pattern {i}: {e}")
        
        # フォールバック処理
        if not patterns:
            logger.warning("No H2 patterns loaded, using fallback patterns")
            patterns = DefaultValues.FALLBACK_H2_HEADINGS.copy()
        
        return patterns
    
    def get_random_pattern(self, work_title: str, affiliate_url: str = '') -> str:
        """
        ランダムなH2パターンを取得し、タイトルとアフィリエイトURLを置換
        
        Args:
            work_title: 作品タイトル
            affiliate_url: アフィリエイトURL
        
        Returns:
            タイトルとURLが置換されたH2パターン
        """
        if not self._patterns:
            return DefaultValues.FALLBACK_H2_HEADINGS[0]
        
        pattern = random.choice(self._patterns)
        
        # タイトルとアフィリエイトURLを置換
        pattern = pattern.replace('「タイトル」', f'「{work_title}」')
        pattern = pattern.replace('#affiliate-link', affiliate_url or '#')
        
        return pattern
    
    def reload_patterns(self) -> int:
        """
        パターンを再読み込み
        
        Returns:
            読み込まれたパターン数
        """
        self._patterns = self._load_patterns()
        return len(self._patterns)


class ArticleGenerator:
    """記事生成クラス（リファクタリング版）"""
    
    def __init__(self, wordpress_api):
        """
        記事生成クラスの初期化
        
        Args:
            wordpress_api: WordPress APIクライアント
        """
        self.wp_api = wordpress_api
        self.h2_manager = H2PatternManager()
        
        logger.info("Article generator initialized")
    
    def generate_article_content(self, work_data: Dict, rewritten_description: str) -> str:
        """
        記事本文を生成
        
        Args:
            work_data: 作品データ
            rewritten_description: リライト済み紹介文
        
        Returns:
            生成された記事本文
        """
        content_parts = []
        
        # 各セクションを順次生成
        content_parts.extend(self._generate_intro_section(work_data))
        content_parts.extend(self._generate_package_image_section(work_data))
        content_parts.extend(self._generate_description_section(rewritten_description))
        content_parts.extend(self._generate_work_info_section(work_data))
        content_parts.extend(self._generate_genre_section(work_data))
        content_parts.extend(self._generate_sample_images_section(work_data))
        content_parts.extend(self._generate_affiliate_button_section(work_data))
        content_parts.extend(self._generate_review_section(work_data))
        content_parts.extend(self._generate_h2_section(work_data))
        content_parts.append('<!-- 関連作品はWordPressプラグインで自動表示 -->')
        
        return '\n\n'.join(content_parts)
    
    def _generate_intro_section(self, work_data: Dict) -> List[str]:
        """導入文セクションを生成"""
        circle_name = work_data.get('circle_name', DefaultValues.CIRCLE_NAME_UNKNOWN)
        circle_tag_url = self.wp_api.get_tag_archive_url(circle_name)
        
        return [f'<p>エロ同人サークル「<a href="{circle_tag_url}">{circle_name}</a>」のエロマンガです。</p>']
    
    def _generate_package_image_section(self, work_data: Dict) -> List[str]:
        """パッケージ画像セクションを生成"""
        package_image_url = work_data.get('package_image_url')
        title = work_data.get('title', '')
        
        if package_image_url:
            return [f'<img src="{package_image_url}" alt="{title}" class="aligncenter size-full" />']
        
        return []
    
    def _generate_description_section(self, rewritten_description: str) -> List[str]:
        """紹介文セクションを生成"""
        if rewritten_description:
            return [f'<p>{rewritten_description}</p>']
        
        return []
    
    def _generate_work_info_section(self, work_data: Dict) -> List[str]:
        """作品情報セクションを生成"""
        sections = []
        page_count = work_data.get('page_count')
        
        if page_count and page_count != DefaultValues.PAGE_COUNT_UNKNOWN:
            sections.append(f'<p><strong>ページ数：</strong>{page_count}</p>')
        
        return sections
    
    def _generate_genre_section(self, work_data: Dict) -> List[str]:
        """ジャンルセクションを生成"""
        genres = work_data.get('genres', [])
        
        if not genres:
            return []
        
        genre_links = []
        for genre in genres:
            genre_url = self.wp_api.get_tag_archive_url(genre)
            genre_links.append(f'<a href="{genre_url}">{genre}</a>')
        
        return [f'<p><strong>ジャンル：</strong>{", ".join(genre_links)}</p>']
    
    def _generate_sample_images_section(self, work_data: Dict) -> List[str]:
        """サンプル画像セクションを生成"""
        sample_images = work_data.get('sample_images', [])
        title = work_data.get('title', '')
        
        if not sample_images:
            logger.debug(f"No sample images found for {title}")
            return []
        
        sections = ['<h3>サンプル画像</h3>']
        
        # 最大件数まで画像を追加
        for img_url in sample_images[:Constants.MAX_SAMPLE_IMAGES]:
            sections.append(
                f'<img src="{img_url}" alt="{title} サンプル画像" class="aligncenter size-full" />'
            )
        
        logger.info(f"Added {min(len(sample_images), Constants.MAX_SAMPLE_IMAGES)} sample images for {title}")
        
        return sections
    
    def _generate_affiliate_button_section(self, work_data: Dict) -> List[str]:
        """アフィリエイトボタンセクションを生成"""
        affiliate_url = work_data.get('affiliate_url', '')
        
        if not affiliate_url:
            return []
        
        return [
            f'<div class="swell-block-button red_ is-style-btn_solid"><a href="{affiliate_url}" class="swell-block-button__link"><span>続きを読むにはクリック</span></a></div>'
        ]
    
    def _generate_review_section(self, work_data: Dict) -> List[str]:
        """レビューセクションを生成"""
        reviews = work_data.get('reviews', [])
        
        if not reviews:
            return []
        
        sections = ['<h3>レビュー</h3>']
        
        for review in reviews:
            rating = review.get('rating')
            text = review.get('text')
            
            if rating:
                sections.append(f'<p><strong>評価：</strong>{rating}</p>')
            if text:
                sections.append(f'<blockquote>{text}</blockquote>')
        
        return sections
    
    def _generate_h2_section(self, work_data: Dict) -> List[str]:
        """H2見出しセクションを生成"""
        title = work_data.get('title', '')
        affiliate_url = work_data.get('affiliate_url', '')
        h2_content = self.h2_manager.get_random_pattern(title, affiliate_url)
        
        return [h2_content]
    
    def prepare_post_data(self, work_data: Dict, rewritten_description: str) -> Dict:
        """
        WordPress投稿用のデータを準備
        
        Args:
            work_data: 作品データ
            rewritten_description: リライト済み紹介文
        
        Returns:
            WordPress投稿用データ
        """
        # 記事タイトル
        title = work_data.get('title', '')
        
        # 記事本文
        content = self.generate_article_content(work_data, rewritten_description)
        
        # タグの準備
        tags = self._prepare_tags(work_data)
        
        # カテゴリー（全てのジャンルを使用）
        category = DefaultValues.DEFAULT_CATEGORY  # デフォルト: '同人'
        genres = work_data.get('genres', [])
        if genres and len(genres) > 0:
            category = genres  # 全てのジャンルをリストで渡す
        elif work_data.get('category'):
            category = work_data.get('category')
        
        return {
            'title': title,
            'content': content,
            'tags': tags,
            'category': category,
            'work_id': work_data.get('work_id', '')
        }
    
    def _prepare_tags(self, work_data: Dict) -> List[str]:
        """タグリストを準備（作者名・サークル名のみ）"""
        tags = []
        
        # サークル名をタグに追加
        circle_name = work_data.get('circle_name')
        if circle_name and circle_name != DefaultValues.CIRCLE_NAME_UNKNOWN:
            tags.append(circle_name)
        
        # 作者名をタグに追加（サークル名と異なる場合のみ）
        author_name = work_data.get('author_name')
        if (author_name and 
            author_name != DefaultValues.CIRCLE_NAME_UNKNOWN and 
            author_name != circle_name):
            tags.append(author_name)
        
        # 重複を除去して返す
        return list(dict.fromkeys(tags))  # 順序を保持しつつ重複除去