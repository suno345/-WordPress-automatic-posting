"""
定数定義モジュール
"""
from typing import Final


class Constants:
    """システム定数定義"""
    
    # API関連
    MAX_SAMPLE_IMAGES: Final[int] = 5
    REQUEST_DELAY: Final[int] = 2
    API_TIMEOUT: Final[int] = 30
    MAX_RETRIES: Final[int] = 3
    
    # 投稿関連
    MAX_POSTS_PER_RUN: Final[int] = 1
    SEARCH_LIMIT: Final[int] = 100
    POST_INTERVAL_MINUTES: Final[int] = 15
    DEFAULT_TARGET_LENGTH: Final[int] = 180
    
    # ファイルパス
    POSTED_WORKS_FILE: Final[str] = 'data/posted_works.json'
    H2_PATTERNS_DIR: Final[str] = 'H2見出し'
    
    # WordPress関連
    WP_API_VERSION: Final[str] = 'wp/v2'
    
    # DMM API関連
    DMM_API_BASE_URL: Final[str] = 'https://api.dmm.com/affiliate/v3'
    DMM_SITE: Final[str] = 'FANZA'
    DMM_SERVICE: Final[str] = 'doujin'
    DMM_FLOOR: Final[str] = 'digital_doujin'
    DMM_GENRE_ID: Final[str] = '156022'  # 男性向けジャンルID
    
    # ログ関連
    LOG_DATE_FORMAT: Final[str] = '%Y%m%d'
    LOG_FORMAT: Final[str] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class ErrorMessages:
    """エラーメッセージ定数"""
    
    CONFIG_NOT_FOUND = "設定ファイルが見つかりません: {}"
    DMM_API_ID_NOT_SET = "DMM API ID が設定されていません。config.ini を確認してください。"
    DMM_API_ID_INVALID = "DMM API ID が無効です。DMM アフィリエイト（https://affiliate.dmm.com/)でAPI IDを取得してください。"
    NO_WORKS_FOUND = "作品が見つかりませんでした"
    NO_NEW_WORKS = "新しい作品はありません"
    GEMINI_MODEL_NOT_FOUND = "利用可能なGeminiモデルが見つかりません"
    H2_PATTERN_FILE_NOT_FOUND = "H2パターンファイルが見つかりません: {}"


class DefaultValues:
    """デフォルト値定義"""
    
    LOG_LEVEL = 'INFO'
    CIRCLE_NAME_UNKNOWN = '不明'
    PAGE_COUNT_UNKNOWN = '不明'
    DEFAULT_DESCRIPTION = 'この作品の詳細な紹介文は準備中です。'
    DEFAULT_CATEGORY = '同人'
    
    # フォールバック用H2見出し
    FALLBACK_H2_HEADINGS = [
        "作品の見どころ",
        "この作品のおすすめポイント", 
        "注目すべき魅力"
    ]