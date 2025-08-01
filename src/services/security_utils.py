"""
セキュリティ関連のユーティリティ
"""
import re
from typing import Any, Dict, Union


class SecretSanitizer:
    """機密情報の安全な取り扱いのためのユーティリティ"""
    
    # 機密情報のキーパターン
    SENSITIVE_KEYS = {
        'password', 'pass', 'pwd', 'secret', 'key', 'token', 
        'api_key', 'api_id', 'client_secret', 'private_key',
        'auth', 'authentication', 'authorization', 'credential'
    }
    
    # 機密情報の値パターン
    SENSITIVE_PATTERNS = [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI API key pattern
        r'[A-Za-z0-9+/]{32,}={0,2}',  # Base64 encoded secrets
        r'[a-fA-F0-9]{32,}',  # MD5/SHA hashes
    ]
    
    @classmethod
    def mask_api_key(cls, api_key: str, show_chars: int = 4) -> str:
        """
        APIキーを安全にマスク
        
        Args:
            api_key: マスクするAPIキー
            show_chars: 末尾に表示する文字数
            
        Returns:
            マスクされたAPIキー
        """
        if not api_key or len(api_key) <= show_chars:
            return '*' * 8
        
        return '*' * (len(api_key) - show_chars) + api_key[-show_chars:]
    
    @classmethod
    def mask_password(cls, password: str) -> str:
        """
        パスワードを完全マスク
        
        Args:
            password: マスクするパスワード
            
        Returns:
            マスクされたパスワード
        """
        return '*' * min(8, len(password)) if password else ''
    
    @classmethod
    def sanitize_config_for_logging(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定情報をログ出力用に安全化
        
        Args:
            config: 設定辞書
            
        Returns:
            安全化された設定辞書
        """
        sanitized = {}
        
        for key, value in config.items():
            key_lower = key.lower()
            
            # 機密情報キーの判定
            if any(sensitive in key_lower for sensitive in cls.SENSITIVE_KEYS):
                if 'password' in key_lower or 'secret' in key_lower:
                    sanitized[key] = cls.mask_password(str(value))
                else:
                    sanitized[key] = cls.mask_api_key(str(value))
            
            # 辞書の場合は再帰的に処理
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_config_for_logging(value)
            
            # リストの場合
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_config_for_logging(item) if isinstance(item, dict) else item
                    for item in value
                ]
            
            # 値のパターンチェック
            elif isinstance(value, str) and cls._is_sensitive_value(value):
                sanitized[key] = cls.mask_api_key(value)
            
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def _is_sensitive_value(cls, value: str) -> bool:
        """
        値が機密情報パターンに一致するかチェック
        
        Args:
            value: チェックする値
            
        Returns:
            機密情報の可能性があるかどうか
        """
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.match(pattern, value):
                return True
        return False
    
    @classmethod
    def safe_str_representation(cls, obj: Any, max_length: int = 200) -> str:
        """
        オブジェクトの安全な文字列表現を生成
        
        Args:
            obj: 文字列化するオブジェクト
            max_length: 最大文字数
            
        Returns:
            安全化された文字列表現
        """
        try:
            if isinstance(obj, dict):
                sanitized = cls.sanitize_config_for_logging(obj)
                str_repr = str(sanitized)
            else:
                str_repr = str(obj)
            
            # 長すぎる場合は切り詰める
            if len(str_repr) > max_length:
                str_repr = str_repr[:max_length] + '...'
            
            return str_repr
            
        except Exception:
            return f"<{type(obj).__name__} object>"


def mask_sensitive_info(data: Union[str, Dict, Any]) -> Union[str, Dict, Any]:
    """
    機密情報をマスクする便利関数
    
    Args:
        data: マスクするデータ
        
    Returns:
        マスクされたデータ
    """
    if isinstance(data, dict):
        return SecretSanitizer.sanitize_config_for_logging(data)
    elif isinstance(data, str):
        return SecretSanitizer.safe_str_representation(data)
    else:
        return SecretSanitizer.safe_str_representation(data)