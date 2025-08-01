"""
SQLiteデータベース管理システム - セキュリティ強化とデータベース移行
"""
import sqlite3
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SQLiteManager:
    """SQLiteデータベース管理システム"""
    
    def __init__(self, db_path: str = "data/blog_automation.db"):
        """
        SQLiteデータベース管理の初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベース初期化
        self._initialize_database()
        
        logger.info(f"SQLiteデータベース管理システム初期化完了: {self.db_path}")
    
    def _initialize_database(self):
        """データベースとテーブルを初期化"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 作品データテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS works (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    author_name TEXT,
                    circle_name TEXT,
                    description TEXT,
                    detail_url TEXT,
                    affiliate_url TEXT,
                    price INTEGER,
                    page_count INTEGER,
                    rating REAL,
                    release_date TEXT,
                    genre TEXT,
                    tags TEXT,  -- JSON array
                    image_urls TEXT,  -- JSON array
                    reviews TEXT,  -- JSON array
                    is_male_oriented BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 投稿履歴テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    post_id INTEGER,
                    post_url TEXT,
                    post_title TEXT,
                    post_content TEXT,
                    post_status TEXT DEFAULT 'published',
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY (work_id) REFERENCES works(work_id)
                )
            """)
            
            # 記事ストックテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    article_title TEXT NOT NULL,
                    article_content TEXT NOT NULL,
                    featured_image_url TEXT,
                    priority INTEGER DEFAULT 0,
                    is_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scheduled_for TIMESTAMP,
                    FOREIGN KEY (work_id) REFERENCES works(work_id)
                )
            """)
            
            # 投稿スケジュールテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS post_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    scheduled_time TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES article_stock(id)
                )
            """)
            
            # APIキャッシュテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    cache_data TEXT NOT NULL,  -- JSON data
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # システム設定テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_work_id ON works(work_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_male_oriented ON works(is_male_oriented)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_created_at ON works(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_history_work_id ON post_history(work_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_history_posted_at ON post_history(posted_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_stock_priority ON article_stock(priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_stock_is_used ON article_stock(is_used)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_schedule_scheduled_time ON post_schedule(scheduled_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_schedule_status ON post_schedule(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_cache_key ON api_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_cache_expires_at ON api_cache(expires_at)")
            
            conn.commit()
            logger.info("データベーステーブル初期化完了")
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            # WALモードの有効化（並行性向上）
            conn.execute("PRAGMA journal_mode=WAL")
            # 外部キー制約の有効化
            conn.execute("PRAGMA foreign_keys=ON")
            # パフォーマンス最適化
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
            yield conn
        finally:
            if conn:
                conn.close()
    
    def save_work_data(self, work_data: Dict[str, Any]) -> bool:
        """作品データを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # JSON フィールドの変換
                tags_json = json.dumps(work_data.get('tags', []), ensure_ascii=False)
                image_urls_json = json.dumps(work_data.get('image_urls', []), ensure_ascii=False)
                reviews_json = json.dumps(work_data.get('reviews', []), ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO works (
                        work_id, title, author_name, circle_name, description,
                        detail_url, affiliate_url, price, page_count, rating,
                        release_date, genre, tags, image_urls, reviews,
                        is_male_oriented, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    work_data.get('work_id'),
                    work_data.get('title'),
                    work_data.get('author_name'),
                    work_data.get('circle_name'),
                    work_data.get('description'),
                    work_data.get('detail_url'),
                    work_data.get('affiliate_url'),
                    work_data.get('price'),
                    work_data.get('page_count'),
                    work_data.get('rating'),
                    work_data.get('release_date'),
                    work_data.get('genre'),
                    tags_json,
                    image_urls_json,
                    reviews_json,
                    work_data.get('is_male_oriented', False),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.debug(f"作品データを保存: {work_data.get('work_id')}")
                return True
                
        except Exception as e:
            logger.error(f"作品データ保存エラー: {e}")
            return False
    
    def get_work_data(self, work_id: str) -> Optional[Dict[str, Any]]:
        """作品データを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM works WHERE work_id = ?", (work_id,))
                row = cursor.fetchone()
                
                if row:
                    work_data = dict(row)
                    # JSON フィールドのパース
                    work_data['tags'] = json.loads(work_data.get('tags', '[]'))
                    work_data['image_urls'] = json.loads(work_data.get('image_urls', '[]'))
                    work_data['reviews'] = json.loads(work_data.get('reviews', '[]'))
                    return work_data
                    
                return None
                
        except Exception as e:
            logger.error(f"作品データ取得エラー ({work_id}): {e}")
            return None
    
    def is_work_posted(self, work_id: str) -> bool:
        """作品が投稿済みかチェック"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM post_history WHERE work_id = ? AND success = 1",
                    (work_id,)
                )
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"投稿履歴確認エラー ({work_id}): {e}")
            return False
    
    def save_post_history(self, work_id: str, post_data: Dict[str, Any]) -> bool:
        """投稿履歴を保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO post_history (
                        work_id, post_id, post_url, post_title, post_content,
                        post_status, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    work_id,
                    post_data.get('post_id'),
                    post_data.get('post_url'),
                    post_data.get('post_title'),
                    post_data.get('post_content'),
                    post_data.get('post_status', 'published'),
                    post_data.get('success', True),
                    post_data.get('error_message')
                ))
                
                conn.commit()
                logger.debug(f"投稿履歴を保存: {work_id}")
                return True
                
        except Exception as e:
            logger.error(f"投稿履歴保存エラー: {e}")
            return False
    
    def save_article_stock(self, work_id: str, article_data: Dict[str, Any]) -> Optional[int]:
        """記事ストックを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO article_stock (
                        work_id, article_title, article_content, featured_image_url,
                        priority, scheduled_for
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    work_id,
                    article_data.get('title'),
                    article_data.get('content'),
                    article_data.get('featured_image_url'),
                    article_data.get('priority', 0),
                    article_data.get('scheduled_for')
                ))
                
                article_id = cursor.lastrowid
                conn.commit()
                logger.debug(f"記事ストックを保存: {work_id} (ID: {article_id})")
                return article_id
                
        except Exception as e:
            logger.error(f"記事ストック保存エラー: {e}")
            return None
    
    def get_available_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """利用可能な記事ストックを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM article_stock 
                    WHERE is_used = 0 
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT ?
                """, (limit,))
                
                articles = []
                for row in cursor.fetchall():
                    articles.append(dict(row))
                
                return articles
                
        except Exception as e:
            logger.error(f"記事ストック取得エラー: {e}")
            return []
    
    def mark_article_used(self, article_id: int) -> bool:
        """記事ストックを使用済みにマーク"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE article_stock SET is_used = 1 WHERE id = ?",
                    (article_id,)
                )
                conn.commit()
                logger.debug(f"記事ストックを使用済みに: {article_id}")
                return True
                
        except Exception as e:
            logger.error(f"記事ストック更新エラー: {e}")
            return False
    
    def schedule_post(self, article_id: int, scheduled_time: datetime) -> bool:
        """投稿をスケジュール"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO post_schedule (article_id, scheduled_time)
                    VALUES (?, ?)
                """, (article_id, scheduled_time.isoformat()))
                
                conn.commit()
                logger.debug(f"投稿スケジュール登録: Article {article_id} at {scheduled_time}")
                return True
                
        except Exception as e:
            logger.error(f"投稿スケジュール登録エラー: {e}")
            return False
    
    def get_scheduled_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """スケジュールされた投稿を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ps.*, ast.work_id, ast.article_title, ast.article_content, 
                           ast.featured_image_url
                    FROM post_schedule ps
                    JOIN article_stock ast ON ps.article_id = ast.id
                    WHERE ps.status = 'pending' 
                      AND ps.scheduled_time <= ?
                    ORDER BY ps.scheduled_time ASC
                    LIMIT ?
                """, (datetime.now().isoformat(), limit))
                
                posts = []
                for row in cursor.fetchall():
                    posts.append(dict(row))
                
                return posts
                
        except Exception as e:
            logger.error(f"スケジュールされた投稿取得エラー: {e}")
            return []
    
    def update_schedule_status(self, schedule_id: int, status: str, error_message: str = None) -> bool:
        """スケジュール状態を更新"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE post_schedule 
                    SET status = ?, attempts = attempts + 1, 
                        last_attempt_at = ?, error_message = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), error_message, schedule_id))
                
                conn.commit()
                logger.debug(f"スケジュール状態更新: {schedule_id} -> {status}")
                return True
                
        except Exception as e:
            logger.error(f"スケジュール状態更新エラー: {e}")
            return False
    
    def cache_set(self, key: str, data: Any, expires_in_seconds: int = 3600) -> bool:
        """キャッシュデータを保存"""
        try:
            expires_at = datetime.now().timestamp() + expires_in_seconds
            expires_at_iso = datetime.fromtimestamp(expires_at).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO api_cache (cache_key, cache_data, expires_at)
                    VALUES (?, ?, ?)
                """, (key, json.dumps(data, ensure_ascii=False), expires_at_iso))
                
                conn.commit()
                logger.debug(f"キャッシュ保存: {key}")
                return True
                
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
            return False
    
    def cache_get(self, key: str) -> Optional[Any]:
        """キャッシュデータを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT cache_data FROM api_cache 
                    WHERE cache_key = ? AND expires_at > ?
                """, (key, datetime.now().isoformat()))
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                
                return None
                
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return None
    
    def cleanup_expired_cache(self) -> int:
        """期限切れキャッシュをクリーンアップ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM api_cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"期限切れキャッシュをクリーンアップ: {deleted_count}件")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"キャッシュクリーンアップエラー: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, int]:
        """システム統計を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 作品数
                cursor.execute("SELECT COUNT(*) FROM works")
                stats['total_works'] = cursor.fetchone()[0]
                
                # 男性向け作品数
                cursor.execute("SELECT COUNT(*) FROM works WHERE is_male_oriented = 1")
                stats['male_oriented_works'] = cursor.fetchone()[0]
                
                # 投稿済み作品数
                cursor.execute("""
                    SELECT COUNT(DISTINCT work_id) FROM post_history WHERE success = 1
                """)
                stats['posted_works'] = cursor.fetchone()[0]
                
                # 記事ストック数
                cursor.execute("SELECT COUNT(*) FROM article_stock WHERE is_used = 0")
                stats['available_articles'] = cursor.fetchone()[0]
                
                # スケジュール済み投稿数
                cursor.execute("SELECT COUNT(*) FROM post_schedule WHERE status = 'pending'")
                stats['scheduled_posts'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {}


# グローバルデータベースマネージャーインスタンス
db_manager = SQLiteManager()