@echo off
REM DevCycle Test Runner - Windows Batch File
REM This file provides easy access to different test types

echo.
echo ============================================================
echo    DevCycle Test Runner
echo ============================================================
echo.
echo Available options:
echo   1. Unit tests only
echo   2. Integration tests only
echo   3. E2E tests only (in batches)
echo   4. All tests (complete suite)
echo   5. E2E Batch 1 - Core Authentication
echo   6. E2E Batch 2 - User Management
echo   7. E2E Batch 3 - Health Endpoints
echo   8. E2E Batch 4 - Performance & SQLite
echo.
echo ============================================================
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" (
    echo Running unit tests...
    poetry run pytest tests/unit/ -v
) else if "%choice%"=="2" (
    echo Running integration tests...
    poetry run pytest tests/integration/ -v
) else if "%choice%"=="3" (
    echo Running all E2E tests in batches...
    python run_tests.py --type e2e
) else if "%choice%"=="4" (
    echo Running complete test suite...
    python run_tests.py --type all
) else if "%choice%"=="5" (
    echo Running E2E Batch 1 - Core Authentication...
    python run_tests.py --type e2e --batch 1
) else if "%choice%"=="6" (
    echo Running E2E Batch 2 - User Management...
    python run_tests.py --type e2e --batch 2
) else if "%choice%"=="7" (
    echo Running E2E Batch 3 - Health Endpoints...
    python run_tests.py --type e2e --batch 3
) else if "%choice%"=="8" (
    echo Running E2E Batch 4 - Performance & SQLite...
    python run_tests.py --type e2e --batch 4
) else (
    echo Invalid choice. Please run the script again.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Test run completed!
echo ============================================================
pause
