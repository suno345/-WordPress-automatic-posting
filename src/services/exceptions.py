"""
カスタム例外クラス定義
"""


class AutoPostingError(Exception):
    """自動投稿システムの基底例外クラス"""
    pass


class ConfigurationError(AutoPostingError):
    """設定関連のエラー"""
    pass


class APIError(AutoPostingError):
    """API関連のエラー"""
    pass


class DMMAPIError(APIError):
    """DMM API関連のエラー"""
    pass


class WordPressAPIError(APIError):
    """WordPress API関連のエラー"""
    pass


class GeminiAPIError(APIError):
    """Gemini API関連のエラー"""
    pass


class DataProcessingError(AutoPostingError):
    """データ処理関連のエラー"""
    pass


class FileOperationError(AutoPostingError):
    """ファイル操作関連のエラー"""
    pass