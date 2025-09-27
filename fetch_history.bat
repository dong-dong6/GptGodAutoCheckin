@echo off
chcp 65001 >nul
echo ========================================
echo GPT-GOD 积分历史记录获取工具
echo ========================================
echo.
echo 此工具将从网站获取所有账号的历史积分记录
echo 首次运行可能需要较长时间...
echo.
pause

python fetch_points_history.py

echo.
echo ========================================
echo 历史记录获取完成！
echo ========================================
pause