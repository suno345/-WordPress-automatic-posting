"""
簡素化設定管理システム - .env直接読み込み
config.iniを使わずに環境変数のみで動作
"""
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleConfigManager:
    """簡素化設定管理システム - .env直接読み込み"""
    
    def __init__(self, env_file: str = ".env"):
        """
        簡素化設定管理の初期化
        
        Args:
            env_file: .envファイルパス
        """
        self.env_file = env_file
        self._config_data = {}
        self._load_env_file()
        self._setup_configuration()
        
        logger.info("簡素化設定管理システム初期化完了")
    
    def _load_env_file(self):
        """手動で.envファイルを読み込み"""
        env_path = Path(self.env_file)
        if not env_path.exists():
            logger.warning(f".envファイルが見つかりません: {self.env_file}")
            return
        
        try:
            with env_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # 既存の環境変数を上書きしない
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = value.strip()
            
            logger.info(f".envファイル読み込み完了: {self.env_file}")
        except Exception as e:
            logger.error(f".envファイル読み込みエラー: {e}")
    
    def _setup_configuration(self):
        """環境変数から設定を構築"""
        # WordPress 設定
        self._config_data['wordpress'] = {
            'url': os.getenv('WORDPRESS_URL', 'https://mania-wiki.com'),
            'username': os.getenv('WORDPRESS_USERNAME', 'automatic'),
            'password': os.getenv('WORDPRESS_PASSWORD', '')
        }
        
        # DMM API 設定
        self._config_data['dmm_api'] = {
            'api_id': os.getenv('DMM_API_ID', ''),
            'affiliate_id': os.getenv('DMM_AFFILIATE_ID', '')
        }
        
        # Gemini API 設定
        self._config_data['gemini'] = {
            'api_key': os.getenv('GEMINI_API_KEY', '')
        }
        
        # システム設定
        self._config_data['system'] = {
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_posts_per_run': int(os.getenv('MAX_POSTS_PER_RUN', '1')),
            'search_limit': int(os.getenv('SEARCH_LIMIT', '100')),  # DMM API制限に合わせて100に修正
            'request_delay': float(os.getenv('REQUEST_DELAY', '3.0')),
            'post_interval': float(os.getenv('POST_INTERVAL', '900.0')),  # 15分間隔（秒）
            'vps_mode': os.getenv('VPS_MODE', 'false').lower() == 'true'
        }
        
        # VPS最適化設定（VPSモード時のみ）
        if self._config_data['system']['vps_mode']:
            self._config_data['vps_optimization'] = {
                'cache_ttl': int(os.getenv('CACHE_TTL', '3600')),
                'max_workers': int(os.getenv('MAX_WORKERS', '2')),
                'memory_limit_mb': int(os.getenv('MEMORY_LIMIT_MB', '256')),
                'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
                'execution_timeout': int(os.getenv('EXECUTION_TIMEOUT', '300'))
            }
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        try:
            return self._config_data.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"設定取得エラー ({section}.{key}): {e}")
            return default
    
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
            post_interval=self.get('system', 'post_interval'),
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
                 request_delay: float, post_interval: float, vps_mode: bool):
        self.log_level = log_level
        self.max_posts_per_run = max_posts_per_run
        self.search_limit = search_limit
        self.request_delay = request_delay
        self.post_interval = post_interval
        self.vps_mode = vps_mode