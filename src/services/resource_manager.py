"""
リソース管理のためのユーティリティ
"""
import logging
from typing import Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ResourceManager:
    """リソース管理のためのコンテキストマネージャー"""
    
    def __init__(self, *resources: Any):
        """
        リソース管理マネージャーの初期化
        
        Args:
            *resources: 管理するリソースオブジェクト
        """
        self.resources = resources
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """リソースの適切なクリーンアップ"""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                    logger.debug(f"Successfully closed resource: {type(resource).__name__}")
                elif hasattr(resource, '__exit__'):
                    resource.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.warning(f"Error closing resource {type(resource).__name__}: {e}")


@contextmanager
def managed_session():
    """リクエストセッションの管理されたコンテキスト"""
    import requests
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()
        logger.debug("HTTP session closed")


class SessionMixin:
    """セッション管理のためのミックスイン"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None
    
    @property
    def session(self):
        """遅延初期化されたセッション"""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session
    
    def close_session(self):
        """セッションのクリーンアップ"""
        if self._session:
            self._session.close()
            self._session = None
            logger.debug(f"{self.__class__.__name__} session closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_session()