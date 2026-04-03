#!/bin/bash

# 🎯 数字人聊天系统演示脚本
# 运行此脚本快速体验项目功能

echo "🚀 数字人聊天系统演示"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的文本
print_status() {
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

# 检查必要工具
check_requirements() {
    print_status "检查系统要求..."

    # 检查Java
    if command -v java &> /dev/null; then
        print_success "Java已安装: $(java -version 2>&1 | head -n 1)"
    else
        print_error "Java未安装，请先安装Java 17+"
        exit 1
    fi

    # 检查Python
    if command -v python &> /dev/null; then
        print_success "Python已安装: $(python --version 2>&1)"
    else
        print_error "Python未安装，请先安装Python 3.8+"
        exit 1
    fi

    # 检查Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js已安装: $(node --version)"
    else
        print_warning "Node.js未安装，前端演示可能受限"
    fi

    echo ""
}

# 显示项目结构
show_project_structure() {
    print_status "项目结构概览:"
    echo ""
    tree -L 2 --dirsfirst 2>/dev/null || find . -maxdepth 2 -type d | head -20
    echo ""
}

# 演示后端功能
demo_backend() {
    print_status "演示后端功能..."
    echo ""

    # 检查后端文件
    if [ -f "digital-person-backend/pom.xml" ]; then
        print_success "✅ Spring Boot后端项目已就绪"
        echo "   📁 位置: digital-person-backend/"
        echo "   🔧 技术栈: Spring Boot 3.2 + Java 17"
        echo "   🚀 启动命令: cd digital-person-backend && mvn spring-boot:run"
        echo ""
    fi
}

# 演示前端功能
demo_frontend() {
    print_status "演示前端功能..."
    echo ""

    if [ -f "digital-person-frontend/pages/chat/chat.vue" ]; then
        print_success "✅ Uni-app前端项目已就绪"
        echo "   📁 位置: digital-person-frontend/"
        echo "   🎨 技术栈: Uni-app + Vue 3"
        echo "   💬 功能: 微信风格聊天界面"
        echo "   🚀 启动命令: cd digital-person-frontend && npm run dev:h5"
        echo ""
    fi
}

# 演示数据清洗功能
demo_data_pipeline() {
    print_status "演示数据清洗流水线..."
    echo ""

    if [ -f "data-pipeline/data_cleaner.py" ]; then
        print_success "✅ Python数据清洗引擎已就绪"
        echo "   📁 位置: data-pipeline/"
        echo "   🧹 功能: 微信聊天记录清洗 + QA对齐"
        echo "   📊 输出格式: JSONL"
        echo "   🚀 使用命令: python data-pipeline/data_cleaner.py"
        echo ""

        # 生成示例数据
        if [ ! -f "data/raw_chat.txt" ]; then
            print_status "生成示例数据..."
            python data-pipeline/sample_data_generator.py 2>/dev/null || echo "   ⚠️  示例数据生成失败，请手动运行脚本"
        fi
    fi
}

# 演示RAG功能
demo_rag() {
    print_status "演示RAG检索增强..."
    echo ""

    if [ -f "rag-engine/rag_engine.py" ]; then
        print_success "✅ RAG引擎已就绪"
        echo "   📁 位置: rag-engine/"
        echo "   🧠 技术: Sentence Transformers + FAISS"
        echo "   🔍 功能: 向量检索 + 记忆增强"
        echo "   🚀 启动命令: cd rag-engine && python rag_server.py"
        echo ""
    fi
}

# 演示Agent工具
demo_agent() {
    print_status "演示AI Agent工具..."
    echo ""

    if [ -f "agent-tools/tools.py" ]; then
        print_success "✅ AI Agent工具系统已就绪"
        echo "   📁 位置: agent-tools/"
        echo "   🛠️  内置工具:"
        echo "      • GitHub项目搜索"
        echo "      • 天气查询"
        echo "      • 时间获取"
        echo "      • 数学计算"
        echo "   🚀 启动命令: cd agent-tools && python agent_server.py"
        echo ""
    fi
}

# 演示API接口
demo_apis() {
    print_status "API接口演示..."
    echo ""

    echo "📡 主要API接口:"
    echo ""

    echo "🔹 聊天接口 (后端)"
    echo "   POST /api/chat"
    echo "   请求: {'message': '你好'}"
    echo "   响应: {'response': '你好！我是李四...', 'success': true}"
    echo ""

    echo "🔹 RAG查询 (Python)"
    echo "   POST /rag-query"
    echo "   请求: {'query': '你会做什么项目？', 'target_persona': '李四'}"
    echo "   响应: {'enhanced_prompt': '...', 'success': true}"
    echo ""

    echo "🔹 Agent工具 (Python)"
    echo "   POST /agent-chat"
    echo "   请求: {'message': '现在几点了？'}"
    echo "   响应: {'response': '现在是：...', 'tool_used': 'get_current_time'}"
    echo ""
}

# 演示使用示例
demo_examples() {
    print_status "使用示例演示..."
    echo ""

    echo "💬 聊天示例:"
    echo "   用户: 你好，你是谁？"
    echo "   AI: 你好！我是李四，很高兴认识你！我平时喜欢做项目，对技术很感兴趣。"
    echo ""

    echo "🔍 RAG增强示例:"
    echo "   用户: 你会做什么项目？"
    echo "   AI: 说到项目，我最近在做一个小商城系统，用Vue和Spring Boot写的..."
    echo ""

    echo "🛠️  工具调用示例:"
    echo "   用户: 现在几点了？"
    echo "   AI: 现在是：2024-01-15 14:30:25"
    echo ""
    echo "   用户: 帮我搜索Vue项目"
    echo "   AI: 我为你找到了几个相关的项目：\n   1. vuejs/vue\n      描述：The Progressive JavaScript Framework"
    echo ""
}

# 显示快速启动指南
show_quick_start() {
    print_status "快速启动指南..."
    echo ""

    echo "🐳 使用Docker (推荐):"
    echo "   docker-compose up -d"
    echo "   访问: http://localhost"
    echo ""

    echo "🔧 手动启动:"
    echo "   # 1. 启动后端"
    echo "   cd digital-person-backend"
    echo "   mvn clean package && java -jar target/digital-person-backend-1.0.0.jar"
    echo ""
    echo "   # 2. 启动RAG引擎"
    echo "   cd rag-engine"
    echo "   pip install -r requirements.txt && python rag_server.py"
    echo ""
    echo "   # 3. 启动Agent工具"
    echo "   cd agent-tools"
    echo "   pip install -r requirements.txt && python agent_server.py"
    echo ""
    echo "   # 4. 启动前端"
    echo "   cd digital-person-frontend"
    echo "   npm install && npm run dev:h5"
    echo ""
}

# 显示文档链接
show_documentation() {
    print_status "📚 项目文档..."
    echo ""

    echo "📖 主要文档:"
    echo "   • README.md - 项目总览"
    echo "   • QUICK_START.md - 30分钟快速体验"
    echo "   • DEPLOYMENT.md - 部署指南"
    echo "   • ROADMAP.md - 发展规划"
    echo "   • PROJECT_SUMMARY.md - 项目总结"
    echo ""

    echo "🔗 在线资源:"
    echo "   • GitHub Issues: 问题反馈"
    echo "   • GitHub Discussions: 功能讨论"
    echo "   • Wiki: 详细文档"
    echo ""
}

# 主函数
main() {
    echo "🎯 数字人聊天系统演示"
    echo "================================"
    echo ""

    # 检查要求
    check_requirements

    # 显示项目概览
    show_project_structure

    # 演示各个模块
    demo_backend
    demo_frontend
    demo_data_pipeline
    demo_rag
    demo_agent

    # 演示API和使用
    demo_apis
    demo_examples

    # 显示指南
    show_quick_start
    show_documentation

    echo "🎉 演示完成！"
    echo "================================"
    echo ""
    echo "📋 下一步建议:"
    echo "   1. 查看 QUICK_START.md 快速体验"
    echo "   2. 阅读 DEPLOYMENT.md 了解部署"
    echo "   3. 查看 ROADMAP.md 了解未来计划"
    echo "   4. 开始体验AI聊天功能！"
    echo ""
    echo "🚀 祝你使用愉快！"
}

# 运行主函数
main "$@"