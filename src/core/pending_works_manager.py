"""
検索済み未投稿作品管理システム
見つかった作品を一時保存し、次回実行時に優先的に処理する
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PendingWorksManager:
    """検索済み未投稿作品管理クラス"""
    
    def __init__(self, pending_file: str = "data/pending_works.json"):
        """
        検索済み未投稿作品管理の初期化
        
        Args:
            pending_file: 未投稿作品保存ファイルのパス
        """
        self.pending_file = Path(pending_file)
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"検索済み未投稿作品管理を初期化: {self.pending_file}")
    
    def save_pending_works(self, works: List[Dict], search_info: Dict) -> None:
        """
        検索済み未投稿作品を保存
        
        Args:
            works: 保存する作品リスト
            search_info: 検索情報（オフセット、バッチサイズ等）
        """
        try:
            save_data = {
                'pending_works': works,
                'search_info': search_info,
                'saved_at': self._get_current_timestamp(),
                'total_count': len(works)
            }
            
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"検索済み未投稿作品を保存: {len(works)}件")
            
        except Exception as e:
            logger.error(f"未投稿作品保存エラー: {e}")
    
    def get_pending_works(self) -> List[Dict]:
        """
        保存された検索済み未投稿作品を取得
        
        Returns:
            保存されている未投稿作品リスト
        """
        try:
            if self.pending_file.exists():
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    works = data.get('pending_works', [])
                    logger.info(f"保存済み未投稿作品を取得: {len(works)}件")
                    return works
            else:
                logger.info("保存済み未投稿作品ファイルが存在しません")
                return []
        except Exception as e:
            logger.error(f"未投稿作品取得エラー: {e}")
            return []
    
    def remove_work_from_pending(self, work_id: str) -> None:
        """
        指定された作品を保存リストから削除
        
        Args:
            work_id: 削除する作品ID
        """
        try:
            if not self.pending_file.exists():
                return
            
            with open(self.pending_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            pending_works = data.get('pending_works', [])
            original_count = len(pending_works)
            
            # 指定されたwork_idの作品を削除
            pending_works = [work for work in pending_works if work.get('work_id') != work_id]
            
            # 更新されたデータを保存
            data['pending_works'] = pending_works
            data['total_count'] = len(pending_works)
            data['last_updated'] = self._get_current_timestamp()
            
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            removed_count = original_count - len(pending_works)
            if removed_count > 0:
                logger.info(f"作品を保存リストから削除: {work_id} (残り: {len(pending_works)}件)")
            
        except Exception as e:
            logger.error(f"作品削除エラー: {e}")
    
    def clear_pending_works(self) -> None:
        """
        保存された未投稿作品をすべてクリア
        """
        try:
            if self.pending_file.exists():
                self.pending_file.unlink()
                logger.info("保存済み未投稿作品をすべてクリアしました")
        except Exception as e:
            logger.error(f"未投稿作品クリアエラー: {e}")
    
    def get_pending_count(self) -> int:
        """
        保存されている未投稿作品数を取得
        
        Returns:
            保存済み未投稿作品数
        """
        try:
            if self.pending_file.exists():
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('total_count', 0)
            return 0
        except Exception as e:
            logger.error(f"未投稿作品数取得エラー: {e}")
            return 0
    
    def get_status(self) -> Dict:
        """
        現在の保存状況を取得
        
        Returns:
            保存状況の辞書
        """
        try:
            if self.pending_file.exists():
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        'pending_count': data.get('total_count', 0),
                        'saved_at': data.get('saved_at', 'unknown'),
                        'search_info': data.get('search_info', {}),
                        'status': 'active'
                    }
            else:
                return {
                    'pending_count': 0,
                    'status': 'no_pending_works'
                }
        except Exception as e:
            logger.error(f"ステータス取得エラー: {e}")
            return {
                'pending_count': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')