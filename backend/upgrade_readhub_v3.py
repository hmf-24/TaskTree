import sqlite3
import os
import json

def upgrade_db():
    db_path = os.path.join(os.path.dirname(__file__), "data", "tasktree.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Upgrading database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to rss_articles
        try:
            cursor.execute("ALTER TABLE rss_articles ADD COLUMN importance VARCHAR(50) DEFAULT 'medium'")
            print("Added importance column to rss_articles")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                print(f"Warning adding importance: {e}")
            else:
                print("Column importance already exists")

        try:
            cursor.execute("ALTER TABLE rss_articles ADD COLUMN tags TEXT")
            print("Added tags column to rss_articles")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                print(f"Warning adding tags: {e}")
            else:
                print("Column tags already exists")

        # Add column to readhub_settings
        try:
            default_tags = json.dumps(["AI", "前沿技术", "数据中心", "算力", "GPU"])
            cursor.execute(f"ALTER TABLE readhub_settings ADD COLUMN interest_tags TEXT DEFAULT '{default_tags}'")
            print("Added interest_tags column to readhub_settings")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                print(f"Warning adding interest_tags: {e}")
            else:
                print("Column interest_tags already exists")

        conn.commit()
        print("Upgrade successful.")

    except Exception as e:
        print(f"Error upgrading database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db()
