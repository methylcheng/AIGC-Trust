@echo off
chcp 65001 >nul
echo ========================================
echo   AIGC-Trust 前端启动脚本
echo ========================================
echo.

REM 检查 Node.js 是否安装
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [信息] Node.js 版本:
node --version
echo.

REM 检查依赖是否已安装
if not exist "node_modules" (
    echo [信息] 首次运行，正在安装依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo.
)

echo [信息] 启动开发服务器...
echo [提示] 访问地址: http://localhost:3000
echo [提示] 按 Ctrl+C 停止服务
echo.

call npm run dev
