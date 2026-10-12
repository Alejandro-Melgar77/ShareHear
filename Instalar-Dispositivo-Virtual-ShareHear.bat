@echo off
setlocal
cd /d "%~dp0"

:: ============================================================
:: ShareHear - Instalador de Tarjeta de Sonido Virtual
:: Instala VB-CABLE como dispositivo de audio exclusivo
:: ============================================================

:: Verificar si ya tenemos permisos de administrador
net session >nul 2>&1
if %errorlevel% == 0 goto :ADMIN
:: No somos admin: relanzar con elevacion UAC
echo Solicitando elevacion de permisos...
powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
exit /b

:ADMIN
echo.
echo ============================================================
echo   ShareHear - Instalando Tarjeta de Sonido Virtual
echo ============================================================
echo.
echo Instalando el controlador VB-CABLE (Windows 10/11 x64)...
echo.
echo IMPORTANTE: 
echo   1. Acepta el cuadro de dialogo del controlador si aparece.
echo   2. Al terminar REINICIA la PC para que Windows lo detecte.
echo.

:: Instalar el driver usando VBCABLE_Setup_x64.exe
"%~dp0vbcable_driver\VBCABLE_Setup_x64.exe"

echo.
echo ============================================================
echo Instalacion completada. Por favor REINICIA la PC.
echo.
echo Despues de reiniciar:
echo   1. Abre ShareHear Server
echo   2. En "Captura de Audio", selecciona "CABLE Output"
echo   3. En Windows (icono de volumen), selecciona "CABLE Input"
echo   4. El audio solo saldra por tus auriculares Bluetooth.
echo ============================================================
echo.
pause
