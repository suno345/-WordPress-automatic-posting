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
        """投稿済み作品IDを保存（強化版：保存確認付き）"""
        import tempfile
        import shutil
        
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.posted_works_file), exist_ok=True)
            
            data = {
                'posted_work_ids': list(self.posted_works)
            }
            
            # 一時ファイルに書き込んでから原子的に移動（安全な保存）
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    encoding='utf-8', 
                    suffix='.json.tmp',
                    dir=os.path.dirname(self.posted_works_file),
                    delete=False
                ) as f:
                    temp_file = f.name
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # ディスクに強制書き込み
                
                # 原子的な移動
                shutil.move(temp_file, self.posted_works_file)
                
                # 保存確認：実際にファイルを読み直して内容を検証
                self._verify_saved_data(data)
                
                logger.info(f"Saved {len(self.posted_works)} posted work IDs (verified)")
                
            except Exception as e:
                # 一時ファイルのクリーンアップ
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise
                
        except Exception as e:
            logger.error(f"Error saving posted works: {e}")
            logger.error(f"File path: {self.posted_works_file}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Data to save: {len(self.posted_works)} items")
            raise RuntimeError(f"Critical: Failed to save posted works data: {e}")
    
    def _verify_saved_data(self, expected_data):
        """保存されたデータの整合性を確認"""
        try:
            with open(self.posted_works_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            expected_ids = set(expected_data['posted_work_ids'])
            saved_ids = set(saved_data.get('posted_work_ids', []))
            
            if expected_ids != saved_ids:
                raise ValueError(f"Data verification failed: expected {len(expected_ids)} IDs, got {len(saved_ids)} IDs")
                
        except Exception as e:
            raise RuntimeError(f"Data verification failed: {e}")
    
    def is_posted(self, work_id: str) -> bool:
        """作品が既に投稿済みかチェック"""
        return work_id in self.posted_works
    
    def mark_as_posted(self, work_id: str):
        """作品を投稿済みとしてマーク（保存確認付き）"""
        if work_id in self.posted_works:
            logger.info(f"Work already marked as posted: {work_id}")
            return
            
        # メモリ上で追加
        self.posted_works.add(work_id)
        
        try:
            # ファイルに保存（検証付き）
            self._save_posted_works()
            logger.info(f"Marked work as posted: {work_id} (total: {len(self.posted_works)})")
            
        except Exception as e:
            # 保存に失敗した場合はメモリからも削除して整合性を保つ
            self.posted_works.discard(work_id)
            logger.error(f"Failed to mark work as posted: {work_id} - {e}")
            raise RuntimeError(f"Critical: Failed to save posted work {work_id}: {e}")
    
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