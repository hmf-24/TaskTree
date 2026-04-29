"""
TaskTree 安全认证模块
====================
提供密码哈希（bcrypt）和 JWT Token 的创建/解码功能。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值。"""
    try:
        # 确保密码和哈希值都是字节类型
        if isinstance(plain_password, str):
            plain_password_bytes = plain_password.encode('utf-8')
        else:
            plain_password_bytes = plain_password
            
        if isinstance(hashed_password, str):
            hashed_password_bytes = hashed_password.encode('utf-8')
        else:
            hashed_password_bytes = hashed_password
            
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """将明文密码转为 bcrypt 哈希。"""
    # 确保密码是字节类型
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
        
    # 生成盐并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 返回字符串形式
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌。

    Args:
        data: 令牌载荷数据，通常包含 {"sub": user_id, "email": email}。
        expires_delta: 自定义过期时间增量，默认使用配置中的 ACCESS_TOKEN_EXPIRE_MINUTES。

    Returns:
        编码后的 JWT 字符串。
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 JWT Token。

    Returns:
        解码成功返回 payload 字典，失败（过期/篡改/格式异常）返回 None。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None