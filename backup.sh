#!/bin/bash

# Telegram 接码平台备份脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 配置
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_NAME="telegram-backup-$TIMESTAMP"
TEMP_DIR="/tmp/$BACKUP_NAME"

print_info "开始备份..."

# 创建备份目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$TEMP_DIR"

# 1. 备份数据库
print_info "备份数据库..."
docker-compose exec -T postgres pg_dump -U telegram_user -d telegram_codes > "$TEMP_DIR/database.sql"
print_success "数据库备份完成"

# 2. 备份 session 文件
print_info "备份 Session 文件..."
cp -r ./sessions "$TEMP_DIR/"
print_success "Session 文件备份完成"

# 3. 备份配置文件
print_info "备份配置文件..."
cp .env "$TEMP_DIR/"
cp docker-compose.yml "$TEMP_DIR/"
print_success "配置文件备份完成"

# 4. 打包压缩
print_info "压缩备份文件..."
cd /tmp
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
mv "$BACKUP_NAME.tar.gz" "$OLDPWD/$BACKUP_DIR/"
cd "$OLDPWD"

# 清理临时文件
rm -rf "$TEMP_DIR"

# 计算备份大小
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)

print_success "备份完成！"
print_info "备份文件: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
print_info "文件大小: $BACKUP_SIZE"

# 清理旧备份（保留最近 7 天）
find "$BACKUP_DIR" -name "telegram-backup-*.tar.gz" -mtime +7 -delete
print_info "已清理 7 天前的旧备份"

echo ""
print_info "恢复命令:"
echo "  tar -xzf $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "  docker-compose down"
echo "  cat $BACKUP_NAME/database.sql | docker-compose exec -T postgres psql -U telegram_user -d telegram_codes"
echo "  cp -r $BACKUP_NAME/sessions/* ./sessions/"
echo "  docker-compose up -d"
