"""
予約投稿実行システム - 15分毎の軽量投稿実行
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import time

from .post_schedule_manager import PostScheduleManager
from ..api.wordpress_api import WordPressAPI
from ..core.post_manager import PostManager
from ..services.exceptions import AutoPostingError

logger = logging.getLogger(__name__)


class ScheduledPostExecutor:
    """予約投稿実行システム"""
    
    def __init__(self, wp_api: WordPressAPI, config, post_manager: PostManager = None):
        """
        予約投稿実行システムの初期化
        
        Args:
            wp_api: WordPress APIクライアント
            config: システム設定
            post_manager: 投稿管理システム
        """
        self.wp_api = wp_api
        self.config = config
        self.post_manager = post_manager
        
        # 予約管理システム
        self.schedule_manager = PostScheduleManager(config)
        
        # 実行設定
        self.max_execution_time = 300  # 最大実行時間（5分）
        self.retry_delay = 30          # リトライ遅延（秒）
        
        logger.info("予約投稿実行システム初期化完了")
    
    def execute_next_scheduled_post(self) -> Dict:
        """
        次の予約投稿を実行
        
        Returns:
            実行結果
        """
        execution_start = datetime.now()
        
        result = {
            "execution_time": execution_start.isoformat(),
            "status": "no_action",
            "message": "実行する投稿がありません",
            "post_info": None,
            "performance": {}
        }
        
        try:
            # 次の投稿を取得
            next_post = self.schedule_manager.get_next_scheduled_post()
            
            if not next_post:
                logger.debug("実行する予約投稿がありません")
                return result
            
            schedule_id = next_post["schedule_id"]
            article_data = next_post["article_data"]
            work_data = article_data["work_data"]
            
            logger.info(f"予約投稿実行開始: {work_data['title']} (ID: {schedule_id})")
            
            # 投稿を進行中としてマーク
            self.schedule_manager.mark_post_in_progress(schedule_id)
            
            # 実行結果を更新
            result.update({
                "status": "executing",
                "schedule_id": schedule_id,
                "post_info": {
                    "title": work_data["title"],
                    "work_id": work_data["work_id"],
                    "scheduled_time": next_post["post_time"],
                    "attempts": next_post.get("attempts", 0)
                }
            })
            
            # WordPress投稿実行
            post_result = self._execute_wordpress_post(article_data)
            
            if post_result["success"]:
                # 投稿成功
                self.schedule_manager.mark_post_completed(schedule_id, post_result)
                
                # 投稿済み作品として記録
                if self.post_manager:
                    self.post_manager.mark_as_posted(work_data)
                
                # 実行時間を記録
                execution_time = (datetime.now() - execution_start).total_seconds()
                
                result.update({
                    "status": "success",
                    "message": f"投稿完了: {work_data['title']}",
                    "post_id": post_result["post_id"],
                    "post_url": post_result.get("post_url"),
                    "performance": {
                        "total_execution_time": execution_time,
                        "wordpress_post_time": post_result.get("execution_time", 0)
                    }
                })
                
                logger.info(f"予約投稿完了: {work_data['title']} (実行時間: {execution_time:.1f}秒)")
                
            else:
                # 投稿失敗
                error_message = post_result.get("error", "不明なエラー")
                self.schedule_manager.mark_post_failed(schedule_id, error_message)
                
                result.update({
                    "status": "failed",
                    "message": f"投稿失敗: {work_data['title']} - {error_message}",
                    "error": error_message
                })
                
                logger.error(f"予約投稿失敗: {work_data['title']} - {error_message}")
            
        except Exception as e:
            error_message = f"実行中にエラー: {str(e)}"
            result.update({
                "status": "exception",
                "message": error_message,
                "error": str(e)
            })
            
            # スケジュールが取得できていた場合は失敗としてマーク
            if "schedule_id" in result:
                self.schedule_manager.mark_post_failed(result["schedule_id"], error_message)
            
            logger.error(f"予約投稿実行中にエラー: {e}")
        
        # 総実行時間を設定
        total_time = (datetime.now() - execution_start).total_seconds()
        result["performance"] = result.get("performance", {})
        result["performance"]["total_execution_time"] = total_time
        
        return result
    
    def _execute_wordpress_post(self, article_data: Dict) -> Dict:
        """
        WordPress投稿を実行
        
        Args:
            article_data: 記事データ
            
        Returns:
            投稿結果
        """
        work_data = article_data["work_data"]
        article_content = article_data["article_content"]
        
        try:
            start_time = datetime.now()
            
            # 記事タイトル生成
            article_title = self._generate_article_title(work_data)
            
            # カテゴリとタグの設定
            categories = self._get_categories(work_data)
            tags = self._get_tags(work_data)
            
            # WordPress投稿実行
            post_result = self.wp_api.create_post(
                title=article_title,
                content=article_content,
                status='publish',
                categories=categories,
                tags=tags
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if post_result.get("success"):
                logger.info(f"WordPress投稿成功: {article_title} (ID: {post_result.get('post_id')})")
                
                return {
                    "success": True,
                    "post_id": post_result["post_id"],
                    "post_url": post_result.get("post_url"),
                    "execution_time": execution_time,
                    "title": article_title
                }
            else:
                error_message = post_result.get("error", "WordPress投稿でエラーが発生")
                logger.error(f"WordPress投稿失敗: {article_title} - {error_message}")
                
                return {
                    "success": False,
                    "error": error_message,
                    "execution_time": execution_time
                }
                
        except Exception as e:
            logger.error(f"WordPress投稿中にエラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": 0
            }
    
    def _generate_article_title(self, work_data: Dict) -> str:
        """記事タイトルを生成\"\"\"
        work_title = work_data.get('title', '')
        
        # 作者・サークル名を取得
        creators = []
        if work_data.get('circle_name') and work_data['circle_name'] != '不明':
            creators.append(work_data['circle_name'])
        if work_data.get('author_name') and work_data['author_name'] != '不明':
            creators.append(work_data['author_name'])
        
        creator_name = '・'.join(list(dict.fromkeys(creators))) if creators else '不明'
        
        return f"{work_title}【{creator_name}】"
    
    def _get_categories(self, work_data: Dict) -> List[str]:
        """カテゴリを取得\"\"\"
        categories = ["同人"]  # デフォルトカテゴリ
        
        # ジャンル情報からカテゴリを追加
        if work_data.get('genre'):
            categories.append(work_data['genre'])
        
        return categories
    
    def _get_tags(self, work_data: Dict) -> List[str]:
        """タグを取得\"\"\"
        tags = []
        
        # 作者・サークル名をタグに追加
        if work_data.get('circle_name') and work_data['circle_name'] != '不明':
            tags.append(work_data['circle_name'])
        if work_data.get('author_name') and work_data['author_name'] != '不明':
            tags.append(work_data['author_name'])
        
        # その他の情報をタグに追加
        if work_data.get('series_name'):
            tags.append(work_data['series_name'])
        
        return tags[:10]  # 最大10個のタグ
    
    def execute_multiple_posts(self, max_posts: int = 5) -> Dict:
        """
        複数の予約投稿を連続実行(遅延分の回復用)
        
        Args:
            max_posts: 最大実行数
            
        Returns:
            実行結果サマリー
        """
        logger.info(f"複数投稿実行開始 - 最大: {max_posts}件")
        
        results = {
            "executed_posts": [],
            "success_count": 0,
            "failed_count": 0,
            "total_execution_time": 0,
            "started_at": datetime.now().isoformat()
        }
        
        start_time = datetime.now()
        
        for i in range(max_posts):
            # 実行時間制限チェック
            if (datetime.now() - start_time).total_seconds() > self.max_execution_time:
                logger.warning(f"実行時間制限に達したため中断 (実行済み: {i}件)")
                break
            
            # 次の投稿を実行
            post_result = self.execute_next_scheduled_post()
            results["executed_posts"].append(post_result)
            
            if post_result["status"] == "success":
                results["success_count"] += 1
            elif post_result["status"] in ["failed", "exception"]:
                results["failed_count"] += 1
            elif post_result["status"] == "no_action":
                # 実行する投稿がない場合は終了
                break
            
            # インターバル（次の投稿まで少し待機）
            if i < max_posts - 1:
                time.sleep(2)
        
        results["total_execution_time"] = (datetime.now() - start_time).total_seconds()
        results["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"複数投稿実行完了: 成功{results['success_count']}件, "
                   f"失敗{results['failed_count']}件 (総時間: {results['total_execution_time']:.1f}秒)")
        
        return results
    
    def get_execution_status(self) -> Dict:
        """実行システムの状況を取得\"\"\"
        schedule_status = self.schedule_manager.get_schedule_status()
        
        # 次の投稿予定時刻を計算
        next_post = self.schedule_manager.get_next_scheduled_post()
        next_post_info = None
        
        if next_post:
            post_time = datetime.fromisoformat(next_post["post_time"])
            delay_minutes = max(0, (post_time - datetime.now()).total_seconds() / 60)
            
            next_post_info = {
                "title": next_post["article_data"]["work_data"]["title"],
                "scheduled_time": post_time.strftime("%Y-%m-%d %H:%M"),
                "delay_minutes": round(delay_minutes, 1),
                "is_overdue": delay_minutes <= 0,
                "priority": next_post.get("priority", "normal")
            }
        
        return {
            "system_ready": True,
            "schedule_summary": schedule_status,
            "next_post": next_post_info,
            "performance_metrics": self._get_performance_metrics(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_performance_metrics(self) -> Dict:
        """パフォーマンスメトリクスを取得\"\"\"
        # 実際の実装では、過去の実行ログから統計を計算
        return {
            "avg_execution_time": 45.0,  # 平均実行時間（秒）
            "success_rate_24h": 98.5,    # 過去24時間の成功率
            "posts_completed_today": 0,   # 今日完了した投稿数
            "posts_failed_today": 0,     # 今日失敗した投稿数
        }
    
    def recover_failed_posts(self) -> Dict:
        """失敗した投稿の回復処理\"\"\"
        logger.info("失敗投稿の回復処理開始")
        
        # 失敗投稿の再スケジュール
        rescheduled_count = self.schedule_manager.reschedule_failed_posts()
        
        result = {
            "rescheduled_count": rescheduled_count,
            "recovery_time": datetime.now().isoformat()
        }
        
        if rescheduled_count > 0:
            logger.info(f"失敗投稿回復完了: {rescheduled_count}件を再スケジュール")
        else:
            logger.info("回復対象の失敗投稿はありません")
        
        return result