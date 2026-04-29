"""
重置用户密码脚本
用法: python reset_password.py <email> <new_password>
"""
import sys
import asyncio
import bcrypt
from sqlalchemy import select
from app.core.database import get_session_maker
from app.models import User


def hash_password(password: str) -> str:
    """使用bcrypt哈希密码"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


async def reset_password(email: str, new_password: str):
    """重置指定用户的密码"""
    session_maker = get_session_maker()
    async with session_maker() as db:
        # 查找用户
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ 用户不存在: {email}")
            return False
        
        # 更新密码
        user.password_hash = hash_password(new_password)
        await db.commit()
        
        print(f"✅ 密码重置成功！")
        print(f"   用户: {user.email}")
        print(f"   昵称: {user.nickname}")
        print(f"   新密码: {new_password}")
        return True


async def list_users():
    """列出所有用户"""
    session_maker = get_session_maker()
    async with session_maker() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("❌ 数据库中没有用户")
            return
        
        print(f"\n📋 用户列表 (共 {len(users)} 个用户):")
        print("-" * 60)
        for user in users:
            print(f"ID: {user.id:3d} | Email: {user.email:30s} | 昵称: {user.nickname or '(未设置)'}")
        print("-" * 60)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 没有参数，列出所有用户
        asyncio.run(list_users())
    elif len(sys.argv) == 3:
        # 重置密码
        email = sys.argv[1]
        new_password = sys.argv[2]
        
        if len(new_password) < 8:
            print("❌ 密码长度至少为8位")
            sys.exit(1)
        
        asyncio.run(reset_password(email, new_password))
    else:
        print("用法:")
        print("  列出所有用户: python reset_password.py")
        print("  重置密码:     python reset_password.py <email> <new_password>")
        print("\n示例:")
        print("  python reset_password.py admin@example.com Admin123456")
        sys.exit(1)
