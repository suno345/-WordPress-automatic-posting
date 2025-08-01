#!/usr/bin/env python3
"""
自動投稿システムのテストモジュール
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.auto_posting_system import AutoPostingSystem
from src.services.exceptions import ConfigurationError, AutoPostingError


class TestAutoPostingSystem:
    """自動投稿システムのテストクラス"""

    @pytest.fixture
    def mock_config(self):
        """テスト用設定のモック"""
        config = MagicMock()
        config.system.log_level = 'INFO'
        config.system.request_delay = 1
        config.system.max_posts_per_run = 5
        config.system.post_interval = 60
        config.dmm_api.api_id = 'test_api_id'
        config.dmm_api.affiliate_id = 'test_affiliate_id'
        config.gemini.api_key = 'test_gemini_key'
        config.wordpress.url = 'https://test.example.com'
        config.wordpress.username = 'testuser'
        config.wordpress.password = 'testpass'
        config.get_config_summary.return_value = {
            'wordpress': {'url': 'https://test.example.com', 'username': 'testuser'},
            'dmm_api': {'configured': True},
            'gemini': {'api_key_configured': True},
            'system': {'max_posts_per_run': 5}
        }
        return config

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_init_success(self, mock_setup_logging, mock_config_manager, mock_config):
        """正常初期化テスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            assert system.skip_review_check is False
            assert system.verbose is False

    @patch('src.core.auto_posting_system.ConfigManager')
    def test_init_with_options(self, mock_config_manager, mock_config):
        """オプション付き初期化テスト"""
        mock_config_manager.return_value = mock_config

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock(),
            setup_logging=MagicMock()
        ):
            system = AutoPostingSystem(
                config_file='custom_config.ini',
                verbose=True,
                skip_review_check=True
            )
            assert system.skip_review_check is True
            assert system.verbose is True

    @patch('src.core.auto_posting_system.ConfigManager')
    def test_init_configuration_error(self, mock_config_manager):
        """設定エラー時の初期化テスト"""
        mock_config_manager.side_effect = Exception("Config error")

        with pytest.raises(ConfigurationError):
            AutoPostingSystem()

    def test_calculate_tomorrow(self):
        """明日の日付計算テスト"""
        with patch.multiple(
            'src.core.auto_posting_system',
            ConfigManager=MagicMock(),
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock(),
            setup_logging=MagicMock()
        ):
            system = AutoPostingSystem()
            
            # 現在時刻をモック
            test_now = datetime(2024, 1, 15, 14, 30, 45)
            with patch('src.core.auto_posting_system.datetime') as mock_datetime:
                mock_datetime.now.return_value = test_now
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                tomorrow = system._calculate_tomorrow()
                expected = datetime(2024, 1, 16, 0, 0, 0, 0)
                assert tomorrow == expected

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_fetch_works(self, mock_setup_logging, mock_config_manager, mock_config):
        """作品取得テスト"""
        mock_config_manager.return_value = mock_config
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        # モックデータ
        mock_api_items = [
            {'content_id': '1', 'title': 'Work 1'},
            {'content_id': '2', 'title': 'Work 2'}
        ]
        mock_work_data = [
            {'work_id': '1', 'title': 'Work 1'},
            {'work_id': '2', 'title': 'Work 2'}
        ]

        mock_dmm_client = MagicMock()
        mock_dmm_client.get_items.return_value = mock_api_items
        mock_dmm_client.convert_to_work_data.side_effect = mock_work_data

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=lambda **kwargs: mock_dmm_client,
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            works = system._fetch_works()
            
            assert len(works) == 2
            mock_dmm_client.get_items.assert_called_once_with(limit=50)

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_filter_unposted_works(self, mock_setup_logging, mock_config_manager, mock_config):
        """未投稿作品フィルタリングテスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        works = [
            {'work_id': '1', 'title': 'Work 1'},
            {'work_id': '2', 'title': 'Work 2'},
            {'work_id': '3', 'title': 'Work 3'}
        ]

        mock_post_manager = MagicMock()
        mock_post_manager.filter_unposted_works.return_value = ['1', '3']

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=lambda: mock_post_manager
        ):
            system = AutoPostingSystem()
            unposted = system._filter_unposted_works(works)
            
            assert len(unposted) == 2
            assert unposted[0]['work_id'] == '1'
            assert unposted[1]['work_id'] == '3'

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_rewrite_description(self, mock_setup_logging, mock_config_manager, mock_config):
        """紹介文リライトテスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        work_data = {
            'title': 'テスト作品',
            'description': '元の説明文'
        }

        mock_gemini = MagicMock()
        mock_gemini.rewrite_description.return_value = 'リライトされた説明文'

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=lambda **kwargs: mock_gemini,
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            result = system._rewrite_description(work_data)
            
            assert result == 'リライトされた説明文'
            mock_gemini.rewrite_description.assert_called_once()

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_rewrite_description_fallback(self, mock_setup_logging, mock_config_manager, mock_config):
        """紹介文リライト失敗時のフォールバックテスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        work_data = {
            'title': 'テスト作品',
            'description': '元の説明文'
        }

        mock_gemini = MagicMock()
        mock_gemini.rewrite_description.return_value = None  # リライト失敗

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=lambda **kwargs: mock_gemini,
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            result = system._rewrite_description(work_data)
            
            # 元の説明文がそのまま返されることを確認
            assert result == '元の説明文'

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_get_category_id(self, mock_setup_logging, mock_config_manager, mock_config):
        """カテゴリーID取得テスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        mock_wp_api = MagicMock()
        mock_wp_api.get_or_create_category.return_value = 123

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=lambda **kwargs: mock_wp_api,
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            category_id = system._get_category_id('テストカテゴリ')
            
            assert category_id == 123
            mock_wp_api.get_or_create_category.assert_called_once_with('テストカテゴリ')

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_get_category_id_empty(self, mock_setup_logging, mock_config_manager, mock_config):
        """空のカテゴリー名でのID取得テスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=MagicMock(),
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            category_id = system._get_category_id('')
            
            assert category_id is None

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_get_tag_ids(self, mock_setup_logging, mock_config_manager, mock_config):
        """タグIDリスト取得テスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        mock_wp_api = MagicMock()
        mock_wp_api.get_or_create_tag.side_effect = [101, 102, 103]

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=MagicMock(),
            GeminiAPI=MagicMock(),
            WordPressAPI=lambda **kwargs: mock_wp_api,
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            tag_ids = system._get_tag_ids(['タグ1', 'タグ2', 'タグ3'])
            
            assert tag_ids == [101, 102, 103]
            assert mock_wp_api.get_or_create_tag.call_count == 3

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_test_connections(self, mock_setup_logging, mock_config_manager, mock_config):
        """接続テストのテスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        mock_wp_api = MagicMock()
        mock_wp_api.test_connection.return_value = True
        mock_wp_api.__enter__.return_value = mock_wp_api
        mock_wp_api.__exit__.return_value = None

        mock_dmm_client = MagicMock()
        mock_dmm_client.get_items.return_value = [{'item': 'test'}]
        mock_dmm_client.__enter__.return_value = mock_dmm_client
        mock_dmm_client.__exit__.return_value = None

        mock_gemini = MagicMock()
        mock_gemini.model = 'test_model'

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=lambda **kwargs: mock_dmm_client,
            GeminiAPI=lambda **kwargs: mock_gemini,
            WordPressAPI=lambda **kwargs: mock_wp_api,
            ArticleGenerator=MagicMock(),
            PostManager=MagicMock()
        ):
            system = AutoPostingSystem()
            results = system.test_connections()
            
            assert 'wordpress' in results
            assert 'dmm_api' in results
            assert 'gemini' in results
            assert results['wordpress'] is True
            assert results['dmm_api'] is True
            assert results['gemini'] is True

    @patch('src.core.auto_posting_system.ConfigManager')
    @patch('src.core.auto_posting_system.setup_logging')
    def test_run_no_works(self, mock_setup_logging, mock_config_manager, mock_config):
        """作品が見つからない場合の実行テスト"""
        mock_config_manager.return_value = mock_config
        mock_setup_logging.return_value = MagicMock()

        mock_dmm_client = MagicMock()
        mock_dmm_client.get_items.return_value = []
        mock_dmm_client.__enter__.return_value = mock_dmm_client
        mock_dmm_client.__exit__.return_value = None

        mock_wp_api = MagicMock()
        mock_wp_api.__enter__.return_value = mock_wp_api
        mock_wp_api.__exit__.return_value = None

        mock_post_manager = MagicMock()
        mock_post_manager.get_posted_count.return_value = 10

        with patch.multiple(
            'src.core.auto_posting_system',
            DMMAPIClient=lambda **kwargs: mock_dmm_client,
            GeminiAPI=MagicMock(),
            WordPressAPI=lambda **kwargs: mock_wp_api,
            ArticleGenerator=MagicMock(),
            PostManager=lambda: mock_post_manager
        ):
            system = AutoPostingSystem()
            result = system.run()
            
            assert result['processed'] == 0
            assert result['posted'] == 0
            assert result['total_posted'] == 10


if __name__ == '__main__':
    pytest.main([__file__])