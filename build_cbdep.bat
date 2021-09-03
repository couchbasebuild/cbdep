setlocal EnableDelayedExpansion
@echo on

set START_DIR="%CD%"

set SCRIPTPATH=%~dp0

echo Setting up Python virtual environment
if not exist "build\" (
    mkdir build
)
python3 -m venv build/venv || goto error
call .\build\venv\Scripts\activate.bat || goto error

echo Adding pyinstaller
pip3 install pyinstaller==4.2 || goto error

echo Installing cbdep requirements
pip3 install -r "%SCRIPTPATH%\requirements.txt" || goto error

@echo on

rem Customize _buildversion.py if build info available in environment
set VERSIONPATH=build\version
rmdir /s /q %VERSIONPATH%
mkdir %VERSIONPATH%

if not "%VERSION%" == "" (
    set PYINSTPATHS=%VERSIONPATH%;%SCRIPTPATH%\cbdep\scripts
    echo __version__ = "%VERSION%" > %VERSIONPATH%\_buildversion.py
    echo __build__ = "%BLD_NUM%" >> %VERSIONPATH%\_buildversion.py
) else (
    set PYINSTPATHS=%SCRIPTPATH%\cbdep\scripts
)

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
    --paths "%PYINSTPATHS%" ^
    "%SCRIPTPATH%\cbdep\scripts\cbdep.py" || goto error

goto eof

:error
set CODE=%ERRORLEVEL%
cd "%START_DIR%"
echo "Failed with error code %CODE%"
exit /b %CODE%

:eof
cd "%START_DIR%"
