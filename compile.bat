@echo off
echo Compilando recursos del plugin...

REM Compilar archivos de recursos si existen
if exist resources.qrc (
    pyrcc5 -o resources.py resources.qrc
    echo Recursos compilados exitosamente
) else (
    echo No se encontraron archivos de recursos
)

echo Compilacion completada
pause
