setlocal EnableDelayedExpansion
@echo on

rem Keep these in sync with build_cbdep
set PYTHON_VERSION=3.11.10
set UV_VERSION=0.4.29

set START_DIR="%CD%"

set SCRIPTPATH=%~dp0

echo Downloading UV
if not exist "uv\" (
    mkdir uv
)
cd uv
curl -LO https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip || goto error
7z x uv-x86_64-pc-windows-msvc.zip || goto error
cd ..
set PATH=%CD%\uv;%PATH%

echo Setting up Python virtual environment
if not exist "build\" (
    mkdir build
)
uv venv --python %PYTHON_VERSION% build\venv || goto error
call .\build\venv\Scripts\activate.bat || goto error

echo Installing cbdep requirements
uv pip install -r "%SCRIPTPATH%\requirements.txt" || goto error

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
    --name cbdep ^
    "%SCRIPTPATH%\cbdep\scripts\main.py" || goto error

goto eof

:error
set CODE=%ERRORLEVEL%
cd "%START_DIR%"
echo "Failed with error code %CODE%"
exit /b %CODE%

:eof
cd "%START_DIR%"
