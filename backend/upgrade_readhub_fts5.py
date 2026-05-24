import sqlite3
import os

def upgrade_db():
    db_path = os.path.join(os.path.dirname(__file__), "data", "tasktree.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Upgrading database for FTS5 at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 创建 FTS5 虚拟表
        # content='rss_articles' 意味着它使用外部内容表
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS rss_articles_fts 
            USING fts5(title, content_html, summary, author, content='rss_articles', content_rowid='id');
        """)
        print("Created virtual table rss_articles_fts")

        # 2. 清理可能存在的旧数据并执行全量同步
        cursor.execute("INSERT INTO rss_articles_fts(rss_articles_fts) VALUES('rebuild');")
        print("Rebuilt FTS5 index for existing articles")

        # 3. 创建触发器，保持数据同步
        # Insert Trigger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS rss_articles_ai AFTER INSERT ON rss_articles
            BEGIN
                INSERT INTO rss_articles_fts(rowid, title, content_html, summary, author)
                VALUES (new.id, new.title, new.content_html, new.summary, new.author);
            END;
        """)
        
        # Delete Trigger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS rss_articles_ad AFTER DELETE ON rss_articles
            BEGIN
                INSERT INTO rss_articles_fts(rss_articles_fts, rowid, title, content_html, summary, author)
                VALUES ('delete', old.id, old.title, old.content_html, old.summary, old.author);
            END;
        """)
        
        # Update Trigger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS rss_articles_au AFTER UPDATE ON rss_articles
            BEGIN
                INSERT INTO rss_articles_fts(rss_articles_fts, rowid, title, content_html, summary, author)
                VALUES ('delete', old.id, old.title, old.content_html, old.summary, old.author);
                
                INSERT INTO rss_articles_fts(rowid, title, content_html, summary, author)
                VALUES (new.id, new.title, new.content_html, new.summary, new.author);
            END;
        """)
        print("Created synchronization triggers for FTS5")

        conn.commit()
        print("FTS5 Upgrade successful.")

    except Exception as e:
        print(f"Error upgrading database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db()
