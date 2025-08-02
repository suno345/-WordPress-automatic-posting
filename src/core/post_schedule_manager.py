"""
投稿予約管理システム - 15分刻み予約投稿の中核システム
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class PostScheduleManager:
    """投稿予約管理システム"""
    
    def __init__(self, config=None):
        """
        予約管理システムの初期化
        
        Args:
            config: システム設定
        """
        self.config = config
        
        # データファイルパス
        self.schedule_dir = Path("data/schedule")
        self.schedule_file = self.schedule_dir / "post_schedule.json"
        self.completed_file = self.schedule_dir / "completed_posts.json"
        self.failed_file = self.schedule_dir / "failed_posts.json"
        
        # ディレクトリ作成
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
        
        # データ初期化
        self.schedule_data = self._load_schedule()
        self.completed_posts = self._load_completed_posts()
        self.failed_posts = self._load_failed_posts()
        
        logger.info("投稿予約管理システム初期化完了")
    
    def _load_schedule(self) -> Dict:
        """予約スケジュールを読み込み"""
        try:
            if self.schedule_file.exists():
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 古い予約を自動クリーンアップ
                    return self._cleanup_old_schedules(data)
            return {}
        except Exception as e:
            logger.error(f"スケジュール読み込みエラー: {e}")
            return {}
    
    def _load_completed_posts(self) -> Dict:
        """完了投稿データを読み込み"""
        try:
            if self.completed_file.exists():
                with open(self.completed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"完了投稿データ読み込みエラー: {e}")
            return {}
    
    def _load_failed_posts(self) -> Dict:
        """失敗投稿データを読み込み"""
        try:
            if self.failed_file.exists():
                with open(self.failed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"失敗投稿データ読み込みエラー: {e}")
            return {}
    
    def _save_schedule(self):
        """予約スケジュールを保存"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.schedule_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"スケジュール保存エラー: {e}")
    
    def _save_completed_posts(self):
        """完了投稿データを保存"""
        try:
            with open(self.completed_file, 'w', encoding='utf-8') as f:
                json.dump(self.completed_posts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"完了投稿データ保存エラー: {e}")
    
    def _save_failed_posts(self):
        """失敗投稿データを保存"""
        try:
            with open(self.failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_posts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"失敗投稿データ保存エラー: {e}")
    
    def create_advance_schedule(self, articles: List[Dict]) -> Dict:
        """
        15分刻みスケジュール内での前倒し投稿予約
        
        Args:
            articles: 記事データのリスト
            
        Returns:
            作成されたスケジュール情報
        """
        now = datetime.now()
        
        # 今日の残り投稿可能数を確認
        remaining_slots = self._get_remaining_daily_slots()
        
        # 利用可能な15分刻み時刻を計算
        available_slots = self._calculate_next_15min_slots(len(articles), remaining_slots)
        
        created_count = 0
        schedule_info = {
            "created_at": now.isoformat(),
            "total_articles": len(articles),
            "schedule_ids": [],
            "type": "advance_schedule",
            "interval_minutes": 15,
            "slots_used": [],
            "remaining_daily_slots": remaining_slots
        }
        
        if not available_slots:
            logger.warning("今日の投稿枠が満杯のため、翌日に振り分けます")
            return self._schedule_for_tomorrow(articles, schedule_info)
        
        # 各記事を利用可能な15分刻み時刻に割り当て
        for i, (article, post_time) in enumerate(zip(articles, available_slots)):
            # スケジュールIDを生成
            schedule_id = f"advance_{post_time.strftime('%Y%m%d_%H%M')}_{uuid.uuid4().hex[:8]}"
            
            # 予約データ作成
            schedule_entry = {
                "schedule_id": schedule_id,
                "post_time": post_time.isoformat(),
                "article_data": article,
                "status": "scheduled",
                "created_at": now.isoformat(),
                "attempts": 0,
                "priority": "high",  # 前倒し投稿は高優先度
                "type": "advance_schedule",
                "estimated_post_time": post_time.isoformat()
            }
            
            # スケジュールに追加
            self.schedule_data[schedule_id] = schedule_entry
            schedule_info["schedule_ids"].append(schedule_id)
            schedule_info["slots_used"].append(post_time.strftime('%Y-%m-%d %H:%M'))
            created_count += 1
        
        # スケジュール保存
        self._save_schedule()
        
        logger.info(f"前倒し投稿スケジュール作成完了: {created_count}件")
        logger.info(f"投稿予定時刻: {', '.join(schedule_info['slots_used'])}")
        
        return schedule_info

    def _get_remaining_daily_slots(self) -> int:
        """今日の残り投稿可能数を計算"""
        today = datetime.now().date()
        today_posts_count = len([
            p for p in self.schedule_data.values()
            if datetime.fromisoformat(p["post_time"]).date() == today
            and p["status"] in ["scheduled", "in_progress", "completed"]
        ])
        
        max_daily_posts = 96
        return max(0, max_daily_posts - today_posts_count)
    
    def _calculate_next_15min_slots(self, needed_count: int, max_slots: int) -> List[datetime]:
        """
        次に利用可能な15分刻み時刻を計算
        
        Args:
            needed_count: 必要な投稿数
            max_slots: 今日の最大利用可能数
            
        Returns:
            利用可能な15分刻み時刻のリスト
        """
        now = datetime.now()
        available_slots = []
        
        # 次の15分刻み時刻を計算
        next_quarter = now.replace(second=0, microsecond=0)
        minutes_to_next = (15 - now.minute % 15) % 15
        if minutes_to_next == 0:
            minutes_to_next = 15
        next_quarter += timedelta(minutes=minutes_to_next)
        
        # 必要数分の空き枠を探す（最大で今日の残り枠まで）
        candidate_time = next_quarter
        max_check_slots = min(needed_count, max_slots, 96)  # 最大96枠まで
        checked_slots = 0
        
        while len(available_slots) < max_check_slots and checked_slots < 96:
            if not self._is_slot_occupied(candidate_time):
                available_slots.append(candidate_time)
            
            candidate_time += timedelta(minutes=15)
            checked_slots += 1
            
            # 日付が変わったら停止（今日の枠のみ）
            if candidate_time.date() != now.date():
                break
        
        logger.info(f"利用可能な15分刻み枠: {len(available_slots)}件 (必要: {needed_count}件)")
        return available_slots
    
    def _is_slot_occupied(self, target_time: datetime) -> bool:
        """指定時刻に既に予約があるかチェック"""
        target_str = target_time.strftime('%Y-%m-%d %H:%M')
        
        for post_info in self.schedule_data.values():
            if post_info["status"] in ["scheduled", "in_progress"]:
                post_time = datetime.fromisoformat(post_info["post_time"])
                if post_time.strftime('%Y-%m-%d %H:%M') == target_str:
                    return True
        return False
    
    def _schedule_for_tomorrow(self, articles: List[Dict], schedule_info: Dict) -> Dict:
        """翌日への振り分けスケジュール作成"""
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        created_count = 0
        for i, article in enumerate(articles):
            post_time = tomorrow + timedelta(minutes=15 * i)
            
            # スケジュールIDを生成
            schedule_id = f"tomorrow_{post_time.strftime('%Y%m%d_%H%M')}_{uuid.uuid4().hex[:8]}"
            
            # 予約データ作成
            schedule_entry = {
                "schedule_id": schedule_id,
                "post_time": post_time.isoformat(),
                "article_data": article,
                "status": "scheduled",
                "created_at": datetime.now().isoformat(),
                "attempts": 0,
                "priority": "normal",
                "type": "tomorrow_schedule",
                "estimated_post_time": post_time.isoformat()
            }
            
            # スケジュールに追加
            self.schedule_data[schedule_id] = schedule_entry
            schedule_info["schedule_ids"].append(schedule_id)
            schedule_info["slots_used"].append(post_time.strftime('%Y-%m-%d %H:%M'))
            created_count += 1
        
        # スケジュール保存
        self._save_schedule()
        
        schedule_info["type"] = "tomorrow_schedule"
        logger.info(f"翌日投稿スケジュール作成完了: {created_count}件 (開始: {tomorrow.strftime('%Y-%m-%d %H:%M')})")
        
        return schedule_info

    def create_daily_schedule(self, articles: List[Dict], start_date: Optional[datetime] = None) -> Dict:
        """
        1日分の投稿スケジュールを作成
        
        Args:
            articles: 記事データのリスト
            start_date: 開始日時（Noneの場合は翌日00:00から）
            
        Returns:
            作成されたスケジュール情報
        """
        if start_date is None:
            # 翌日の00:00から開始
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date += timedelta(days=1)
        
        created_count = 0
        schedule_info = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat(),
            "total_articles": len(articles),
            "schedule_ids": []
        }
        
        for i, article in enumerate(articles[:96]):  # 最大96件/日
            post_time = start_date + timedelta(minutes=15 * i)
            
            # スケジュールIDを生成
            schedule_id = f"post_{post_time.strftime('%Y%m%d_%H%M')}_{uuid.uuid4().hex[:8]}"
            
            # 予約データ作成
            schedule_entry = {
                "schedule_id": schedule_id,
                "post_time": post_time.isoformat(),
                "article_data": article,
                "status": "scheduled",  # scheduled, in_progress, completed, failed
                "created_at": datetime.now().isoformat(),
                "attempts": 0,
                "priority": "normal",  # normal, high, emergency
                "estimated_post_time": post_time.isoformat()
            }
            
            # スケジュールに追加
            self.schedule_data[schedule_id] = schedule_entry
            schedule_info["schedule_ids"].append(schedule_id)
            created_count += 1
        
        # スケジュール保存
        self._save_schedule()
        
        logger.info(f"日次スケジュール作成完了: {created_count}件 (開始: {start_date.strftime('%Y-%m-%d %H:%M')})")
        
        return schedule_info
    
    def get_next_scheduled_post(self, time_buffer_minutes: int = 2) -> Optional[Dict]:
        """
        次に投稿すべき記事を取得
        
        Args:
            time_buffer_minutes: 投稿時刻の余裕時間（分）
            
        Returns:
            次の投稿データまたはNone
        """
        now = datetime.now()
        buffer_time = now + timedelta(minutes=time_buffer_minutes)
        
        # 投稿対象の候補を取得
        candidates = []
        
        for schedule_id, post_info in self.schedule_data.items():
            if post_info["status"] == "scheduled":
                post_time = datetime.fromisoformat(post_info["post_time"])
                
                # 投稿時刻が来ているかチェック
                if post_time <= buffer_time:
                    candidates.append({
                        "schedule_id": schedule_id,
                        "post_time": post_time,
                        "priority": post_info.get("priority", "normal"),
                        "attempts": post_info.get("attempts", 0),
                        **post_info
                    })
        
        if not candidates:
            return None
        
        # 優先度とスケジュール時刻でソート
        priority_order = {"emergency": 0, "high": 1, "normal": 2}
        candidates.sort(key=lambda x: (
            priority_order.get(x["priority"], 2),
            x["post_time"],
            x["attempts"]
        ))
        
        return candidates[0]
    
    def mark_post_in_progress(self, schedule_id: str) -> bool:
        """投稿を進行中としてマーク"""
        if schedule_id not in self.schedule_data:
            return False
        
        self.schedule_data[schedule_id]["status"] = "in_progress"
        self.schedule_data[schedule_id]["started_at"] = datetime.now().isoformat()
        self.schedule_data[schedule_id]["attempts"] += 1
        
        self._save_schedule()
        return True
    
    def mark_post_completed(self, schedule_id: str, post_result: Dict) -> bool:
        """投稿完了としてマーク"""
        if schedule_id not in self.schedule_data:
            return False
        
        post_info = self.schedule_data[schedule_id]
        
        try:
            # post_resultをJSONシリアライズ可能な形式に変換
            serializable_post_result = {}
            for key, value in post_result.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    serializable_post_result[key] = value
                else:
                    serializable_post_result[key] = str(value)
            
            # 完了データ作成（スプレッド演算子を使わずに明示的にコピー）
            completed_entry = {
                "schedule_id": schedule_id,
                "article_data": post_info.get("article_data"),
                "post_time": post_info.get("post_time"),
                "priority": post_info.get("priority", "normal"),
                "created_at": post_info.get("created_at"),
                "attempts": post_info.get("attempts", 0),
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "post_result": serializable_post_result,
                "final_attempts": post_info.get("attempts", 0)
            }
            
            # 完了リストに追加
            self.completed_posts[schedule_id] = completed_entry
            
            # スケジュールから削除
            del self.schedule_data[schedule_id]
            
            # 保存
            self._save_schedule()
            self._save_completed_posts()
            
            logger.info(f"投稿完了: {post_info['article_data']['work_data']['title']}")
            return True
            
        except Exception as e:
            logger.error(f"投稿完了マーク中にエラー: {e}")
            logger.error(f"post_result type: {type(post_result)}, content: {post_result}")
            logger.error(f"post_info type: {type(post_info)}, keys: {list(post_info.keys()) if isinstance(post_info, dict) else 'not dict'}")
            raise
    
    def mark_post_failed(self, schedule_id: str, error_info: str, retry: bool = True) -> bool:
        """投稿失敗としてマーク"""
        if schedule_id not in self.schedule_data:
            return False
        
        post_info = self.schedule_data[schedule_id]
        attempts = post_info.get("attempts", 0)
        max_attempts = 3
        
        if retry and attempts < max_attempts:
            # 再試行設定
            retry_delay_minutes = min(15 * attempts, 60)  # 最大60分遅延
            original_time = datetime.fromisoformat(post_info["post_time"])
            new_post_time = datetime.now() + timedelta(minutes=retry_delay_minutes)
            
            self.schedule_data[schedule_id].update({
                "status": "scheduled",
                "post_time": new_post_time.isoformat(),
                "original_post_time": original_time.isoformat(),
                "last_error": error_info,
                "last_failed_at": datetime.now().isoformat(),
                "priority": "high"  # 失敗した投稿は高優先度に
            })
            
            logger.warning(f"投稿失敗 - 再試行予定: {post_info['article_data']['work_data']['title']} (試行回数: {attempts}/{max_attempts})")
            
        else:
            # 最大試行回数に達した場合は失敗として記録
            failed_entry = {
                **post_info,
                "status": "failed",
                "failed_at": datetime.now().isoformat(),
                "final_error": error_info,
                "final_attempts": attempts
            }
            
            # 失敗リストに追加
            self.failed_posts[schedule_id] = failed_entry
            
            # スケジュールから削除
            del self.schedule_data[schedule_id]
            
            logger.error(f"投稿最終失敗: {post_info['article_data']['work_data']['title']} (試行回数: {attempts})")
            
            self._save_failed_posts()
        
        self._save_schedule()
        return True
    
    def get_schedule_status(self) -> Dict:
        """スケジュール状況を取得"""
        now = datetime.now()
        
        status_counts = {"scheduled": 0, "in_progress": 0, "overdue": 0}
        next_posts = []
        
        for schedule_id, post_info in self.schedule_data.items():
            status = post_info["status"]
            post_time = datetime.fromisoformat(post_info["post_time"])
            
            if status == "scheduled":
                if post_time <= now:
                    status_counts["overdue"] += 1
                else:
                    status_counts["scheduled"] += 1
                    if len(next_posts) < 5:  # 次の5件を表示
                        next_posts.append({
                            "title": post_info["article_data"]["work_data"]["title"],
                            "post_time": post_time.strftime("%Y-%m-%d %H:%M"),
                            "priority": post_info.get("priority", "normal")
                        })
            else:
                status_counts[status] += 1
        
        # 次の投稿を時刻順でソート
        next_posts.sort(key=lambda x: x["post_time"])
        
        return {
            "total_scheduled": sum(status_counts.values()),
            "status_breakdown": status_counts,
            "completed_today": len([
                p for p in self.completed_posts.values()
                if datetime.fromisoformat(p["completed_at"]).date() == now.date()
            ]),
            "failed_today": len([
                p for p in self.failed_posts.values()
                if datetime.fromisoformat(p["failed_at"]).date() == now.date()
            ]),
            "next_posts": next_posts,
            "last_updated": now.isoformat()
        }
    
    def _cleanup_old_schedules(self, schedule_data: Dict) -> Dict:
        """古いスケジュールをクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=2)  # 2日前より古いものを削除
        
        cleaned_data = {}
        removed_count = 0
        
        for schedule_id, post_info in schedule_data.items():
            post_time = datetime.fromisoformat(post_info["post_time"])
            
            if post_time >= cutoff_date:
                cleaned_data[schedule_id] = post_info
            else:
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"古いスケジュールをクリーンアップ: {removed_count}件")
        
        return cleaned_data
    
    def reschedule_failed_posts(self) -> int:
        """失敗した投稿を再スケジュール"""
        rescheduled_count = 0
        now = datetime.now()
        
        # 今日失敗した投稿を対象にする
        today_failed = [
            (schedule_id, post_info) for schedule_id, post_info in self.failed_posts.items()
            if datetime.fromisoformat(post_info["failed_at"]).date() == now.date()
            and post_info.get("final_attempts", 0) < 5  # 最終試行回数が5回未満
        ]
        
        for schedule_id, post_info in today_failed:
            try:
                # 新しいスケジュール時刻を設定（次の空き時間）
                new_post_time = self._find_next_available_slot()
                
                if new_post_time:
                    # 新しいスケジュールIDで再登録
                    new_schedule_id = f"retry_{schedule_id}_{uuid.uuid4().hex[:8]}"
                    
                    new_schedule_entry = {
                        **post_info,
                        "schedule_id": new_schedule_id,
                        "post_time": new_post_time.isoformat(),
                        "status": "scheduled",
                        "priority": "high",
                        "rescheduled_at": now.isoformat(),
                        "original_schedule_id": schedule_id,
                        "attempts": 0  # 試行回数リセット
                    }
                    
                    self.schedule_data[new_schedule_id] = new_schedule_entry
                    rescheduled_count += 1
                    
                    logger.info(f"失敗投稿を再スケジュール: {post_info['article_data']['work_data']['title']}")
                
            except Exception as e:
                logger.error(f"再スケジュールエラー: {e}")
        
        if rescheduled_count > 0:
            self._save_schedule()
        
        return rescheduled_count
    
    def get_activity_summary(self, days: int = 7) -> Dict:
        """\u30a2\u30af\u30c6\u30a3\u30d3\u30c6\u30a3\u30b5\u30de\u30ea\u30fc\u3092\u53d6\u5f97"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_activities = [
            activity for activity in self.activity_log
            if datetime.fromisoformat(activity["timestamp"]) >= cutoff_date
        ]
        
        # \u30a2\u30af\u30c6\u30a3\u30d3\u30c6\u30a3\u30bf\u30a4\u30d7\u5225\u96c6\u8a08
        activity_counts = {}
        for activity in recent_activities:
            activity_type = activity["type"]
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        return {
            "period_days": days,
            "total_activities": len(recent_activities),
            "activity_breakdown": activity_counts,
            "recent_activities": recent_activities[-10:],  # \u6700\u65b010\u4ef6
            "generated_at": datetime.now().isoformat()
        }
    
    def _find_next_available_slot(self) -> Optional[datetime]:
        """次の利用可能な時間枠を検索"""
        now = datetime.now()
        
        # 15分間隔で次の空き時間を検索
        for minutes_ahead in range(15, 24 * 60, 15):  # 15分後から24時間後まで
            candidate_time = now + timedelta(minutes=minutes_ahead)
            
            # この時間に既に予約があるかチェック
            time_str = candidate_time.replace(second=0, microsecond=0).isoformat()
            
            conflict = any(
                datetime.fromisoformat(post_info["post_time"]).replace(second=0, microsecond=0).isoformat() == time_str
                for post_info in self.schedule_data.values()
                if post_info["status"] in ["scheduled", "in_progress"]
            )
            
            if not conflict:
                return candidate_time
        
        return None