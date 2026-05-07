"""允许ai_conversations表的project_id为NULL"""
import sqlite3

conn = sqlite3.connect('backend/data/tasktree.db')
cursor = conn.cursor()

# 1. 创建新表（允许project_id为NULL）
cursor.execute("""
CREATE TABLE ai_conversations_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    task_id INTEGER,
    conversation_type VARCHAR(20) NOT NULL,
    title VARCHAR(255),
    messages TEXT NOT NULL,
    context_data TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL,
    FOREIGN KEY(task_id) REFERENCES tasks (id) ON DELETE SET NULL
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
cursor.execute("CREATE INDEX ix_ai_conversations_user_id ON ai_conversations (user_id)")
cursor.execute("CREATE INDEX ix_ai_conversations_project_id ON ai_conversations (project_id)")
cursor.execute("CREATE INDEX ix_ai_conversations_task_id ON ai_conversations (task_id)")
cursor.execute("CREATE INDEX ix_ai_conversations_created_at ON ai_conversations (created_at)")

conn.commit()
conn.close()

print("✓ 已允许ai_conversations表的project_id为NULL")
