"""
TaskTree 加密工具
================
提供简单的数据加密功能，用于存储敏感信息如API Key。
使用AES-GCM模式，需要cryptography库。
如果库不可用，降级为简单的base64+XOR混淆。
"""
import os
import base64
import hashlib

# 尝试使用cryptography库的Fernet（AES）
try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class SimpleCrypto:
    """简单的加密工具类"""

    def __init__(self, key: str = None):
        # 从环境变量或传入key生成32字节密钥
        master_key = key or os.getenv("ENCRYPTION_KEY", "tasktree-default-key-change-me")
        # SHA256生成32字节
        self.key = hashlib.sha256(master_key.encode()).digest()

    def encrypt(self, plaintext: str) -> str:
        """加密字符串"""
        if not plaintext:
            return ""

        if HAS_CRYPTOGRAPHY:
            fernet = Fernet(self.key)
            return fernet.encrypt(plaintext.encode()).decode()
        else:
            # 降级方案：base64 + XOR
            data = plaintext.encode()
            key_bytes = self.key
            encrypted = bytearray()
            for i, b in enumerate(data):
                encrypted.append(b ^ key_bytes[i % len(key_bytes)])
            return base64.b64encode(bytes(encrypted)).decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密字符串"""
        if not ciphertext:
            return ""

        if HAS_CRYPTOGRAPHY:
            fernet = Fernet(self.key)
            return fernet.decrypt(ciphertext.encode()).decode()
        else:
            # 降级方案：base64 + XOR
            try:
                encrypted = base64.b64decode(ciphertext.encode())
                key_bytes = self.key
                decrypted = bytearray()
                for i, b in enumerate(encrypted):
                    decrypted.append(b ^ key_bytes[i % len(key_bytes)])
                return bytes(decrypted).decode()
            except Exception:
                return ""


# 全局加密实例（使用应用密钥）
encryption = SimpleCrypto()


def encrypt_api_key(api_key: str) -> str:
    """加密API Key"""
    return encryption.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """解密API Key"""
    return encryption.decrypt(encrypted_key)