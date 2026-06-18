"""Authentication service - JWT token generation and user validation."""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from fastapi import HTTPException, status

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# users.json 路径
USERS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "users.json"
)


def load_users():
    """从 users.json 加载用户列表."""
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_user(name: str, password: str) -> Optional[dict]:
    """验证用户名和密码，返回用户信息或 None."""
    users = load_users()
    for user in users:
        if user.get("name") == name and user.get("password") == password:
            return user
    return None


def create_access_token(name: str) -> str:
    """为用户创建 JWT token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": name,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def authenticate(name: str, password: str) -> dict:
    """认证用户，成功返回 token，失败抛出 HTTPException."""
    user = verify_user(name, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    token = create_access_token(name)
    return {"access_token": token, "token_type": "bearer"}
