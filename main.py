#!/usr/bin/env python3
import configparser
import logging
import os
import sys
from datetime import datetime, timedelta
import time

from modules.fanza_scraper import FANZAScraper
from modules.gemini_api import GeminiAPI
from modules.wordpress_api import WordPressAPI
from modules.article_generator import ArticleGenerator
from modules.post_manager import PostManager


def setup_logging(log_level: str = 'INFO'):
    """ログ設定のセットアップ"""
    # ログディレクトリの作成
    os.makedirs('logs', exist_ok=True)
    
    # ログファイル名（日付付き）
    log_file = f'logs/auto_post_{datetime.now().strftime("%Y%m%d")}.log'
    
    # ログフォーマット
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ログ設定
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(config_file: str = 'config.ini'):
    """設定ファイルを読み込む"""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_file}")
    
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    return config


def main():
    """メイン処理"""
    try:
        # 設定ファイルの読み込み
        config = load_config()
        
        # ログのセットアップ
        log_level = config.get('settings', 'log_level', fallback='INFO')
        logger = setup_logging(log_level)
        logger.info("=== WordPress自動投稿システム開始 ===")
        
        # 各種設定の取得
        wp_url = config.get('wordpress', 'url')
        wp_username = config.get('wordpress', 'username')
        wp_password = config.get('wordpress', 'password')
        
        fanza_affiliate_id = config.get('fanza', 'affiliate_id', fallback='')
        
        gemini_api_key = config.get('gemini', 'api_key')
        
        max_posts = config.getint('settings', 'max_posts_per_run', fallback=1)
        request_delay = config.getint('settings', 'request_delay', fallback=2)
        
        # 各モジュールの初期化
        logger.info("モジュールを初期化中...")
        
        scraper = FANZAScraper(
            affiliate_id=fanza_affiliate_id,
            request_delay=request_delay
        )
        
        gemini = GeminiAPI(api_key=gemini_api_key)
        
        wp_api = WordPressAPI(
            url=wp_url,
            username=wp_username,
            password=wp_password
        )
        
        article_gen = ArticleGenerator(wordpress_api=wp_api)
        
        post_manager = PostManager()
        
        # FANZAの作品一覧URL
        list_url = "https://www.dmm.co.jp/dc/doujin/-/list/=/media=comic/review_score=3.5/section=mens/sort=date/?dmmref=detailedSearch"
        
        # 作品リストの取得
        logger.info(f"作品リストを取得中: {list_url}")
        work_urls = scraper.get_work_list(list_url)
        
        if not work_urls:
            logger.warning("作品が見つかりませんでした")
            return
        
        # 未投稿作品のフィルタリング
        work_ids = [scraper._extract_work_id(url) for url in work_urls]
        unposted_ids = post_manager.filter_unposted_works(work_ids)
        
        if not unposted_ids:
            logger.info("新しい作品はありません")
            return
        
        # 投稿処理
        posted_count = 0
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i, work_id in enumerate(unposted_ids[:max_posts]):
            try:
                # 作品URLの再構築
                work_url = next(url for url in work_urls if work_id in url)
                
                logger.info(f"作品情報を取得中 ({i+1}/{len(unposted_ids[:max_posts])}): {work_url}")
                
                # 作品詳細の取得
                work_data = scraper.scrape_work_detail(work_url)
                
                if not work_data:
                    logger.error(f"作品情報の取得に失敗: {work_url}")
                    continue
                
                # 紹介文のリライト
                logger.info("紹介文をリライト中...")
                rewritten_description = gemini.rewrite_description(
                    title=work_data['title'],
                    original_description=work_data['description']
                )
                
                if not rewritten_description:
                    logger.warning("リライトに失敗したため、元の紹介文を使用します")
                    rewritten_description = work_data['description']
                
                # 記事データの準備
                post_data = article_gen.prepare_post_data(work_data, rewritten_description)
                
                # カテゴリーとタグの処理
                category_id = wp_api.get_or_create_category(post_data['category'])
                tag_ids = []
                for tag in post_data['tags']:
                    tag_id = wp_api.get_or_create_tag(tag)
                    if tag_id:
                        tag_ids.append(tag_id)
                
                # 投稿時刻の計算（15分間隔）
                post_time = tomorrow + timedelta(minutes=15 * posted_count)
                
                # WordPress投稿
                logger.info(f"WordPressに投稿中: {post_data['title']}")
                post_id = wp_api.create_post(
                    title=post_data['title'],
                    content=post_data['content'],
                    categories=[category_id] if category_id else [],
                    tags=tag_ids,
                    status='future',
                    scheduled_date=post_time
                )
                
                if post_id:
                    # 投稿成功
                    post_manager.mark_as_posted(work_data['work_id'])
                    posted_count += 1
                    logger.info(f"投稿完了: {post_data['title']} (予約: {post_time})")
                else:
                    logger.error(f"投稿に失敗: {post_data['title']}")
                
                # 次の処理まで待機
                if i < len(unposted_ids[:max_posts]) - 1:
                    time.sleep(request_delay)
                
            except Exception as e:
                logger.error(f"処理中にエラーが発生: {e}", exc_info=True)
                continue
        
        # 処理結果のサマリー
        logger.info(f"=== 処理完了: {posted_count}件の記事を投稿しました ===")
        logger.info(f"総投稿数: {post_manager.get_posted_count()}件")
        
    except Exception as e:
        logger.error(f"システムエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()