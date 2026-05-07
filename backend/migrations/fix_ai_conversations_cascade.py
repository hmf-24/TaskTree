"""修复 ai_conversations 表的级联删除问题"""
import sqlite3
import os

def fix_cascade():
    db_path = "./data/tasktree.db"
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("开始修复 ai_conversations 表...")
        
        # 1. 创建临时表(带正确的级联删除)
        cursor.execute("""
            CREATE TABLE ai_conversations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                conversation_type VARCHAR(20) NOT NULL,
                title VARCHAR(255),
                messages TEXT NOT NULL,
                context_data TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """)
        
        # 2. 复制数据
        cursor.execute("""
            INSERT INTO ai_conversations_new 
            SELECT * FROM ai_conversations
        """)
        
        # 3. 删除旧表
        cursor.execute("DROP TABLE ai_conversations")
        
        # 4. 重命名新表
        cursor.execute("ALTER TABLE ai_conversations_new RENAME TO ai_conversations")
        
        # 5. 重建索引
        cursor.execute("CREATE INDEX ix_ai_conversations_user_id ON ai_conversations(user_id)")
        cursor.execute("CREATE INDEX ix_ai_conversations_project_id ON ai_conversations(project_id)")
        cursor.execute("CREATE INDEX ix_ai_conversations_task_id ON ai_conversations(task_id)")
        cursor.execute("CREATE INDEX ix_ai_conversations_created_at ON ai_conversations(created_at)")
        
        conn.commit()
        print("✅ 修复成功!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 修复失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_cascade()
