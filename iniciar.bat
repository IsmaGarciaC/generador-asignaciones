@echo off
title Generador de Asignaciones
cd /d "%~dp0"
call venv\Scripts\activate
python src\interfaz_grafica.py