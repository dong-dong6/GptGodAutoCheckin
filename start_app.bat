@echo off
:: GPT-GOD 自动签到服务启动脚本
:: 用于Windows计划任务

cd /d "%~dp0"

:: 激活虚拟环境（如果存在）
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: 启动Flask应用
echo [%date% %time%] 启动GPT-GOD服务... >> startup.log
python app.py >> startup.log 2>&1

:: 如果服务意外停止，等待10秒后重启
if %errorlevel% neq 0 (
    echo [%date% %time%] 服务异常退出，10秒后重启... >> startup.log
    timeout /t 10 /nobreak
    goto :restart
)

:restart
python app.py >> startup.log 2>&1