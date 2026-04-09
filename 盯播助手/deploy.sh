#!/bin/bash

# 盯播助手部署脚本
#
# @author: exbox0403-cmd
# @since: 2026/4/8

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 命令未找到，请先安装 $1"
        exit 1
    fi
}

# 检查Docker和Docker Compose
check_prerequisites() {
    print_message "检查前置条件..."

    check_command "docker"
    check_command "docker-compose"

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi

    print_success "前置条件检查通过"
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."

    mkdir -p logs/{backend,python,mysql,redis,rabbitmq}
    mkdir -p data/{mysql,redis,rabbitmq}
    mkdir -p config

    print_success "目录创建完成"
}

# 环境变量配置
setup_environment() {
    print_message "设置环境变量..."

    if [ ! -f .env ]; then
        cat > .env << EOL
# 微信配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# AI服务配置
AI_API_BASE_URL=https://api.deepseek.com
AI_API_KEY=your_ai_api_key

# JWT配置
JWT_SECRET=your_jwt_secret_key_change_this_in_production

# 数据库配置
DB_HOST=mysql
DB_PORT=3306
DB_NAME=stream_monitor
DB_USERNAME=stream_user
DB_PASSWORD=stream_password

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# RabbitMQ配置
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=stream_user
RABBITMQ_PASSWORD=stream_password

# 其他配置
ENVIRONMENT=production
DEBUG=false
EOL
        print_warning "已创建 .env 文件，请根据实际环境修改配置"
    else
        print_message ".env 文件已存在，跳过创建"
    fi

    print_success "环境变量设置完成"
}

# 构建Docker镜像
build_images() {
    print_message "构建Docker镜像..."

    # 检查Dockerfile是否存在
    if [ ! -f docker/Dockerfile.backend ]; then
        print_error "Dockerfile.backend 不存在"
        exit 1
    fi

    if [ ! -f docker/Dockerfile.python ]; then
        print_error "Dockerfile.python 不存在"
        exit 1
    fi

    # 构建镜像
    docker-compose -f docker/docker-compose.yml build

    print_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    print_message "启动服务..."

    # 启动服务
    docker-compose -f docker/docker-compose.yml up -d

    # 等待服务启动
    print_message "等待服务启动..."
    sleep 30

    # 检查服务状态
    docker-compose -f docker/docker-compose.yml ps

    print_success "服务启动完成"
}

# 健康检查
health_check() {
    print_message "执行健康检查..."

    # 检查MySQL
    if docker-compose -f docker/docker-compose.yml exec mysql mysqladmin ping -h localhost -u root -proot123 &> /dev/null; then
        print_success "MySQL服务正常"
    else
        print_error "MySQL服务异常"
    fi

    # 检查Redis
    if docker-compose -f docker/docker-compose.yml exec redis redis-cli ping &> /dev/null; then
        print_success "Redis服务正常"
    else
        print_error "Redis服务异常"
    fi

    # 检查RabbitMQ
    if docker-compose -f docker/docker-compose.yml exec rabbitmq rabbitmqctl status &> /dev/null; then
        print_success "RabbitMQ服务正常"
    else
        print_error "RabbitMQ服务异常"
    fi

    # 检查后端服务
    sleep 10
    if curl -f -s http://localhost:8080/api/health > /dev/null; then
        print_success "Spring Boot后端服务正常"
    else
        print_warning "Spring Boot后端服务检查失败，可能还在启动中"
    fi

    # 检查Python服务
    if curl -f -s http://localhost:5000/health > /dev/null; then
        print_success "Python服务正常"
    else
        print_warning "Python服务检查失败，可能还在启动中"
    fi

    print_success "健康检查完成"
}

# 初始化数据库
init_database() {
    print_message "初始化数据库..."

    # 等待MySQL完全启动
    sleep 20

    # 执行数据库初始化脚本
    docker-compose -f docker/docker-compose.yml exec mysql mysql -u root -proot123 stream_monitor < database/init.sql

    print_success "数据库初始化完成"
}

# 显示服务信息
show_service_info() {
    print_message "服务信息:"
    echo ""
    echo "MySQL: localhost:3306 (root/root123)"
    echo "Redis: localhost:6379 (password: redis_password)"
    echo "RabbitMQ: localhost:5672 (stream_user/stream_password)"
    echo "RabbitMQ管理界面: http://localhost:15672 (stream_user/stream_password)"
    echo "Spring Boot后端: http://localhost:8080/api"
    echo "Python服务: http://localhost:5000"
    echo "Nginx: http://localhost"
    echo "Prometheus: http://localhost:9090"
    echo "Grafana: http://localhost:3000 (admin/admin123)"
    echo ""
}

# 清理服务
cleanup() {
    print_message "清理服务..."

    docker-compose -f docker/docker-compose.yml down -v

    print_success "服务清理完成"
}

# 查看日志
view_logs() {
    print_message "查看服务日志..."

    docker-compose -f docker/docker-compose.yml logs -f
}

# 显示帮助信息
show_help() {
    cat << EOL
盯播助手部署脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -c, --check         检查前置条件
    -d, --dirs          创建目录
    -e, --env           设置环境变量
    -b, --build         构建镜像
    -s, --start         启动服务
    -h, --health        健康检查
    -i, --init-db       初始化数据库
    -a, --all           执行完整部署流程
    -l, --logs          查看日志
    -cl, --cleanup      清理服务
    -i, --info          显示服务信息

示例:
    $0 --all              # 完整部署
    $0 --start            # 仅启动服务
    $0 --logs             # 查看日志
    $0 --cleanup          # 清理服务

EOL
}

# 主函数
main() {
    case "$1" in
        -h|--help)
            show_help
            ;;
        -c|--check)
            check_prerequisites
            ;;
        -d|--dirs)
            create_directories
            ;;
        -e|--env)
            setup_environment
            ;;
        -b|--build)
            build_images
            ;;
        -s|--start)
            start_services
            ;;
        --health)
            health_check
            ;;
        -i|--init-db)
            init_database
            ;;
        -a|--all)
            check_prerequisites
            create_directories
            setup_environment
            build_images
            start_services
            health_check
            init_database
            show_service_info
            ;;
        -l|--logs)
            view_logs
            ;;
        -cl|--cleanup)
            cleanup
            ;;
        --info)
            show_service_info
            ;;
        *)
            if [ -z "$1" ]; then
                show_help
            else
                print_error "未知选项: $1"
                show_help
                exit 1
            fi
            ;;
    esac
}

# 执行主函数
main "$@"