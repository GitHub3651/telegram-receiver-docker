import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://telegram_user:password@postgres:5432/telegram_codes')

# Telegram API 配置
API_ID = int(os.getenv('API_ID', '2040'))
API_HASH = os.getenv('API_HASH', 'b18441a1ff607e10a989891a5462e627')

# 应用配置
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', '300'))

# 目录配置
SESSION_DIR = './sessions'
LOG_DIR = './logs'
