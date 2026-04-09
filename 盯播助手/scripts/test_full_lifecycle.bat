@echo off

REM 盯播助手完整生命周期测试脚本
REM 作者: exbox0403-cmd
REM 日期: 2026/4/8

echo 🚀 开始盯播助手完整生命周期测试...
echo ======================================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    exit /b 1
)

echo ✅ Python检查通过

REM 检查Java是否安装
java -version >nul 2>&1
if errorlevel 1 (
    echo ❌ Java未安装或未添加到PATH
    exit /b 1
)

echo ✅ Java检查通过

REM 检查Maven是否安装
mvn --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Maven未安装或未添加到PATH
    exit /b 1
)

echo ✅ Maven检查通过

REM 检查Docker是否安装（用于RabbitMQ）
docker --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Docker未安装，将跳过RabbitMQ检查
) else (
    echo ✅ Docker检查通过
)

echo.
echo 📋 测试步骤:
echo 1. 启动RabbitMQ服务
echo 2. 启动Java后端服务
echo 3. 启动Python爬虫服务
echo 4. 运行集成测试
echo.

REM 询问用户是否继续
set /p continue="是否继续? (y/n): "
if /i "%continue%" neq "y" (
    echo 🛑 测试已取消
    exit /b 0
)

echo.
echo 🔄 正在启动服务...

REM 启动RabbitMQ（如果Docker可用）
docker --version >nul 2>&1
if not errorlevel 1 (
    echo 🐰 正在启动RabbitMQ...
    docker run -d --name rabbitmq-test -p 5672:5672 -p 15672:15672 rabbitmq:3-management
    if errorlevel 1 (
        echo ⚠️  RabbitMQ启动失败，尝试使用已存在的容器
        docker start rabbitmq-test >nul 2>&1
    )
    timeout /t 5 >nul
) else (
    echo ⚠️  跳过RabbitMQ启动（Docker不可用）
)

REM 启动Java后端服务
echo ☕ 正在启动Java后端服务...
cd /d "%~dp0..\stream-backend-java"
start "Java Backend" cmd /c "mvn spring-boot:run"
timeout /t 10 >nul

REM 启动Python爬虫服务
echo 🐍 正在启动Python爬虫服务...
cd /d "%~dp0..\stream-spider-python"
start "Python Crawler" cmd /c "python main.py"
timeout /t 5 >nul

echo.
echo 🔍 正在运行集成测试...
cd /d "%~dp0.."
python test_integration.py

if errorlevel 1 (
    echo ❌ 测试失败
    echo.
    echo 建议检查以下内容:
    echo - Java服务是否正常运行 (http://localhost:8080/health)
    echo - Python服务是否正常运行 (http://localhost:5000/health)
    echo - RabbitMQ是否正常运行 (http://localhost:15672)
    echo - 数据库连接是否正常
) else (
    echo ✅ 所有测试通过！
    echo.
    echo 🎉 盯播助手完整生命周期测试成功完成！
    echo.
    echo 现在可以:
    echo - 在小程序中创建监控任务
    echo - 验证任务是否成功发送到RabbitMQ
    echo - 检查Python服务是否开始监控
    echo - 测试直播状态变化时的通知功能
)

echo.
echo 📝 查看详细测试文档: LIFECYCLE_TEST.md

echo.
echo ⏹️  按任意键退出...
pause >nul