@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ was not found. Install it from python.org and enable Add Python to PATH.
    pause
    exit /b 1
  )
  set "PY=python"
) else (
  set "PY=py -3"
)
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)
if not exist ".env" copy ".env.example" ".env" >nul
set "VPY=.venv\Scripts\python.exe"
if exist "wheels\*.whl" (
  %VPY% -m pip install --no-index --find-links wheels -r requirements.txt
  if errorlevel 1 (
    echo Offline wheel install failed; trying PyPI...
    %VPY% -m pip install -r requirements.txt
  )
) else (
  %VPY% -m pip install -r requirements.txt
)
if errorlevel 1 goto failed
start "" "http://127.0.0.1:8080"
:run
%VPY% run.py
if errorlevel 1 (
  echo Application stopped with an error. Restarting in 3 seconds; press Ctrl+C to stop.
  timeout /t 3 /nobreak >nul
  goto run
)
goto done
:failed
echo Setup failed. Check Python and internet access, then retry.
pause
exit /b 1
:done
endlocal
