# Informe de archivos no utilizados

Este documento resume la revisión realizada para identificar archivos de código que actualmente no forman parte de la ejecución del plugin de QGIS **Índices Morfológicos**.

## Metodología

1. Se analizaron las importaciones de los módulos principales del plugin (`plugin.py`, `elongacion_algorithm.py`, `gradiente_algorithm.py` y `about_dialog.py`).
2. Se utilizaron búsquedas de texto con `rg` (ripgrep) para localizar referencias a cada módulo dentro del repositorio.
3. Se comprobó que no existan cargas dinámicas ni usos indirectos de los archivos evaluados.

## Archivos identificados como no utilizados

| Archivo | Ubicación | Evidencia |
|---------|-----------|-----------|
| `generacion_reportes.py` | `utils/generacion_reportes.py` | No aparece importado ni referenciado en ningún archivo de código. |
| `validacion_datos.py` | `utils/validacion_datos.py` | No aparece importado ni referenciado en ningún archivo de código. |

Ambos archivos solo se mencionan en la sección de estructura de directorios del `README.md`, pero no son utilizados por el plugin en tiempo de ejecución.

## Recomendaciones

- Eliminar estos archivos si ya no se planea integrarlos en el flujo del plugin para reducir el mantenimiento innecesario.
- Alternativamente, documentar su propósito futuro si se desea conservarlos como parte de la hoja de ruta.

