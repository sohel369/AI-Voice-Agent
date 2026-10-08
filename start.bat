@echo off
title Voice to Bitrix24 Bot Server
echo ========================================================
echo   Starting Voice to Bitrix24 Bot Server (FastAPI)
echo ========================================================
echo.
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
