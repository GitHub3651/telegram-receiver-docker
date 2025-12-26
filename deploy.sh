#!/bin/bash

# Telegram 接码平台 Docker 一键部署脚本
# 适用于: Ubuntu 22.04 / Debian 11+ / CentOS 7+

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║       Telegram 接码平台 Docker 一键部署脚本             ║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        print_info "检测到操作系统: $OS $VER"
    else
        print_error "无法检测操作系统版本"
        exit 1
    fi
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_warning "此脚本需要 root 权限运行"
        print_info "正在尝试使用 sudo 重新运行..."
        sudo "$0" "$@"
        exit $?
    fi
}

# 安装 Docker
install_docker() {
    print_info "检查 Docker 安装状态..."
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker 已安装: $DOCKER_VERSION"
        return 0
    fi
    
    print_info "开始安装 Docker..."
    
    # 安装依赖
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt-get update
        apt-get install -y ca-certificates curl gnupg lsb-release
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum install -y yum-utils
    fi
    
    # 使用官方安装脚本
    curl -fsSL https://get.docker.com | sh
    
    # 启动 Docker
    systemctl start docker
    systemctl enable docker
    
    print_success "Docker 安装完成"
}

# 安装 Docker Compose
install_docker_compose() {
    print_info "检查 Docker Compose 安装状态..."
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose 已安装: $COMPOSE_VERSION"
        return 0
    fi
    
    print_info "开始安装 Docker Compose..."
    
    # 获取最新版本
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # 下载并安装
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    print_success "Docker Compose 安装完成"
}

# 配置防火墙
configure_firewall() {
    print_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian 使用 UFW
        ufw allow 22/tcp comment 'SSH'
        ufw allow 80/tcp comment 'HTTP'
        ufw allow 443/tcp comment 'HTTPS'
        echo "y" | ufw enable
        print_success "UFW 防火墙配置完成"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL 使用 firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        print_success "Firewalld 防火墙配置完成"
    else
        print_warning "未检测到防火墙，请手动开放 22, 80, 443 端口"
    fi
}

# 创建配置文件
create_config() {
    print_info "创建配置文件..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        
        # 生成随机密码和密钥
        DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        SECRET_KEY=$(openssl rand -hex 32)
        
        # 替换配置文件
        sed -i "s/your_strong_password_here_CHANGE_THIS/$DB_PASSWORD/g" .env
        sed -i "s/your_secret_key_here_CHANGE_THIS/$SECRET_KEY/g" .env
        
        print_success "配置文件创建完成"
        print_warning "请编辑 .env 文件，修改域名等配置"
        print_info "数据库密码: $DB_PASSWORD"
        print_info "SECRET_KEY: $SECRET_KEY"
    else
        print_success ".env 文件已存在"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p sessions logs backups nginx/ssl
    chmod 700 sessions
    chmod 755 logs backups
    
    print_success "目录创建完成"
}

# 构建前端
build_frontend() {
    print_info "构建前端..."
    
    if [ ! -d "frontend/dist" ]; then
        if command -v npm &> /dev/null; then
            cd frontend
            npm install
            npm run build
            cd ..
            print_success "前端构建完成"
        else
            print_warning "未安装 Node.js，跳过前端构建"
            print_info "请手动安装 Node.js 并运行: cd frontend && npm install && npm run build"
        fi
    else
        print_success "前端已构建"
    fi
}

# 启动服务
start_services() {
    print_info "启动 Docker 容器..."
    
    # 拉取镜像
    docker-compose pull
    
    # 构建自定义镜像
    docker-compose build
    
    # 启动服务
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    docker-compose ps
    
    print_success "服务启动完成"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    # 等待数据库就绪
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U telegram_user > /dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    
    # 运行初始化脚本
    docker-compose exec -T backend python init_db.py
    
    print_success "数据库初始化完成"
}

# 显示访问信息
show_access_info() {
    # 获取服务器 IP
    SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "无法获取")
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║                   🎉 部署完成！                          ║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    print_success "访问地址: http://$SERVER_IP"
    echo ""
    print_info "常用命令:"
    echo "  查看服务状态: docker-compose ps"
    echo "  查看日志:     docker-compose logs -f"
    echo "  重启服务:     docker-compose restart"
    echo "  停止服务:     docker-compose stop"
    echo "  启动服务:     docker-compose start"
    echo ""
    print_info "下一步:"
    echo "  1. 访问 Web 界面添加 Telegram 账号"
    echo "  2. 配置 SSL 证书（可选）"
    echo "  3. 设置定时备份（可选）"
    echo ""
    print_warning "请妥善保管 .env 文件中的密码！"
    echo ""
}

# 主函数
main() {
    print_header
    
    # 检查权限
    check_root
    
    # 检测系统
    detect_os
    
    # 安装依赖
    install_docker
    install_docker_compose
    
    # 配置系统
    configure_firewall
    create_config
    create_directories
    
    # 构建项目
    build_frontend
    
    # 启动服务
    start_services
    
    # 初始化数据库
    init_database
    
    # 显示访问信息
    show_access_info
}

# 运行主函数
main
