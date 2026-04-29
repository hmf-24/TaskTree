#!/usr/bin/env python3
"""创建测试任务"""
import sqlite3
from datetime import datetime, timedelta

try:
    conn = sqlite3.connect('/app/data/tasktree.db')
    cursor = conn.cursor()
    
    # 查询user_id=1的项目
    cursor.execute("SELECT id FROM projects WHERE owner_id=1 LIMIT 1")
    project = cursor.fetchone()
    
    if not project:
        print("错误: 没有找到项目，请先在前端创建一个项目")
        conn.close()
        exit(1)
    
    project_id = project[0]
    print(f"找到项目 ID: {project_id}")
    
    # 创建测试任务
    now = datetime.now().isoformat()
    due_date = (datetime.now() + timedelta(days=7)).date().isoformat()
    
    tasks = [
        ("测试任务", "这是一个测试任务，用于测试钉钉机器人", "pending", "medium", 0),
        ("开发功能", "开发新功能模块", "in_progress", "high", 30),
        ("修复Bug", "修复系统中的已知Bug", "pending", "high", 0),
        ("文档编写", "编写项目文档", "in_progress", "low", 50),
    ]
    
    for name, desc, status, priority, progress in tasks:
        cursor.execute("""
            INSERT INTO tasks (
                project_id, name, description, assignee_id, 
                status, priority, progress, due_date, 
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id, name, desc, 1,
            status, priority, progress, due_date,
            now, now
        ))
        print(f"✅ 创建任务: {name}")
    
    conn.commit()
    conn.close()
    
    print(f"\n成功创建 {len(tasks)} 个测试任务！")
    print("现在你可以在钉钉中发送消息测试了，例如：")
    print("  - '测试任务的进度'")
    print("  - '开发功能怎么样了'")
    print("  - '我的任务'")
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
