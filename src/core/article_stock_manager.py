"""
記事ストック管理システム - 100%成功率実現のためのフェールセーフ機能
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

from .article_generator import ArticleGenerator
from ..api.dmm_api import DMMAPIClient
from ..api.gemini_api import GeminiAPI
from ..services.exceptions import AutoPostingError

logger = logging.getLogger(__name__)


class ArticleStockManager:
    """記事ストック管理システム"""
    
    def __init__(self, dmm_client: DMMAPIClient, gemini_api: GeminiAPI, config):
        """
        記事ストックマネージャーの初期化
        
        Args:
            dmm_client: DMM APIクライアント
            gemini_api: Gemini APIクライアント
            config: システム設定
        """
        self.dmm_client = dmm_client
        self.gemini_api = gemini_api
        self.config = config
        
        # ストック関連設定
        self.stock_dir = Path("data/article_stock")
        self.stock_meta_file = self.stock_dir / "stock_metadata.json"
        
        # ストック設定
        self.target_stock_count = 50  # 常時50件をストック
        self.min_stock_threshold = 10  # 最小ストック数（これを下回ったら緊急生成）
        self.max_stock_age_days = 7    # ストック記事の最大age（7日）
        
        # ディレクトリ作成
        self.stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 記事生成器
        self.article_generator = ArticleGenerator(
            gemini_api=self.gemini_api,
            config=self.config
        )
        
        logger.info(f"記事ストックマネージャー初期化完了 - 目標ストック数: {self.target_stock_count}件")
    
    def get_stock_count(self) -> int:
        """現在のストック記事数を取得"""
        try:
            stock_files = list(self.stock_dir.glob("article_*.json"))
            return len(stock_files)
        except Exception as e:
            logger.error(f"ストック数取得エラー: {e}")
            return 0
    
    def get_stock_metadata(self) -> Dict:
        """ストックメタデータを取得"""
        try:
            if self.stock_meta_file.exists():
                with open(self.stock_meta_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"articles": {}, "last_updated": None, "total_generated": 0}
        except Exception as e:
            logger.error(f"メタデータ取得エラー: {e}")
            return {"articles": {}, "last_updated": None, "total_generated": 0}
    
    def save_stock_metadata(self, metadata: Dict):
        """ストックメタデータを保存"""
        try:
            metadata["last_updated"] = datetime.now().isoformat()
            with open(self.stock_meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"メタデータ保存エラー: {e}")
    
    def generate_stock_articles(self, count: int) -> int:
        """
        指定数のストック記事を生成
        
        Args:
            count: 生成する記事数
            
        Returns:
            実際に生成された記事数
        """
        logger.info(f"ストック記事生成開始 - 目標: {count}件")
        
        generated_count = 0
        metadata = self.get_stock_metadata()
        
        try:
            # 幅広い範囲から作品を取得（ストック用は過去作品も含める）
            search_ranges = [
                {"offset": 1, "limit": 100},      # 最新作品
                {"offset": 101, "limit": 200},    # 準新作品
                {"offset": 301, "limit": 300},    # 中堅作品
                {"offset": 601, "limit": 500},    # 過去作品
                {"offset": 1101, "limit": 1000}, # 更に過去の作品
            ]
            
            all_works = []
            for search_range in search_ranges:
                if len(all_works) >= count * 3:  # 十分な候補を確保
                    break
                    
                api_items = self.dmm_client.get_items(
                    limit=search_range["limit"], 
                    offset=search_range["offset"]
                )
                
                for item in api_items:
                    work_data = self.dmm_client.convert_to_work_data(item, skip_review_check=True)
                    if work_data and work_data not in all_works:
                        all_works.append(work_data)
            
            logger.info(f"ストック記事候補: {len(all_works)}件取得")
            
            # 既存のストック記事と重複しないようにフィルタリング
            existing_work_ids = set()
            for article_id in metadata.get("articles", {}):
                try:
                    article_file = self.stock_dir / f"{article_id}.json"
                    if article_file.exists():
                        with open(article_file, 'r', encoding='utf-8') as f:
                            article_data = json.load(f)
                            existing_work_ids.add(article_data.get("work_id"))
                except Exception as e:
                    logger.warning(f"既存記事読み込みエラー: {e}")
            
            # 新しい作品のみを対象にする
            new_works = [work for work in all_works if work["work_id"] not in existing_work_ids][:count]
            
            logger.info(f"新規作品候補: {len(new_works)}件")
            
            # 記事生成実行
            for work_data in new_works:
                try:
                    # 記事生成
                    article_content = self.article_generator.generate_article(work_data)
                    
                    if article_content:
                        # ストック記事として保存
                        article_id = self._save_stock_article(work_data, article_content)
                        
                        # メタデータ更新
                        metadata["articles"][article_id] = {
                            "work_id": work_data["work_id"],
                            "title": work_data["title"],
                            "generated_at": datetime.now().isoformat(),
                            "used": False
                        }
                        
                        generated_count += 1
                        logger.info(f"ストック記事生成完了: {work_data['title']} ({generated_count}/{count})")
                        
                        if generated_count >= count:
                            break
                            
                except Exception as e:
                    logger.error(f"記事生成エラー: {work_data.get('title', 'Unknown')}: {e}")
                    continue
            
            # メタデータ保存
            metadata["total_generated"] = metadata.get("total_generated", 0) + generated_count
            self.save_stock_metadata(metadata)
            
            logger.info(f"ストック記事生成完了 - 生成数: {generated_count}件, 総ストック: {self.get_stock_count()}件")
            
        except Exception as e:
            logger.error(f"ストック記事生成中にエラー: {e}")
        
        return generated_count
    
    def _save_stock_article(self, work_data: Dict, article_content: str) -> str:
        """ストック記事をファイルに保存"""
        # 記事IDを生成（work_idとタイムスタンプから）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        article_id = f"article_{work_data['work_id']}_{timestamp}"
        
        # 記事データ構築
        article_data = {
            "article_id": article_id,
            "work_id": work_data["work_id"],
            "title": work_data["title"],
            "content": article_content,
            "work_data": work_data,
            "generated_at": datetime.now().isoformat(),
            "used": False
        }
        
        # ファイル保存
        article_file = self.stock_dir / f"{article_id}.json"
        with open(article_file, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        return article_id
    
    def get_emergency_article(self) -> Optional[Dict]:
        """
        緊急時用のストック記事を取得
        
        Returns:
            記事データまたはNone
        """
        try:
            metadata = self.get_stock_metadata()
            
            # 未使用の記事から最古のものを取得
            available_articles = [
                (article_id, info) for article_id, info in metadata.get("articles", {}).items()
                if not info.get("used", False)
            ]
            
            if not available_articles:
                logger.warning("利用可能なストック記事がありません")
                return None
            
            # 最古の記事を選択
            available_articles.sort(key=lambda x: x[1]["generated_at"])
            article_id, article_info = available_articles[0]
            
            # 記事ファイル読み込み
            article_file = self.stock_dir / f"{article_id}.json"
            if not article_file.exists():
                logger.error(f"ストック記事ファイルが見つかりません: {article_file}")
                return None
            
            with open(article_file, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
            
            # 使用済みマーク
            metadata["articles"][article_id]["used"] = True
            metadata["articles"][article_id]["used_at"] = datetime.now().isoformat()
            self.save_stock_metadata(metadata)
            
            # 使用済みファイルを別ディレクトリに移動
            used_dir = self.stock_dir / "used"
            used_dir.mkdir(exist_ok=True)
            article_file.rename(used_dir / f"{article_id}.json")
            
            logger.info(f"緊急時ストック記事を使用: {article_data['title']}")
            
            return {
                "work_data": article_data["work_data"],
                "article_content": article_data["content"],
                "source": "emergency_stock"
            }
            
        except Exception as e:
            logger.error(f"緊急時記事取得エラー: {e}")
            return None
    
    def maintain_stock(self) -> Dict:
        """
        ストック記事のメンテナンス
        
        Returns:
            メンテナンス結果
        """
        logger.info("ストック記事メンテナンス開始")
        
        current_count = self.get_stock_count()
        metadata = self.get_stock_metadata()
        
        result = {
            "initial_count": current_count,
            "cleaned_count": 0,
            "generated_count": 0,
            "final_count": current_count
        }
        
        try:
            # 古い記事のクリーンアップ
            result["cleaned_count"] = self._cleanup_old_articles()
            
            # 不足分の補充
            current_count = self.get_stock_count()
            if current_count < self.target_stock_count:
                needed_count = self.target_stock_count - current_count
                result["generated_count"] = self.generate_stock_articles(needed_count)
            
            result["final_count"] = self.get_stock_count()
            
            logger.info(f"ストックメンテナンス完了: {result}")
            
        except Exception as e:
            logger.error(f"ストックメンテナンス中にエラー: {e}")
        
        return result
    
    def _cleanup_old_articles(self) -> int:
        """古いストック記事をクリーンアップ"""
        cleaned_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.max_stock_age_days)
        metadata = self.get_stock_metadata()
        
        try:
            articles_to_remove = []
            
            for article_id, article_info in metadata.get("articles", {}).items():
                generated_at = datetime.fromisoformat(article_info["generated_at"])
                
                if generated_at < cutoff_date:
                    # 古い記事ファイルを削除
                    article_file = self.stock_dir / f"{article_id}.json"
                    if article_file.exists():
                        article_file.unlink()
                        cleaned_count += 1
                    
                    articles_to_remove.append(article_id)
            
            # メタデータから削除
            for article_id in articles_to_remove:
                del metadata["articles"][article_id]
            
            if articles_to_remove:
                self.save_stock_metadata(metadata)
                logger.info(f"古いストック記事を削除: {cleaned_count}件")
            
        except Exception as e:
            logger.error(f"古い記事クリーンアップエラー: {e}")
        
        return cleaned_count
    
    def is_emergency_mode_needed(self) -> bool:
        """
        緊急モード（ストック記事使用）が必要かどうかを判定
        
        Returns:
            緊急モードが必要ならTrue
        """
        current_stock = self.get_stock_count()
        return current_stock <= self.min_stock_threshold
    
    def get_stock_status(self) -> Dict:
        """ストック状況を取得"""
        metadata = self.get_stock_metadata()
        current_count = self.get_stock_count()
        
        available_count = sum(
            1 for info in metadata.get("articles", {}).values()
            if not info.get("used", False)
        )
        
        return {
            "total_stock": current_count,
            "available_stock": available_count,
            "used_stock": current_count - available_count,
            "target_stock": self.target_stock_count,
            "is_sufficient": available_count >= self.min_stock_threshold,
            "emergency_mode_needed": self.is_emergency_mode_needed(),
            "last_updated": metadata.get("last_updated"),
            "total_generated": metadata.get("total_generated", 0)
        }