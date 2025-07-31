import random
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ArticleGenerator:
    def __init__(self, wordpress_api):
        """記事生成クラスの初期化"""
        self.wp_api = wordpress_api
        
    def generate_article_content(self, work_data: Dict, rewritten_description: str) -> str:
        """記事本文を生成"""
        
        # サークル名のタグアーカイブURL
        circle_tag_url = self.wp_api.get_tag_archive_url(work_data['circle_name'])
        
        # H2見出しパターンをランダムに選択
        h2_pattern = random.randint(1, 3)
        h2_headings = {
            1: "作品の見どころ",
            2: "この作品のおすすめポイント",
            3: "注目すべき魅力"
        }
        h2_heading = h2_headings[h2_pattern]
        
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
        if work_data['sample_images']:
            content_parts.append('<h3>サンプル画像</h3>')
            for img_url in work_data['sample_images'][:5]:  # 最大5枚まで
                content_parts.append(
                    f'<img src="{img_url}" alt="{work_data["title"]} サンプル画像" class="aligncenter size-full" />'
                )
        
        # アフィリエイトリンク（ボタン）
        content_parts.append(
            f'<div class="swell-block-button red_ is-style-btn_solid">'
            f'<a href="{work_data["affiliate_url"]}" class="swell-block-button__link">'
            f'<span>続きを読むにはクリック</span></a></div>'
        )
        
        # レビュー
        if work_data['reviews']:
            content_parts.append('<h3>レビュー</h3>')
            for review in work_data['reviews']:
                if review['rating']:
                    content_parts.append(f'<p><strong>評価：</strong>{review["rating"]}</p>')
                content_parts.append(f'<blockquote>{review["text"]}</blockquote>')
        
        # H2見出し
        content_parts.append(f'<h2>{h2_heading}</h2>')
        content_parts.append(
            '<p>この作品は、ストーリー展開と魅力的なキャラクターが特徴的です。'
            'ぜひ一度ご覧になってみてください。</p>'
        )
        
        # 関連作品（WordPressの機能で自動表示される想定のためコメント）
        content_parts.append('<!-- 関連作品はWordPressプラグインで自動表示 -->')
        
        return '\n\n'.join(content_parts)
    
    def prepare_post_data(self, work_data: Dict, rewritten_description: str) -> Dict:
        """WordPress投稿用のデータを準備"""
        
        # 記事タイトル
        title = work_data['title']
        
        # 記事本文
        content = self.generate_article_content(work_data, rewritten_description)
        
        # タグ（作者名、サークル名）
        tags = []
        if work_data['circle_name']:
            tags.append(work_data['circle_name'])
        if work_data['author_name'] and work_data['author_name'] != work_data['circle_name']:
            tags.append(work_data['author_name'])
        
        # ジャンルもタグとして追加
        if work_data['genres']:
            tags.extend(work_data['genres'])
        
        # カテゴリー
        category = work_data['category'] if work_data['category'] else '同人'
        
        return {
            'title': title,
            'content': content,
            'tags': tags,
            'category': category,
            'work_id': work_data['work_id']
        }