@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   ShareHear — Servidor Web Estatico Local
echo ============================================================
echo.
echo Iniciando servidor web local en el puerto 8080...
echo Carpeta raiz: %~dp0website
echo.
echo Abriendo navegador en http://localhost:8080...
start http://localhost:8080

python -m http.server 8080 --directory website

pause
