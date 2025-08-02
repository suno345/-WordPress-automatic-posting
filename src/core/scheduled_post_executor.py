"""
予約投稿実行システム - 15分毎の軽量投稿実行
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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
                try:
                    self.schedule_manager.mark_post_completed(schedule_id, post_result)
                except Exception as e:
                    logger.error(f"mark_post_completed でエラー: {e}")
                    logger.error(f"schedule_id: {schedule_id}")
                    logger.error(f"post_result: {post_result}")
                    import traceback
                    logger.error(f"スタックトレース: {traceback.format_exc()}")
                    raise
                
                # 投稿済み作品として記録
                if self.post_manager:
                    try:
                        self.post_manager.mark_as_posted(work_data["work_id"])
                    except Exception as e:
                        logger.error(f"mark_as_posted でエラー: {e}")
                        logger.error(f"work_data: {work_data}")
                        raise
                
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
            category_names = self._get_categories(work_data)
            tag_names = self._get_tags(work_data)
            
            # 名前をIDに変換
            categories = self._convert_categories_to_ids(category_names)
            tags = self._convert_tags_to_ids(tag_names)
            
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
    
    # Note: 記事タイトル生成、カテゴリ、タグ処理はPostScheduleManagerに移動済み
    
    def create_wordpress_schedule_from_articles(self, articles: List[Dict]) -> Dict:
        """
        記事データからWordPress予約投稿を一括作成
        
        Args:
            articles: 記事データのリスト
            
        Returns:
            作成結果
        """
        try:
            logger.info(f"WordPress予約投稿一括作成開始: {len(articles)}件")
            
            # PostScheduleManagerを使用して予約投稿を作成
            schedule_result = self.schedule_manager.create_advance_schedule(articles)
            
            result = {
                "success": True,
                "total_articles": len(articles),
                "created_posts": len(schedule_result.get("wordpress_post_ids", [])),
                "schedule_type": schedule_result.get("type", "unknown"),
                "wordpress_post_ids": schedule_result.get("wordpress_post_ids", []),
                "slots_used": schedule_result.get("slots_used", []),
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"WordPress予約投稿一括作成完了: {result['created_posts']}件作成")
            
            return result
            
        except Exception as e:
            error_message = f"WordPress予約投稿一括作成エラー: {e}"
            logger.error(error_message)
            
            return {
                "success": False,
                "error": error_message,
                "total_articles": len(articles),
                "created_posts": 0,
                "created_at": datetime.now().isoformat()
            }
    
    def get_wordpress_schedule_summary(self) -> Dict:
        """
        WordPress予約投稿のサマリーを取得
        
        Returns:
            サマリー情報
        """
        try:
            scheduled_posts = self.schedule_manager.get_wordpress_scheduled_posts()
            activity_summary = self.schedule_manager.get_activity_summary(days=7)
            
            # 24時間以内の予約投稿をカウント
            now = datetime.now()
            next_24h_posts = 0
            
            for post in scheduled_posts:
                try:
                    post_time = datetime.fromisoformat(post['scheduled_time'].replace('T', ' ').replace('Z', ''))
                    if post_time <= now + timedelta(hours=24):
                        next_24h_posts += 1
                except Exception:
                    continue
            
            return {
                "total_scheduled_posts": len(scheduled_posts),
                "next_24h_posts": next_24h_posts,
                "activity_summary": activity_summary,
                "wordpress_posts": scheduled_posts[:5],  # 最初の5件
                "system_type": "wordpress_native",
                "last_updated": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"WordPressスケジュールサマリー取得エラー: {e}")
            
            return {
                "total_scheduled_posts": 0,
                "next_24h_posts": 0,
                "activity_summary": {"total_activities": 0, "activity_breakdown": {}},
                "wordpress_posts": [],
                "system_type": "wordpress_native",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
