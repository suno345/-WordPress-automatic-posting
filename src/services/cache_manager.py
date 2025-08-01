"""
多層キャッシュ管理システム

L1: メモリキャッシュ（最高速）
L2: ファイルキャッシュ（永続化）
"""

import json
import pickle
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging
import hashlib

logger = logging.getLogger(__name__)


class MultiTierCacheManager:
    """多層キャッシュ管理システム"""
    
    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 1000):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリのパス
            max_memory_items: メモリキャッシュの最大アイテム数
        """
        # L1: メモリキャッシュ（最高速）
        self.memory_cache: Dict[str, Any] = {}
        self.memory_cache_ttl: Dict[str, datetime] = {}
        self.max_memory_items = max_memory_items
        self._memory_lock = threading.RLock()
        
        # L2: ファイルキャッシュ（永続化）
        self.file_cache_dir = Path(cache_dir)
        self.file_cache_dir.mkdir(exist_ok=True)
        
        # 統計情報
        self.stats = {
            'memory_hits': 0,
            'file_hits': 0,
            'misses': 0,
            'sets': 0
        }
        
        logger.info(f"MultiTierCacheManager initialized: {cache_dir}")
        self._cleanup_expired_files()
    
    def get(self, key: str, category: str = "default") -> Optional[Any]:
        """
        多層キャッシュから値を取得
        
        Args:
            key: キャッシュキー
            category: カテゴリ（名前空間的な役割）
        
        Returns:
            キャッシュされた値またはNone
        """
        cache_key = self._build_cache_key(category, key)
        
        # L1: メモリキャッシュをチェック
        value = self._get_from_memory(cache_key)
        if value is not None:
            self.stats['memory_hits'] += 1
            logger.debug(f"Memory cache hit: {cache_key}")
            return value
        
        # L2: ファイルキャッシュをチェック
        value = self._get_from_file(cache_key)
        if value is not None:
            self.stats['file_hits'] += 1
            logger.debug(f"File cache hit: {cache_key}")
            # L1キャッシュに昇格
            self._set_memory_cache(cache_key, value, ttl_minutes=30)
            return value
        
        # キャッシュミス
        self.stats['misses'] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def set(self, key: str, value: Any, category: str = "default", 
            ttl_hours: int = 24) -> None:
        """
        多層キャッシュに値を設定
        
        Args:
            key: キャッシュキー
            value: 保存する値
            category: カテゴリ
            ttl_hours: 有効期限（時間）
        """
        cache_key = self._build_cache_key(category, key)
        
        # 統計更新
        self.stats['sets'] += 1
        
        # L1: メモリキャッシュに設定
        self._set_memory_cache(cache_key, value, ttl_minutes=min(60, ttl_hours * 60))
        
        # L2: ファイルキャッシュに設定
        self._set_file_cache(cache_key, value, ttl_hours=ttl_hours)
        
        logger.debug(f"Cache set: {cache_key} (TTL: {ttl_hours}h)")
    
    def delete(self, key: str, category: str = "default") -> bool:
        """
        キャッシュから値を削除
        
        Args:
            key: キャッシュキー
            category: カテゴリ
        
        Returns:
            削除に成功したかどうか
        """
        cache_key = self._build_cache_key(category, key)
        deleted = False
        
        # メモリキャッシュから削除
        with self._memory_lock:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                if cache_key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[cache_key]
                deleted = True
        
        # ファイルキャッシュから削除
        file_path = self._get_file_path(cache_key)
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        if deleted:
            logger.debug(f"Cache deleted: {cache_key}")
        
        return deleted
    
    def clear_category(self, category: str) -> int:
        """
        指定カテゴリのキャッシュをクリア
        
        Args:
            category: クリアするカテゴリ
        
        Returns:
            削除されたアイテム数
        """
        deleted_count = 0
        category_prefix = f"{category}:"
        
        # メモリキャッシュをクリア
        with self._memory_lock:
            keys_to_delete = [
                key for key in self.memory_cache.keys() 
                if key.startswith(category_prefix)
            ]
            for key in keys_to_delete:
                del self.memory_cache[key]
                if key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[key]
                deleted_count += 1
        
        # ファイルキャッシュをクリア
        for file_path in self.file_cache_dir.glob(f"{category}_*.json"):
            file_path.unlink()
            deleted_count += 1
        
        logger.info(f"Cleared {deleted_count} items from category: {category}")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """キャッシュ統計を取得"""
        total_requests = sum([
            self.stats['memory_hits'], 
            self.stats['file_hits'], 
            self.stats['misses']
        ])
        
        if total_requests == 0:
            hit_rate = 0.0
        else:
            hit_rate = (self.stats['memory_hits'] + self.stats['file_hits']) / total_requests
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'memory_items': len(self.memory_cache),
            'file_items': len(list(self.file_cache_dir.glob("*.json")))
        }
    
    def _build_cache_key(self, category: str, key: str) -> str:
        """キャッシュキーを構築"""
        return f"{category}:{key}"
    
    def _get_from_memory(self, cache_key: str) -> Optional[Any]:
        """メモリキャッシュから取得"""
        with self._memory_lock:
            if cache_key not in self.memory_cache:
                return None
            
            # TTLチェック
            if cache_key in self.memory_cache_ttl:
                if datetime.now() > self.memory_cache_ttl[cache_key]:
                    # 期限切れ
                    del self.memory_cache[cache_key]
                    del self.memory_cache_ttl[cache_key]
                    return None
            
            return self.memory_cache[cache_key]
    
    def _set_memory_cache(self, cache_key: str, value: Any, ttl_minutes: int) -> None:
        """メモリキャッシュに設定"""
        with self._memory_lock:
            # 容量制限チェック
            if len(self.memory_cache) >= self.max_memory_items:
                # 古いアイテムを削除（LRU的な動作）
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
                if oldest_key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[oldest_key]
            
            self.memory_cache[cache_key] = value
            if ttl_minutes > 0:
                self.memory_cache_ttl[cache_key] = datetime.now() + timedelta(minutes=ttl_minutes)
    
    def _get_from_file(self, cache_key: str) -> Optional[Any]:
        """ファイルキャッシュから取得"""
        file_path = self._get_file_path(cache_key)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # TTLチェック
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                # 期限切れファイルを削除
                file_path.unlink()
                return None
            
            return cache_data['data']
            
        except Exception as e:
            logger.warning(f"Error reading file cache {file_path}: {e}")
            # 破損したファイルを削除
            if file_path.exists():
                file_path.unlink()
            return None
    
    def _set_file_cache(self, cache_key: str, value: Any, ttl_hours: int) -> None:
        """ファイルキャッシュに設定"""
        file_path = self._get_file_path(cache_key)
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        cache_data = {
            'data': value,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat(),
            'ttl_hours': ttl_hours
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error writing file cache {file_path}: {e}")
    
    def _get_file_path(self, cache_key: str) -> Path:
        """ファイルパスを取得"""
        # キャッシュキーをファイル名に安全な形式に変換
        safe_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
        return self.file_cache_dir / f"{safe_key}.json"
    
    def _cleanup_expired_files(self) -> None:
        """期限切れファイルをクリーンアップ"""
        deleted_count = 0
        
        try:
            for file_path in self.file_cache_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(cache_data['expires_at'])
                    if datetime.now() > expires_at:
                        file_path.unlink()
                        deleted_count += 1
                        
                except Exception as e:
                    # 読み取れないファイルは削除
                    logger.debug(f"Removing unreadable cache file {file_path}: {e}")
                    file_path.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache files")
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


# グローバルキャッシュインスタンス
_global_cache: Optional[MultiTierCacheManager] = None


def get_cache() -> MultiTierCacheManager:
    """グローバルキャッシュインスタンスを取得"""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiTierCacheManager()
    return _global_cache


def set_cache(cache_manager: MultiTierCacheManager) -> None:
    """グローバルキャッシュインスタンスを設定"""
    global _global_cache
    _global_cache = cache_manager