import sqlite3

def upgrade_db():
    conn = sqlite3.connect('e:/Project/TaskTree/backend/data/tasktree.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE readhub_settings ADD COLUMN wewe_server_url VARCHAR(500)")
        print("Added wewe_server_url")
    except Exception as e:
        print("wewe_server_url already exists or error:", e)
        
    try:
        cursor.execute("ALTER TABLE readhub_settings ADD COLUMN wewe_auth_code VARCHAR(100)")
        print("Added wewe_auth_code")
    except Exception as e:
        print("wewe_auth_code already exists or error:", e)
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade_db()
