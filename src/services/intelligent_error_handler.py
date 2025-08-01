"""
インテリジェントエラーハンドリングシステム

API特化型のエラーパターン認識と適応的リトライ戦略
"""

import time
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Type, Union
from enum import Enum
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """エラーカテゴリの定義"""
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    SAFETY_FILTER = "safety_filter"
    MODEL_OVERLOAD = "model_overload"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class APIErrorPattern:
    """APIエラーパターンの定義"""
    
    def __init__(self, category: ErrorCategory, codes: List[int] = None, 
                 exception_types: List[Type] = None, base_delay: int = 5, 
                 max_retries: int = 3, adaptive_delay: bool = True):
        self.category = category
        self.codes = codes or []
        self.exception_types = exception_types or []
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.adaptive_delay = adaptive_delay


class IntelligentErrorHandler:
    """API特化型インテリジェントエラーハンドラー"""
    
    # APIごとのエラーパターンマッピング
    API_ERROR_PATTERNS = {
        'dmm_api': {
            ErrorCategory.RATE_LIMIT: APIErrorPattern(
                ErrorCategory.RATE_LIMIT,
                codes=[429],
                base_delay=60,
                max_retries=5
            ),
            ErrorCategory.SERVER_ERROR: APIErrorPattern(
                ErrorCategory.SERVER_ERROR,
                codes=[500, 502, 503, 504],
                base_delay=5,
                max_retries=3
            ),
            ErrorCategory.TIMEOUT: APIErrorPattern(
                ErrorCategory.TIMEOUT,
                exception_types=[Timeout, ConnectionError],
                base_delay=2,
                max_retries=4
            ),
            ErrorCategory.NETWORK_ERROR: APIErrorPattern(
                ErrorCategory.NETWORK_ERROR,
                exception_types=[ConnectionError],
                base_delay=3,
                max_retries=3
            )
        },
        'wordpress_api': {
            ErrorCategory.RATE_LIMIT: APIErrorPattern(
                ErrorCategory.RATE_LIMIT,
                codes=[429],
                base_delay=30,
                max_retries=3
            ),
            ErrorCategory.AUTH_ERROR: APIErrorPattern(
                ErrorCategory.AUTH_ERROR,
                codes=[401, 403],
                base_delay=0,
                max_retries=1,
                adaptive_delay=False
            ),
            ErrorCategory.SERVER_ERROR: APIErrorPattern(
                ErrorCategory.SERVER_ERROR,
                codes=[500, 502, 503, 504],
                base_delay=10,
                max_retries=2
            )
        },
        'gemini_api': {
            ErrorCategory.QUOTA_EXCEEDED: APIErrorPattern(
                ErrorCategory.QUOTA_EXCEEDED,
                codes=[429],
                base_delay=120,
                max_retries=2
            ),
            ErrorCategory.SAFETY_FILTER: APIErrorPattern(
                ErrorCategory.SAFETY_FILTER,
                codes=[400],
                base_delay=0,
                max_retries=0,
                adaptive_delay=False
            ),
            ErrorCategory.MODEL_OVERLOAD: APIErrorPattern(
                ErrorCategory.MODEL_OVERLOAD,
                codes=[503],
                base_delay=30,
                max_retries=3
            )
        }
    }
    
    def __init__(self):
        """初期化"""
        self.api_load_history: Dict[str, List[Tuple[datetime, bool]]] = {}
        self.global_retry_counts: Dict[str, int] = {}
    
    def handle_error(self, error: Exception, api_name: str, operation: str,
                    attempt: int = 1) -> Tuple[bool, int]:
        """
        APIエラーをインテリジェントに処理
        
        Args:
            error: 発生したエラー
            api_name: API名 ('dmm_api', 'wordpress_api', 'gemini_api')
            operation: 操作名（ログ用）
            attempt: 試行回数
        
        Returns:
            (should_retry, delay_seconds)
        """
        try:
            error_pattern = self._identify_error_pattern(error, api_name)
            
            if not error_pattern:
                logger.warning(f"Unknown error pattern for {api_name}.{operation}: {error}")
                return False, 0
            
            # 最大リトライ回数チェック
            if attempt > error_pattern.max_retries:
                logger.error(f"Max retries exceeded for {api_name}.{operation} (attempt {attempt})")
                return False, 0
            
            # 遅延時間計算
            if error_pattern.adaptive_delay:
                delay = self._calculate_adaptive_delay(
                    error_pattern.base_delay, attempt, api_name, operation
                )
            else:
                delay = error_pattern.base_delay
            
            # ログ出力
            self._log_retry_info(error, api_name, operation, attempt, 
                               error_pattern.max_retries, delay)
            
            # API負荷履歴に記録
            self._record_api_failure(api_name)
            
            return True, delay
            
        except Exception as e:
            logger.error(f"Error in intelligent error handler: {e}")
            # フォールバック: 基本的なリトライ
            return attempt <= 3, min(5 * attempt, 30)
    
    def _identify_error_pattern(self, error: Exception, api_name: str) -> Optional[APIErrorPattern]:
        """エラーパターンを特定"""
        api_patterns = self.API_ERROR_PATTERNS.get(api_name, {})
        
        for category, pattern in api_patterns.items():
            # HTTPステータスコードによる判定
            if hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                if status_code in pattern.codes:
                    return pattern
            
            # 例外タイプによる判定
            if any(isinstance(error, exc_type) for exc_type in pattern.exception_types):
                return pattern
            
            # HTTPError の詳細チェック
            if isinstance(error, HTTPError) and hasattr(error, 'response'):
                status_code = error.response.status_code
                if status_code in pattern.codes:
                    return pattern
        
        return None
    
    def _calculate_adaptive_delay(self, base_delay: int, attempt: int, 
                                api_name: str, operation: str) -> int:
        """現在の負荷状況に基づく適応的遅延計算"""
        # 基本指数バックオフ
        exponential_delay = base_delay * (2 ** (attempt - 1))
        
        # API負荷を考慮した調整
        load_multiplier = self._get_api_load_multiplier(api_name)
        
        # 時間帯による調整（日本時間の深夜は負荷が低い）
        time_multiplier = self._get_time_based_multiplier()
        
        # ジッター追加（同時リクエストの分散）
        jitter = random.uniform(0.8, 1.2)
        
        # 最終遅延時間の計算
        final_delay = int(
            exponential_delay * load_multiplier * time_multiplier * jitter
        )
        
        # 上限値の適用
        max_delay = 300  # 5分
        return min(final_delay, max_delay)
    
    def _get_api_load_multiplier(self, api_name: str) -> float:
        """API負荷に基づく倍率を取得"""
        if api_name not in self.api_load_history:
            return 1.0
        
        # 過去1時間の失敗率を計算
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_attempts = [
            (timestamp, success) for timestamp, success in self.api_load_history[api_name]
            if timestamp > one_hour_ago
        ]
        
        if not recent_attempts:
            return 1.0
        
        failure_rate = 1 - (sum(success for _, success in recent_attempts) / len(recent_attempts))
        
        # 失敗率に基づく倍率（0.0-1.0 → 1.0-2.0）
        load_multiplier = 1.0 + failure_rate
        
        logger.debug(f"API load multiplier for {api_name}: {load_multiplier:.2f} (failure rate: {failure_rate:.2f})")
        return load_multiplier
    
    def _get_time_based_multiplier(self) -> float:
        """時間帯に基づく倍率を取得"""
        current_hour = datetime.now().hour
        
        # 日本時間での負荷パターンを想定
        # 深夜(2-6時): 0.7倍、早朝(6-9時): 0.9倍、日中(9-18時): 1.2倍、夜(18-2時): 1.0倍
        if 2 <= current_hour < 6:
            return 0.7  # 深夜は負荷が低い
        elif 6 <= current_hour < 9:
            return 0.9  # 早朝
        elif 9 <= current_hour < 18:
            return 1.2  # 日中は負荷が高い
        else:
            return 1.0  # 夜間
    
    def _record_api_failure(self, api_name: str) -> None:
        """API失敗を履歴に記録"""
        if api_name not in self.api_load_history:
            self.api_load_history[api_name] = []
        
        current_time = datetime.now()
        self.api_load_history[api_name].append((current_time, False))
        
        # 古い履歴を削除（24時間以内のみ保持）
        cutoff_time = current_time - timedelta(hours=24)
        self.api_load_history[api_name] = [
            (timestamp, success) for timestamp, success in self.api_load_history[api_name]
            if timestamp > cutoff_time
        ]
    
    def record_api_success(self, api_name: str) -> None:
        """API成功を履歴に記録"""
        if api_name not in self.api_load_history:
            self.api_load_history[api_name] = []
        
        current_time = datetime.now()
        self.api_load_history[api_name].append((current_time, True))
        
        # 古い履歴を削除
        cutoff_time = current_time - timedelta(hours=24)
        self.api_load_history[api_name] = [
            (timestamp, success) for timestamp, success in self.api_load_history[api_name]
            if timestamp > cutoff_time
        ]
    
    def _log_retry_info(self, error: Exception, api_name: str, operation: str,
                       attempt: int, max_retries: int, delay: int) -> None:
        """リトライ情報をログ出力"""
        error_type = type(error).__name__
        error_msg = str(error)
        
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
            error_msg = f"HTTP {status_code}: {error_msg}"
        
        logger.warning(
            f"Retrying {api_name}.{operation} in {delay}s "
            f"(attempt {attempt}/{max_retries}) - Error: {error_type}: {error_msg}"
        )
    
    def get_stats(self) -> Dict[str, Dict]:
        """エラーハンドリング統計を取得"""
        stats = {}
        
        for api_name, history in self.api_load_history.items():
            if not history:
                continue
            
            # 過去24時間の統計
            total_attempts = len(history)
            successful_attempts = sum(1 for _, success in history if success)
            failed_attempts = total_attempts - successful_attempts
            
            success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0
            
            stats[api_name] = {
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'failed_attempts': failed_attempts,
                'success_rate': success_rate,
                'current_load_multiplier': self._get_api_load_multiplier(api_name)
            }
        
        return stats


# グローバルエラーハンドラーインスタンス
_global_error_handler: Optional[IntelligentErrorHandler] = None


def get_error_handler() -> IntelligentErrorHandler:
    """グローバルエラーハンドラーインスタンスを取得"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = IntelligentErrorHandler()
    return _global_error_handler


def handle_api_error(error: Exception, api_name: str, operation: str,
                    attempt: int = 1) -> Tuple[bool, int]:
    """
    APIエラーを処理（グローバル関数）
    
    Args:
        error: 発生したエラー
        api_name: API名
        operation: 操作名
        attempt: 試行回数
    
    Returns:
        (should_retry, delay_seconds)
    """
    return get_error_handler().handle_error(error, api_name, operation, attempt)


def record_api_success(api_name: str) -> None:
    """API成功を記録（グローバル関数）"""
    get_error_handler().record_api_success(api_name)


def with_intelligent_retry(api_name: str, operation: str, max_attempts: int = None):
    """
    インテリジェントリトライデコレータ
    
    Args:
        api_name: API名
        operation: 操作名
        max_attempts: 最大試行回数（Noneの場合はエラーパターンに従う）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 1
            last_error = None
            
            while True:
                try:
                    result = func(*args, **kwargs)
                    # 成功時の記録
                    record_api_success(api_name)
                    return result
                    
                except Exception as error:
                    last_error = error
                    
                    # 最大試行回数チェック（カスタム制限）
                    if max_attempts and attempt >= max_attempts:
                        logger.error(f"Custom max attempts ({max_attempts}) reached for {api_name}.{operation}")
                        raise error
                    
                    # インテリジェントエラーハンドリング
                    should_retry, delay = handle_api_error(error, api_name, operation, attempt)
                    
                    if not should_retry:
                        raise error
                    
                    # 遅延実行
                    if delay > 0:
                        time.sleep(delay)
                    
                    attempt += 1
            
            # このコードには到達しないはずだが、安全のため
            if last_error:
                raise last_error
        
        return wrapper
    return decorator