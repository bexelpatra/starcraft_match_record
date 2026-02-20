@echo off
chcp 65001 >nul 2>&1
title StarRecord Launcher

echo ============================================
echo   StarRecord - 스타크래프트 전적 관리
echo ============================================
echo.

REM 스타크래프트와 리플레이 감시를 동시에 시작합니다.
REM 처음 사용 시 아래 설정이 필요합니다:
REM   python main.py set-sc-path "C:\...\StarCraft.exe"
REM   python main.py set-replay-dir "C:\...\Replays"

cd /d "%~dp0"
python main.py launch

echo.
pause
