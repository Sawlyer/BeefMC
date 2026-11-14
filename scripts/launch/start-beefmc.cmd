@echo off
setlocal EnableExtensions EnableDelayedExpansion
if "%~1"=="" (
    echo Usage: set BEEFMC_MINECRAFT_VERSION=1.21.11 ^& start-beefmc.cmd SERVER.jar [server arguments]
    exit /b 2
)
if not defined BEEFMC_MINECRAFT_VERSION (
    echo Set BEEFMC_MINECRAFT_VERSION to 1.8.8, 1.21.11, 26.1.2, or 26.3. 1>&2
    exit /b 2
)
if not exist "BeefMC-Launcher.jar" (
    echo BeefMC-Launcher.jar is required for automatic updates. Place it beside the server JAR. 1>&2
    exit /b 2
)
set "SERVER_JAR=%~1"
shift
if not defined JAVA set "JAVA=java"
if not defined BEEFMC_XMS set "BEEFMC_XMS=512M"
if "%BEEFMC_PROFILE%"=="compact" (
    "%JAVA%" -XX:+UseCompactObjectHeaders -version >nul 2>&1
    if errorlevel 1 goto unsupported
    if not defined BEEFMC_XMX set "BEEFMC_XMX=2944M"
    set "BEEFMC_HEADER_FLAG=-XX:+UseCompactObjectHeaders"
) else (
    if not defined BEEFMC_XMX set "BEEFMC_XMX=3G"
    set "BEEFMC_HEADER_FLAG="
)
set "SERVER_ARGS="
:collect_args
if "%~1"=="" goto launch
set SERVER_ARGS=!SERVER_ARGS! "%~1"
shift
goto collect_args
:launch
"%JAVA%" -jar BeefMC-Launcher.jar --minecraft-version "%BEEFMC_MINECRAFT_VERSION%" --server-jar "%SERVER_JAR%" -- "-Xms%BEEFMC_XMS%" "-Xmx%BEEFMC_XMX%" %BEEFMC_HEADER_FLAG% !SERVER_ARGS!
exit /b %ERRORLEVEL%

:unsupported
echo The compact profile requires a Java runtime with UseCompactObjectHeaders support. Use Java 25. 1>&2
exit /b 2
