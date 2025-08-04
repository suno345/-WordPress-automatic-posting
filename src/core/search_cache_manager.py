"""
検索キャッシュ管理システム
検索済み未投稿作品の商品IDを一時的にキャッシュして効率化を図る
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SearchCacheManager:
    """検索キャッシュ管理クラス"""
    
    def __init__(self, cache_file: str = "data/search_cache.json"):
        """
        検索キャッシュ管理の初期化
        
        Args:
            cache_file: キャッシュファイルのパス
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"検索キャッシュ管理を初期化: {self.cache_file}")
    
    def get_cached_work_ids(self) -> List[str]:
        """
        キャッシュされた未投稿作品IDリストを取得
        
        Returns:
            キャッシュされた作品IDリスト
        """
        try:
            if not self.cache_file.exists():
                logger.info("キャッシュファイルが存在しません")
                return []
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # キャッシュの有効期限チェック（24時間）
            if self._is_cache_expired(data.get('timestamp')):
                logger.info("キャッシュが期限切れです。クリアします")
                self.clear_cache()
                return []
            
            work_ids = data.get('work_ids', [])
            logger.info(f"キャッシュから{len(work_ids)}件の作品IDを取得")
            return work_ids
            
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return []
    
    def save_work_ids(self, work_ids: List[str]) -> None:
        """
        作品IDリストをキャッシュに保存
        
        Args:
            work_ids: 保存する作品IDリスト
        """
        try:
            cache_data = {
                'work_ids': work_ids,
                'timestamp': datetime.now().isoformat(),
                'count': len(work_ids)
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"キャッシュに{len(work_ids)}件の作品IDを保存")
            
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    def remove_work_id(self, work_id: str) -> None:
        """
        投稿完了した作品IDをキャッシュから削除
        
        Args:
            work_id: 削除する作品ID
        """
        try:
            cached_ids = self.get_cached_work_ids()
            if work_id in cached_ids:
                cached_ids.remove(work_id)
                self.save_work_ids(cached_ids)
                logger.info(f"キャッシュから作品ID '{work_id}' を削除（残り{len(cached_ids)}件）")
            else:
                logger.warning(f"作品ID '{work_id}' がキャッシュに見つかりません")
                
        except Exception as e:
            logger.error(f"キャッシュから作品ID削除エラー: {e}")
    
    def clear_cache(self) -> None:
        """
        キャッシュをクリア
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("キャッシュをクリアしました")
            else:
                logger.info("クリア対象のキャッシュファイルが存在しません")
                
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")
    
    def get_cache_status(self) -> Dict:
        """
        キャッシュの状況を取得
        
        Returns:
            キャッシュ状況の辞書
        """
        try:
            if not self.cache_file.exists():
                return {'status': 'not_found', 'count': 0}
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            is_expired = self._is_cache_expired(data.get('timestamp'))
            
            return {
                'status': 'expired' if is_expired else 'valid',
                'count': len(data.get('work_ids', [])),
                'timestamp': data.get('timestamp'),
                'age_hours': self._get_cache_age_hours(data.get('timestamp'))
            }
            
        except Exception as e:
            logger.error(f"キャッシュ状況取得エラー: {e}")
            return {'status': 'error', 'count': 0, 'error': str(e)}
    
    def _is_cache_expired(self, timestamp_str: Optional[str]) -> bool:
        """
        キャッシュが期限切れかチェック
        
        Args:
            timestamp_str: タイムスタンプ文字列
            
        Returns:
            True if expired, False otherwise
        """
        if not timestamp_str:
            return True
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            expire_time = timestamp + timedelta(hours=24)  # 24時間で期限切れ
            return datetime.now() > expire_time
        except Exception:
            return True
    
    def _get_cache_age_hours(self, timestamp_str: Optional[str]) -> float:
        """
        キャッシュの経過時間（時間）を取得
        
        Args:
            timestamp_str: タイムスタンプ文字列
            
        Returns:
            経過時間（時間）
        """
        if not timestamp_str:
            return 0.0
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            delta = datetime.now() - timestamp
            return delta.total_seconds() / 3600
        except Exception:
            return 0.0