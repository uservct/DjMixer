@echo off
setlocal

cd /d "%~dp0"

echo ======================================
echo DJ Mixer - One Click Launcher
echo ======================================

set "NEED_SETUP=0"

if not exist "venv\Scripts\python.exe" set "NEED_SETUP=1"
if not exist "venv\.deps_installed" set "NEED_SETUP=1"

if "%NEED_SETUP%"=="1" (
    echo [1/4] Dang tao virtual environment...
    if not exist "venv\Scripts\python.exe" (
        py -m venv venv
        if errorlevel 1 (
            echo Khong tao duoc venv bang lenh ^"py^". Thu bang ^"python^"...
            python -m venv venv
            if errorlevel 1 (
                echo [LOI] Khong the tao virtual environment.
                pause
                exit /b 1
            )
        )
    ) else (
        echo Venv da ton tai.
    )

    echo [2/4] Dang nang cap pip...
    call "venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
        echo [LOI] Khong nang cap duoc pip.
        pause
        exit /b 1
    )

    echo [3/4] Dang cai dependencies tu requirements.txt...
    call "venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [LOI] Cai dependencies that bai.
        pause
        exit /b 1
    )

    echo [4/4] Hoan tat cai dat lan dau.
    type nul > "venv\.deps_installed"
) else (
    echo Moi truong da san sang. Bo qua buoc cai dat.
)

echo.
echo Dang chay DJ Mixer...
call "venv\Scripts\python.exe" "main.py"

if errorlevel 1 (
    echo.
    echo [LOI] Ung dung dong voi ma loi %errorlevel%.
    pause
    exit /b %errorlevel%
)

exit /b 0
