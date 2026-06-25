"""
用户认证API - 登录、注册
使用简单Token进行身份验证（适合内部系统）
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
import hashlib
import secrets
from datetime import datetime
from db.db_conn import get_db_session
from db.models import User

router = APIRouter()

# 简单的Token存储（生产环境应使用Redis或数据库）
active_tokens = {}

# 请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

def hash_password(password: str) -> str:
    """密码哈希（SHA256）"""
    return hashlib.sha256(password.encode()).hexdigest()

async def get_current_user(authorization: str = Header(None)):
    """从Header中获取当前用户（依赖注入）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    token = authorization.replace("Bearer ", "")
    
    # 查找token对应的用户
    if token in active_tokens:
        user_info = active_tokens[token]
        return user_info
    else:
        raise HTTPException(status_code=401, detail="无效的认证令牌")

@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        db = get_db_session()
        
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            db.close()
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建新用户
        new_user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            role=request.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()
        
        return {
            "success": True,
            "message": "注册成功",
            "user_id": new_user.user_id,
            "username": new_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@router.post("/login")
async def login(request: LoginRequest):
    """用户登录"""
    try:
        db = get_db_session()
        
        # 查找用户
        user = db.query(User).filter(User.username == request.username).first()
        if not user:
            db.close()
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 验证密码
        password_hash = hash_password(request.password)
        if user.password_hash != password_hash:
            db.close()
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 生成随机Token
        token = secrets.token_hex(32)
        
        # 存储Token（包含用户信息）
        active_tokens[token] = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "login_time": datetime.now().isoformat()
        }
        
        db.close()
        
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """用户登出"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token in active_tokens:
            del active_tokens[token]
            return {"success": True, "message": "登出成功"}
    
    raise HTTPException(status_code=400, detail="无效的请求")
