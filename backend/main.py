from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import database
from database import get_db, Account, VerificationCode
import scheduler
import receiver
import logging
import sys

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

@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库和调度器"""
    database.init_db()
    scheduler.start_scheduler()

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/accounts")
async def get_accounts(db: Session = Depends(get_db)):
    """获取所有账号"""
    accounts = db.query(Account).all()
    return [{
        "id": acc.id,
        "phone": acc.phone,
        "is_active": acc.is_active,
        "created_at": acc.created_at.isoformat()
    } for acc in accounts]

@app.post("/api/accounts/send-code")
async def send_code(request: SendCodeRequest, db: Session = Depends(get_db)):
    """发送 Telegram 验证码"""
    try:
        # 检查账号是否已存在
        existing = db.query(Account).filter(Account.phone == request.phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="该手机号已添加")
        
        # 发送验证码
        await receiver.send_verification_code(request.phone)
        return {"status": "ok", "message": "验证码已发送"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts/verify")
async def verify_and_login(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    """验证码登录并保存账号"""
    try:
        # 执行登录
        session_name = await receiver.verify_and_create_session(
            request.phone, 
            request.code, 
            request.password
        )
        
        # 保存到数据库
        new_account = Account(
            phone=request.phone,
            session_name=session_name,
            is_active=True
        )
        db.add(new_account)
        db.commit()
        db.refresh(new_account)
        
        return {
            "status": "ok",
            "message": "登录成功",
            "account": {
                "id": new_account.id,
                "phone": new_account.phone,
                "created_at": new_account.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 删除 session 文件
    await receiver.delete_session(account.session_name)
    
    # 从数据库删除
    db.delete(account)
    db.commit()
    
    return {"status": "ok", "message": "账号已删除"}

@app.post("/api/accounts/check/{phone}")
async def check_account_codes(phone: str, db: Session = Depends(get_db)):
    """手动触发检查指定账号的验证码"""
    account = db.query(Account).filter(Account.phone == phone).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    try:
        count = await receiver.check_codes_for_account(account.phone, account.session_name)
        
        if count == -1:
            raise HTTPException(status_code=401, detail="Session 已失效，请重新登录")
            
        if count > 0:
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
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取验证码列表"""
    time_threshold = datetime.utcnow() - timedelta(hours=hours)
    codes = db.query(VerificationCode).filter(
        VerificationCode.received_at >= time_threshold
    ).order_by(VerificationCode.received_at.desc()).limit(limit).all()
    
    return [{
        "id": code.id,
        "phone": code.phone,
        "code": code.code,
        "message": code.message,
        "service": code.service,
        "received_at": code.received_at.isoformat()
    } for code in codes]

@app.get("/api/codes/latest/{phone}")
async def get_latest_code(phone: str, db: Session = Depends(get_db)):
    """获取指定手机号的最新验证码"""
    code = db.query(VerificationCode).filter(
        VerificationCode.phone == phone
    ).order_by(VerificationCode.received_at.desc()).first()
    
    if not code:
        raise HTTPException(status_code=404, detail="未找到验证码")
    
    return {
        "code": code.code,
        "message": code.message,
        "received_at": code.received_at.isoformat()
    }

@app.delete("/api/codes")
async def clear_codes(db: Session = Depends(get_db)):
    """清空所有验证码记录"""
    try:
        db.query(VerificationCode).delete()
        db.commit()
        return {"status": "ok", "message": "所有验证码记录已清空"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 使用 log_config=None 以使用上面配置的 logging 格式
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
