from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import os
import re
from datetime import datetime, timedelta, timezone
import config
from database import SessionLocal, Account, VerificationCode

# 用于临时存储登录过程中的 client
_login_clients = {}

async def send_verification_code(phone: str):
    """发送 Telegram 验证码"""
    # 确保目录存在
    os.makedirs(config.SESSION_DIR, exist_ok=True)
    
    session_name = f"temp_{phone.replace('+', '').replace(' ', '')}"
    session_path = os.path.join(config.SESSION_DIR, session_name)
    
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    
    try:
        await client.connect()
        await client.send_code_request(phone)
        _login_clients[phone] = client
        print(f"✅ 验证码已发送到 {phone}")
    except Exception as e:
        await client.disconnect()
        # 删除临时 session 文件
        if os.path.exists(f"{session_path}.session"):
            os.remove(f"{session_path}.session")
        raise Exception(f"发送验证码失败: {str(e)}")

async def verify_and_create_session(phone: str, code: str, password: str = None, target_session_name: str = None):
    """验证登录并创建 session"""
    client = _login_clients.get(phone)
    if not client:
        raise Exception("请先发送验证码")
    
    # 如果指定了目标 session 名，则使用指定的，否则使用默认的 (兼容旧逻辑)
    if target_session_name:
        final_session_name = target_session_name
    else:
        final_session_name = phone.replace('+', '').replace(' ', '')
        
    temp_session = f"temp_{phone.replace('+', '').replace(' ', '')}"
    
    try:
        # 尝试登录
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            # 需要两步验证密码
            if not password:
                await client.disconnect()
                del _login_clients[phone]
                raise Exception("该账号开启了两步验证，请输入密码")
            await client.sign_in(password=password)
        
        # 登录成功
        print(f"✅ 账号 {phone} 登录成功")
        
        # 断开连接
        await client.disconnect()
        
        # 重命名 session 文件
        old_path = os.path.join(config.SESSION_DIR, f"{temp_session}.session")
        new_path = os.path.join(config.SESSION_DIR, f"{final_session_name}.session")
        
        if os.path.exists(old_path):
            # 如果目标文件已存在，先删除
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(old_path, new_path)
            print(f"✅ Session 文件已保存: {final_session_name}.session")
        else:
            raise Exception(f"Session 文件不存在: {old_path}")
        
        # 清理临时 client
        if phone in _login_clients:
            del _login_clients[phone]
        
        return final_session_name
        
    except Exception as e:
        # 打印详细错误堆栈
        import traceback
        traceback.print_exc()
        print(f"❌ 登录过程出错: {str(e)}")

        # 清理
        if client:
            try:
                await client.disconnect()
            except:
                pass
        if phone in _login_clients:
            del _login_clients[phone]
        
        # 删除临时 session 文件
        temp_path = os.path.join(config.SESSION_DIR, f"{temp_session}.session")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        # 提取错误信息
        error_msg = str(e)
        if "PHONE_CODE_INVALID" in error_msg:
            raise Exception("验证码错误，请检查后重试")
        elif "SESSION_PASSWORD_NEEDED" in error_msg:
            raise Exception("该账号开启了两步验证，请输入密码")
        elif "PHONE_CODE_EXPIRED" in error_msg:
            raise Exception("验证码已过期，请重新发送")
        elif "API_ID_INVALID" in error_msg:
            raise Exception("API ID 或 Hash 无效，请检查配置文件")
        elif "FLOOD_WAIT" in error_msg:
            raise Exception("请求过于频繁，请稍后再试")
        else:
            raise Exception(f"登录失败: {error_msg}")

async def delete_session(session_name: str):
    """删除 session 文件"""
    session_path = os.path.join(config.SESSION_DIR, f"{session_name}.session")
    if os.path.exists(session_path):
        os.remove(session_path)
        print(f"✅ Session 文件已删除: {session_name}")

async def check_codes_for_account(phone: str, session_name: str, account_id: int = None):
    """检查单个账号的验证码"""
    session_path = os.path.join(config.SESSION_DIR, session_name)
    
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    db = SessionLocal()
    new_codes_count = 0
    valid_codes_count = 0
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"⚠️ 账号 {phone} 未授权 (Session 已失效)")
            return -1
        
        # 获取最近30分钟的消息
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        print(f"🔍 正在检查账号 {phone} 的消息 (最近30分钟)...")
        
        # 仅监听官方账号 777000
        async for message in client.iter_messages(777000, limit=20):
            if not message.message or message.date < time_threshold:
                continue
            
            # 提取验证码
            code_match = re.search(r'\b(\d{5,6})\b', message.message)
            if code_match:
                valid_codes_count += 1
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
                        received_at=message.date,
                        service="Telegram",
                        account_id=account_id
                    )
                    db.add(new_code)
                    db.commit()
                    new_codes_count += 1
                    print(f"✅ 新验证码: {phone} -> {code}")
        
        return valid_codes_count
    
    except Exception as e:
        print(f"❌ 检查账号 {phone} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    finally:
        await client.disconnect()
        db.close()

async def keep_alive_account(phone: str, session_name: str):
    """仅进行 Session 保活，不检查验证码"""
    client = TelegramClient(
        f"sessions/{session_name}", 
        config.API_ID, 
        config.API_HASH,
        device_model="Desktop",
        system_version="Linux",
        app_version="1.0",
        lang_code="en"
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"⚠️ 保活失败: 账号 {phone} 未授权 (Session 已失效)")
            return
        
        # 获取自身信息作为保活操作
        me = await client.get_me()
        print(f"✅ 账号保活成功: {phone} (ID: {me.id})")
        
    except Exception as e:
        print(f"❌ 账号保活出错 {phone}: {e}")
    
    finally:
        await client.disconnect()

async def keep_alive_all_accounts():
    """对所有账号进行保活"""
    db = SessionLocal()
    accounts = db.query(Account).filter(Account.is_active == True).all()
    db.close()
    
    print(f"🔄 开始执行账号保活任务 ({len(accounts)} 个账号)...")
    
    for account in accounts:
        await keep_alive_account(account.phone, account.session_name)

async def check_all_accounts():
    """检查所有账号的验证码"""
    db = SessionLocal()
    accounts = db.query(Account).filter(Account.is_active == True).all()
    db.close()
    
    print(f"🔍 开始检查 {len(accounts)} 个账号...")
    
    for account in accounts:
        await check_codes_for_account(account.phone, account.session_name, account_id=account.id)
