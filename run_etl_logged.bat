@echo off
setlocal enabledelayedexpansion

:: Create logs folder
if not exist "D:\pfe_final\logs" mkdir "D:\pfe_final\logs"

set LOG=D:\pfe_final\logs\etl_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log

(
echo ====================================================
echo ETL Job Started at %date% %time%
echo ====================================================

set WAREHOUSE_SERVER=.\SQLEXPRESS
set WAREHOUSE_DB=StudentPerformanceDW
set WAREHOUSE_USER=wejden
set WAREHOUSE_PASSWORD=wejden123A*
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: === STEP 1: PYTHON ETL ===
echo [STEP 1] Running Python ETL...

:: Use the EXE that works for your user (update this path to match YOUR working Python)
"D:\pfe_final\venv\Scripts\python.exe" -B -X utf8 "D:\pfe_final\main.py"

if %errorlevel% neq 0 (
    echo [ERROR] Python ETL failed! Exit code: %errorlevel%
    exit /b %errorlevel%
)
echo [OK] Python ETL completed.

:: === STEP 2a: REFRESH PERFORMANCE MVW ===
echo [STEP 2a] Refreshing mvw_StudentPerformance...
sqlcmd -S .\SQLEXPRESS -d StudentPerformanceDW -E -C -Q "EXEC usp_Refresh_Materialized_StudentPerformance;"
if %errorlevel% neq 0 (
    echo [ERROR] Performance refresh failed!
    exit /b %errorlevel%
)
echo [OK] mvw_StudentPerformance refreshed.

:: === STEP 2b: REFRESH ATTENDANCE MVW ===
echo [STEP 2b] Refreshing mvw_StudentAttendance...
sqlcmd -S .\SQLEXPRESS -d StudentPerformanceDW -E -C -Q "EXEC usp_Refresh_Materialized_StudentAttendance;"
if errorlevel 1 (
    echo [ERROR] Performance refresh failed!
    exit /b %errorlevel%
)
echo [OK] mvw_StudentAttendance refreshed.

echo ====================================================
echo ETL Job completed successfully at %date% %time%
echo ====================================================

) >> "%LOG%" 2>&1