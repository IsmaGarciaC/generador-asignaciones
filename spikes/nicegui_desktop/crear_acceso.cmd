@echo off
setlocal
pushd "%~dp0" || exit /b 1
powershell.exe -NoProfile -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$baseSpike = (Get-Location).Path;" ^
  "$acceso = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $baseSpike 'Asignaciones.lnk'));" ^
  "$acceso.TargetPath = (Resolve-Path -LiteralPath 'venv\Scripts\pythonw.exe').Path;" ^
  "$acceso.Arguments = [char]34 + (Resolve-Path -LiteralPath 'app.py').Path + [char]34;" ^
  "$acceso.WorkingDirectory = $baseSpike; $acceso.Save()"
set "resultadoSpike=%ERRORLEVEL%"
popd
exit /b %resultadoSpike%
