@echo off
title Elden Ring Lore DB
cd /d "%~dp0"

echo.
echo  Elden Ring Lore DB
echo  ==================
echo.

REM lore.db 없으면 자동 빌드
if not exist "data\lore.db" (
    echo  [Setup] DB not found. Building...
    echo.
    python scripts/fetch_erdb.py
    python scripts/parse_fmg.py
    python scripts/parse_html.py
    python scripts/merge_entries.py
    python scripts/build_db.py
    echo.
)

echo  Starting app at http://localhost:8501
echo  (Close this window to stop the server)
echo.

REM 2초 후 브라우저 자동 오픈
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8501"

python -m streamlit run app/app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
