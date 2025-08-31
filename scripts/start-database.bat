@echo off
echo Starting DevCycle Database Services...
echo.

REM Load environment variables from config.env if it exists
if exist "config.env" (
    echo Loading environment variables from config.env...
    for /f "tokens=1,2 delims==" %%a in (config.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Set default values if not defined
if not defined POSTGRES_DB set "POSTGRES_DB=devcycle"
if not defined POSTGRES_USER set "POSTGRES_USER=postgres"
if not defined POSTGRES_PASSWORD set "POSTGRES_PASSWORD=devcycle123"
if not defined POSTGRES_PORT set "POSTGRES_PORT=5432"
if not defined PGADMIN_EMAIL set "PGADMIN_EMAIL=admin@devcycle.dev"
if not defined PGADMIN_PASSWORD set "PGADMIN_PASSWORD=admin123"

echo Starting PostgreSQL and pgAdmin...
docker-compose up -d postgres pgadmin

echo.
echo Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Database services started!
echo.
echo PostgreSQL: localhost:%POSTGRES_PORT%
echo   - Database: %POSTGRES_DB%
echo   - Username: %POSTGRES_USER%
echo   - Password: %POSTGRES_PASSWORD%
echo.
echo pgAdmin: http://localhost:5050
echo   - Email: %PGADMIN_EMAIL%
echo   - Password: %PGADMIN_PASSWORD%
echo.
echo Default users:
echo   - admin/admin123 (admin role)
echo   - user/user123 (user role)
echo.
pause
