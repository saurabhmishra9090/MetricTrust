
@echo off
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo       MetricTrust GitHub Saver
echo ========================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git repository nahi mila.
    pause
    exit /b 1
)

echo Checking project changes...
git status --short

echo.
git add -A
if errorlevel 1 (
    echo ERROR: Files stage nahi ho payi.
    pause
    exit /b 1
)

git diff --cached --quiet
if not errorlevel 1 (
    echo.
    echo No changes to save.
    pause
    exit /b 0
)

echo.
set /p "commitmsg=Commit message: "
if not defined commitmsg set "commitmsg=Update MetricTrust"

git -c core.quotepath=false commit -m "%commitmsg%"
if errorlevel 1 (
    echo.
    echo ERROR: Commit failed.
    pause
    exit /b 1
)

echo.
git push
if errorlevel 1 (
    echo.
    echo ERROR: Push failed. Check GitHub connection.
    pause
    exit /b 1
)

echo.
echo SUCCESS: MetricTrust saved to GitHub!
pause
