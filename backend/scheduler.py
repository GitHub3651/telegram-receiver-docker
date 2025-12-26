from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import config
import receiver
import random
from datetime import datetime, timedelta, timezone
from database import SessionLocal, VerificationCode

scheduler = BackgroundScheduler()

def cleanup_old_codes():
    """清理超过7天的验证码"""
    db = SessionLocal()
    try:
        seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        deleted_count = db.query(VerificationCode).filter(VerificationCode.received_at < seven_days_ago).delete()
        db.commit()
        if deleted_count > 0:
            print(f"🧹 已清理 {deleted_count} 条过期验证码")
    except Exception as e:
        print(f"❌ 清理验证码失败: {e}")
    finally:
        db.close()

def schedule_next_job():
    """安排下一次保活任务"""
    # 随机 4-5 天 (秒)
    min_seconds = 4 * 24 * 3600  # 345600
    max_seconds = 5 * 24 * 3600  # 432000
    interval = random.randint(min_seconds, max_seconds)
    
    run_date = datetime.now() + timedelta(seconds=interval)
    
    scheduler.add_job(
        keep_alive_job,
        'date',
        run_date=run_date,
        id='keep_alive_job',
        name='账号保活任务',
        replace_existing=True
    )
    print(f"📅 下次保活任务将于 {run_date.strftime('%Y-%m-%d %H:%M:%S')} 执行 (间隔 {interval/3600:.1f} 小时)")

def keep_alive_job():
    """定时任务：账号保活"""
    asyncio.run(receiver.keep_alive_all_accounts())
    schedule_next_job()

def start_scheduler():
    """启动调度器"""
    # 启动时先安排第一次任务
    schedule_next_job()
    
    # 每天执行一次清理任务
    scheduler.add_job(cleanup_old_codes, 'interval', hours=24, id='cleanup_codes', name='清理过期验证码')
    
    scheduler.start()
    print("✅ 调度器已启动，任务模式：随机 4-5 天保活 + 每日清理过期验证码")
