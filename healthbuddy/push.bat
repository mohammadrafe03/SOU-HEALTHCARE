@echo off
setlocal enabledelayedexpansion
title 1-Click GitHub Auto Push
echo ========================================================
echo       SOU HEALTHCARE - 1-CLICK GITHUB SYNC
echo ========================================================
echo.

set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d "%~dp0.."

:: 1. Check & Set Git User Identity if not configured
git config user.name >nul 2>&1
if %errorlevel% neq 0 (
    echo [SETUP] Configuring default Git Author Identity...
    git config --global user.name "HealthBuddy Dev"
    git config --global user.email "developer@healthbuddy.local"
)

:: 2. Check if Remote 'origin' is configured
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo  [FIRST TIME SETUP] GitHub Repository URL Required!
    echo ========================================================
    echo  Please paste your GitHub repo link below
    echo  (e.g., https://github.com/YourUsername/YourRepo.git)
    echo.
    set /p REPO_URL="GitHub URL: "
    if not "!REPO_URL!"=="" (
        git remote add origin !REPO_URL!
        echo.
        echo Remote origin set to: !REPO_URL!
    ) else (
        echo [ERROR] No URL entered. Aborting push.
        pause
        exit /b
    )
)

:: 3. Stage all files
echo.
echo [1/3] Adding all files to Git...
git add .

:: 4. Commit changes
echo [2/3] Committing changes...
set COMMIT_MSG=Update SOU Healthcare bot: %date% %time%
git commit -m "%COMMIT_MSG%"

:: 5. Ensure branch is main
git branch -M main

:: 6. Push to GitHub
echo [3/3] Pushing to GitHub (origin main)...
git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo [Retrying push to origin main]
    git push origin master
)

echo.
echo ========================================================
if %errorlevel% equ 0 (
    echo   [SUCCESS] Code successfully pushed to GitHub!
) else (
    echo   [NOTICE] If push failed, check your GitHub repo permissions / login.
)
echo ========================================================
echo.
pause
