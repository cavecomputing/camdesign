@echo off
REM Start CamDesign and open it in the default browser.
REM   start-camdesign.bat        - local only, http://127.0.0.1:5000
REM   start-camdesign.bat lan    - also reachable from a phone or tablet on the same network
setlocal
cd /d "%~dp0"

set HOST=127.0.0.1
if /i "%~1"=="lan" set HOST=0.0.0.0
set CAMDESIGN_HOST=%HOST%

REM A stable secret key keeps open tabs saving across restarts. Generated once,
REM stored in data\ which Git ignores.
if not exist "data" mkdir "data"
if not exist "data\secret.key" (
    echo Generating a local secret key...
    uv run python -c "import secrets; print(secrets.token_hex(32))" > "data\secret.key"
    if errorlevel 1 goto :failed
)
set /p CAMDESIGN_SECRET_KEY=<data\secret.key

echo Checking dependencies...
uv sync --frozen
if errorlevel 1 echo   ...skipped, continuing with the installed environment.

REM The server applies pending database migrations itself as it starts.

if /i "%HOST%"=="0.0.0.0" (
    echo.
    echo Other devices on this network can reach CamDesign at:
    for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
        for /f "tokens=*" %%B in ("%%A") do echo     http://%%B:5000
    )
    echo   Allow access on Private networks only if Windows asks.
)

echo.
echo Starting CamDesign. Close this window or press Ctrl+C to stop it.
echo.
uv run python app.py
if errorlevel 1 goto :failed
goto :eof

:failed
echo.
echo CamDesign failed to start. See the message above.
pause
