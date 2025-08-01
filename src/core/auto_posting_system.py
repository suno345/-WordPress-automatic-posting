"""
自動投稿システムメインクラス（リファクタリング版）
"""
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .config_manager import ConfigManager
from .dmm_api_refactored import DMMAPIClient
from .gemini_api import GeminiAPI
from .wordpress_api_refactored import WordPressAPI
from .article_generator_refactored import ArticleGenerator
from .post_manager import PostManager
from .constants import Constants, ErrorMessages
from .exceptions import AutoPostingError, ConfigurationError
from .utils import setup_logging


logger = logging.getLogger(__name__)


class AutoPostingSystem:
    """WordPress自動投稿システム（リファクタリング版）"""
    
    def __init__(self, config_file: str = 'config.ini'):
        """
        自動投稿システムの初期化
        
        Args:
            config_file: 設定ファイルのパス
        
        Raises:
            ConfigurationError: 設定に問題がある場合
        """
        try:
            # 設定を読み込み
            self.config = ConfigManager(config_file)
            
            # ログ設定
            self.logger = setup_logging(self.config.system.log_level)
            self.logger.info("=== WordPress自動投稿システム開始 ===")
            self.logger.info(f"設定概要: {self.config.get_config_summary()}")
            
            # 各クライアントを初期化
            self._initialize_clients()
            
            # 投稿管理
            self.post_manager = PostManager()
            
            self.logger.info("システム初期化完了")
            
        except Exception as e:
            logger.error(f"システム初期化エラー: {e}")
            raise ConfigurationError(f"システム初期化に失敗しました: {e}")
    
    def _initialize_clients(self) -> None:
        """各種APIクライアントを初期化"""
        try:
            # DMM APIクライアント
            self.dmm_client = DMMAPIClient(
                api_id=self.config.dmm_api.api_id,
                affiliate_id=self.config.dmm_api.affiliate_id,
                request_delay=self.config.system.request_delay
            )
            
            # Gemini APIクライアント
            self.gemini = GeminiAPI(api_key=self.config.gemini.api_key)
            
            # WordPress APIクライアント
            self.wp_api = WordPressAPI(
                url=self.config.wordpress.url,
                username=self.config.wordpress.username,
                password=self.config.wordpress.password
            )
            
            # 記事生成クライアント
            self.article_gen = ArticleGenerator(wordpress_api=self.wp_api)
            
            self.logger.info("全APIクライアント初期化完了")
            
        except Exception as e:
            raise ConfigurationError(f"APIクライアント初期化エラー: {e}")
    
    def run(self) -> Dict[str, int]:
        """
        メイン実行処理
        
        Returns:
            実行結果の統計情報
        """
        try:
            with self.dmm_client, self.wp_api:
                # 作品データを取得
                works = self._fetch_works()
                
                if not works:
                    self.logger.warning(ErrorMessages.NO_WORKS_FOUND)
                    return {'processed': 0, 'posted': 0, 'total_posted': self.post_manager.get_posted_count()}
                
                # 未投稿作品をフィルタリング
                unposted_works = self._filter_unposted_works(works)
                
                if not unposted_works:
                    self.logger.info(ErrorMessages.NO_NEW_WORKS)
                    return {'processed': 0, 'posted': 0, 'total_posted': self.post_manager.get_posted_count()}
                
                # 投稿処理
                posted_count = self._process_works(unposted_works)
                
                # 結果サマリー
                result = {
                    'processed': len(unposted_works),
                    'posted': posted_count,
                    'total_posted': self.post_manager.get_posted_count()
                }
                
                self.logger.info(f"=== 処理完了: {posted_count}件の記事を投稿しました ===")
                self.logger.info(f"総投稿数: {result['total_posted']}件")
                
                return result
                
        except Exception as e:
            self.logger.error(f"システムエラー: {e}", exc_info=True)
            raise AutoPostingError(f"実行中にエラーが発生しました: {e}")
    
    def _fetch_works(self) -> List[Dict]:
        """作品データを取得"""
        self.logger.info("DMM API から作品リストを取得中...")
        
        api_items = self.dmm_client.get_items(limit=50)
        
        if not api_items:
            return []
        
        # 作品データに変換
        work_list = []
        for item in api_items:
            work_data = self.dmm_client.convert_to_work_data(item)
            if work_data:
                work_list.append(work_data)
        
        self.logger.info(f"{len(work_list)}件の作品データを変換しました")
        return work_list
    
    def _filter_unposted_works(self, works: List[Dict]) -> List[Dict]:
        """未投稿作品のフィルタリング"""
        work_ids = [work['work_id'] for work in works]
        unposted_ids = self.post_manager.filter_unposted_works(work_ids)
        unposted_works = [work for work in works if work['work_id'] in unposted_ids]
        
        self.logger.info(f"{len(unposted_works)}件の未投稿作品を発見")
        return unposted_works
    
    def _process_works(self, unposted_works: List[Dict]) -> int:
        """作品リストを処理して投稿"""
        posted_count = 0
        max_posts = self.config.system.max_posts_per_run
        tomorrow = self._calculate_tomorrow()
        
        # 処理する作品を制限
        works_to_process = unposted_works[:max_posts]
        
        for i, work_data in enumerate(works_to_process):
            try:
                self.logger.info(f"作品を処理中 ({i+1}/{len(works_to_process)}): {work_data['title']}")
                
                if self._process_single_work(work_data, tomorrow, posted_count):
                    posted_count += 1
                
                # 次の処理まで待機（最後以外）
                if i < len(works_to_process) - 1:
                    time.sleep(self.config.system.request_delay)
                    
            except Exception as e:
                self.logger.error(f"作品処理中にエラーが発生: {e}", exc_info=True)
                continue
        
        return posted_count
    
    def _process_single_work(self, work_data: Dict, tomorrow: datetime, posted_count: int) -> bool:
        """
        単一作品の処理
        
        Args:
            work_data: 作品データ
            tomorrow: 明日の基準時刻
            posted_count: 既に投稿済みの件数
        
        Returns:
            投稿成功時True、失敗時False
        """
        try:
            # 紹介文のリライト
            rewritten_description = self._rewrite_description(work_data)
            
            # 記事データの準備
            post_data = self.article_gen.prepare_post_data(work_data, rewritten_description)
            
            # カテゴリーとタグの処理
            category_id = self._get_category_id(post_data['category'])
            tag_ids = self._get_tag_ids(post_data['tags'])
            
            # 投稿時刻の計算
            post_time = tomorrow + timedelta(minutes=self.config.system.post_interval * posted_count)
            
            # WordPress投稿
            post_id = self._create_wordpress_post(post_data, category_id, tag_ids, post_time)
            
            if post_id:
                # 投稿成功
                self.post_manager.mark_as_posted(work_data['work_id'])
                self.logger.info(f"投稿完了: {post_data['title']} (予約: {post_time})")
                return True
            else:
                self.logger.error(f"投稿に失敗: {post_data['title']}")
                return False
                
        except Exception as e:
            self.logger.error(f"作品処理エラー: {e}")
            return False
    
    def _rewrite_description(self, work_data: Dict) -> str:
        """紹介文のリライト"""
        self.logger.info("紹介文をリライト中...")
        
        rewritten_description = self.gemini.rewrite_description(
            title=work_data['title'],
            original_description=work_data['description'],
            target_length=Constants.DEFAULT_TARGET_LENGTH
        )
        
        if not rewritten_description:
            self.logger.warning("リライトに失敗したため、元の紹介文を使用します")
            rewritten_description = work_data['description']
        
        return rewritten_description
    
    def _get_category_id(self, category_name: str) -> Optional[int]:
        """カテゴリーIDを取得"""
        if not category_name:
            return None
        
        return self.wp_api.get_or_create_category(category_name)
    
    def _get_tag_ids(self, tag_names: List[str]) -> List[int]:
        """タグIDリストを取得"""
        tag_ids = []
        
        for tag_name in tag_names:
            tag_id = self.wp_api.get_or_create_tag(tag_name)
            if tag_id:
                tag_ids.append(tag_id)
        
        return tag_ids
    
    def _create_wordpress_post(
        self, 
        post_data: Dict, 
        category_id: Optional[int], 
        tag_ids: List[int], 
        post_time: datetime
    ) -> Optional[int]:
        """WordPress投稿を作成"""
        self.logger.info(f"WordPressに投稿中: {post_data['title']}")
        
        categories = [category_id] if category_id else []
        
        return self.wp_api.create_post(
            title=post_data['title'],
            content=post_data['content'],
            categories=categories,
            tags=tag_ids,
            status='future',
            scheduled_date=post_time
        )
    
    def _calculate_tomorrow(self) -> datetime:
        """明日の00:00を計算"""
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def test_connections(self) -> Dict[str, bool]:
        """
        各種API接続テスト
        
        Returns:
            接続テスト結果
        """
        results = {}
        
        try:
            # WordPress接続テスト
            with self.wp_api:
                results['wordpress'] = self.wp_api.test_connection()
        except Exception as e:
            self.logger.error(f"WordPress接続テストエラー: {e}")
            results['wordpress'] = False
        
        try:
            # DMM API接続テスト（少量のデータで確認）
            with self.dmm_client:
                test_items = self.dmm_client.get_items(limit=1)
                results['dmm_api'] = len(test_items) > 0
        except Exception as e:
            self.logger.error(f"DMM API接続テストエラー: {e}")
            results['dmm_api'] = False
        
        # Gemini API接続テスト（実際のリライトは重いので簡易テスト）
        try:
            results['gemini'] = hasattr(self.gemini, 'model') and self.gemini.model is not None
        except Exception as e:
            self.logger.error(f"Gemini API接続テストエラー: {e}")
            results['gemini'] = False
        
        return results
    
    def get_system_status(self) -> Dict[str, any]:
        """
        システム状態を取得
        
        Returns:
            システム状態情報
        """
        return {
            'config_summary': self.config.get_config_summary(),
            'posted_count': self.post_manager.get_posted_count(),
            'connection_tests': self.test_connections(),
            'h2_patterns_count': len(self.article_gen.h2_manager._patterns)
        }