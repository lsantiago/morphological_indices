@echo off
set PLUGIN_NAME=indices_morfologicos
set VERSION=1.0

echo Empaquetando plugin  v...

REM Crear directorio de distribución
if not exist dist mkdir dist

REM Crear archivo ZIP
powershell Compress-Archive -Path * -DestinationPath dist\_v.zip -Force

echo Plugin empaquetado en: dist\_v.zip
echo Listo para instalar en QGIS
pause
