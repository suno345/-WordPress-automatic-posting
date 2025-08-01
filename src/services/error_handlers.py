"""
統一されたエラーハンドリングシステム
"""
import logging
import traceback
from typing import Any, Dict, Optional, Callable, Type
from functools import wraps
from enum import Enum

from .exceptions import (
    DMMAPIError, WordPressAPIError, GeminiAPIError, 
    ConfigurationError, FileOperationError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """エラーの重要度レベル"""
    CRITICAL = "critical"  # システム停止が必要
    ERROR = "error"        # 処理失敗だが続行可能
    WARNING = "warning"    # 警告レベル
    INFO = "info"          # 情報レベル


class ErrorCategory(Enum):
    """エラーのカテゴリ"""
    API_ERROR = "api"
    CONFIGURATION_ERROR = "config"
    NETWORK_ERROR = "network"
    FILE_ERROR = "file"
    VALIDATION_ERROR = "validation"
    SYSTEM_ERROR = "system"


class ErrorContext:
    """エラーコンテキスト情報"""
    
    def __init__(
        self, 
        operation: str,
        work_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.work_id = work_id
        self.additional_info = additional_info or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式でコンテキスト情報を返す"""
        return {
            'operation': self.operation,
            'work_id': self.work_id,
            'additional_info': self.additional_info,
            'timestamp': self.timestamp
        }


class UnifiedErrorHandler:
    """統一エラーハンドラー"""
    
    # エラータイプと重要度のマッピング
    ERROR_SEVERITY_MAP = {
        ConfigurationError: ErrorSeverity.CRITICAL,
        FileOperationError: ErrorSeverity.ERROR,
        DMMAPIError: ErrorSeverity.ERROR,
        WordPressAPIError: ErrorSeverity.ERROR,
        GeminiAPIError: ErrorSeverity.ERROR,
        ConnectionError: ErrorSeverity.ERROR,
        TimeoutError: ErrorSeverity.WARNING,
        ValueError: ErrorSeverity.WARNING,
        KeyError: ErrorSeverity.WARNING,
    }
    
    # エラータイプとカテゴリのマッピング
    ERROR_CATEGORY_MAP = {
        ConfigurationError: ErrorCategory.CONFIGURATION_ERROR,
        FileOperationError: ErrorCategory.FILE_ERROR,
        DMMAPIError: ErrorCategory.API_ERROR,
        WordPressAPIError: ErrorCategory.API_ERROR,
        GeminiAPIError: ErrorCategory.API_ERROR,
        ConnectionError: ErrorCategory.NETWORK_ERROR,
        TimeoutError: ErrorCategory.NETWORK_ERROR,
        ValueError: ErrorCategory.VALIDATION_ERROR,
        KeyError: ErrorCategory.VALIDATION_ERROR,
    }
    
    @classmethod
    def handle_error(
        cls,
        error: Exception,
        context: ErrorContext,
        reraise_critical: bool = True
    ) -> bool:
        """
        エラーを適切に処理
        
        Args:
            error: 発生したエラー
            context: エラーコンテキスト
            reraise_critical: 致命的エラーを再発生させるか
            
        Returns:
            処理を続行すべきかどうか
        """
        error_type = type(error)
        severity = cls.ERROR_SEVERITY_MAP.get(error_type, ErrorSeverity.ERROR)
        category = cls.ERROR_CATEGORY_MAP.get(error_type, ErrorCategory.SYSTEM_ERROR)
        
        # ログ出力
        cls._log_error(error, context, severity, category)
        
        # 致命的エラーの場合
        if severity == ErrorSeverity.CRITICAL:
            if reraise_critical:
                raise error
            return False
        
        # 続行可能なエラー
        return True
    
    @classmethod
    def _log_error(
        cls,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity,
        category: ErrorCategory
    ):
        """エラーログの出力"""
        log_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'category': category.value,
            'context': context.to_dict()
        }
        
        # 重要度に応じたログレベル
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(
                f"CRITICAL ERROR in {context.operation}: {error}",
                extra=log_data,
                exc_info=True
            )
        elif severity == ErrorSeverity.ERROR:
            logger.error(
                f"ERROR in {context.operation}: {error}",
                extra=log_data
            )
        elif severity == ErrorSeverity.WARNING:
            logger.warning(
                f"WARNING in {context.operation}: {error}",
                extra=log_data
            )
        else:
            logger.info(
                f"INFO in {context.operation}: {error}",
                extra=log_data
            )
    
    @classmethod
    def create_safe_wrapper(
        cls,
        operation_name: str,
        default_return: Any = None,
        reraise_critical: bool = True
    ) -> Callable:
        """
        安全な関数ラッパーを作成
        
        Args:
            operation_name: 操作名
            default_return: エラー時のデフォルト戻り値
            reraise_critical: 致命的エラーを再発生させるか
            
        Returns:
            デコレータ関数
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context = ErrorContext(
                        operation=f"{operation_name}.{func.__name__}",
                        additional_info={
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                    )
                    
                    should_continue = cls.handle_error(
                        e, context, reraise_critical
                    )
                    
                    if not should_continue:
                        raise
                    
                    return default_return
            return wrapper
        return decorator


# 便利なデコレータ関数
def safe_api_call(operation_name: str, default_return: Any = None):
    """API呼び出し用の安全なデコレータ"""
    return UnifiedErrorHandler.create_safe_wrapper(
        operation_name=f"api.{operation_name}",
        default_return=default_return,
        reraise_critical=False
    )


def safe_file_operation(operation_name: str, default_return: Any = None):
    """ファイル操作用の安全なデコレータ"""
    return UnifiedErrorHandler.create_safe_wrapper(
        operation_name=f"file.{operation_name}",
        default_return=default_return,
        reraise_critical=False
    )


def critical_operation(operation_name: str):
    """致命的操作用のデコレータ（エラー時は必ず再発生）"""
    return UnifiedErrorHandler.create_safe_wrapper(
        operation_name=f"critical.{operation_name}",
        reraise_critical=True
    )


class ErrorRecovery:
    """エラー回復のためのユーティリティ"""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ) -> Any:
        """
        指数バックオフでリトライ実行
        
        Args:
            func: 実行する関数
            max_retries: 最大リトライ回数
            base_delay: 基本遅延時間（秒）
            max_delay: 最大遅延時間（秒）
            exponential_base: 指数の底
            
        Returns:
            関数の戻り値
        """
        import time
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                # 遅延時間の計算
                delay = min(
                    base_delay * (exponential_base ** attempt),
                    max_delay
                )
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries + 1} "
                    f"after {delay:.1f}s delay. Error: {e}"
                )
                
                time.sleep(delay)
        
        # 全てのリトライが失敗した場合
        raise last_exception