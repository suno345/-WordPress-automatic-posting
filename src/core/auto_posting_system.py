"""
自動投稿システムメインクラス（リファクタリング版）
"""
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..config.config_manager import ConfigManager
from ..api.dmm_api import DMMAPIClient
from ..api.gemini_api import GeminiAPI
from ..api.wordpress_api import WordPressAPI
from .article_generator import ArticleGenerator
from .post_manager import PostManager
from ..utils.constants import Constants, ErrorMessages
from ..services.exceptions import AutoPostingError, ConfigurationError
from ..utils.utils import setup_logging


logger = logging.getLogger(__name__)


class AutoPostingSystem:
    """WordPress自動投稿システム（リファクタリング版）"""
    
    def __init__(self, config_file: str = 'config/config.ini', verbose: bool = False, skip_review_check: bool = False):
        """
        自動投稿システムの初期化
        
        Args:
            config_file: 設定ファイルのパス
            verbose: 詳細ログを出力するか
            skip_review_check: レビューチェックをスキップするか（テスト用）
        
        Raises:
            ConfigurationError: 設定に問題がある場合
        """
        self.verbose = verbose
        self.skip_review_check = skip_review_check
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
            
            # 改善：ジャンル情報キャッシュを初期化（GenreSearch API活用）
            self.dmm_client.initialize_genre_cache()
            
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
        """作品データを取得（必要に応じて追加検索を実行）"""
        self.logger.info("DMM API から作品リストを取得中...")
        
        # 初回検索
        work_list = self._search_and_convert_works(limit=self.config.system.search_limit, offset=1)
        
        # 必要投稿数に対してコミック作品が不足している場合は追加検索
        required_works = self.config.system.max_posts_per_run
        if len(work_list) < required_works:
            self.logger.warning(f"初回検索でコミック作品が不足: {len(work_list)}/{required_works}件")
            work_list.extend(self._perform_additional_searches(work_list, required_works))
        
        self.logger.info(f"最終的に{len(work_list)}件のコミック作品を取得しました")
        return work_list
    
    def _search_and_convert_works(self, limit: int, offset: int) -> List[Dict]:
        """指定した範囲でAPIを呼び出してコミック作品に変換"""
        api_items = self.dmm_client.get_items(limit=limit, offset=offset)
        
        if not api_items:
            return []
        
        # 作品データに変換（コミック作品のみ）
        work_list = []
        for item in api_items:
            work_data = self.dmm_client.convert_to_work_data(item, skip_review_check=self.skip_review_check)
            if work_data:
                work_list.append(work_data)
        
        self.logger.info(f"検索範囲{offset}-{offset+limit-1}: {len(work_list)}件のコミック作品を発見")
        return work_list
    
    def _perform_additional_searches(self, existing_works: List[Dict], required_count: int) -> List[Dict]:
        """追加検索を実行してコミック作品を補充"""
        additional_works = []
        current_offset = self.config.system.search_limit + 1
        batch_size = Constants.ADDITIONAL_SEARCH_BATCH_SIZE
        max_searches = Constants.MAX_ADDITIONAL_SEARCHES
        
        existing_work_ids = {work['work_id'] for work in existing_works}
        
        for search_round in range(max_searches):
            if len(existing_works) + len(additional_works) >= required_count:
                break
                
            self.logger.info(f"追加検索 {search_round + 1}/{max_searches} を実行中...")
            
            # 追加検索実行
            new_works = self._search_and_convert_works(limit=batch_size, offset=current_offset)
            
            # 重複除去
            for work in new_works:
                if work['work_id'] not in existing_work_ids:
                    additional_works.append(work)
                    existing_work_ids.add(work['work_id'])
                    
                    if len(existing_works) + len(additional_works) >= required_count:
                        break
            
            current_offset += batch_size
            
            # API制限を考慮した待機
            if search_round < max_searches - 1:
                time.sleep(self.config.system.request_delay)
        
        if additional_works:
            self.logger.info(f"追加検索で{len(additional_works)}件のコミック作品を追加取得")
        else:
            self.logger.warning("追加検索でもコミック作品が見つかりませんでした")
            
        return additional_works
    
    def _filter_unposted_works(self, works: List[Dict]) -> List[Dict]:
        """未投稿作品のフィルタリング"""
        work_ids = [work['work_id'] for work in works]
        unposted_ids = self.post_manager.filter_unposted_works(work_ids)
        unposted_works = [work for work in works if work['work_id'] in unposted_ids]
        
        self.logger.info(f"{len(unposted_works)}件の未投稿作品を発見")
        return unposted_works
    
    def _process_works(self, unposted_works: List[Dict]) -> int:
        """作品リストを処理して投稿（前倒し投稿対応）"""
        # 既存の投稿済み件数を取得（重要な修正）
        total_posted_count = self.post_manager.get_posted_count()
        self.logger.info(f"既存投稿済み件数: {total_posted_count}件")
        
        session_posted_count = 0  # このセッションでの投稿件数
        max_posts = self.config.system.max_posts_per_run
        
        # 処理する作品を制限
        works_to_process = unposted_works[:max_posts]
        
        # 複数作品が見つかった場合は前倒し投稿を実行
        if len(works_to_process) > 1:
            self.logger.info(f"複数作品発見（{len(works_to_process)}件）- 前倒し投稿を実行します")
            return self._process_works_immediate_schedule(works_to_process)
        else:
            # 単一作品の場合は従来の処理
            return self._process_works_regular_schedule(works_to_process, total_posted_count)

    def _process_works_immediate_schedule(self, works: List[Dict]) -> int:
        """即時前倒し投稿処理"""
        try:
            # 記事生成処理
            articles = []
            for work_data in works:
                try:
                    # 紹介文のリライト
                    rewritten_description = self._rewrite_description(work_data)
                    
                    # 記事データの準備
                    article_data = {
                        "work_data": work_data,
                        "rewritten_description": rewritten_description,
                        "article_content": self.article_gen.generate_complete_article(work_data, rewritten_description)
                    }
                    articles.append(article_data)
                    
                    self.logger.info(f"記事生成完了: {work_data['title']}")
                    
                except Exception as e:
                    self.logger.error(f"記事生成エラー: {work_data['title']} - {e}")
                    continue
            
            if not articles:
                self.logger.warning("記事生成に失敗したため投稿をスキップします")
                return 0
            
            # 前倒し投稿スケジュールを作成
            from .post_schedule_manager import PostScheduleManager
            schedule_manager = PostScheduleManager(self.config)
            
            schedule_info = schedule_manager.create_immediate_schedule(
                articles=articles,
                start_delay_minutes=2  # 2分後から開始
            )
            
            self.logger.info(f"前倒し投稿スケジュール作成: {len(articles)}件")
            self.logger.info(f"投稿予定時刻: {schedule_info['start_time']}から15分間隔")
            
            # 投稿済みとして記録
            for article in articles:
                self.post_manager.mark_as_posted(article["work_data"]["work_id"])
            
            return len(articles)
            
        except Exception as e:
            self.logger.error(f"前倒し投稿処理エラー: {e}")
            return 0

    def _process_works_regular_schedule(self, works: List[Dict], total_posted_count: int) -> int:
        """通常の投稿スケジュール処理"""
        session_posted_count = 0
        tomorrow = self._calculate_tomorrow()
        
        for i, work_data in enumerate(works):
            try:
                self.logger.info(f"作品を処理中 ({i+1}/{len(works)}): {work_data['title']}")
                
                # 全体の投稿済み件数を基準に時刻計算
                current_posted_count = total_posted_count + session_posted_count
                
                if self._process_single_work(work_data, tomorrow, current_posted_count):
                    session_posted_count += 1
                
                # 次の処理まで待機（最後以外）
                if i < len(works) - 1:
                    time.sleep(self.config.system.request_delay)
                    
            except Exception as e:
                self.logger.error(f"作品処理中にエラーが発生: {e}", exc_info=True)
                continue
        
        return session_posted_count
    
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
            category_ids = self._get_category_ids(post_data['category'])
            tag_ids = self._get_tag_ids(post_data['tags'])
            
            # 投稿時刻の計算
            post_time = tomorrow + timedelta(minutes=self.config.system.post_interval * posted_count)
            
            # WordPress投稿
            post_id = self._create_wordpress_post(post_data, category_ids, tag_ids, post_time)
            
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
    
    def _get_category_ids(self, category_names) -> List[int]:
        """複数カテゴリーIDを取得"""
        category_ids = []
        
        if not category_names:
            return []
        
        # リストでない場合はリスト化
        if not isinstance(category_names, list):
            category_names = [category_names]
        
        for category_name in category_names:
            # 文字列でない場合は文字列化
            if not isinstance(category_name, str):
                category_name = str(category_name)
            
            # 空文字列や不正な値をスキップ
            if category_name and category_name.strip():
                category_id = self.wp_api.get_or_create_category(category_name.strip())
                if category_id:
                    category_ids.append(category_id)
        
        return category_ids
    
    def _get_tag_ids(self, tag_names) -> List[int]:
        """タグIDリストを取得"""
        tag_ids = []
        
        # リストでない場合はリスト化
        if not isinstance(tag_names, list):
            if tag_names:
                tag_names = [tag_names]
            else:
                return []
        
        for tag_name in tag_names:
            # 文字列でない場合は文字列化
            if not isinstance(tag_name, str):
                tag_name = str(tag_name)
            
            # 空文字列や不正な値をスキップ
            if tag_name and tag_name.strip():
                tag_id = self.wp_api.get_or_create_tag(tag_name.strip())
                if tag_id:
                    tag_ids.append(tag_id)
        
        return tag_ids
    
    def _create_wordpress_post(
        self, 
        post_data: Dict, 
        category_ids: List[int], 
        tag_ids: List[int], 
        post_time: datetime
    ) -> Optional[int]:
        """WordPress投稿を作成"""
        self.logger.info(f"WordPressに投稿中: {post_data['title']}")
        
        categories = category_ids if category_ids else []
        
        # 商品IDをスラッグとして使用
        slug = post_data.get('work_id', None)
        
        return self.wp_api.create_post(
            title=post_data['title'],
            content=post_data['content'],
            categories=categories,
            tags=tag_ids,
            status='future',
            scheduled_date=post_time,
            slug=slug
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
    
    def display_status(self) -> None:
        """システム状態を表示"""
        try:
            print("=== WordPress自動投稿システム状態 ===")
            
            # 設定概要
            config_summary = self.config.get_config_summary()
            print(f"\n📊 設定情報:")
            print(f"  WordPress URL: {config_summary['wordpress']['url']}")
            print(f"  ユーザー名: {config_summary['wordpress']['username']}")
            print(f"  DMM API設定: {'✅' if config_summary['dmm_api']['configured'] else '❌'}")
            print(f"  Gemini API設定: {'✅' if config_summary['gemini']['api_key_configured'] else '❌'}")
            print(f"  最大投稿数: {config_summary['system']['max_posts_per_run']}")
            
            # 投稿統計
            posted_count = self.post_manager.get_posted_count()
            print(f"\n📈 投稿統計:")
            print(f"  総投稿数: {posted_count}件")
            
            # H2パターン
            h2_count = len(self.article_gen.h2_manager._patterns)
            print(f"  H2パターン数: {h2_count}件")
            
            # 接続テスト
            print(f"\n🔗 接続テスト:")
            connection_tests = self.test_connections()
            for service, status in connection_tests.items():
                status_icon = "✅" if status else "❌"
                print(f"  {service}: {status_icon}")
            
            # 全体ステータス
            all_connected = all(connection_tests.values())
            overall_status = "✅ 正常" if all_connected else "⚠️  一部問題あり"
            print(f"\n🎯 総合状態: {overall_status}")
            
        except Exception as e:
            print(f"❌ 状態表示エラー: {e}")
            self.logger.error(f"Status display error: {e}", exc_info=True)