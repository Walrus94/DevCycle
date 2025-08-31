@echo off
setlocal enabledelayedexpansion

REM Start Kafka services for DevCycle development
echo Starting Kafka services for DevCycle...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Start Kafka (KRaft mode - no Zookeeper needed)
echo Starting Kafka (KRaft mode)...
docker-compose up -d kafka

REM Wait for Kafka to be ready
echo Waiting for Kafka to be ready...
:wait_loop
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list >nul 2>&1
if errorlevel 1 (
    echo Waiting for Kafka...
    timeout /t 5 /nobreak >nul
    goto wait_loop
)

echo Kafka is ready!

REM Check if dev profile is requested
if "%1"=="--dev" (
    echo Starting development services (Kafka UI)...
    docker-compose --profile dev up -d
    echo.
    echo Services available at:
    echo   Kafka: localhost:9092
    echo   Kafka UI: http://localhost:8080
) else (
    echo.
    echo Kafka is running at localhost:9092
    echo To start development services, run: %0 --dev
)

echo.
echo To stop services: docker-compose down
echo To view logs: docker-compose logs -f
pause
