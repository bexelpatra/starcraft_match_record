@echo off
chcp 65001 >nul 2>&1
title StarRecord Daemon

echo ============================================
echo   StarRecord - 백그라운드 감시 모드
echo ============================================
echo.
echo   스타크래프트가 실행되면 자동으로
echo   리플레이 감시를 시작합니다.
echo.

cd /d "%~dp0"
python main.py daemon

echo.
pause
