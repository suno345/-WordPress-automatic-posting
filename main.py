#!/usr/bin/env python3
import configparser
import logging
import os
import sys
from datetime import datetime, timedelta
import time

from modules.dmm_api import DMMAPIClient
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
        
        try:
            dmm_api_id = config.get('dmm_api', 'api_id')
            if dmm_api_id == 'your_dmm_api_id':
                logger.error("DMM API ID が設定されていません。config.ini を確認してください。")
                logger.error("DMM アフィリエイト（https://affiliate.dmm.com/)でAPI IDを取得してください。")
                return
        except Exception as e:
            logger.error(f"DMM API 設定の読み込みに失敗: {e}")
            return
            
        dmm_affiliate_id = config.get('dmm_api', 'affiliate_id', fallback='')
        
        gemini_api_key = config.get('gemini', 'api_key')
        
        max_posts = config.getint('settings', 'max_posts_per_run', fallback=1)
        request_delay = config.getint('settings', 'request_delay', fallback=2)
        
        # 各モジュールの初期化
        logger.info("モジュールを初期化中...")
        
        dmm_client = DMMAPIClient(
            api_id=dmm_api_id,
            affiliate_id=dmm_affiliate_id,
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
        
        # DMM API から作品リストを取得
        logger.info("DMM API から作品リストを取得中...")
        api_items = dmm_client.get_items(limit=50)  # 50件取得
        
        if not api_items:
            logger.warning("作品が見つかりませんでした")
            return
        
        # 作品データに変換
        work_list = []
        for item in api_items:
            work_data = dmm_client.convert_to_work_data(item)
            if work_data:
                work_list.append(work_data)
        
        # 未投稿作品のフィルタリング
        work_ids = [work['work_id'] for work in work_list]
        unposted_ids = post_manager.filter_unposted_works(work_ids)
        unposted_works = [work for work in work_list if work['work_id'] in unposted_ids]
        
        if not unposted_works:
            logger.info("新しい作品はありません")
            return
        
        # 投稿処理
        posted_count = 0
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i, work_data in enumerate(unposted_works[:max_posts]):
            try:
                logger.info(f"作品を処理中 ({i+1}/{len(unposted_works[:max_posts])}): {work_data['title']}")
                
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
                if i < len(unposted_works[:max_posts]) - 1:
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