#!/usr/bin/env python3
"""数据库初始化脚本"""

import database

if __name__ == "__main__":
    print("🚀 开始初始化数据库...")
    database.init_db()
    print("✅ 数据库初始化完成！")
