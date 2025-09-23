# Índices Morfológicos

Plugin de QGIS que proporciona herramientas especializadas para el cálculo de índices morfológicos en cuencas hidrográficas.

## Descripción

Este plugin convierte y adapta las herramientas desarrolladas originalmente para ArcGIS al entorno QGIS, proporcionando funcionalidades avanzadas para el análisis geomorfológico:

- **Cálculo de Elongación**: Análisis de la forma de cuencas hidrográficas mediante la relación área-distancia
- **Cálculo de Gradiente**: Análisis del gradiente longitudinal de ríos con el índice SL-K
- **Visualización Integrada**: Generación automática de gráficos y reportes
- **Validación Automática**: Verificación de datos de entrada y formatos

## Archivos de ejemplo

Puedes encontrar archivos de ejemplo para practicar el cálculo de elongación y gradiente en el siguiente enlace:

**[📁 Archivos de ejemplo - Google Drive](https://drive.google.com/drive/folders/1iaC3_CPA62TPP22A2cG7knSvwNTzoYLq?usp=sharing)**

Los archivos incluyen datos de cuencas hidrográficas y perfiles de ríos listos para usar con el plugin.

## Características principales

### Cálculo de Elongación

- Procesamiento automático de polígonos de cuencas
- Identificación de puntos de máxima y mínima elevación
- Cálculo preciso de distancias y áreas
- Clasificación automática según rangos estándar:
  - Muy alargada (Re < 0.22)
  - Alargada (0.22 ≤ Re < 0.30)
  - Ligeramente alargada (0.30 ≤ Re < 0.37)
  - Ni alargada ni ensanchada (0.37 ≤ Re < 0.45)
  - Ligeramente ensanchada (0.45 ≤ Re ≤ 0.60)
  - Ensanchada (0.60 < Re ≤ 0.80)
  - Muy ensanchada (0.80 < Re ≤ 1.20)
  - Rodeando el desagüe (Re > 1.20)

### Cálculo de Gradiente

- Análisis de perfiles longitudinales de ríos
- Cálculo del índice SL-K (Stream Length-gradient index)
- Generación automática de gráficos de perfil y gradiente
- Análisis estadístico de pendientes y puntos medios
- Parámetros personalizables para visualización

### Funcionalidades Adicionales

- Validación automática de campos requeridos
- Manejo de diferentes sistemas de coordenadas
- Exportación de resultados en formatos estándar
- Generación de reportes detallados
- Integración completa con el entorno QGIS

## Instalación

### Requisitos previos

El plugin requiere QGIS 3.16 o superior y las siguientes dependencias de Python:

```bash
pip install numpy pandas matplotlib
```

### Instalación del plugin

1. Descarga la última versión del plugin desde el repositorio
2. En QGIS, ve a "Complementos" > "Administrar e instalar complementos..."
3. Selecciona "Instalar a partir de ZIP"
4. Navega hasta el archivo ZIP descargado y selecciónalo
5. Haz clic en "Instalar complemento"

## Uso básico

### Cálculo de Elongación

1. En el menú principal de QGIS, selecciona "Índices Morfológicos" > "Calcular Elongación"
2. Selecciona la capa de cuencas (polígonos) con campo 'Shape_Area'
3. Selecciona la capa de puntos con elevación (campos X, Y, Z)
4. Especifica la ubicación del archivo de salida
5. Haz clic en "Ejecutar"

### Cálculo de Gradiente

1. En el menú principal de QGIS, selecciona "Índices Morfológicos" > "Calcular Gradiente"
2. Selecciona la capa de puntos del río (ordenados por elevación)
3. Configura los parámetros del gráfico (opcional)
4. Especifica la ubicación del archivo de salida
5. Haz clic en "Ejecutar"

## Estructura de datos

### Para Elongación

**Capa de cuencas (polígonos):**
- Campo requerido: `Shape_Area` (área de la cuenca)

**Capa de puntos:**
- Campos requeridos: `X`, `Y`, `Z` (coordenadas y elevación)

### Para Gradiente

**Capa de puntos del río:**
- Campos requeridos: `X`, `Y`, `Z` (coordenadas y elevación)
- Los puntos deben estar ordenados desde la cabecera hasta la desembocadura

## Desarrollo

### Estructura del proyecto

```
indices_morfologicos/
├── __init__.py
├── metadata.txt
├── plugin.py
├── about_dialog.py
├── elongacion_algorithm.py
├── gradiente_algorithm.py
├── icon.png
├── README.md
└── utils/
    ├── __init__.py
    ├── validacion_datos.py
    └── generacion_reportes.py
```

### Contribuciones

Las contribuciones son bienvenidas. Este proyecto está basado en el trabajo original de:

- Ing. Santiago Quiñones
- Ing. María Fernanda Guarderas  
- Nelson Aranda

Para contribuir:
1. Haz un fork del repositorio
2. Crea una rama para tu característica
3. Realiza los cambios necesarios
4. Envía un pull request

## Licencia

Este plugin está licenciado bajo la Licencia Pública General de GNU v2 o posterior.

## Autor

Universidad Técnica Particular de Loja (UTPL)  
Departamento de Ingeniería Civil

## Versiones

- **v2.0** (2025-06-29): Versión inicial
  - Algoritmo de cálculo de elongación
  - Algoritmo de cálculo de gradiente
  - Interfaz integrada en QGIS
  - Validación automática de datos
  - Generación de reportes