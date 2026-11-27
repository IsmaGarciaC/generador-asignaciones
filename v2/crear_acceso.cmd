@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not exist "venv\Scripts\pythonw.exe" (
  echo Primero prepara el entorno de V2 segun README.md.
  popd
  exit /b 1
)
powershell.exe -NoProfile -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$carpetaV2 = (Get-Location).Path;" ^
  "$acceso = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $carpetaV2 'Generador de Asignaciones V2.lnk'));" ^
  "$acceso.TargetPath = (Resolve-Path -LiteralPath 'venv\Scripts\pythonw.exe').Path;" ^
  "$acceso.Arguments = '-m generador_asignaciones_v2';" ^
  "$acceso.WorkingDirectory = $carpetaV2; $acceso.Save()"
set "resultadoV2=%ERRORLEVEL%"
popd
exit /b %resultadoV2%
