"""
共通ユーティリティ関数
"""
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union


def safe_get_nested(data: Dict[str, Any], *keys, default=None) -> Any:
    """
    安全なネストされた辞書アクセス
    
    Args:
        data: 辞書データ
        *keys: アクセスするキーのパス
        default: デフォルト値
    
    Returns:
        取得した値またはデフォルト値
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def setup_logging(log_level: str = 'INFO', log_dir: str = 'logs') -> logging.Logger:
    """
    ログ設定のセットアップ
    
    Args:
        log_level: ログレベル
        log_dir: ログディレクトリ
    
    Returns:
        設定済みのロガー
    """
    from .constants import Constants
    
    # ログディレクトリの作成
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイル名（日付付き）
    log_file = os.path.join(log_dir, f'auto_post_{datetime.now().strftime(Constants.LOG_DATE_FORMAT)}.log')
    
    # ログ設定
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=Constants.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def validate_required_config(config, section: str, required_keys: list) -> None:
    """
    設定ファイルの必須項目をバリデーション
    
    Args:
        config: ConfigParserオブジェクト
        section: セクション名
        required_keys: 必須キーのリスト
    
    Raises:
        ValueError: 必須項目が不足している場合
    """
    if section not in config:
        raise ValueError(f"設定セクション '{section}' が見つかりません")
    
    missing_keys = []
    for key in required_keys:
        if key not in config[section] or not config[section][key].strip():
            missing_keys.append(key)
    
    if missing_keys:
        raise ValueError(f"設定項目が不足しています [{section}]: {', '.join(missing_keys)}")


def normalize_string(text: str) -> str:
    """
    文字列の正規化（タグやカテゴリ名用）
    
    Args:
        text: 正規化する文字列
    
    Returns:
        正規化された文字列
    """
    if not text:
        return ""
    
    # 前後の空白を削除し、内部の連続空白を単一空白に変換
    return ' '.join(text.strip().split())


def create_tag_slug(tag_name: str) -> str:
    """
    タグ名からスラッグを生成
    
    Args:
        tag_name: タグ名
    
    Returns:
        スラッグ文字列
    """
    import re
    
    # 日本語を含む文字列をそのまま使用し、スペースをハイフンに変換
    slug = normalize_string(tag_name)
    slug = re.sub(r'\s+', '-', slug)
    slug = slug.lower()
    
    return slug


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """
    例外発生時のリトライデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        delay: リトライ間隔（秒）
    """
    import time
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.getLogger(__name__).warning(
                            f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logging.getLogger(__name__).error(
                            f"All {max_retries + 1} attempts failed"
                        )
                        break
            
            raise last_exception
        
        return wrapper
    
    return decorator


def format_file_size(size_bytes: int) -> str:
    """
    ファイルサイズを人間が読みやすい形式にフォーマット
    
    Args:
        size_bytes: バイト数
    
    Returns:
        フォーマットされたサイズ文字列
    """
    if size_bytes == 0:
        return "0B"
    
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    return f"{size:.1f}{units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """
    ファイル名として安全な文字列に変換
    
    Args:
        filename: 元のファイル名
    
    Returns:
        サニタイズされたファイル名
    """
    import re
    
    # 危険な文字を削除・置換
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    
    # 長すぎる場合は切り詰め
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized