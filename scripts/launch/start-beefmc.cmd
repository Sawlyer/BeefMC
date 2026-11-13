@echo off
setlocal
if "%~1"=="" (
    echo Usage: start-beefmc.cmd SERVER.jar
    exit /b 2
)
if not defined JAVA set "JAVA=java"
if not defined BEEFMC_XMS set "BEEFMC_XMS=512M"
if not defined BEEFMC_XMX set "BEEFMC_XMX=3G"
"%JAVA%" -Xms%BEEFMC_XMS% -Xmx%BEEFMC_XMX% -jar "%~1"
exit /b %ERRORLEVEL%
