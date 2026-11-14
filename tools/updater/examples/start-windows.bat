@echo off
setlocal
if "%~2"=="" (
    echo Usage: start-windows.bat MINECRAFT_VERSION SERVER.jar [server arguments]
    exit /b 2
)
set "VERSION=%~1"
set "SERVER_JAR=%~2"
shift
shift
set "SERVER_ARGS="
:collect
if "%~1"=="" goto launch
set SERVER_ARGS=%SERVER_ARGS% %~1
shift
goto collect
:launch
java -jar BeefMC-Launcher.jar --minecraft-version "%VERSION%" --server-jar "%SERVER_JAR%" -- %SERVER_ARGS%
exit /b %ERRORLEVEL%
