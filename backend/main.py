from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional
import database
from database import get_db, Account, VerificationCode, User
import scheduler
import receiver
import logging
import sys
import auth
from auth import get_current_user

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram 接码平台")

# 捕获验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ 请求验证失败: {exc}")
    try:
        body = await request.json()
        logger.error(f"❌ 请求体: {body}")
    except:
        logger.error("❌ 无法解析请求体")
    
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class SendCodeRequest(BaseModel):
    phone: str

class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

# --- 认证 API ---

@app.post("/api/auth/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # 统一转换为小写
    email = req.email.lower()

    # 1. 校验邮箱格式
    if not auth.validate_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    
    # 2. 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 3. 创建用户
    hashed_password = auth.get_password_hash(req.password)
    new_user = User(email=email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "注册成功", "user_id": new_user.id}

@app.post("/api/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    # 统一转换为小写
    email = req.email.lower()

    # 1. 查询用户
    user = db.query(User).filter(User.email == email).first()
    
    # 2. 检查用户是否存在
    if not user:
        raise HTTPException(status_code=400, detail="该邮箱未注册")
        
    # 3. 检查密码
    if not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被封禁")
    
    # 4. 生成 Token
    access_token = auth.create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "is_active": current_user.is_active
    }

@app.put("/api/auth/me/password")
async def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    current_user.password_hash = auth.get_password_hash(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}

@app.delete("/api/auth/me")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 删除用户的所有 Session 文件
    import os
    import glob
    
    # 查找该用户的所有 session 文件
    session_files = glob.glob(f"sessions/user_{current_user.id}_*.session")
    for f in session_files:
        try:
            os.remove(f)
        except Exception as e:
            logger.error(f"删除 Session 文件失败: {f}, {e}")
            
    # 删除数据库记录 (级联删除 accounts 和 codes)
    db.delete(current_user)
    db.commit()
    return {"message": "账号已注销"}

@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库和调度器"""
    database.init_db()
    scheduler.start_scheduler()

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/accounts")
async def get_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的所有账号"""
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    return [{
        "id": acc.id,
        "phone": acc.phone,
        "is_active": acc.is_active,
        "created_at": acc.created_at.isoformat()
    } for acc in accounts]

@app.post("/api/accounts/send-code")
async def send_code(
    request: SendCodeRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发送 Telegram 验证码"""
    try:
        # 检查账号是否已存在 (仅检查当前用户)
        existing = db.query(Account).filter(
            Account.phone == request.phone,
            Account.user_id == current_user.id
        ).first()
        if existing and existing.is_active:
            raise HTTPException(status_code=400, detail="已存在该账号")
        
        # 发送验证码
        await receiver.send_verification_code(request.phone)
        return {"status": "ok", "message": "验证码已发送"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts/verify")
async def verify_and_login(
    request: VerifyCodeRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """验证码登录并保存账号"""
    try:
        # 再次检查账号是否已存在 (仅检查当前用户)
        existing = db.query(Account).filter(
            Account.phone == request.phone,
            Account.user_id == current_user.id
        ).first()
        if existing and existing.is_active:
            raise HTTPException(status_code=400, detail="已存在该账号")

        # 生成唯一的 session 名: user_{user_id}_{phone}
        clean_phone = request.phone.replace('+', '').replace(' ', '')
        target_session_name = f"user_{current_user.id}_{clean_phone}"

        # 执行登录
        session_name = await receiver.verify_and_create_session(
            request.phone, 
            request.code, 
            request.password,
            target_session_name=target_session_name
        )
        
        if existing:
            # 更新现有账号
            existing.session_name = session_name
            existing.is_active = True
            # existing.created_at = datetime.now(timezone.utc) # 保持原创建时间
            db.commit()
            db.refresh(existing)
            account_data = existing
        else:
            # 保存到数据库
            new_account = Account(
                phone=request.phone,
                session_name=session_name,
                is_active=True,
                user_id=current_user.id
            )
            db.add(new_account)
            db.commit()
            db.refresh(new_account)
            account_data = new_account
        
        return {
            "status": "ok",
            "message": "登录成功",
            "account": {
                "id": account_data.id,
                "phone": account_data.phone,
                "created_at": account_data.created_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除账号"""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 删除 session 文件
    await receiver.delete_session(account.session_name)
    
    # 从数据库删除
    db.delete(account)
    db.commit()
    
    return {"status": "ok", "message": "账号已删除"}

@app.post("/api/accounts/check/{account_id}")
async def check_account_codes(
    account_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动触发检查指定账号的验证码"""
    logger.info(f"Checking account {account_id} for user {current_user.id}")
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        logger.warning(f"Account {account_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="账号不存在")
    
    try:
        count = await receiver.check_codes_for_account(
            account.phone, 
            account.session_name,
            account_id=account.id
        )
        
        if count == -1:
            # Session 失效，更新数据库状态
            account.is_active = False
            db.commit()
            raise HTTPException(status_code=409, detail="Session 已失效，请重新登录")
            
        if count > 0:
            # 如果成功获取到验证码，确保账号状态为活跃
            if not account.is_active:
                account.is_active = True
                db.commit()
            return {"status": "ok", "message": f"检查完成，发现 {count} 个有效验证码"}
        else:
            # 虽然成功执行了检查，但没有新验证码，返回特定消息供前端判断
            return {"status": "ok", "message": "未发现验证码（检查了最近30分钟消息）"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")

@app.get("/api/codes")
async def get_codes(
    phone: Optional[str] = None,
    account_id: Optional[int] = None,
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取验证码列表"""
    time_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    
    query = db.query(VerificationCode).join(
        Account, VerificationCode.account_id == Account.id
    ).filter(
        VerificationCode.received_at >= time_threshold,
        Account.user_id == current_user.id
    )
    
    if account_id:
        query = query.filter(Account.id == account_id)
    elif phone:
        query = query.filter(Account.phone == phone)
        
    codes = query.order_by(VerificationCode.received_at.desc()).limit(limit).all()
    
    return [{
        "id": code.id,
        "phone": code.phone,
        "code": code.code,
        "message": code.message,
        "service": code.service,
        "received_at": code.received_at.isoformat()
    } for code in codes]

@app.get("/api/codes/latest/account/{account_id}")
async def get_latest_code_by_id(
    account_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定账号ID的最新验证码"""
    # 检查该账号是否属于当前用户
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在或不属于您")

    code = db.query(VerificationCode).filter(
        VerificationCode.account_id == account.id
    ).order_by(VerificationCode.received_at.desc()).first()
    
    if not code:
        raise HTTPException(status_code=404, detail="未找到验证码")
    
    return {
        "code": code.code,
        "message": code.message,
        "received_at": code.received_at.isoformat()
    }

@app.get("/api/codes/latest/{phone}")
async def get_latest_code(
    phone: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定手机号的最新验证码"""
    # 检查该手机号是否属于当前用户
    account = db.query(Account).filter(
        Account.phone == phone,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在或不属于您")

    code = db.query(VerificationCode).filter(
        VerificationCode.phone == phone,
        VerificationCode.account_id == account.id
    ).order_by(VerificationCode.received_at.desc()).first()
    
    if not code:
        raise HTTPException(status_code=404, detail="未找到验证码")
    
    return {
        "code": code.code,
        "message": code.message,
        "received_at": code.received_at.isoformat()
    }

@app.delete("/api/codes")
async def clear_codes(
    phone: Optional[str] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """清空验证码记录"""
    try:
        query = db.query(VerificationCode).filter(
            VerificationCode.account_id.in_(
                db.query(Account.id).filter(Account.user_id == current_user.id)
            )
        )
        
        if account_id:
            # 验证该账号是否属于当前用户
            account = db.query(Account).filter(
                Account.id == account_id, 
                Account.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(status_code=404, detail="账号不存在")
            
            query = query.filter(VerificationCode.account_id == account.id)
        elif phone:
            # 验证该手机号是否属于当前用户
            account = db.query(Account).filter(
                Account.phone == phone, 
                Account.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(status_code=404, detail="账号不存在")
            
            query = query.filter(VerificationCode.account_id == account.id)
            
        query.delete(synchronize_session=False)
        db.commit()
        return {"status": "ok", "message": "验证码记录已清空"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 使用 log_config=None 以使用上面配置的 logging 格式
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
