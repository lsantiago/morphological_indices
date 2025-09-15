# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingException,
                       QgsProject, QgsVectorLayer, QgsFields, QgsField,
                       QgsFeature, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsWkbTypes, QgsFeatureRequest, QgsExpression,
                       QgsGeometry, QgsPointXY, QgsSymbol, QgsRendererCategory,
                       QgsCategorizedSymbolRenderer, QgsSimpleMarkerSymbolLayer,
                       QgsLayoutManager, QgsLayout, QgsLayoutItemMap,
                       QgsLayoutItemLabel, QgsLayoutSize, QgsLayoutPoint,
                       QgsLayoutItemPicture, QgsUnitTypes)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
import processing
import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Qt5Agg')
import tempfile
from datetime import datetime
import webbrowser
from collections import defaultdict

class ElongacionAlgorithm(QgsProcessingAlgorithm):
    INPUT_CUENCAS = 'INPUT_CUENCAS'
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    GENERAR_VISUALIZACION = 'GENERAR_VISUALIZACION'
    TIPO_VISUALIZACION = 'TIPO_VISUALIZACION'
    ARCHIVO_SALIDA = 'ARCHIVO_SALIDA'
    GENERAR_REPORTE = 'GENERAR_REPORTE'
    APLICAR_SIMBOLOGIA = 'APLICAR_SIMBOLOGIA'
    
    def initAlgorithm(self, config=None):
        # Capa de entrada - polígonos de cuencas
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_CUENCAS,
                self.tr('Polígonos de cuencas (con Shape_Area)'),
                [QgsProcessing.TypeVectorPolygon],
                defaultValue=None
            )
        )
        
        # Capa de entrada - puntos con elevación
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_PUNTOS,
                self.tr('Puntos con elevación (con campos X, Y, Z)'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )
        
        # Parámetro para generar visualización
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_VISUALIZACION,
                self.tr('Generar visualización de elongación'),
                defaultValue=True
            )
        )
        
        # Tipo de visualización - SOLO REPORTE HTML
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.TIPO_VISUALIZACION,
                self.tr('Generar reporte HTML interactivo completo'),
                defaultValue=True
            )
        )
        
        # Archivo de salida para visualizaciones
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.ARCHIVO_SALIDA,
                self.tr('Archivo de salida (imagen/reporte)'),
                fileFilter='PNG files (*.png);;PDF files (*.pdf);;HTML files (*.html)',
                optional=True,
                defaultValue=None
            )
        )
        
        # Generar reporte estadístico
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_REPORTE,
                self.tr('Generar reporte estadístico detallado'),
                defaultValue=True
            )
        )
        
        # Aplicar simbología automática
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.APLICAR_SIMBOLOGIA,
                self.tr('Aplicar simbología automática por clasificación'),
                defaultValue=True
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        # ===== MARCADORES DE VERSIÓN =====
        feedback.pushInfo("=" * 70)
        feedback.pushInfo("🚀 EJECUTANDO ELONGACIÓN VERSIÓN 2.0 - ANÁLISIS GEOMORFOLÓGICO QGIS")
        feedback.pushInfo("=" * 70)
        
        try:
            # Obtener parámetros
            cuencas_layer = self.parameterAsVectorLayer(parameters, self.INPUT_CUENCAS, context)
            puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
            generar_viz = self.parameterAsBool(parameters, self.GENERAR_VISUALIZACION, context)
            generar_html = self.parameterAsBool(parameters, self.TIPO_VISUALIZACION, context)
            archivo_salida = self.parameterAsFileOutput(parameters, self.ARCHIVO_SALIDA, context)
            generar_reporte = self.parameterAsBool(parameters, self.GENERAR_REPORTE, context)
            aplicar_simbologia = self.parameterAsBool(parameters, self.APLICAR_SIMBOLOGIA, context)
            
            feedback.pushInfo("✅ Parámetros obtenidos correctamente")
            
            # Validar capas
            if not cuencas_layer.isValid():
                raise QgsProcessingException(self.tr("Capa de cuencas no válida"))
            
            if not puntos_layer.isValid():
                raise QgsProcessingException(self.tr("Capa de puntos no válida"))
            
            # Validar campos requeridos
            campos_cuencas = self._validar_campos_cuencas(cuencas_layer)
            if not campos_cuencas:
                raise QgsProcessingException(
                    self.tr("La capa de cuencas debe contener el campo 'Shape_Area'")
                )
            
            campos_puntos = self._detectar_campos_coordenadas(puntos_layer)
            if not campos_puntos:
                raise QgsProcessingException(
                    self.tr("La capa de puntos debe contener campos de coordenadas X, Y, Z")
                )
            
            campo_area = campos_cuencas
            campo_x, campo_y, campo_z = campos_puntos
            
            feedback.pushInfo(f"Usando campos - Área: {campo_area}, X: {campo_x}, Y: {campo_y}, Z: {campo_z}")
            
            # Procesar datos
            feedback.pushInfo("📊 Procesando cuencas y puntos...")
            datos_cuencas = self._leer_datos_cuencas(cuencas_layer, campo_area, feedback)
            datos_puntos = self._leer_datos_puntos(puntos_layer, campo_x, campo_y, campo_z, feedback)
            
            if not datos_cuencas or not datos_puntos:
                raise QgsProcessingException(self.tr("No se encontraron datos válidos para procesar"))
            
            # Agrupar puntos por cuenca y encontrar extremos
            feedback.pushInfo("🔍 Agrupando puntos por cuenca y encontrando extremos...")
            cuencas_con_puntos = self._agrupar_puntos_por_cuenca(datos_cuencas, datos_puntos, feedback)
            
            if not cuencas_con_puntos:
                raise QgsProcessingException(self.tr("No se pudieron asociar puntos con cuencas"))
            
            # Calcular índices de elongación
            feedback.pushInfo("📐 Calculando índices de elongación...")
            resultados_elongacion = self._calcular_elongacion_todas_cuencas(cuencas_con_puntos, feedback)
            
            # Crear nueva capa de salida
            feedback.pushInfo("🔧 Creando nueva capa con resultados...")
            output_path = self._crear_capa_elongacion(
                cuencas_layer, resultados_elongacion, aplicar_simbologia, feedback
            )
            
            # Calcular estadísticas
            estadisticas = self._calcular_estadisticas_elongacion(resultados_elongacion, feedback)
            
            # Generar reporte HTML si se solicita
            if generar_html:
                feedback.pushInfo("📄 Generando reporte HTML interactivo...")
                self._generar_reporte_html_elongacion(
                    resultados_elongacion, estadisticas, archivo_salida, feedback
                )
            
            # Generar reporte de texto si se solicita
            if generar_reporte:
                feedback.pushInfo("📄 Generando reporte estadístico detallado...")
                self._generar_reporte_elongacion(
                    resultados_elongacion, estadisticas, archivo_salida, feedback
                )
            
            # Mostrar estadísticas en log
            self._mostrar_estadisticas_log(estadisticas, feedback)
            
            feedback.pushInfo("=" * 70)
            feedback.pushInfo("🎉 ELONGACIÓN V2.0 - PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            feedback.pushInfo(f"📊 Cuencas procesadas: {len(resultados_elongacion)}")
            feedback.pushInfo(f"📁 Archivo de salida: {output_path}")
            feedback.pushInfo("=" * 70)
            
            return {}
            
        except Exception as e:
            feedback.reportError(f"❌ Error durante el procesamiento: {str(e)}")
            import traceback
            feedback.pushInfo(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
            return {}
    
    def _validar_campos_cuencas(self, layer):
        """Valida que exista el campo Shape_Area en la capa de cuencas"""
        campos = [field.name() for field in layer.fields()]
        nombres_area = ["Shape_Area", "SHAPE_AREA", "Area", "AREA", "area"]
        
        campo_area = next((campo for campo in nombres_area if campo in campos), None)
        return campo_area
    
    def _detectar_campos_coordenadas(self, layer):
        """Detecta automáticamente los campos de coordenadas en puntos"""
        campos = [field.name() for field in layer.fields()]
        
        nombres_x = ["POINT_X", "X", "x", "Point_X", "coord_x"]
        nombres_y = ["POINT_Y", "Y", "y", "Point_Y", "coord_y"]  
        nombres_z = ["Z", "z", "elevation", "altura", "elev", "ELEVATION"]
        
        campo_x = next((campo for campo in nombres_x if campo in campos), None)
        campo_y = next((campo for campo in nombres_y if campo in campos), None)
        campo_z = next((campo for campo in nombres_z if campo in campos), None)
        
        if campo_x and campo_y and campo_z:
            return campo_x, campo_y, campo_z
        return None
    
    def _leer_datos_cuencas(self, layer, campo_area, feedback):
        """Lee los datos de las cuencas con sus áreas"""
        datos_cuencas = {}
        
        for feature in layer.getFeatures():
            try:
                area_val = feature[campo_area]
                if area_val is None or area_val <= 0:
                    continue
                
                area = float(area_val)
                
                datos_cuencas[area] = {
                    'feature': feature,
                    'area': area,
                    'geometry': feature.geometry()
                }
                
            except (ValueError, TypeError) as e:
                feedback.pushWarning(f"Error leyendo cuenca {feature.id()}: {e}")
                continue
        
        feedback.pushInfo(f"V2.0: {len(datos_cuencas)} cuencas válidas encontradas")
        return datos_cuencas
    
    def _leer_datos_puntos(self, layer, campo_x, campo_y, campo_z, feedback):
        """Lee los puntos con sus coordenadas"""
        puntos = []
        
        for feature in layer.getFeatures():
            try:
                x_val = feature[campo_x]
                y_val = feature[campo_y]
                z_val = feature[campo_z]
                
                if any(val is None for val in [x_val, y_val, z_val]):
                    continue
                
                x = float(x_val)
                y = float(y_val)
                z = float(z_val)
                
                if not all(math.isfinite(val) for val in [x, y, z]):
                    continue
                
                puntos.append({
                    'x': x, 'y': y, 'z': z,
                    'feature': feature,
                    'geometry': feature.geometry()
                })
                
            except (ValueError, TypeError) as e:
                feedback.pushWarning(f"Error leyendo punto {feature.id()}: {e}")
                continue
        
        feedback.pushInfo(f"V2.0: {len(puntos)} puntos válidos encontrados")
        return puntos
    
    def _agrupar_puntos_por_cuenca(self, datos_cuencas, datos_puntos, feedback):
        """Agrupa puntos por cuenca y encuentra extremos de elevación"""
        cuencas_con_puntos = {}
        
        for area, datos_cuenca in datos_cuencas.items():
            cuenca_geom = datos_cuenca['geometry']
            puntos_en_cuenca = []
            
            # Encontrar puntos dentro de cada cuenca
            for punto in datos_puntos:
                punto_geom = punto['geometry']
                if cuenca_geom.contains(punto_geom) or cuenca_geom.intersects(punto_geom):
                    puntos_en_cuenca.append(punto)
            
            if len(puntos_en_cuenca) < 2:
                feedback.pushWarning(f"Cuenca {area:.2f} tiene menos de 2 puntos, saltando...")
                continue
            
            # Encontrar puntos de máxima y mínima elevación
            punto_max = max(puntos_en_cuenca, key=lambda p: p['z'])
            punto_min = min(puntos_en_cuenca, key=lambda p: p['z'])
            
            # Manejar duplicados - seleccionar por coordenada X máxima/mínima
            puntos_z_max = [p for p in puntos_en_cuenca if abs(p['z'] - punto_max['z']) < 1e-6]
            puntos_z_min = [p for p in puntos_en_cuenca if abs(p['z'] - punto_min['z']) < 1e-6]
            
            if len(puntos_z_max) > 1:
                punto_max = max(puntos_z_max, key=lambda p: p['x'])
            else:
                punto_max = puntos_z_max[0]
            
            if len(puntos_z_min) > 1:
                punto_min = min(puntos_z_min, key=lambda p: p['x'])
            else:
                punto_min = puntos_z_min[0]
            
            cuencas_con_puntos[area] = {
                'cuenca': datos_cuenca,
                'punto_max': punto_max,
                'punto_min': punto_min,
                'total_puntos': len(puntos_en_cuenca)
            }
        
        feedback.pushInfo(f"V2.0: {len(cuencas_con_puntos)} cuencas con puntos válidos")
        return cuencas_con_puntos
    
    def _calcular_elongacion_todas_cuencas(self, cuencas_con_puntos, feedback):
        """Calcula índices de elongación para todas las cuencas"""
        resultados = []
        
        for area, datos in cuencas_con_puntos.items():
            try:
                cuenca = datos['cuenca']
                punto_max = datos['punto_max']
                punto_min = datos['punto_min']
                
                # Calcular distancia 3D entre puntos extremos
                dx = punto_max['x'] - punto_min['x']
                dy = punto_max['y'] - punto_min['y']
                dz = punto_max['z'] - punto_min['z']
                
                distancia_max = math.sqrt(dx**2 + dy**2 + dz**2)
                
                # Calcular diámetro equivalente del círculo
                diametro_equivalente = 2 * math.sqrt(area / math.pi)
                
                # Calcular índice de elongación
                if distancia_max > 0:
                    indice_elongacion = diametro_equivalente / distancia_max
                else:
                    indice_elongacion = 0.0
                
                # Clasificar elongación
                clasificacion = self._clasificar_elongacion(indice_elongacion)
                
                resultado = {
                    'area': area,
                    'feature': cuenca['feature'],
                    'punto_min_x': punto_min['x'],
                    'punto_min_y': punto_min['y'],
                    'punto_min_z': punto_min['z'],
                    'punto_max_x': punto_max['x'],
                    'punto_max_y': punto_max['y'],
                    'punto_max_z': punto_max['z'],
                    'distancia_max': distancia_max,
                    'diametro_equivalente': diametro_equivalente,
                    'indice_elongacion': indice_elongacion,
                    'clasificacion': clasificacion,
                    'total_puntos': datos['total_puntos']
                }
                
                resultados.append(resultado)
                
            except Exception as e:
                feedback.pushWarning(f"Error calculando elongación para cuenca {area}: {e}")
                continue
        
        feedback.pushInfo(f"V2.0: Cálculos completados para {len(resultados)} cuencas")
        return resultados
    
    def _clasificar_elongacion(self, indice):
        """Clasifica el índice de elongación según rangos estándar"""
        if indice < 0.22:
            return "Muy alargada"
        elif indice < 0.30:
            return "Alargada"
        elif indice < 0.37:
            return "Ligeramente alargada"
        elif indice < 0.45:
            return "Ni alargada ni ensanchada"
        elif indice <= 0.60:
            return "Ligeramente ensanchada"
        elif indice <= 0.80:
            return "Ensanchada"
        elif indice <= 1.20:
            return "Muy ensanchada"
        else:
            return "Rodeando el desagüe"
    
    def _crear_capa_elongacion(self, input_layer, resultados, aplicar_simbologia, feedback):
        """Crea nueva capa independiente con resultados de elongación preservando geometrías de cuencas"""
        # Crear campos de salida - PRESERVAR TODOS LOS CAMPOS ORIGINALES
        fields = QgsFields(input_layer.fields())
        
        # Agregar campos específicos de elongación
        campos_elongacion = [
            ("MINPOINT_X", QVariant.Double, "double", 20, 6),
            ("MINPOINT_Y", QVariant.Double, "double", 20, 6),
            ("MINPOINT_Z", QVariant.Double, "double", 20, 2),
            ("MAXPOINT_X", QVariant.Double, "double", 20, 6),
            ("MAXPOINT_Y", QVariant.Double, "double", 20, 6),
            ("MAXPOINT_Z", QVariant.Double, "double", 20, 2),
            ("DIST_MAX", QVariant.Double, "double", 20, 2),
            ("DIAMETRO_EQ", QVariant.Double, "double", 20, 2),
            ("VALOR_ELON", QVariant.Double, "double", 20, 6),
            ("CLASIF_ELON", QVariant.String, "string", 50, 0),
            ("AREA_CUENCA", QVariant.Double, "double", 20, 2),
            ("NUM_PUNTOS", QVariant.Int, "integer", 10, 0)
        ]
        
        for nombre, tipo, tipo_str, longitud, precision in campos_elongacion:
            fields.append(QgsField(nombre, tipo, tipo_str, longitud, precision))
        
        # Determinar ubicación de salida - MULTIPLATAFORMA usando pathlib
        from pathlib import Path
        import os
        
        # Usar directorio home del usuario (funciona en Windows, Linux, macOS)
        home_dir = Path.home()
        documentos = home_dir / "Documents" / "Indices_Morfologicos" / "Resultados_Elongacion"
        
        # Crear directorio si no existe (multiplataforma)
        documentos.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"elongacion_cuencas_poligonos_{timestamp}.shp"
        output_path = str(documentos / nombre_archivo)
        
        feedback.pushInfo(f"📁 V2.0: Creando shapefile de polígonos en: {output_path}")
        feedback.pushInfo(f"🗺️ V2.0: Preservando geometrías de cuencas para visualización")
        
        # Crear writer - MANTENER TIPO DE GEOMETRÍA ORIGINAL (Polígonos)
        writer = QgsVectorFileWriter(
            output_path,
            "UTF-8",
            fields,
            QgsWkbTypes.Polygon,  # FORZAR polígonos para visualización de cuencas
            input_layer.crs(),
            "ESRI Shapefile"
        )
        
        if writer.hasError() != QgsVectorFileWriter.NoError:
            feedback.reportError(f"Error creando archivo: {writer.errorMessage()}")
            del writer
            return None
        
        # Crear diccionario para mapear áreas a features originales
        area_to_feature = {}
        for feature in input_layer.getFeatures():
            area_val = feature[self._validar_campos_cuencas(input_layer)]
            if area_val is not None and area_val > 0:
                area_to_feature[float(area_val)] = feature
        
        feedback.pushInfo(f"📊 V2.0: Mapeando {len(area_to_feature)} polígonos de cuencas originales")
        
        # Escribir features con geometrías de polígonos originales
        features_escritas = 0
        cuencas_sin_poligono = 0
        
        for resultado in resultados:
            try:
                area_cuenca = resultado['area']
                
                # Buscar la feature original correspondiente por área
                original_feature = area_to_feature.get(area_cuenca)
                
                if original_feature is None:
                    feedback.pushWarning(f"No se encontró polígono original para cuenca con área {area_cuenca}")
                    cuencas_sin_poligono += 1
                    continue
                
                # Crear nueva feature con campos expandidos
                new_feature = QgsFeature(fields)
                
                # Copiar TODOS los atributos originales de la cuenca
                for field in input_layer.fields():
                    field_name = field.name()
                    valor_original = original_feature[field_name]
                    new_feature[field_name] = valor_original
                
                # Asignar valores calculados de elongación
                new_feature["MINPOINT_X"] = resultado['punto_min_x']
                new_feature["MINPOINT_Y"] = resultado['punto_min_y']
                new_feature["MINPOINT_Z"] = resultado['punto_min_z']
                new_feature["MAXPOINT_X"] = resultado['punto_max_x']
                new_feature["MAXPOINT_Y"] = resultado['punto_max_y']
                new_feature["MAXPOINT_Z"] = resultado['punto_max_z']
                new_feature["DIST_MAX"] = resultado['distancia_max']
                new_feature["DIAMETRO_EQ"] = resultado['diametro_equivalente']
                new_feature["VALOR_ELON"] = resultado['indice_elongacion']
                new_feature["CLASIF_ELON"] = resultado['clasificacion']
                new_feature["AREA_CUENCA"] = resultado['area']
                new_feature["NUM_PUNTOS"] = resultado['total_puntos']
                
                # IMPORTANTE: Copiar la geometría ORIGINAL del polígono de cuenca
                new_feature.setGeometry(original_feature.geometry())
                
                if writer.addFeature(new_feature):
                    features_escritas += 1
                else:
                    feedback.pushWarning(f"No se pudo escribir polígono para cuenca {area_cuenca}")
                
            except Exception as e:
                feedback.pushWarning(f"Error escribiendo polígono de cuenca: {e}")
                continue
        
        del writer
        
        # Mostrar estadísticas de escritura
        feedback.pushInfo(f"✅ V2.0: Polígonos de cuencas escritos: {features_escritas}/{len(resultados)}")
        if cuencas_sin_poligono > 0:
            feedback.pushWarning(f"⚠️ V2.0: Cuencas sin polígono original: {cuencas_sin_poligono}")
        
        # Cargar al proyecto con nombre descriptivo
        layer_name = f"Elongacion_Cuencas_Poligonos_{timestamp}"
        nueva_capa = QgsVectorLayer(output_path, layer_name, "ogr")
        
        if nueva_capa.isValid():
            # Verificar información básica de la capa SIN operaciones de interfaz
            feedback.pushInfo(f"🔍 V2.0: Capa válida - CRS: {nueva_capa.crs().authid()}")
            feedback.pushInfo(f"🔍 V2.0: Geometría: {nueva_capa.geometryType()}")
            feedback.pushInfo(f"🔍 V2.0: Features: {nueva_capa.featureCount()}")
            
            # Verificar extent de manera segura
            try:
                extent = nueva_capa.extent()
                if not extent.isEmpty():
                    feedback.pushInfo(f"🔍 V2.0: Extent válido: {extent.toString()}")
                else:
                    feedback.pushWarning("⚠️ V2.0: Extent vacío detectado")
            except Exception as e:
                feedback.pushWarning(f"⚠️ V2.0: No se pudo calcular extent: {e}")
            
            # Aplicar simbología ANTES de agregar al proyecto
            if aplicar_simbologia:
                feedback.pushInfo("🎨 V2.0: Aplicando simbología antes de cargar...")
                self._aplicar_simbologia_elongacion_directa(nueva_capa, feedback)
            else:
                # Simbología básica segura
                self._aplicar_simbologia_basica_segura(nueva_capa, feedback)
            
            # Agregar al proyecto de manera segura
            QgsProject.instance().addMapLayer(nueva_capa)
            feedback.pushInfo(f"✅ V2.0: Capa '{layer_name}' agregada correctamente")
            feedback.pushInfo(f"📊 V2.0: Total polígonos: {nueva_capa.featureCount()}")
            
            # NO hacer operaciones de zoom/interfaz que pueden congelar QGIS
            feedback.pushInfo("🗺️ V2.0: Capa lista para visualización manual")
            
        else:
            feedback.reportError("❌ V2.0: Capa no válida")
            if nueva_capa.error().summary():
                feedback.reportError(f"❌ Error: {nueva_capa.error().summary()}")
        
        return output_path
    
    def _aplicar_simbologia_basica_segura(self, capa, feedback):
        """Aplica simbología básica de manera segura sin operaciones de interfaz"""
        try:
            # Verificar que la capa tiene el campo necesario
            field_names = [field.name() for field in capa.fields()]
            if 'CLASIF_ELON' not in field_names:
                feedback.pushWarning("Campo CLASIF_ELON no encontrado")
                return
            
            # Crear símbolo básico pero visible
            simbolo = QgsSymbol.defaultSymbol(capa.geometryType())
            simbolo.setColor(QColor(70, 130, 180))  # Azul acero
            simbolo.setOpacity(0.7)
            
            # Configurar borde
            if simbolo.symbolLayer(0):
                simbolo.symbolLayer(0).setStrokeColor(QColor(0, 0, 0))
                simbolo.symbolLayer(0).setStrokeWidth(0.3)
            
            # Aplicar renderer simple
            from qgis.core import QgsSingleSymbolRenderer
            renderer = QgsSingleSymbolRenderer(simbolo)
            capa.setRenderer(renderer)
            
            feedback.pushInfo("🎨 V2.0: Simbología básica aplicada de manera segura")
            
        except Exception as e:
            feedback.pushWarning(f"Error en simbología básica: {e}")
    
    def _aplicar_simbologia_elongacion_directa(self, capa, feedback):
        """Aplica simbología de elongación de manera segura"""
        try:
            # Verificar campo
            field_names = [field.name() for field in capa.fields()]
            if 'CLASIF_ELON' not in field_names:
                feedback.pushWarning("Campo CLASIF_ELON no encontrado")
                return False
            
            # Definir colores
            colores_clasificacion = {
                "Muy alargada": QColor(139, 0, 0),
                "Alargada": QColor(255, 69, 0),
                "Ligeramente alargada": QColor(255, 140, 0),
                "Ni alargada ni ensanchada": QColor(255, 215, 0),
                "Ligeramente ensanchada": QColor(173, 255, 47),
                "Ensanchada": QColor(0, 255, 127),
                "Muy ensanchada": QColor(0, 191, 255),
                "Rodeando el desagüe": QColor(30, 144, 255)
            }
            
            # Obtener valores únicos de manera segura
            valores_unicos = set()
            request = QgsFeatureRequest().setSubsetOfAttributes(['CLASIF_ELON'], capa.fields())
            
            try:
                for feature in capa.getFeatures(request):
                    valor = feature['CLASIF_ELON']
                    if valor and isinstance(valor, str):
                        valores_unicos.add(valor)
            except Exception as e:
                feedback.pushWarning(f"Error leyendo valores: {e}")
                return False
            
            feedback.pushInfo(f"🎨 V2.0: Clasificaciones encontradas: {list(valores_unicos)}")
            
            if not valores_unicos:
                feedback.pushWarning("No se encontraron valores de clasificación")
                return False
            
            # Crear categorías solo para valores existentes
            categorias = []
            for clasificacion in valores_unicos:
                if clasificacion in colores_clasificacion:
                    color = colores_clasificacion[clasificacion]
                    simbolo = QgsSymbol.defaultSymbol(capa.geometryType())
                    simbolo.setColor(color)
                    simbolo.setOpacity(0.8)
                    
                    # Borde negro para definición
                    if simbolo.symbolLayer(0):
                        simbolo.symbolLayer(0).setStrokeColor(QColor(0, 0, 0))
                        simbolo.symbolLayer(0).setStrokeWidth(0.2)
                    
                    categoria = QgsRendererCategory(clasificacion, simbolo, clasificacion)
                    categorias.append(categoria)
            
            if categorias:
                renderer = QgsCategorizedSymbolRenderer('CLASIF_ELON', categorias)
                capa.setRenderer(renderer)
                feedback.pushInfo(f"🎨 V2.0: Simbología aplicada - {len(categorias)} categorías")
                return True
            else:
                feedback.pushWarning("No se pudieron crear categorías")
                return False
            
        except Exception as e:
            feedback.reportError(f"Error en simbología categorizada: {e}")
            return False
    
    def _aplicar_simbologia_elongacion(self, output_path, feedback):
        """Método alternativo simplificado para simbología"""
        try:
            # Buscar la capa recién agregada
            capas = QgsProject.instance().mapLayers().values()
            capa_elongacion = None
            
            for capa in capas:
                if 'Elongacion_Cuencas_Poligonos' in capa.name():
                    capa_elongacion = capa
                    break
            
            if capa_elongacion:
                return self._aplicar_simbologia_elongacion_directa(capa_elongacion, feedback)
            else:
                feedback.pushWarning("No se encontró la capa para simbología alternativa")
                return False
            
        except Exception as e:
            feedback.reportError(f"Error en método alternativo: {e}")
            return False
    
    def _calcular_estadisticas_elongacion(self, resultados, feedback):
        """Calcula estadísticas completas de elongación"""
        if not resultados:
            return {"error": "No hay resultados"}
        
        # Extraer valores
        indices = [r['indice_elongacion'] for r in resultados]
        areas = [r['area'] for r in resultados]
        distancias = [r['distancia_max'] for r in resultados]
        clasificaciones = [r['clasificacion'] for r in resultados]
        
        # Contar clasificaciones
        conteo_clasificaciones = {}
        for clasif in clasificaciones:
            conteo_clasificaciones[clasif] = conteo_clasificaciones.get(clasif, 0) + 1
        
        # Calcular porcentajes
        total_cuencas = len(resultados)
        porcentajes_clasificaciones = {
            clasif: (count / total_cuencas) * 100 
            for clasif, count in conteo_clasificaciones.items()
        }
        
        estadisticas = {
            "total_cuencas": total_cuencas,
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
            # Estadísticas de índices
            "indice_promedio": np.mean(indices),
            "indice_maximo": np.max(indices),
            "indice_minimo": np.min(indices),
            "indice_mediana": np.median(indices),
            "indice_desviacion": np.std(indices),
            
            # Estadísticas de áreas
            "area_promedio": np.mean(areas),
            "area_maxima": np.max(areas),
            "area_minima": np.min(areas),
            "area_total": np.sum(areas),
            
            # Estadísticas de distancias
            "distancia_promedio": np.mean(distancias),
            "distancia_maxima": np.max(distancias),
            "distancia_minima": np.min(distancias),
            
            # Clasificaciones
            "conteo_clasificaciones": conteo_clasificaciones,
            "porcentajes_clasificaciones": porcentajes_clasificaciones,
            "clasificacion_predominante": max(conteo_clasificaciones.items(), key=lambda x: x[1])[0]
        }
        
        return estadisticas
    
    def _generar_visualizaciones(self, resultados, estadisticas, tipo_viz, archivo_salida, context, feedback):
        """Genera visualizaciones según el tipo seleccionado"""
        
        if tipo_viz == 0:  # Gráfico de barras interactivo
            self._mostrar_grafico_barras_interactivo(estadisticas, feedback)
        
        elif tipo_viz == 1:  # Mapa temático (ya aplicado en simbología)
            feedback.pushInfo("🗺️ V4.0: Mapa temático aplicado mediante simbología automática")
        
        elif tipo_viz == 2:  # Layout automático en QGIS
            self._crear_layout_elongacion(resultados, estadisticas, context, feedback)
        
        elif tipo_viz == 3:  # Reporte HTML completo
            self._generar_reporte_html_elongacion(resultados, estadisticas, archivo_salida, feedback)
        
        elif tipo_viz == 4:  # Archivo de imagen (gráfico)
            self._guardar_grafico_barras_archivo(estadisticas, archivo_salida, feedback)
    
    def _mostrar_grafico_barras_interactivo(self, estadisticas, feedback):
        """Muestra gráfico de barras interactivo con clasificaciones"""
        try:
            conteo = estadisticas['conteo_clasificaciones']
            porcentajes = estadisticas['porcentajes_clasificaciones']
            
            # Configurar matplotlib para ventana interactiva
            plt.ion()
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # Gráfico de conteos
            clasificaciones = list(conteo.keys())
            valores = list(conteo.values())
            colores = ['#8B0000', '#FF4500', '#FF8C00', '#FFD700', '#ADFF2F', '#00FF7F', '#00BFFF', '#1E90FF']
            
            bars1 = ax1.bar(range(len(clasificaciones)), valores, color=colores[:len(clasificaciones)])
            ax1.set_xlabel('Clasificación de Elongación', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Número de Cuencas', fontsize=12, fontweight='bold')
            ax1.set_title('Distribución de Cuencas por Clasificación\n(Conteo Absoluto)', fontsize=14, fontweight='bold')
            ax1.set_xticks(range(len(clasificaciones)))
            ax1.set_xticklabels(clasificaciones, rotation=45, ha='right')
            ax1.grid(True, alpha=0.3)
            
            # Agregar valores sobre las barras
            for bar, valor in zip(bars1, valores):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{valor}', ha='center', va='bottom', fontweight='bold')
            
            # Gráfico de porcentajes
            porcentajes_vals = [porcentajes[clasif] for clasif in clasificaciones]
            bars2 = ax2.bar(range(len(clasificaciones)), porcentajes_vals, color=colores[:len(clasificaciones)])
            ax2.set_xlabel('Clasificación de Elongación', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Porcentaje (%)', fontsize=12, fontweight='bold')
            ax2.set_title('Distribución de Cuencas por Clasificación\n(Porcentajes)', fontsize=14, fontweight='bold')
            ax2.set_xticks(range(len(clasificaciones)))
            ax2.set_xticklabels(clasificaciones, rotation=45, ha='right')
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
            
            # Agregar valores sobre las barras
            for bar, porcentaje in zip(bars2, porcentajes_vals):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{porcentaje:.1f}%', ha='center', va='bottom', fontweight='bold')
            
            # Título general
            fig.suptitle('Análisis de Elongación de Cuencas V4.0\nUniversidad Técnica Particular de Loja', 
                        fontsize=16, fontweight='bold', y=0.95)
            
            plt.tight_layout()
            plt.show()
            
            feedback.pushInfo("📊 V4.0: Gráfico interactivo mostrado exitosamente")
            
        except Exception as e:
            feedback.reportError(f"Error mostrando gráfico interactivo: {e}")
    
    def _crear_layout_elongacion(self, resultados, estadisticas, context, feedback):
        """Crea layout automático en QGIS"""
        try:
            # Crear gráfico temporal
            temp_grafico = os.path.join(tempfile.gettempdir(), 
                                      f"elongacion_grafico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            self._guardar_grafico_barras_archivo(estadisticas, temp_grafico, feedback)
            
            # Crear layout en QGIS
            project = QgsProject.instance()
            layout_manager = project.layoutManager()
            layout_name = f"Elongacion_V4_0_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            layout = QgsLayout(project)
            layout.setName(layout_name)
            
            # Configurar página A4 horizontal
            page = layout.pageCollection().page(0)
            if page:
                page.setPageSize(QgsLayoutSize(297, 210, QgsUnitTypes.LayoutMillimeters))
            
            # Título principal
            titulo = QgsLayoutItemLabel(layout)
            titulo.setText("Análisis de Elongación de Cuencas V4.0")
            titulo.attemptResize(QgsLayoutSize(250, 15, QgsUnitTypes.LayoutMillimeters))
            titulo.attemptMove(QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(titulo)
            
            # Subtítulo
            subtitulo = QgsLayoutItemLabel(layout)
            subtitulo.setText("Universidad Técnica Particular de Loja - UTPL")
            subtitulo.attemptResize(QgsLayoutSize(200, 10, QgsUnitTypes.LayoutMillimeters))
            subtitulo.attemptMove(QgsLayoutPoint(20, 35, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(subtitulo)
            
            # Imagen del gráfico
            if os.path.exists(temp_grafico):
                imagen_grafico = QgsLayoutItemPicture(layout)
                imagen_grafico.setPicturePath(temp_grafico)
                imagen_grafico.attemptResize(QgsLayoutSize(180, 120, QgsUnitTypes.LayoutMillimeters))
                imagen_grafico.attemptMove(QgsLayoutPoint(20, 50, QgsUnitTypes.LayoutMillimeters))
                layout.addLayoutItem(imagen_grafico)
            
            # Estadísticas resumen
            texto_stats = self._crear_texto_estadisticas_layout(estadisticas)
            label_stats = QgsLayoutItemLabel(layout)
            label_stats.setText(texto_stats)
            label_stats.attemptResize(QgsLayoutSize(90, 120, QgsUnitTypes.LayoutMillimeters))
            label_stats.attemptMove(QgsLayoutPoint(205, 50, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(label_stats)
            
            # Agregar al proyecto
            layout_manager.addLayout(layout)
            
            feedback.pushInfo(f"📋 V4.0: Layout '{layout_name}' creado exitosamente")
            
        except Exception as e:
            feedback.reportError(f"Error creando layout: {e}")
    
    def _guardar_grafico_barras_archivo(self, estadisticas, archivo_salida, feedback):
        """Guarda gráfico de barras en archivo"""
        try:
            conteo = estadisticas['conteo_clasificaciones']
            porcentajes = estadisticas['porcentajes_clasificaciones']
            
            # Configurar matplotlib para exportación
            matplotlib.use('Agg')
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            clasificaciones = list(conteo.keys())
            valores = list(conteo.values())
            colores = ['#8B0000', '#FF4500', '#FF8C00', '#FFD700', '#ADFF2F', '#00FF7F', '#00BFFF', '#1E90FF']
            
            # Gráfico de conteos
            bars1 = ax1.bar(range(len(clasificaciones)), valores, color=colores[:len(clasificaciones)], alpha=0.8)
            ax1.set_xlabel('Clasificación de Elongación', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Número de Cuencas', fontsize=14, fontweight='bold')
            ax1.set_title('Distribución por Clasificación\n(Conteo Absoluto)', fontsize=14, fontweight='bold')
            ax1.set_xticks(range(len(clasificaciones)))
            ax1.set_xticklabels(clasificaciones, rotation=45, ha='right', fontsize=10)
            ax1.grid(True, alpha=0.3)
            
            for bar, valor in zip(bars1, valores):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                        f'{valor}', ha='center', va='bottom', fontweight='bold', fontsize=12)
            
            # Gráfico de porcentajes
            porcentajes_vals = [porcentajes[clasif] for clasif in clasificaciones]
            bars2 = ax2.bar(range(len(clasificaciones)), porcentajes_vals, color=colores[:len(clasificaciones)], alpha=0.8)
            ax2.set_xlabel('Clasificación de Elongación', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Porcentaje (%)', fontsize=14, fontweight='bold')
            ax2.set_title('Distribución por Clasificación\n(Porcentajes)', fontsize=14, fontweight='bold')
            ax2.set_xticks(range(len(clasificaciones)))
            ax2.set_xticklabels(clasificaciones, rotation=45, ha='right', fontsize=10)
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, max(porcentajes_vals) * 1.2)
            
            for bar, porcentaje in zip(bars2, porcentajes_vals):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{porcentaje:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)
            
            # Título general
            fig.suptitle('Análisis de Elongación de Cuencas V4.0\nUniversidad Técnica Particular de Loja - UTPL', 
                        fontsize=18, fontweight='bold', y=0.95)
            
            # Determinar ruta de archivo
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                ruta_grafico = archivo_salida
            else:
                from pathlib import Path
                documentos = Path.home() / "Documents" / "Indices_Morfologicos" / "Graficos"
                documentos.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ruta_grafico = str(documentos / f"elongacion_barras_v4_{timestamp}.png")
            
            plt.tight_layout()
            plt.savefig(ruta_grafico, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            feedback.pushInfo(f"📊 V4.0: Gráfico guardado en: {ruta_grafico}")
            return ruta_grafico
            
        except Exception as e:
            feedback.reportError(f"Error guardando gráfico: {e}")
            return None
    
    def _generar_reporte_html_elongacion(self, resultados, estadisticas, archivo_salida, feedback):
        """Genera reporte HTML completo interactivo"""
        try:
            # Preparar datos para tablas y gráficos
            tabla_cuencas = self._crear_tabla_html_cuencas(resultados)
            grafico_datos = self._preparar_datos_grafico_html(estadisticas)
            
            # Crear contenido HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reporte Elongación V4.0 - UTPL</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    * {{
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                        color: #1a202c;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
                        border: 1px solid #e2e8f0;
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #2d3748;
                        padding-bottom: 25px;
                        margin-bottom: 35px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: -40px -40px 35px -40px;
                        padding: 40px 40px 25px 40px;
                        border-radius: 12px 12px 0 0;
                        color: white;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 2.8em;
                        font-weight: 700;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                        font-family: 'Times New Roman', serif;
                    }}
                    .header p {{
                        margin: 10px 0 5px 0;
                        font-size: 1.1em;
                        opacity: 0.95;
                    }}
                    .version-badge {{
                        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                        color: white;
                        padding: 8px 20px;
                        border-radius: 25px;
                        font-size: 0.9em;
                        font-weight: 600;
                        display: inline-block;
                        margin-top: 15px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    }}
                    .section {{
                        margin: 35px 0;
                        padding: 25px;
                        background: #f8fafc;
                        border-radius: 10px;
                        border-left: 5px solid #4299e1;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                    }}
                    .section h2 {{
                        color: #2d3748;
                        margin-top: 0;
                        font-size: 1.6em;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                        gap: 20px;
                        margin: 25px 0;
                    }}
                    .stat-card {{
                        background: white;
                        padding: 25px;
                        border-radius: 10px;
                        border-left: 5px solid #48bb78;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                    }}
                    .stat-card:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
                    }}
                    .stat-value {{
                        font-size: 2.2em;
                        font-weight: 700;
                        color: #2d3748;
                        margin: 0;
                        font-family: 'Arial', sans-serif;
                    }}
                    .stat-label {{
                        color: #718096;
                        margin: 8px 0 0 0;
                        font-size: 0.95em;
                        font-weight: 500;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .tabla-cuencas {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 25px 0;
                        font-size: 0.9em;
                        background: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    }}
                    .tabla-cuencas th {{
                        background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
                        color: white;
                        font-weight: 600;
                        padding: 15px 12px;
                        text-align: left;
                        font-size: 0.85em;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .tabla-cuencas td {{
                        padding: 12px;
                        border-bottom: 1px solid #e2e8f0;
                    }}
                    .tabla-cuencas tr:nth-child(even) {{
                        background-color: #f7fafc;
                    }}
                    .tabla-cuencas tr:hover {{
                        background-color: #edf2f7;
                    }}
                    .grafico-container {{
                        margin: 30px 0;
                        padding: 25px;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                        border: 1px solid #e2e8f0;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 50px;
                        padding-top: 30px;
                        border-top: 2px solid #e2e8f0;
                        color: #718096;
                        background: #f8fafc;
                        margin-left: -40px;
                        margin-right: -40px;
                        margin-bottom: -40px;
                        padding-left: 40px;
                        padding-right: 40px;
                        padding-bottom: 30px;
                        border-radius: 0 0 12px 12px;
                    }}
                    .footer p {{
                        margin: 8px 0;
                    }}
                    .interpretacion {{
                        background: linear-gradient(135deg, #e6fffa 0%, #b2f5ea 100%);
                        padding: 25px;
                        border-radius: 10px;
                        border-left: 5px solid #38b2ac;
                        margin: 25px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                    }}
                    .interpretacion h3 {{
                        color: #234e52;
                        margin-top: 0;
                        font-size: 1.3em;
                    }}
                    .interpretacion ul {{
                        color: #2c7a7b;
                        line-height: 1.8;
                    }}
                    .interpretacion li {{
                        margin-bottom: 8px;
                    }}
                    @media print {{
                        body {{ background: white; }}
                        .container {{ box-shadow: none; }}
                        .header {{ background: #2d3748 !important; }}
                    }}
                    @media (max-width: 768px) {{
                        .container {{ padding: 20px; margin: 10px; }}
                        .header {{ margin: -20px -20px 25px -20px; padding: 30px 20px 20px 20px; }}
                        .header h1 {{ font-size: 2.2em; }}
                        .stats-grid {{ grid-template-columns: 1fr; }}
                        .tabla-cuencas {{ font-size: 0.8em; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Análisis de Elongación de Cuencas</h1>
                        <div class="version-badge">Versión 2.0 Interactiva</div>
                        <p>Universidad Técnica Particular de Loja - UTPL</p>
                        <p>Fecha de análisis: {estadisticas.get('fecha_analisis', 'N/A')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>📊 Resumen Ejecutivo</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('total_cuencas', 0)}</p>
                                <p class="stat-label">Total de Cuencas Analizadas</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('area_total', 0):.2f}</p>
                                <p class="stat-label">Área Total Analizada</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('indice_promedio', 0):.3f}</p>
                                <p class="stat-label">Índice de Elongación Promedio</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('clasificacion_predominante', 'N/A')}</p>
                                <p class="stat-label">Clasificación Predominante</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📈 Análisis Morfométrico de Cuencas</h2>
                        <div class="grafico-container">
                            <div id="grafico-barras" style="width:100%;height:600px;margin-bottom:40px;"></div>
                        </div>
                        <div class="grafico-container">
                            <div id="grafico-circular" style="width:100%;height:500px;"></div>
                        </div>
                        <p style="text-align: center; margin-top: 20px; color: #666; font-style: italic;">
                            <strong>Nota metodológica:</strong> Clasificación basada en Schumm (1956) mediante el índice Re = Diámetro equivalente / Distancia máxima.<br>
                            El análisis considera la relación área-forma para caracterización geomorfológica de cuencas hidrográficas.
                        </p>
                    </div>
                    
                    <div class="section">
                        <h2>📋 Estadísticas Detalladas</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('indice_maximo', 0):.4f}</p>
                                <p class="stat-label">Índice Máximo</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('indice_minimo', 0):.4f}</p>
                                <p class="stat-label">Índice Mínimo</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('indice_mediana', 0):.4f}</p>
                                <p class="stat-label">Mediana</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('indice_desviacion', 0):.4f}</p>
                                <p class="stat-label">Desviación Estándar</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('area_maxima', 0):.2f}</p>
                                <p class="stat-label">Área Máxima de Cuenca</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('distancia_maxima', 0):.2f} m</p>
                                <p class="stat-label">Distancia Máxima</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📊 Detalle por Cuencas</h2>
                        {tabla_cuencas}
                    </div>
                    
                    <div class="section">
                        <h2>📏 Tabla de Clasificación de Elongación</h2>
                        <p><strong>Clasificación según Schumm (1956):</strong></p>
                        <table class="tabla-cuencas" style="margin-top: 15px;">
                            <thead>
                                <tr>
                                    <th>Clasificación</th>
                                    <th>Rango del Índice (Re)</th>
                                    <th>Descripción Morfológica</th>
                                    <th>Características</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><strong>Muy alargada</strong></td>
                                    <td>Re &lt; 0.22</td>
                                    <td>Forma muy estrecha y alargada</td>
                                    <td>Cuencas con control estructural fuerte</td>
                                </tr>
                                <tr>
                                    <td><strong>Alargada</strong></td>
                                    <td>0.22 ≤ Re &lt; 0.30</td>
                                    <td>Forma alargada</td>
                                    <td>Topografía montañosa pronunciada</td>
                                </tr>
                                <tr>
                                    <td><strong>Ligeramente alargada</strong></td>
                                    <td>0.30 ≤ Re &lt; 0.37</td>
                                    <td>Tendencia alargada</td>
                                    <td>Desarrollo fluvial en terrenos inclinados</td>
                                </tr>
                                <tr>
                                    <td><strong>Intermedia</strong></td>
                                    <td>0.37 ≤ Re &lt; 0.45</td>
                                    <td>Forma equilibrada</td>
                                    <td>Topografía moderada, desarrollo maduro</td>
                                </tr>
                                <tr>
                                    <td><strong>Ligeramente ensanchada</strong></td>
                                    <td>0.45 ≤ Re ≤ 0.60</td>
                                    <td>Tendencia ensanchada</td>
                                    <td>Pendientes suaves, erosión moderada</td>
                                </tr>
                                <tr>
                                    <td><strong>Ensanchada</strong></td>
                                    <td>0.60 &lt; Re ≤ 0.80</td>
                                    <td>Forma ensanchada</td>
                                    <td>Control litológico horizontal</td>
                                </tr>
                                <tr>
                                    <td><strong>Muy ensanchada</strong></td>
                                    <td>0.80 &lt; Re ≤ 1.20</td>
                                    <td>Forma muy ancha</td>
                                    <td>Topografía muy suave</td>
                                </tr>
                                <tr>
                                    <td><strong>Circular</strong></td>
                                    <td>Re &gt; 1.20</td>
                                    <td>Forma tendiendo a circular</td>
                                    <td>Cuencas rodeando el punto de desagüe</td>
                                </tr>
                            </tbody>
                        </table>
                        <p style="margin-top: 15px; font-style: italic; color: #666;">
                            <strong>Nota:</strong> Re = Índice de elongación = Diámetro equivalente / Distancia máxima<br>
                            Donde: Diámetro equivalente = 2√(Área/π)
                        </p>
                    </div>
                    
                    <div class="section">
                        <h2>💡 Interpretación Geomorfológica</h2>
                        <div class="interpretacion">
                            {self._generar_interpretacion_elongacion_html(estadisticas)}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Reporte generado automáticamente por el Plugin de Índices Morfológicos V2.0</strong></p>
                        <p>Universidad Técnica Particular de Loja - Departamento de Ingeniería Civil</p>
                        <p>Basado en el trabajo de: Ing. Santiago Quiñones, Ing. María Fernanda Guarderas, Nelson Aranda</p>
                    </div>
                </div>
                
                <script>
                    {grafico_datos}
                </script>
            </body>
            </html>
            """
            
            # Determinar ubicación de salida - MULTIPLATAFORMA
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                if not archivo_salida.lower().endswith('.html'):
                    archivo_salida += '.html'
                ruta_html = archivo_salida
            else:
                from pathlib import Path
                # Usar directorio home multiplataforma
                home_dir = Path.home()
                documentos = home_dir / "Documents" / "Indices_Morfologicos" / "Reportes"
                documentos.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ruta_html = str(documentos / f"reporte_elongacion_v2_interactivo_{timestamp}.html")
            
            with open(ruta_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Abrir en navegador
            webbrowser.open(f"file://{ruta_html}")
            feedback.pushInfo(f"📄 V2.0: Reporte HTML interactivo: {ruta_html}")
                
        except Exception as e:
            feedback.reportError(f"Error generando reporte HTML: {e}")
    
    def _crear_tabla_html_cuencas(self, resultados):
        """Crea tabla HTML con detalles de cada cuenca"""
        tabla_html = '<table class="tabla-cuencas">\n'
        tabla_html += '<thead>\n<tr>\n'
        tabla_html += '<th>Cuenca ID</th><th>Área</th><th>Distancia Máx</th><th>Índice Elongación</th>'
        tabla_html += '<th>Clasificación</th><th>Puntos Analizados</th>\n'
        tabla_html += '</tr>\n</thead>\n<tbody>\n'
        
        for i, resultado in enumerate(resultados, 1):
            tabla_html += f'<tr>\n'
            tabla_html += f'<td>Cuenca {i}</td>'
            tabla_html += f'<td>{resultado["area"]:.2f}</td>'
            tabla_html += f'<td>{resultado["distancia_max"]:.2f} m</td>'
            tabla_html += f'<td>{resultado["indice_elongacion"]:.4f}</td>'
            tabla_html += f'<td>{resultado["clasificacion"]}</td>'
            tabla_html += f'<td>{resultado["total_puntos"]}</td>'
            tabla_html += f'</tr>\n'
        
        tabla_html += '</tbody>\n</table>'
        return tabla_html
    
    def _preparar_datos_grafico_html(self, estadisticas):
        """Prepara datos JavaScript para gráfico Plotly profesional"""
        conteo = estadisticas['conteo_clasificaciones']
        porcentajes = estadisticas['porcentajes_clasificaciones']
        
        # Ordenar las clasificaciones según el índice de elongación (de menos a más elongada)
        orden_clasificaciones = [
            "Rodeando el desagüe",
            "Muy ensanchada", 
            "Ensanchada",
            "Ligeramente ensanchada",
            "Ni alargada ni ensanchada",
            "Ligeramente alargada",
            "Alargada",
            "Muy alargada"
        ]
        
        # Filtrar solo las que existen en los datos
        clasificaciones_existentes = [c for c in orden_clasificaciones if c in conteo]
        valores = [conteo[c] for c in clasificaciones_existentes]
        porcentajes_vals = [porcentajes[c] for c in clasificaciones_existentes]
        
        # Colores profesionales según el espectro científico estándar
        colores_profesionales = {
            "Muy alargada": "#8B0000",           # Rojo oscuro
            "Alargada": "#DC143C",               # Crimson
            "Ligeramente alargada": "#FF6347",    # Tomate
            "Ni alargada ni ensanchada": "#FFD700", # Dorado
            "Ligeramente ensanchada": "#9ACD32",  # Verde amarillo
            "Ensanchada": "#32CD32",             # Verde lima
            "Muy ensanchada": "#1E90FF",         # Azul Dodger
            "Rodeando el desagüe": "#4169E1"     # Azul real
        }
        
        colores = [colores_profesionales.get(c, "#808080") for c in clasificaciones_existentes]
        
        # Abreviaciones para mejor presentación en gráfico
        clasificaciones_abrev = []
        for c in clasificaciones_existentes:
            if c == "Ni alargada ni ensanchada":
                clasificaciones_abrev.append("Intermedia")
            elif c == "Ligeramente alargada":
                clasificaciones_abrev.append("Lig. alargada")
            elif c == "Ligeramente ensanchada":
                clasificaciones_abrev.append("Lig. ensanchada")
            elif c == "Rodeando el desagüe":
                clasificaciones_abrev.append("Circular")
            elif c == "Muy alargada":
                clasificaciones_abrev.append("Muy alargada")
            elif c == "Muy ensanchada":
                clasificaciones_abrev.append("Muy ensanchada")
            else:
                clasificaciones_abrev.append(c)
        
        script_js = f"""
        // Datos del análisis morfométrico
        var clasificaciones_completas = {clasificaciones_existentes};
        var clasificaciones_display = {clasificaciones_abrev};
        var valores = {valores};
        var porcentajes = {porcentajes_vals};
        var colores = {colores};
        
        // Configuración del gráfico principal
        var trace_barras = {{
            x: clasificaciones_display,
            y: valores,
            type: 'bar',
            marker: {{
                color: colores,
                opacity: 0.85,
                line: {{
                    color: '#2F2F2F',
                    width: 1.2
                }}
            }},
            text: valores.map((v, i) => `${{v}} cuencas<br>(${{porcentajes[i].toFixed(1)}}%)`),
            textposition: 'outside',
            textfont: {{
                family: 'Arial, sans-serif',
                size: 11,
                color: '#2F2F2F'
            }},
            hovertemplate: 
                '<b>%{{data.name}}: %{{x}}</b><br>' +
                'Número de cuencas: %{{y}}<br>' +
                'Porcentaje: %{{customdata:.1f}}%<br>' +
                '<extra></extra>',
            customdata: porcentajes,
            name: 'Distribución Morfométrica'
        }};
        
        // Layout profesional estilo paper científico
        var layout_principal = {{
            title: {{
                text: 'Distribución Morfométrica de Cuencas Hidrográficas<br><sub>Índice de Elongación según Schumm (1956)</sub>',
                font: {{ 
                    family: 'Times New Roman, serif',
                    size: 16, 
                    color: '#1f2937',
                    weight: 'bold'
                }},
                x: 0.5,
                y: 0.95
            }},
            xaxis: {{
                title: {{
                    text: 'Clasificación Morfométrica',
                    font: {{ family: 'Arial, sans-serif', size: 13, color: '#374151' }}
                }},
                tickangle: -35,
                tickfont: {{ family: 'Arial, sans-serif', size: 10, color: '#4B5563' }},
                showgrid: false,
                showline: true,
                linecolor: '#D1D5DB',
                linewidth: 1,
                mirror: true
            }},
            yaxis: {{
                title: {{
                    text: 'Número de Cuencas',
                    font: {{ family: 'Arial, sans-serif', size: 13, color: '#374151' }}
                }},
                tickfont: {{ family: 'Arial, sans-serif', size: 10, color: '#4B5563' }},
                showgrid: true,
                gridcolor: '#F3F4F6',
                gridwidth: 1,
                showline: true,
                linecolor: '#D1D5DB',
                linewidth: 1,
                mirror: true,
                zeroline: false
            }},
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            showlegend: false,
            margin: {{
                l: 80,
                r: 40,
                t: 100,
                b: 120
            }},
            font: {{
                family: 'Arial, sans-serif'
            }},
            annotations: [
                {{
                    text: 'Re = Diámetro equivalente / Distancia máxima',
                    showarrow: false,
                    x: 0.5,
                    y: -0.25,
                    xref: 'paper',
                    yref: 'paper',
                    font: {{
                        family: 'Arial, sans-serif',
                        size: 10,
                        color: '#6B7280',
                        style: 'italic'
                    }}
                }},
                {{
                    text: 'n = {estadisticas.get("total_cuencas", 0)} cuencas analizadas',
                    showarrow: false,
                    x: 0.02,
                    y: 0.98,
                    xref: 'paper',
                    yref: 'paper',
                    font: {{
                        family: 'Arial, sans-serif',
                        size: 10,
                        color: '#6B7280'
                    }}
                }}
            ]
        }};
        
        // Configuración de herramientas profesional
        var config_principal = {{
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: [
                'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d',
                'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'
            ],
            toImageButtonOptions: {{
                format: 'png',
                filename: 'distribucion_morfometrica_cuencas',
                height: 600,
                width: 900,
                scale: 3
            }},
            locale: 'es'
        }};
        
        // Crear gráfico principal
        Plotly.newPlot('grafico-barras', [trace_barras], layout_principal, config_principal);
        
        // Gráfico circular complementario (pie chart)
        var trace_circular = {{
            labels: clasificaciones_display,
            values: porcentajes,
            type: 'pie',
            marker: {{
                colors: colores,
                line: {{
                    color: '#FFFFFF',
                    width: 2
                }}
            }},
            textinfo: 'label+percent',
            textposition: 'outside',
            textfont: {{
                family: 'Arial, sans-serif',
                size: 11
            }},
            hovertemplate: 
                '<b>%{{label}}</b><br>' +
                'Porcentaje: %{{percent}}<br>' +
                'Cuencas: %{{value:.1f}}%<br>' +
                '<extra></extra>',
            hole: 0.3
        }};
        
        var layout_circular = {{
            title: {{
                text: 'Distribución Porcentual<br><sub>Análisis Morfométrico Regional</sub>',
                font: {{ 
                    family: 'Times New Roman, serif',
                    size: 14, 
                    color: '#1f2937'
                }},
                x: 0.5,
                y: 0.95
            }},
            showlegend: true,
            legend: {{
                orientation: 'v',
                x: 1.02,
                y: 0.5,
                font: {{
                    family: 'Arial, sans-serif',
                    size: 10
                }}
            }},
            margin: {{
                l: 20,
                r: 120,
                t: 80,
                b: 20
            }},
            paper_bgcolor: 'white',
            annotations: [
                {{
                    text: 'Total:<br>{estadisticas.get("total_cuencas", 0)}<br>cuencas',
                    showarrow: false,
                    x: 0.5,
                    y: 0.5,
                    font: {{
                        family: 'Arial, sans-serif',
                        size: 12,
                        color: '#374151'
                    }}
                }}
            ]
        }};
        
        // Crear gráfico circular
        Plotly.newPlot('grafico-circular', [trace_circular], layout_circular, config_principal);
        """
        
        return script_js
    
    def _generar_interpretacion_elongacion_html(self, estadisticas):
        """Genera interpretación geomorfológica automática"""
        try:
            indice_promedio = estadisticas.get('indice_promedio', 0)
            clasificacion_pred = estadisticas.get('clasificacion_predominante', '')
            porcentajes = estadisticas.get('porcentajes_clasificaciones', {})
            
            interpretacion = "<h3>Análisis Geomorfológico Automático:</h3><ul>"
            
            # Interpretación del índice promedio
            if indice_promedio < 0.30:
                interpretacion += "<li><strong>Cuencas Predominantemente Alargadas:</strong> El índice promedio indica que las cuencas tienden a ser alargadas, característica de sistemas fluviales con control estructural fuerte o topografía montañosa pronunciada.</li>"
            elif indice_promedio < 0.45:
                interpretacion += "<li><strong>Cuencas de Forma Intermedia:</strong> El índice promedio sugiere cuencas con formas equilibradas, típicas de terrenos con topografía moderada y desarrollo fluvial maduro.</li>"
            elif indice_promedio < 0.80:
                interpretacion += "<li><strong>Cuencas Tendiendo a Ensanchadas:</strong> El índice promedio indica cuencas con tendencia al ensanchamiento, características de terrenos con pendientes suaves y control litológico horizontal.</li>"
            else:
                interpretacion += "<li><strong>Cuencas Muy Ensanchadas:</strong> El índice promedio sugiere cuencas muy ensanchadas, típicas de zonas con topografía muy suave o control estructural particular.</li>"
            
            # Análisis de la clasificación predominante
            porcentaje_pred = porcentajes.get(clasificacion_pred, 0)
            interpretacion += f"<li><strong>Clasificación Predominante:</strong> {clasificacion_pred} ({porcentaje_pred:.1f}% de las cuencas), lo que sugiere un patrón geomorfológico dominante en la región de estudio.</li>"
            
            # Análisis de variabilidad
            desviacion = estadisticas.get('indice_desviacion', 0)
            if desviacion > 0.2:
                interpretacion += "<li><strong>Alta Variabilidad:</strong> La desviación estándar elevada indica gran diversidad en las formas de cuencas, sugiriendo heterogeneidad geológica o topográfica en la región.</li>"
            else:
                interpretacion += "<li><strong>Variabilidad Moderada:</strong> La desviación estándar moderada sugiere cierta homogeneidad en los procesos geomorfológicos de la región.</li>"
            
            # Análisis de distribución
            num_clasificaciones = len([p for p in porcentajes.values() if p > 5])
            if num_clasificaciones > 4:
                interpretacion += "<li><strong>Diversidad Geomorfológica:</strong> La presencia de múltiples clasificaciones indica complejidad en los procesos formativos y posible influencia de diferentes controles geológicos.</li>"
            
            interpretacion += "</ul>"
            
            # Recomendaciones
            interpretacion += "<h3>Recomendaciones:</h3><ul>"
            interpretacion += "<li>Correlacionar los patrones de elongación con mapas geológicos para identificar controles litológicos.</li>"
            interpretacion += "<li>Analizar la relación entre elongación y características hidrográficas (orden de corrientes, densidad de drenaje).</li>"
            interpretacion += "<li>Considerar análisis complementarios de otros índices morfométricos para validación.</li>"
            interpretacion += "<li>Evaluar la influencia de la actividad tectónica en las formas de cuencas más alargadas.</li>"
            interpretacion += "</ul>"
            
            return interpretacion
        except Exception:
            return "<p>No se pudo generar interpretación automática. Consulte las estadísticas numéricas para análisis manual.</p>"
    
    def _crear_texto_estadisticas_layout(self, estadisticas):
        """Crea texto formateado para layout QGIS"""
        if "error" in estadisticas:
            return "Error en estadísticas V2.0"
        
        texto = f"""ESTADÍSTICAS ELONGACIÓN V2.0

Total cuencas: {estadisticas.get('total_cuencas', 0)}
Área total: {estadisticas.get('area_total', 0):.2f}

ÍNDICES:
Promedio: {estadisticas.get('indice_promedio', 0):.4f}
Máximo: {estadisticas.get('indice_maximo', 0):.4f}
Mínimo: {estadisticas.get('indice_minimo', 0):.4f}

PREDOMINANTE:
{estadisticas.get('clasificacion_predominante', 'N/A')}

{estadisticas.get('fecha_analisis', 'N/A')}"""
        
        return texto
    
    def _generar_reporte_elongacion(self, resultados, estadisticas, archivo_salida, feedback):
        """Genera reporte estadístico detallado en archivo de texto"""
        try:
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                archivo_reporte = archivo_salida.replace('.png', '_reporte_v2.txt').replace('.pdf', '_reporte_v2.txt')
            else:
                from pathlib import Path
                # Usar directorio home multiplataforma
                home_dir = Path.home()
                documentos = home_dir / "Documents" / "Indices_Morfologicos" / "Reportes"
                documentos.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archivo_reporte = str(documentos / f"reporte_elongacion_v2_{timestamp}.txt")
            
            with open(archivo_reporte, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("REPORTE ANÁLISIS ELONGACIÓN DE CUENCAS V2.0\n")
                f.write("Universidad Técnica Particular de Loja - UTPL\n")
                f.write("="*80 + "\n\n")
                f.write(f"Fecha: {estadisticas.get('fecha_analisis', 'N/A')}\n\n")
                
                f.write("RESUMEN EJECUTIVO:\n")
                f.write("-"*40 + "\n")
                f.write(f"Total de cuencas analizadas: {estadisticas.get('total_cuencas', 0)}\n")
                f.write(f"Área total analizada: {estadisticas.get('area_total', 0):.2f}\n")
                f.write(f"Clasificación predominante: {estadisticas.get('clasificacion_predominante', 'N/A')}\n\n")
                
                f.write("ESTADÍSTICAS DE ÍNDICES DE ELONGACIÓN:\n")
                f.write("-"*40 + "\n")
                f.write(f"Promedio: {estadisticas.get('indice_promedio', 0):.6f}\n")
                f.write(f"Máximo: {estadisticas.get('indice_maximo', 0):.6f}\n")
                f.write(f"Mínimo: {estadisticas.get('indice_minimo', 0):.6f}\n")
                f.write(f"Mediana: {estadisticas.get('indice_mediana', 0):.6f}\n")
                f.write(f"Desviación estándar: {estadisticas.get('indice_desviacion', 0):.6f}\n\n")
                
                f.write("DISTRIBUCIÓN POR CLASIFICACIONES:\n")
                f.write("-"*40 + "\n")
                conteo = estadisticas.get('conteo_clasificaciones', {})
                porcentajes = estadisticas.get('porcentajes_clasificaciones', {})
                for clasif, count in conteo.items():
                    porcentaje = porcentajes.get(clasif, 0)
                    f.write(f"{clasif}: {count} cuencas ({porcentaje:.1f}%)\n")
                
                f.write("\n" + "DETALLE POR CUENCAS:\n")
                f.write("-"*40 + "\n")
                f.write("ID\tÁrea\t\tDist_Max\tÍndice\t\tClasificación\n")
                f.write("-"*80 + "\n")
                
                for i, resultado in enumerate(resultados, 1):
                    f.write(f"{i}\t{resultado['area']:.2f}\t\t{resultado['distancia_max']:.2f}\t\t"
                           f"{resultado['indice_elongacion']:.4f}\t\t{resultado['clasificacion']}\n")
                
                f.write("\n" + "="*80 + "\n")
                f.write("Fin del reporte V2.0\n")
            
            feedback.pushInfo(f"📄 V2.0: Reporte detallado: {archivo_reporte}")
            
        except Exception as e:
            feedback.reportError(f"Error generando reporte: {e}")
    
    def _mostrar_estadisticas_log(self, estadisticas, feedback):
        """Muestra estadísticas completas en el log"""
        if "error" in estadisticas:
            feedback.reportError("V2.0: No se pudieron calcular estadísticas válidas")
            return
        
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("📊 ESTADÍSTICAS ELONGACIÓN")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"Total de cuencas: {estadisticas['total_cuencas']}")
        feedback.pushInfo(f"Área total analizada: {estadisticas['area_total']:.2f}")
        feedback.pushInfo(f"Clasificación predominante: {estadisticas['clasificacion_predominante']}")
        feedback.pushInfo("")
        feedback.pushInfo("ÍNDICES DE ELONGACIÓN:")
        feedback.pushInfo(f"  Promedio: {estadisticas['indice_promedio']:.4f}")
        feedback.pushInfo(f"  Máximo: {estadisticas['indice_maximo']:.4f}")
        feedback.pushInfo(f"  Mínimo: {estadisticas['indice_minimo']:.4f}")
        feedback.pushInfo(f"  Mediana: {estadisticas['indice_mediana']:.4f}")
        feedback.pushInfo(f"  Desviación: {estadisticas['indice_desviacion']:.4f}")
        feedback.pushInfo("")
        feedback.pushInfo("DISTRIBUCIÓN POR CLASIFICACIONES:")
        conteo = estadisticas['conteo_clasificaciones']
        porcentajes = estadisticas['porcentajes_clasificaciones']
        for clasif, count in conteo.items():
            porcentaje = porcentajes[clasif]
            feedback.pushInfo(f"  {clasif}: {count} ({porcentaje:.1f}%)")
        feedback.pushInfo("")
        feedback.pushInfo("ESTADÍSTICAS DE ÁREAS:")
        feedback.pushInfo(f"  Área promedio: {estadisticas['area_promedio']:.2f}")
        feedback.pushInfo(f"  Área máxima: {estadisticas['area_maxima']:.2f}")
        feedback.pushInfo(f"  Área mínima: {estadisticas['area_minima']:.2f}")
        feedback.pushInfo("")
        feedback.pushInfo("ESTADÍSTICAS DE DISTANCIAS:")
        feedback.pushInfo(f"  Distancia promedio: {estadisticas['distancia_promedio']:.2f} m")
        feedback.pushInfo(f"  Distancia máxima: {estadisticas['distancia_maxima']:.2f} m")
        feedback.pushInfo(f"  Distancia mínima: {estadisticas['distancia_minima']:.2f} m")
        feedback.pushInfo("=" * 60)
    
    def name(self):
        return 'elongacion_v2'
        
    def displayName(self):
        return self.tr('Calcular Elongación V2.0 🚀')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
        
    def shortHelpString(self):
        return self.tr('''
        <h3>Cálculo de Elongación de Cuencas V2.0</h3>
        
        <p>Calcula el índice de elongación de cuencas hidrográficas analizando la relación 
        entre el área de la cuenca y la distancia máxima entre puntos extremos de elevación.</p>
        
        <h4>Método:</h4>
        <p><strong>Re = Diámetro equivalente / Distancia máxima</strong><br>
        Donde: Diámetro equivalente = 2√(Área/π)</p>
        
        <h4>Datos de entrada:</h4>
        <ul>
        <li><strong>Polígonos de cuencas:</strong> Capa vectorial con campo de área (Shape_Area)</li>
        <li><strong>Puntos con elevación:</strong> Capa vectorial con coordenadas X, Y, Z</li>
        </ul>
        
        <h4>Resultados:</h4>
        <ul>
        <li><strong>Shapefile de cuencas:</strong> Polígonos con análisis de elongación</li>
        <li><strong>Simbología automática:</strong> Colores por tipo de elongación</li>
        <li><strong>Reporte HTML:</strong> Análisis estadístico con gráficos interactivos</li>
        <li><strong>Reporte de texto:</strong> Datos tabulares detallados</li>
        </ul>
        
        <h4>Campos de salida principales:</h4>
        <ul>
        <li><strong>VALOR_ELON:</strong> Índice de elongación calculado</li>
        <li><strong>CLASIF_ELON:</strong> Clasificación morfológica (Muy alargada, Alargada, Intermedia, etc.)</li>
        <li><strong>DIST_MAX:</strong> Distancia máxima entre puntos extremos</li>
        <li><strong>MINPOINT/MAXPOINT:</strong> Coordenadas de puntos de elevación extrema</li>
        </ul>
        
        <h4>Clasificación:</h4>
        <p>El algoritmo clasifica las cuencas en 8 categorías desde "Muy alargada" (Re < 0.22) 
        hasta "Circular" (Re > 1.20) según los rangos establecidos por Schumm (1956). 
        La clasificación completa está disponible en el reporte HTML generado.</p>
        
        <h4>Archivos de salida:</h4>
        <p>Se guardan automáticamente en:<br>
        <em>Documentos/Indices_Morfologicos/Resultados_Elongacion/</em></p>
        
        <p><strong>Nota:</strong> El algoritmo identifica automáticamente los puntos de máxima y mínima 
        elevación dentro de cada cuenca para calcular la distancia máxima.</p>
        
        <p><em>Universidad Técnica Particular de Loja (UTPL)</em></p>
        ''')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return ElongacionAlgorithm()