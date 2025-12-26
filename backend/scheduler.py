from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import config
import receiver
import random
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

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
    
    scheduler.start()
    print("✅ 调度器已启动，任务模式：随机 4-5 天保活")
