import random
import os
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ArticleGenerator:
    def __init__(self, wordpress_api):
        """記事生成クラスの初期化"""
        self.wp_api = wordpress_api
        self.h2_patterns_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'H2見出し')
    
    def load_h2_pattern(self, work_title: str) -> str:
        """H2見出しパターンファイルを読み込み、タイトルを置換"""
        try:
            # パターン1-3からランダムに選択
            pattern_num = random.randint(1, 3)
            # 装飾版を優先的に選択
            decorated_pattern_file = os.path.join(self.h2_patterns_dir, f'パターン{pattern_num}_装飾版')
            standard_pattern_file = os.path.join(self.h2_patterns_dir, f'パターン{pattern_num}')
            
            pattern_file = decorated_pattern_file if os.path.exists(decorated_pattern_file) else standard_pattern_file
            
            if os.path.exists(pattern_file):
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_content = f.read().strip()
                    # 「タイトル」を実際の作品名に置換
                    return pattern_content.replace('「タイトル」', f'「{work_title}」')
            else:
                logger.warning(f"H2パターンファイルが見つかりません: {pattern_file}")
                # フォールバック用の固定見出し
                fallback_headings = {
                    1: "作品の見どころ",
                    2: "この作品のおすすめポイント", 
                    3: "注目すべき魅力"
                }
                return fallback_headings.get(pattern_num, fallback_headings[1])
                
        except Exception as e:
            logger.error(f"H2パターン読み込みエラー: {e}")
            return "作品の見どころ"
        
    def generate_article_content(self, work_data: Dict, rewritten_description: str) -> str:
        """記事本文を生成"""
        
        # サークル名のタグアーカイブURL
        circle_tag_url = self.wp_api.get_tag_archive_url(work_data['circle_name'])
        
        # 記事本文の組み立て
        content_parts = []
        
        # 導入文
        content_parts.append(
            f'<p>エロ同人サークル「<a href="{circle_tag_url}">{work_data["circle_name"]}</a>」のエロマンガです。</p>'
        )
        
        # パッケージ画像
        if work_data['package_image_url']:
            content_parts.append(
                f'<img src="{work_data["package_image_url"]}" alt="{work_data["title"]}" class="aligncenter size-full" />'
            )
        
        # 商品紹介文（リライト済み）
        content_parts.append(f'<p>{rewritten_description}</p>')
        
        # 作品情報
        if work_data['page_count']:
            content_parts.append(f'<p><strong>ページ数：</strong>{work_data["page_count"]}</p>')
        
        # ジャンル（内部リンク化を想定）
        if work_data['genres']:
            genre_links = []
            for genre in work_data['genres']:
                genre_url = self.wp_api.get_tag_archive_url(genre)
                genre_links.append(f'<a href="{genre_url}">{genre}</a>')
            content_parts.append(f'<p><strong>ジャンル：</strong>{", ".join(genre_links)}</p>')
        
        # サンプル画像
        logger.info(f"Processing sample images for {work_data['title']}: {len(work_data.get('sample_images', []))} images")
        if work_data.get('sample_images'):
            logger.info(f"Adding sample images section with {len(work_data['sample_images'])} images")
            content_parts.append('<h3>サンプル画像</h3>')
            for i, img_url in enumerate(work_data['sample_images'][:5]):  # 最大5枚まで
                logger.info(f"Adding sample image {i+1}: {img_url}")
                content_parts.append(
                    f'<img src="{img_url}" alt="{work_data["title"]} サンプル画像" class="aligncenter size-full" />'
                )
        else:
            logger.info(f"No sample images found for {work_data['title']}")
        
        # アフィリエイトリンク（ボタン）- SWELLボタン形式
        content_parts.append(
            f'<div class="swell-block-button red_ is-style-btn_solid"><a href="{work_data["affiliate_url"]}" class="swell-block-button__link"><span>続きを読むにはクリック</span></a></div>'
        )
        
        # レビュー
        if work_data['reviews']:
            content_parts.append('<h3>レビュー</h3>')
            for review in work_data['reviews']:
                if review['rating']:
                    content_parts.append(f'<p><strong>評価：</strong>{review["rating"]}</p>')
                content_parts.append(f'<blockquote>{review["text"]}</blockquote>')
        
        # H2見出しパターンを読み込み
        h2_content = self.load_h2_pattern(work_data['title'])
        content_parts.append(h2_content)
        
        # 関連作品（WordPressの機能で自動表示される想定のためコメント）
        content_parts.append('<!-- 関連作品はWordPressプラグインで自動表示 -->')
        
        return '\n\n'.join(content_parts)
    
    def prepare_post_data(self, work_data: Dict, rewritten_description: str) -> Dict:
        """WordPress投稿用のデータを準備"""
        
        # 記事タイトル
        title = work_data['title']
        
        # 記事本文
        content = self.generate_article_content(work_data, rewritten_description)
        
        # タグ（作者名、サークル名のみ）
        tags = []
        if work_data['circle_name']:
            tags.append(work_data['circle_name'])
        if work_data['author_name'] and work_data['author_name'] != work_data['circle_name']:
            tags.append(work_data['author_name'])
        
        # カテゴリー（全てのジャンルを使用）
        category = '同人'  # デフォルト
        if work_data['genres'] and len(work_data['genres']) > 0:
            category = work_data['genres']  # 全てのジャンルをリストで渡す
        elif work_data['category']:
            category = work_data['category']
        
        return {
            'title': title,
            'content': content,
            'tags': tags,
            'category': category,
            'work_id': work_data['work_id']
        }