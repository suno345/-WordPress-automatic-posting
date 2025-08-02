import json
import os
from typing import List, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PostManager:
    def __init__(self, posted_works_file: str = None):
        """投稿管理クラスの初期化"""
        if posted_works_file is None:
            # 新しいディレクトリ構造に対応
            project_root = Path(__file__).parent.parent.parent
            posted_works_file = project_root / "data" / "posted_works.json"
        
        self.posted_works_file = str(posted_works_file)
        self.posted_works = self._load_posted_works()
        
    def _load_posted_works(self) -> Set[str]:
        """投稿済み作品IDをロード"""
        if os.path.exists(self.posted_works_file):
            try:
                with open(self.posted_works_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('posted_work_ids', []))
            except Exception as e:
                logger.error(f"Error loading posted works: {e}")
        
        return set()
    
    def _save_posted_works(self):
        """投稿済み作品IDを保存"""
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.posted_works_file), exist_ok=True)
            
            data = {
                'posted_work_ids': list(self.posted_works)
            }
            
            with open(self.posted_works_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(self.posted_works)} posted work IDs")
            
        except Exception as e:
            logger.error(f"Error saving posted works: {e}")
    
    def is_posted(self, work_id: str) -> bool:
        """作品が既に投稿済みかチェック"""
        return work_id in self.posted_works
    
    def mark_as_posted(self, work_id: str):
        """作品を投稿済みとしてマーク"""
        self.posted_works.add(work_id)
        self._save_posted_works()
        logger.info(f"Marked work as posted: {work_id}")
    
    def get_posted_count(self) -> int:
        """投稿済み作品数を取得"""
        return len(self.posted_works)
    
    def reset_posted_count(self) -> bool:
        """投稿カウンターをリセット（投稿済みデータをクリア）"""
        try:
            old_count = len(self.posted_works)
            self.posted_works.clear()
            self._save_posted_works()
            logger.info(f"投稿カウンターをリセット: {old_count}件 → 0件")
            return True
        except Exception as e:
            logger.error(f"投稿カウンターのリセットに失敗: {e}")
            return False
    
    def filter_unposted_works(self, work_ids: List[str]) -> List[str]:
        """未投稿の作品IDのみをフィルタリング"""
        unposted = [work_id for work_id in work_ids if not self.is_posted(work_id)]
        logger.info(f"Filtered {len(unposted)} unposted works from {len(work_ids)} total")
        return unposted