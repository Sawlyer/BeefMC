@echo off
setlocal
if "%~1"=="" (
    echo Usage: start-beefmc.cmd SERVER.jar
    exit /b 2
)
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
"%JAVA%" -Xms%BEEFMC_XMS% -Xmx%BEEFMC_XMX% %BEEFMC_HEADER_FLAG% -jar "%~1"
exit /b %ERRORLEVEL%

:unsupported
echo The compact profile requires a Java runtime with UseCompactObjectHeaders support. Use Java 25. 1>&2
exit /b 2
