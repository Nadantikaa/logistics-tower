@echo off
REM Reset the database by removing volumes and recreating the container
REM WARNING: This will delete all data in the database!

echo.
echo ^! WARNING: This will DELETE all database data!
echo.
set /p confirm="Are you sure? Type 'yes' to confirm: "

if /i not "%confirm%"=="yes" (
    echo Operation cancelled.
    exit /b 0
)

echo.
echo Stopping services...
docker-compose down

echo.
echo Removing database volume...
docker volume rm logistics-ai_db_data >nul 2>&1

echo.
echo Rebuilding and starting services...
docker-compose up --build -d

echo.
echo Waiting for database to be ready...
timeout /t 5 /nobreak

echo.
echo Database has been reset! Services are running.
docker-compose ps
