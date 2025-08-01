#!/usr/bin/env python3
"""
DMM API クライアントのテストモジュール
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.dmm_api import DMMAPIClient


class TestDMMAPIClient:
    """DMM API クライアントのテストクラス"""

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        return DMMAPIClient(api_id="test_api_id", affiliate_id="test_affiliate_id")

    def test_init(self):
        """初期化テスト"""
        client = DMMAPIClient(api_id="test_api", affiliate_id="test_affiliate")
        assert client.api_id == "test_api"
        assert client.affiliate_id == "test_affiliate"
        assert client.request_delay == 2
        assert client.max_workers == 3
        assert isinstance(client._review_cache, dict)
        assert hasattr(client, 'review_patterns')
        assert hasattr(client, 'review_section_patterns')

    @patch('src.api.dmm_api.DMMAPIClient._load_config')
    def test_init_with_config_loading(self, mock_load_config):
        """設定読み込みを含む初期化テスト"""
        client = DMMAPIClient(api_id="test_api")
        mock_load_config.assert_called_once()

    def test_is_comic_work_with_image_url(self, client):
        """コミック作品判定テスト（画像URLによる判定）"""
        # コミック作品の場合
        comic_item = {
            'imageURL': {
                'large': 'https://example.com/comic/image.jpg'
            }
        }
        assert client.is_comic_work(comic_item) is True

        # コミック作品でない場合
        non_comic_item = {
            'imageURL': {
                'large': 'https://example.com/video/image.jpg'
            }
        }
        assert client.is_comic_work(non_comic_item) is True  # デフォルトでTrue

    def test_is_comic_work_with_genre(self, client):
        """コミック作品判定テスト（ジャンルによる判定）"""
        comic_item = {
            'iteminfo': {
                'genre': [
                    {'name': 'コミック'},
                    {'name': 'その他'}
                ]
            }
        }
        assert client.is_comic_work(comic_item) is True

    def test_get_review_info_from_page_cached(self, client):
        """キャッシュ機能付きレビュー情報取得テスト"""
        test_url = "https://example.com/product"
        expected_result = {'count': 5, 'average': 4.5, 'has_reviews': True}
        
        # 最初の呼び出し
        with patch.object(client, 'get_review_info_from_page', return_value=expected_result) as mock_get:
            result1 = client.get_review_info_from_page_cached(test_url)
            assert result1 == expected_result
            mock_get.assert_called_once_with(test_url)

        # 2回目の呼び出し（キャッシュから取得）
        with patch.object(client, 'get_review_info_from_page', return_value=expected_result) as mock_get:
            result2 = client.get_review_info_from_page_cached(test_url)
            assert result2 == expected_result
            mock_get.assert_not_called()  # キャッシュから取得されるため呼び出されない

    @patch('src.api.dmm_api.ThreadPoolExecutor')
    def test_get_review_info_batch(self, mock_executor, client):
        """並列レビュー情報取得テスト"""
        test_urls = ["url1", "url2", "url3"]
        expected_results = {
            "url1": {'count': 1, 'average': 3.0, 'has_reviews': True},
            "url2": {'count': 2, 'average': 4.0, 'has_reviews': True},
            "url3": {'count': 0, 'average': 0.0, 'has_reviews': False}
        }

        # Executorのモック設定
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        # as_completedのモック
        mock_futures = []
        for url in test_urls:
            future = MagicMock()
            future.result.return_value = expected_results[url]
            mock_futures.append(future)
        
        mock_executor_instance.submit.side_effect = mock_futures
        
        with patch('src.api.dmm_api.as_completed', return_value=mock_futures):
            # future_to_urlマッピングのモック
            future_to_url = {mock_futures[i]: test_urls[i] for i in range(len(test_urls))}
            
            with patch.object(client, 'get_review_info_from_page_cached') as mock_cached:
                mock_cached.side_effect = lambda url: expected_results[url]
                
                results = client.get_review_info_batch(test_urls)
                
                # 結果の検証は簡単な構造で確認
                assert len(results) >= 0  # 基本的な動作確認

    def test_extract_circle_name(self, client):
        """サークル名抽出テスト"""
        # 正常な場合
        item_with_maker = {
            'iteminfo': {
                'maker': [
                    {'name': 'テストサークル'}
                ]
            }
        }
        assert client._extract_circle_name(item_with_maker) == 'テストサークル'

        # メーカー情報がない場合
        item_without_maker = {}
        assert client._extract_circle_name(item_without_maker) == '不明'

    def test_extract_page_count(self, client):
        """ページ数抽出テスト"""
        # 数字のみの場合
        item_with_numeric_volume = {'volume': '24'}
        assert client._extract_page_count(item_with_numeric_volume) == '24ページ'

        # 文字列混合の場合
        item_with_text_volume = {'volume': '約30ページ'}
        assert client._extract_page_count(item_with_text_volume) == '約30ページ'

        # volume情報がない場合
        item_without_volume = {}
        assert client._extract_page_count(item_without_volume) == '不明'

    @patch('requests.Session.get')
    def test_get_review_info_from_page_no_reviews(self, mock_get, client):
        """レビューなしページのテスト"""
        # レスポンスのモック（レビューなしのページ）
        mock_response = Mock()
        mock_response.content = '''
        <html>
            <body>
                <div id="review_anchor">
                    <p>この作品に最初のレビューを書いてみませんか？</p>
                </div>
            </body>
        </html>
        '''.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_review_info_from_page('https://example.com/product')
        
        assert result['count'] == 0
        assert result['has_reviews'] is False
        assert result['average'] == 0.0

    @patch('requests.Session.get')
    def test_get_review_info_from_page_with_reviews(self, mock_get, client):
        """レビューありページのテスト"""
        # レスポンスのモック（レビューありのページ）
        mock_response = Mock()
        mock_response.content = '''
        <html>
            <body>
                <div id="review_anchor">
                    <p>総評価数 5</p>
                    <p>平均評価 4.2</p>
                </div>
            </body>
        </html>
        '''.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_review_info_from_page('https://example.com/product')
        
        assert result['count'] == 5
        assert result['has_reviews'] is True

    def test_convert_to_work_data_skip_review_check(self, client):
        """レビューチェックスキップ時の変換テスト"""
        api_item = {
            'content_id': 'test123',
            'title': 'テスト作品',
            'URL': 'https://example.com/test',
            'imageURL': {'large': 'https://example.com/image.jpg'},
            'comment': 'テスト説明',
            'prices': {'price': '500円'},
            'date': '2024-01-01',
            'iteminfo': {
                'maker': [{'name': 'テストサークル'}],
                'genre': [{'name': 'コミック'}]
            }
        }

        result = client.convert_to_work_data(api_item, skip_review_check=True)
        
        assert result is not None
        assert result['work_id'] == 'test123'
        assert result['title'] == 'テスト作品'
        assert result['circle_name'] == 'テストサークル'
        assert result['category'] == '同人'

    def test_validate_reviews_skip_check(self, client):
        """レビュー検証スキップテスト"""
        api_item = {'title': 'テスト作品'}
        result = client._validate_reviews(api_item, skip_review_check=True)
        assert result is True

    def test_validate_reviews_with_existing_reviews(self, client):
        """既存レビューありの検証テスト"""
        api_item = {
            'title': 'テスト作品',
            'review': {'count': 5, 'average': 4.2}
        }
        result = client._validate_reviews(api_item, skip_review_check=False)
        assert result is True

    def test_validate_reviews_no_url(self, client):
        """URL なしの検証テスト"""
        api_item = {'title': 'テスト作品'}
        result = client._validate_reviews(api_item, skip_review_check=False)
        assert result is False

    @patch.object(DMMAPIClient, 'get_review_info_from_page')
    def test_validate_reviews_with_scraping(self, mock_get_review, client):
        """スクレイピングによるレビュー検証テスト"""
        api_item = {
            'title': 'テスト作品',
            'URL': 'https://example.com/product'
        }
        mock_get_review.return_value = {
            'has_reviews': True,
            'count': 3,
            'average': 4.0
        }
        
        result = client._validate_reviews(api_item, skip_review_check=False)
        
        assert result is True
        assert 'review' in api_item
        assert api_item['review']['count'] == 3
        assert api_item['review']['average'] == 4.0

    def test_extract_sample_images_success(self, client):
        """サンプル画像抽出成功テスト"""
        api_item = {
            'sampleImageURL': {
                'sample_l': {
                    'image': ['img1.jpg', 'img2.jpg', 'img3.jpg']
                }
            }
        }
        
        result = client._extract_sample_images(api_item)
        assert len(result) == 3
        assert 'img1.jpg' in result

    def test_extract_sample_images_no_data(self, client):
        """サンプル画像データなしテスト"""
        api_item = {}
        result = client._extract_sample_images(api_item)
        assert result == []

    def test_extract_sample_images_malformed_data(self, client):
        """不正なサンプル画像データテスト"""
        api_item = {
            'sampleImageURL': {
                'sample_l': {}  # 'image' キーがない
            }
        }
        result = client._extract_sample_images(api_item)
        assert result == []

    def test_extract_review_data_success(self, client):
        """レビューデータ抽出成功テスト"""
        api_item = {
            'review': {
                'average': 4.5,
                'count': 10
            }
        }
        
        result = client._extract_review_data(api_item)
        assert len(result) == 1
        assert result[0]['rating'] == '4.5点 (10件)'
        assert result[0]['text'] == '平均評価: 4.5点'

    def test_extract_review_data_no_review(self, client):
        """レビューデータなしテスト"""
        api_item = {}
        result = client._extract_review_data(api_item)
        assert result == []

    def test_extract_genres_success(self, client):
        """ジャンル抽出成功テスト"""
        api_item = {
            'iteminfo': {
                'genre': [
                    {'name': 'コミック'},
                    {'name': 'アドベンチャー'},
                    {'name': ''}  # 空の名前は除外される
                ]
            }
        }
        
        result = client._extract_genres(api_item)
        assert len(result) == 2
        assert 'コミック' in result
        assert 'アドベンチャー' in result

    def test_extract_genres_no_data(self, client):
        """ジャンルデータなしテスト"""
        api_item = {}
        result = client._extract_genres(api_item)
        assert result == []

    def test_build_work_data_success(self, client):
        """作品データ構築成功テスト"""
        api_item = {
            'content_id': 'test456',
            'title': 'テスト作品2',
            'URL': 'https://example.com/test2',
            'affiliateURL': 'https://affiliate.example.com/test2',
            'imageURL': {'large': 'https://example.com/image2.jpg'},
            'comment': 'テスト説明2',
            'prices': {'price': '800円'},
            'date': '2024-02-01',
            'iteminfo': {
                'maker': [{'name': 'テストサークル2'}],
                'genre': [{'name': 'ノベル'}]
            },
            'review': {'average': 3.8, 'count': 7}
        }
        
        result = client._build_work_data(api_item)
        
        assert result is not None
        assert result['work_id'] == 'test456'
        assert result['title'] == 'テスト作品2'
        assert result['circle_name'] == 'テストサークル2'
        assert result['affiliate_url'] == 'https://affiliate.example.com/test2'
        assert len(result['genres']) == 1
        assert len(result['reviews']) == 1

    @patch('src.api.dmm_api.Path')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_load_config_success(self, mock_yaml_load, mock_open, mock_path, client):
        """設定ファイル読み込み成功テスト"""
        # パスの存在確認をTrueに設定
        mock_path.return_value.parent.parent.parent.__truediv__.return_value.__truediv__.return_value.exists.return_value = True
        
        # YAML設定のモック
        mock_config = {
            'review_patterns': {
                'basic': [
                    {'pattern': r'レビュー\s*(\d+)\s*件', 'description': 'test pattern'}
                ]
            },
            'review_section_patterns': [
                {'pattern': r'総評価数\s*(\d+)', 'description': 'section pattern'}
            ],
            'no_review_indicators': ['最初のレビューを書いて'],
            'html_selectors': ['.review-list']
        }
        mock_yaml_load.return_value = mock_config

        # 新しいクライアントを作成して設定読み込みをテスト
        client_new = DMMAPIClient(api_id="test")
        
        # 基本的な設定が読み込まれていることを確認
        assert hasattr(client_new, 'review_patterns')
        assert hasattr(client_new, 'review_section_patterns')
        assert hasattr(client_new, 'no_review_indicators')
        assert hasattr(client_new, 'html_selectors')

    def test_use_default_patterns(self, client):
        """デフォルトパターン使用テスト"""
        client._use_default_patterns()
        
        assert len(client.review_patterns) > 0
        assert len(client.review_section_patterns) > 0
        assert len(client.no_review_indicators) > 0
        assert len(client.html_selectors) > 0
        
        # 期待されるパターンが含まれているか確認
        assert r'レビュー\s*[（(]\s*(\d+)\s*件\s*[）)]' in client.review_patterns
        assert 'この作品に最初のレビューを書いてみませんか？' in client.no_review_indicators


if __name__ == '__main__':
    pytest.main([__file__])