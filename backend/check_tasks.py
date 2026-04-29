#!/usr/bin/env python3
"""检查数据库中的任务"""
import sqlite3
import sys

try:
    conn = sqlite3.connect('/app/data/tasktree.db')
    cursor = conn.cursor()
    
    # 查询user_id=1的待处理任务
    cursor.execute("""
        SELECT id, name, status, assignee_id, description 
        FROM tasks 
        WHERE assignee_id=1 AND status IN ('pending', 'in_progress')
        LIMIT 20
    """)
    
    tasks = cursor.fetchall()
    print(f'找到 {len(tasks)} 个任务:')
    print('-' * 80)
    
    for task in tasks:
        print(f'ID: {task[0]}')
        print(f'名称: {task[1]}')
        print(f'状态: {task[2]}')
        print(f'描述: {task[4] or "无"}')
        print('-' * 80)
    
    conn.close()
    
except Exception as e:
    print(f'错误: {e}')
    sys.exit(1)
