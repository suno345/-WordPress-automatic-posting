"""
セキュア設定管理システム - 環境変数とデータ暗号化によるセキュリティ強化
"""
import os
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SecureConfigManager:
    """セキュア設定管理システム"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        セキュア設定管理の初期化
        
        Args:
            config_file: 設定ファイルパス（環境変数が優先）
        """
        self.config_file = config_file or self._get_config_file_path()
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # 設定データ
        self._config_data = {}
        self._load_configuration()
        
        logger.info("セキュア設定管理システム初期化完了")
    
    def _get_config_file_path(self) -> str:
        """設定ファイルパスを取得"""
        # 環境変数から設定ファイルパスを取得
        config_path = os.getenv('BLOG_AUTOMATION_CONFIG', 'config/config.vps.ini')
        
        # VPSモードの場合は専用設定を使用
        if os.getenv('VPS_MODE', '').lower() == 'true':
            config_path = 'config/config.vps.ini'
            
        return config_path
    
    def _get_or_create_encryption_key(self) -> bytes:
        """暗号化キーを取得または作成"""
        # 環境変数から暗号化キーを取得
        env_key = os.getenv('BLOG_AUTOMATION_ENCRYPTION_KEY')
        
        if env_key:
            try:
                return base64.urlsafe_b64decode(env_key.encode())
            except Exception as e:
                logger.warning(f"環境変数の暗号化キーが無効: {e}")
        
        # キーファイルから取得を試行
        key_file = Path('.encryption_key')
        if key_file.exists():
            try:
                return key_file.read_bytes()
            except Exception as e:
                logger.warning(f"キーファイル読み込みエラー: {e}")
        
        # 新しいキーを生成
        logger.info("新しい暗号化キーを生成中...")
        key = Fernet.generate_key()
        
        # キーファイルに保存（権限を制限）
        try:
            key_file.write_bytes(key)
            os.chmod(key_file, 0o600)  # 所有者のみ読み書き可能
            logger.info("暗号化キーをファイルに保存しました")
        except Exception as e:
            logger.error(f"暗号化キー保存エラー: {e}")
        
        return key
    
    def _load_configuration(self):
        """設定を読み込み"""
        # 環境変数からの設定読み込み
        self._load_from_environment()
        
        # 設定ファイルからの読み込み（環境変数がない場合のフォールバック）
        if Path(self.config_file).exists():
            self._load_from_file()
        
        # 必須設定の検証
        self._validate_required_settings()
    
    def _load_from_environment(self):
        """環境変数から設定を読み込み"""
        logger.info("環境変数から設定を読み込み中...")
        
        # WordPress 設定
        self._config_data['wordpress'] = {
            'url': self._get_secure_env('WORDPRESS_URL', 'https://mania-wiki.com'),
            'username': self._get_secure_env('WORDPRESS_USERNAME', 'automatic'),
            'password': self._get_secure_env('WORDPRESS_PASSWORD', required=True)
        }
        
        # DMM API 設定
        self._config_data['dmm_api'] = {
            'api_id': self._get_secure_env('DMM_API_ID', required=True),
            'affiliate_id': self._get_secure_env('DMM_AFFILIATE_ID', required=True)
        }
        
        # Gemini API 設定
        self._config_data['gemini'] = {
            'api_key': self._get_secure_env('GEMINI_API_KEY', required=True)
        }
        
        # システム設定
        self._config_data['system'] = {
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_posts_per_run': int(os.getenv('MAX_POSTS_PER_RUN', '1')),
            'search_limit': int(os.getenv('SEARCH_LIMIT', '200')),
            'request_delay': float(os.getenv('REQUEST_DELAY', '3.0')),
            'vps_mode': os.getenv('VPS_MODE', 'false').lower() == 'true'
        }
        
        # VPS最適化設定
        if self._config_data['system']['vps_mode']:
            self._config_data['vps_optimization'] = {
                'cache_ttl': int(os.getenv('CACHE_TTL', '3600')),
                'max_workers': int(os.getenv('MAX_WORKERS', '2')),
                'memory_limit_mb': int(os.getenv('MEMORY_LIMIT_MB', '256')),
                'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
                'execution_timeout': int(os.getenv('EXECUTION_TIMEOUT', '300'))
            }
    
    def _get_secure_env(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """セキュアな環境変数取得"""
        value = os.getenv(key, default)
        
        if required and not value:
            raise ValueError(f"必須環境変数が設定されていません: {key}")
        
        # 機密情報の場合は暗号化されている可能性をチェック
        if key.endswith(('_PASSWORD', '_KEY', '_SECRET')) and value:
            try:
                # Base64エンコードされた暗号化データの復号化を試行
                if value.startswith('gAAAAAB'):  # Fernetの暗号化データの識別子
                    decrypted = self.fernet.decrypt(value.encode()).decode()
                    logger.debug(f"環境変数 {key} を復号化しました")
                    return decrypted
            except Exception:
                # 復号化に失敗した場合は平文として扱う
                pass
        
        return value or ''
    
    def _load_from_file(self):
        """設定ファイルから読み込み（フォールバック）"""
        logger.info(f"設定ファイルから読み込み中: {self.config_file}")
        
        try:
            # 既存の設定ファイル読み込みロジックを流用
            # ただし、環境変数が設定されている場合は上書きしない
            pass  # 実装は既存のConfigManagerから移植
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
    
    def _validate_required_settings(self):
        """必須設定の検証"""
        required_settings = [
            ('wordpress', 'url'),
            ('wordpress', 'username'),
            ('wordpress', 'password'),
            ('dmm_api', 'api_id'),
            ('dmm_api', 'affiliate_id'),
            ('gemini', 'api_key')
        ]
        
        missing_settings = []
        for section, key in required_settings:
            if not self.get(section, key):
                missing_settings.append(f"{section}.{key}")
        
        if missing_settings:
            raise ValueError(f"必須設定が不足しています: {', '.join(missing_settings)}")
        
        logger.info("必須設定の検証完了")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        try:
            return self._config_data.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"設定取得エラー ({section}.{key}): {e}")
            return default
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """機密データを暗号化"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"データ暗号化エラー: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """暗号化データを復号化"""
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"データ復号化エラー: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """設定サマリーを取得（機密情報をマスク）"""
        summary = {}
        
        for section, config in self._config_data.items():
            summary[section] = {}
            for key, value in config.items():
                # 機密情報をマスク
                if any(sensitive in key.lower() for sensitive in ['password', 'key', 'secret', 'token']):
                    if value:
                        summary[section][key] = f"{'*' * min(len(str(value)), 8)}"
                        if len(str(value)) > 4:
                            summary[section][key] += str(value)[-4:]
                    else:
                        summary[section][key] = "未設定"
                else:
                    summary[section][key] = value
        
        return summary
    
    @property
    def wordpress(self) -> 'WordPressConfig':
        """WordPress設定を取得"""
        return WordPressConfig(
            url=self.get('wordpress', 'url'),
            username=self.get('wordpress', 'username'),
            password=self.get('wordpress', 'password')
        )
    
    @property
    def dmm_api(self) -> 'DMMAPIConfig':
        """DMM API設定を取得"""
        return DMMAPIConfig(
            api_id=self.get('dmm_api', 'api_id'),
            affiliate_id=self.get('dmm_api', 'affiliate_id')
        )
    
    @property
    def gemini(self) -> 'GeminiConfig':
        """Gemini設定を取得"""
        return GeminiConfig(
            api_key=self.get('gemini', 'api_key')
        )
    
    @property
    def system(self) -> 'SystemConfig':
        """システム設定を取得"""
        return SystemConfig(
            log_level=self.get('system', 'log_level'),
            max_posts_per_run=self.get('system', 'max_posts_per_run'),
            search_limit=self.get('system', 'search_limit'),
            request_delay=self.get('system', 'request_delay'),
            vps_mode=self.get('system', 'vps_mode')
        )


class WordPressConfig:
    """WordPress設定クラス"""
    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password


class DMMAPIConfig:
    """DMM API設定クラス"""
    def __init__(self, api_id: str, affiliate_id: str):
        self.api_id = api_id
        self.affiliate_id = affiliate_id


class GeminiConfig:
    """Gemini設定クラス"""
    def __init__(self, api_key: str):
        self.api_key = api_key


class SystemConfig:
    """システム設定クラス"""
    def __init__(self, log_level: str, max_posts_per_run: int, search_limit: int, 
                 request_delay: float, vps_mode: bool):
        self.log_level = log_level
        self.max_posts_per_run = max_posts_per_run
        self.search_limit = search_limit
        self.request_delay = request_delay
        self.vps_mode = vps_mode