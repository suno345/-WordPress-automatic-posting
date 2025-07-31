"""
設定管理クラス
"""
import configparser
import os
from typing import Dict, Any
from dataclasses import dataclass

from .constants import Constants, ErrorMessages, DefaultValues
from .exceptions import ConfigurationError
from .utils import validate_required_config


@dataclass
class WordPressConfig:
    """WordPress設定"""
    url: str
    username: str
    password: str


@dataclass
class DMMAPIConfig:
    """DMM API設定"""
    api_id: str
    affiliate_id: str


@dataclass
class GeminiConfig:
    """Gemini API設定"""
    api_key: str


@dataclass
class SystemConfig:
    """システム設定"""
    log_level: str
    max_posts_per_run: int
    request_delay: int
    post_interval: int


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_file: str = 'config.ini'):
        """
        設定管理クラスの初期化
        
        Args:
            config_file: 設定ファイルのパス
        
        Raises:
            ConfigurationError: 設定ファイルに問題がある場合
        """
        self.config_file = config_file
        self._config = self._load_config()
        self._validate_config()
        
        # 各設定をパース
        self.wordpress = self._parse_wordpress_config()
        self.dmm_api = self._parse_dmm_api_config()
        self.gemini = self._parse_gemini_config()
        self.system = self._parse_system_config()
    
    def _load_config(self) -> configparser.ConfigParser:
        """設定ファイルを読み込む"""
        if not os.path.exists(self.config_file):
            raise ConfigurationError(ErrorMessages.CONFIG_NOT_FOUND.format(self.config_file))
        
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file, encoding='utf-8')
        except Exception as e:
            raise ConfigurationError(f"設定ファイルの読み込みに失敗しました: {e}")
        
        return config
    
    def _validate_config(self) -> None:
        """設定ファイルの必須項目をバリデーション"""
        try:
            validate_required_config(self._config, 'wordpress', ['url', 'username', 'password'])
            validate_required_config(self._config, 'dmm_api', ['api_id'])
            validate_required_config(self._config, 'gemini', ['api_key'])
        except ValueError as e:
            raise ConfigurationError(str(e))
    
    def _parse_wordpress_config(self) -> WordPressConfig:
        """WordPress設定をパース"""
        section = self._config['wordpress']
        return WordPressConfig(
            url=section['url'].strip(),
            username=section['username'].strip(),
            password=section['password'].strip()
        )
    
    def _parse_dmm_api_config(self) -> DMMAPIConfig:
        """DMM API設定をパース"""
        section = self._config['dmm_api']
        api_id = section['api_id'].strip()
        
        # API IDのバリデーション
        if api_id == 'your_dmm_api_id':
            raise ConfigurationError(ErrorMessages.DMM_API_ID_NOT_SET)
        
        return DMMAPIConfig(
            api_id=api_id,
            affiliate_id=section.get('affiliate_id', '').strip()
        )
    
    def _parse_gemini_config(self) -> GeminiConfig:
        """Gemini API設定をパース"""
        section = self._config['gemini']
        return GeminiConfig(
            api_key=section['api_key'].strip()
        )
    
    def _parse_system_config(self) -> SystemConfig:
        """システム設定をパース"""
        if 'settings' in self._config:
            section = self._config['settings']
            log_level = section.get('log_level', DefaultValues.LOG_LEVEL)
            max_posts_per_run = section.getint('max_posts_per_run', Constants.MAX_POSTS_PER_RUN)
            request_delay = section.getint('request_delay', Constants.REQUEST_DELAY)
            post_interval = section.getint('post_interval', Constants.POST_INTERVAL_MINUTES)
        else:
            log_level = DefaultValues.LOG_LEVEL
            max_posts_per_run = Constants.MAX_POSTS_PER_RUN
            request_delay = Constants.REQUEST_DELAY
            post_interval = Constants.POST_INTERVAL_MINUTES
        
        return SystemConfig(
            log_level=log_level,
            max_posts_per_run=max_posts_per_run,
            request_delay=request_delay,
            post_interval=post_interval
        )
    
    def get_config_summary(self) -> Dict[str, Any]:
        """設定の要約を取得（デバッグ用）"""
        return {
            'wordpress_url': self.wordpress.url,
            'wordpress_username': self.wordpress.username,
            'dmm_api_id': self.dmm_api.api_id[:10] + '...' if len(self.dmm_api.api_id) > 10 else self.dmm_api.api_id,
            'has_gemini_key': bool(self.gemini.api_key),
            'log_level': self.system.log_level,
            'max_posts_per_run': self.system.max_posts_per_run
        }