@echo off
chcp 65001 >nul
title HYDISA
cd /d "%~dp0"
echo ============================================
echo   HYDISA - iniciando...
echo   No cierres esta ventana mientras uses la app.
echo   Para apagar HYDISA, cierra esta ventana.
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (
  py servidor.py
) else (
  python servidor.py
)
echo.
echo HYDISA se detuvo. Si hubo un error, copialo y envialo.
pause
