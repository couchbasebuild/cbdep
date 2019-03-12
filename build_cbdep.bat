setlocal

set START_DIR="%CD%"

set SCRIPTPATH=%~dp0

echo Setting up Python virtual environment
if not exist "build\" (
    mkdir build
)
python3 -m venv build/venv || goto error
call .\build\venv\Scripts\activate.bat || goto error

echo Adding pyinstaller
pip3 install pyinstaller || goto error

echo Installing cbdep requirements
pip3 install -r "%SCRIPTPATH%\requirements.txt" || goto error

echo Compiling cbdep
set PYINSTDIR=build\pyinstaller
if not exist "%PYINSTDIR%\" (
    mkdir %PYINSTDIR%
)
pyinstaller --add-data "%SCRIPTPATH%\cbdep.config;." ^
    --workpath %PYINSTDIR% ^
    --specpath %PYINSTDIR% ^
    --distpath dist --noconfirm ^
    --onefile ^
    --paths "%SCRIPTPATH%\cbdep\scripts" ^
    "%SCRIPTPATH%\cbdep\scripts\cbdep.py" || goto error

goto eof

:error
set CODE=%ERRORLEVEL%
cd "%START_DIR%"
echo "Failed with error code %CODE%"
exit /b %CODE%

:eof
cd "%START_DIR%"
