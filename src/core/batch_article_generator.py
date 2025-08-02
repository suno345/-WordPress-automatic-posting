"""
バッチ記事生成システム - 1回の検索で96件分の記事を効率的に生成
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

from .article_generator import ArticleGenerator
from .post_schedule_manager import PostScheduleManager
from ..api.dmm_api import DMMAPIClient
from ..api.gemini_api import GeminiAPI
from ..services.exceptions import AutoPostingError

logger = logging.getLogger(__name__)


class BatchArticleGenerator:
    """バッチ記事生成システム"""
    
    def __init__(self, dmm_client: DMMAPIClient, gemini_api: GeminiAPI, config, post_manager=None):
        """
        バッチ記事生成システムの初期化
        
        Args:
            dmm_client: DMM APIクライアント
            gemini_api: Gemini APIクライアント
            config: システム設定
            post_manager: 投稿管理システム
        """
        self.dmm_client = dmm_client
        self.gemini_api = gemini_api
        self.config = config
        self.post_manager = post_manager
        
        # 記事生成器
        self.article_generator = ArticleGenerator(
            gemini_api=self.gemini_api,
            config=self.config
        )
        
        # 予約管理システム
        self.schedule_manager = PostScheduleManager(config)
        
        # バッチ生成設定
        self.target_daily_count = 96  # 1日の目標記事数
        self.max_search_range = 3000  # 最大検索範囲
        self.parallel_workers = 4     # 並列処理ワーカー数
        
        logger.info("バッチ記事生成システム初期化完了")
    
    def generate_daily_batch(self, target_date: Optional[datetime] = None) -> Dict:
        """
        1日分の記事を一括生成し、15分間隔で予約設定
        
        Args:
            target_date: 対象日付（Noneの場合は翌日）
            
        Returns:
            生成結果の詳細
        """
        if target_date is None:
            target_date = datetime.now() + timedelta(days=1)
        
        logger.info(f"バッチ記事生成開始 - 対象日: {target_date.strftime('%Y-%m-%d')}, 目標: {self.target_daily_count}件")
        
        result = {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "target_count": self.target_daily_count,
            "started_at": datetime.now().isoformat(),
            "works_fetched": 0,
            "articles_generated": 0,
            "articles_scheduled": 0,
            "errors": [],
            "performance": {}
        }
        
        try:
            # Phase 1: 大量作品取得
            start_time = datetime.now()
            works_pool = self._fetch_bulk_works(self.target_daily_count * 3)  # 3倍の候補を確保
            result["works_fetched"] = len(works_pool)
            result["performance"]["works_fetch_time"] = (datetime.now() - start_time).total_seconds()
            
            if not works_pool:
                raise AutoPostingError("作品候補が取得できませんでした")
            
            # Phase 2: 投稿済み作品の除外
            start_time = datetime.now()
            unposted_works = self._filter_unposted_works(works_pool)
            result["performance"]["filtering_time"] = (datetime.now() - start_time).total_seconds()
            
            if len(unposted_works) < self.target_daily_count * 0.5:  # 目標の50%未満なら警告
                logger.warning(f"未投稿作品が不足: {len(unposted_works)}件 (目標: {self.target_daily_count}件)")
            
            # Phase 3: 並列記事生成
            start_time = datetime.now()
            generated_articles = self._generate_articles_parallel(
                unposted_works[:self.target_daily_count]
            )
            result["articles_generated"] = len(generated_articles)
            result["performance"]["generation_time"] = (datetime.now() - start_time).total_seconds()
            
            # Phase 4: 15分間隔予約設定
            if generated_articles:
                start_time = datetime.now()
                schedule_info = self._create_posting_schedule(generated_articles, target_date)
                result["articles_scheduled"] = len(schedule_info["schedule_ids"])
                result["performance"]["scheduling_time"] = (datetime.now() - start_time).total_seconds()
                result["schedule_info"] = schedule_info
            
            # Phase 5: 結果サマリー
            result["completed_at"] = datetime.now().isoformat()
            result["total_time"] = sum(result["performance"].values())
            result["success_rate"] = (result["articles_generated"] / result["target_count"]) * 100
            
            logger.info(f"バッチ記事生成完了: {result['articles_generated']}/{result['target_count']}件 "
                       f"(成功率: {result['success_rate']:.1f}%, 総時間: {result['total_time']:.1f}秒)")
            
        except Exception as e:
            result["error"] = str(e)
            result["completed_at"] = datetime.now().isoformat()
            logger.error(f"バッチ記事生成中にエラー: {e}")
        
        return result
    
    def _fetch_bulk_works(self, target_count: int) -> List[Dict]:
        """
        大量の作品データを効率的に取得
        
        Args:
            target_count: 目標取得数
            
        Returns:
            作品データのリスト
        """
        logger.info(f"大量作品取得開始 - 目標: {target_count}件")
        
        # 戦略的検索パターン（時間帯別に最適化）
        current_hour = datetime.now().hour
        
        if 2 <= current_hour <= 6:  # 深夜バッチ時間
            search_strategies = [
                {"offset": 1, "limit": 400, "desc": "最新400件"},
                {"offset": 401, "limit": 600, "desc": "準新作600件"},
                {"offset": 1001, "limit": 800, "desc": "中堅800件"},
                {"offset": 1801, "limit": 1200, "desc": "過去1200件"},
            ]
        else:  # 緊急時間
            search_strategies = [
                {"offset": 1, "limit": 200, "desc": "最新200件"},
                {"offset": 201, "limit": 300, "desc": "準新作300件"},
                {"offset": 501, "limit": 500, "desc": "中堅500件"},
            ]
        
        all_works = []
        total_api_calls = 0
        
        for strategy in search_strategies:
            if len(all_works) >= target_count:
                break
            
            try:
                logger.info(f"検索実行: {strategy['desc']} (オフセット: {strategy['offset']})")
                
                api_items = self.dmm_client.get_items(
                    limit=strategy["limit"], 
                    offset=strategy["offset"],
                    use_genre_filter=True  # ジャンルフィルター使用
                )
                total_api_calls += 1
                
                # 作品データに変換
                batch_works = []
                for item in api_items:
                    work_data = self.dmm_client.convert_to_work_data(
                        item, 
                        skip_review_check=False  # バッチ生成時はレビューチェック実行
                    )
                    if work_data:
                        batch_works.append(work_data)
                
                all_works.extend(batch_works)
                logger.info(f"検索結果: {len(batch_works)}件のコミック作品を取得 (累計: {len(all_works)}件)")
                
            except Exception as e:
                logger.error(f"検索エラー ({strategy['desc']}): {e}")
                continue
        
        # 重複除去（work_idベース）
        unique_works = []
        seen_work_ids = set()
        for work in all_works:
            if work["work_id"] not in seen_work_ids:
                unique_works.append(work)
                seen_work_ids.add(work["work_id"])
        
        logger.info(f"大量作品取得完了: {len(unique_works)}件 (API呼び出し: {total_api_calls}回)")
        return unique_works
    
    def _filter_unposted_works(self, works: List[Dict]) -> List[Dict]:
        """投稿済み作品を除外"""
        if not self.post_manager:
            return works
        
        unposted_works = []
        for work in works:
            if not self.post_manager.is_posted(work["work_id"]):
                unposted_works.append(work)
        
        logger.info(f"未投稿作品フィルタリング: {len(unposted_works)}/{len(works)}件")
        return unposted_works
    
    def _generate_articles_parallel(self, works: List[Dict]) -> List[Dict]:
        """
        並列処理で記事を生成
        
        Args:
            works: 作品データリスト
            
        Returns:
            生成された記事データリスト
        """
        logger.info(f"並列記事生成開始: {len(works)}件 (ワーカー: {self.parallel_workers})")
        
        generated_articles = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
            # 記事生成タスクを投入
            future_to_work = {
                executor.submit(self._generate_single_article, work): work 
                for work in works
            }
            
            # 結果を収集
            for future in as_completed(future_to_work):
                work = future_to_work[future]
                try:
                    result = future.result()
                    if result:
                        generated_articles.append(result)
                        logger.debug(f"記事生成完了: {work['title']}")
                    else:
                        errors.append(f"記事生成失敗: {work['title']}")
                        
                except Exception as e:
                    error_msg = f"記事生成エラー: {work['title']}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        if errors:
            logger.warning(f"記事生成で{len(errors)}件のエラーが発生")
        
        logger.info(f"並列記事生成完了: {len(generated_articles)}件成功, {len(errors)}件失敗")
        return generated_articles
    
    def _generate_single_article(self, work_data: Dict) -> Optional[Dict]:
        """
        単一記事の生成
        
        Args:
            work_data: 作品データ
            
        Returns:
            生成された記事データまたはNone
        """
        try:
            article_content = self.article_generator.generate_article(work_data)
            
            if article_content:
                return {
                    "work_data": work_data,
                    "article_content": article_content,
                    "generated_at": datetime.now().isoformat(),
                    "generation_source": "batch"
                }
            
        except Exception as e:
            logger.error(f"単一記事生成エラー ({work_data['title']}): {e}")
        
        return None
    
    def _create_posting_schedule(self, articles: List[Dict], target_date: datetime) -> Dict:
        """
        記事の投稿スケジュールを作成
        
        Args:
            articles: 記事データリスト
            target_date: 投稿開始日
            
        Returns:
            スケジュール情報
        """
        logger.info(f"投稿スケジュール作成開始: {len(articles)}件")
        
        # 投稿開始時刻を設定（対象日の00:00）
        start_datetime = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # スケジュール作成
        schedule_info = self.schedule_manager.create_daily_schedule(
            articles=articles,
            start_date=start_datetime
        )
        
        logger.info(f"投稿スケジュール作成完了: {len(schedule_info['schedule_ids'])}件予約")
        
        return schedule_info
    
    def get_generation_statistics(self, days: int = 7) -> Dict:
        """
        バッチ生成の統計情報を取得
        
        Args:
            days: 統計対象日数
            
        Returns:
            統計情報
        """
        # スケジュール管理システムから統計を取得
        schedule_status = self.schedule_manager.get_schedule_status()
        
        return {
            "current_schedule": schedule_status,
            "system_status": "operational",
            "last_batch_generation": self._get_last_batch_info(),
            "recommendations": self._get_optimization_recommendations()
        }
    
    def _get_last_batch_info(self) -> Dict:
        """最後のバッチ生成情報を取得"""
        # 実装は実際のログファイルまたはメタデータから取得
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "articles_generated": 0,
            "success_rate": 0.0,
            "total_time": 0.0
        }
    
    def _get_optimization_recommendations(self) -> List[str]:
        """最適化の推奨事項を取得"""
        recommendations = []
        
        # スケジュール状況に基づく推奨事項
        schedule_status = self.schedule_manager.get_schedule_status()
        
        if schedule_status["total_scheduled"] < 48:  # 48件未満（2日分未満）
            recommendations.append("記事ストックが不足しています。追加のバッチ生成を推奨します。")
        
        if schedule_status["status_breakdown"]["overdue"] > 5:
            recommendations.append("遅延投稿が蓄積しています。システムの確認が必要です。")
        
        if schedule_status["failed_today"] > 3:
            recommendations.append("本日の失敗投稿が多いです。API設定の確認を推奨します。")
        
        return recommendations
    
    def emergency_generation(self, count: int = 24) -> Dict:
        """
        緊急時の記事生成（少数を迅速に生成）
        
        Args:
            count: 生成する記事数
            
        Returns:
            生成結果
        """
        logger.warning(f"緊急記事生成開始: {count}件")
        
        try:
            # 最新作品から迅速に取得
            api_items = self.dmm_client.get_items(limit=count * 2, offset=1)
            
            works = []
            for item in api_items:
                work_data = self.dmm_client.convert_to_work_data(item, skip_review_check=True)
                if work_data and (not self.post_manager or not self.post_manager.is_posted(work_data["work_id"])):
                    works.append(work_data)
                    if len(works) >= count:
                        break
            
            # 記事生成（単一スレッド、高速処理）
            articles = []
            for work in works:
                try:
                    article_content = self.article_generator.generate_article(work)
                    if article_content:
                        articles.append({
                            "work_data": work,
                            "article_content": article_content,
                            "generated_at": datetime.now().isoformat(),
                            "generation_source": "emergency"
                        })
                except Exception as e:
                    logger.error(f"緊急生成エラー: {work['title']}: {e}")
                    continue
            
            # 即座にスケジュール設定
            if articles:
                schedule_info = self._create_posting_schedule(articles, datetime.now())
                logger.info(f"緊急記事生成完了: {len(articles)}件生成, {len(schedule_info['schedule_ids'])}件予約")
                
                return {
                    "success": True,
                    "generated_count": len(articles),
                    "scheduled_count": len(schedule_info["schedule_ids"]),
                    "schedule_info": schedule_info
                }
            
        except Exception as e:
            logger.error(f"緊急生成中にエラー: {e}")
        
        return {"success": False, "generated_count": 0, "scheduled_count": 0}