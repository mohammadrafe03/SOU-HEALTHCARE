@echo off
setlocal enabledelayedexpansion
title 1-Click GitHub Auto Push
echo ========================================================
echo       SOU HEALTHCARE - 1-CLICK GITHUB SYNC
echo ========================================================
echo.

set PATH=C:\Program Files\Git\cmd;%PATH%

echo [1/3] Adding all updated files...
git add .

echo [2/3] Committing changes...
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (
    for /f "tokens=1-2 delims=: " %%e in ("%time%") do (
        set COMMIT_MSG=Auto-update SOU Healthcare: %%a-%%b-%%c %%e:%%f
    )
)
git commit -m "%COMMIT_MSG%"

echo [3/3] Pushing to GitHub (origin main)...
git push origin main

echo.
echo ========================================================
if %errorlevel% equ 0 (
    echo   [SUCCESS] Code successfully pushed to GitHub!
    echo   Streamlit Cloud will now auto-update.
) else (
    echo   [NOTICE] If push failed, please check your internet or permissions.
)
echo ========================================================
echo.
pause
