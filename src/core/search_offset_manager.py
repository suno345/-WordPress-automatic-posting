"""
検索オフセット管理システム
次回検索の開始位置を記録・管理する
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SearchOffsetManager:
    """検索オフセット管理クラス"""
    
    def __init__(self, offset_file: str = "data/search_offset.json"):
        """
        検索オフセット管理の初期化
        
        Args:
            offset_file: オフセット記録ファイルのパス
        """
        self.offset_file = Path(offset_file)
        self.offset_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"検索オフセット管理を初期化: {self.offset_file}")
    
    def get_next_offset(self) -> int:
        """
        次回検索の開始オフセットを取得
        
        Returns:
            次の検索開始位置（デフォルト: 1）
        """
        try:
            if self.offset_file.exists():
                with open(self.offset_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    offset = data.get('next_offset', 1)
                    logger.info(f"保存されたオフセットを取得: {offset}")
                    return offset
            else:
                logger.info("オフセットファイルが存在しないため、初期値1を返します")
                return 1
        except Exception as e:
            logger.error(f"オフセット取得エラー: {e}")
            return 1
    
    def save_next_offset(self, current_offset: int, batch_size: int, found_count: int) -> None:
        """
        次回検索用のオフセットを保存
        
        Args:
            current_offset: 現在の検索開始位置
            batch_size: 1回の検索件数
            found_count: 今回見つかった件数
        """
        try:
            # 次回検索開始位置を計算
            next_offset = current_offset + batch_size
            
            save_data = {
                'current_offset': current_offset,
                'batch_size': batch_size,
                'found_count': found_count,
                'next_offset': next_offset,
                'last_updated': self._get_current_timestamp()
            }
            
            with open(self.offset_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"次回オフセットを保存: {current_offset} → {next_offset} ({found_count}件発見)")
            
        except Exception as e:
            logger.error(f"オフセット保存エラー: {e}")
    
    def reset_offset(self) -> None:
        """
        オフセットを初期化（1に戻す）
        """
        try:
            reset_data = {
                'next_offset': 1,
                'reset_at': self._get_current_timestamp(),
                'reason': 'manual_reset'
            }
            
            with open(self.offset_file, 'w', encoding='utf-8') as f:
                json.dump(reset_data, f, ensure_ascii=False, indent=2)
            
            logger.info("検索オフセットを1にリセットしました")
            
        except Exception as e:
            logger.error(f"オフセットリセットエラー: {e}")
    
    def get_status(self) -> dict:
        """
        現在のオフセット状況を取得
        
        Returns:
            オフセット状況の辞書
        """
        try:
            if self.offset_file.exists():
                with open(self.offset_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            else:
                return {'next_offset': 1, 'status': 'file_not_found'}
        except Exception as e:
            logger.error(f"ステータス取得エラー: {e}")
            return {'next_offset': 1, 'status': 'error', 'error': str(e)}
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')