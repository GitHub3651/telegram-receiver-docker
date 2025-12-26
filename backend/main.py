from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import database
from database import get_db, Account, VerificationCode
import scheduler

app = FastAPI(title="Telegram 接码平台")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
