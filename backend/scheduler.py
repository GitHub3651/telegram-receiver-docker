from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
import config
import receiver

scheduler = BackgroundScheduler()

def check_codes_job():
    """定时任务：检查验证码"""
    asyncio.run(receiver.check_all_accounts())

def start_scheduler():
    """启动调度器"""
    scheduler.add_job(
        check_codes_job,
        trigger=IntervalTrigger(seconds=config.SCHEDULER_INTERVAL),
        id='check_codes',
        name='检查验证码',
        replace_existing=True
    )
    scheduler.start()
    print(f"✅ 调度器已启动，每 {config.SCHEDULER_INTERVAL} 秒检查一次")
