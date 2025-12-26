from telethon import TelegramClient
import os
import re
from datetime import datetime, timedelta, timezone
import config
from database import SessionLocal, Account, VerificationCode

async def check_codes_for_account(phone: str, session_name: str):
    """检查单个账号的验证码"""
    session_path = os.path.join(config.SESSION_DIR, session_name)
    
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    db = SessionLocal()
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"⚠️ 账号 {phone} 未授权，跳过")
            return
        
        # 获取最近5分钟的消息
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        async for message in client.iter_messages(777000, limit=10):
            if not message.message or message.date < time_threshold:
                continue
            
            # 提取验证码
            code_match = re.search(r'\b(\d{5,6})\b', message.message)
            if code_match:
                code = code_match.group(1)
                
                # 检查是否已存在
                existing = db.query(VerificationCode).filter(
                    VerificationCode.phone == phone,
                    VerificationCode.code == code,
                    VerificationCode.received_at >= time_threshold
                ).first()
                
                if not existing:
                    new_code = VerificationCode(
                        phone=phone,
                        code=code,
                        message=message.message,
                        received_at=message.date
                    )
                    db.add(new_code)
                    db.commit()
                    print(f"✅ 新验证码: {phone} -> {code}")
    
    except Exception as e:
        print(f"❌ 检查账号 {phone} 时出错: {e}")
    
    finally:
        await client.disconnect()
        db.close()

async def check_all_accounts():
    """检查所有账号的验证码"""
    db = SessionLocal()
    accounts = db.query(Account).filter(Account.is_active == True).all()
    db.close()
    
    print(f"🔍 开始检查 {len(accounts)} 个账号...")
    
    for account in accounts:
        await check_codes_for_account(account.phone, account.session_name)
