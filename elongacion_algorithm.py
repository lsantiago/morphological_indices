# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingException,
                       QgsProject, QgsVectorLayer, QgsFields, QgsField,
                       QgsFeature, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsWkbTypes, QgsFeatureRequest, QgsExpression,
                       QgsGeometry, QgsPointXY, QgsSymbol, QgsRendererCategory,
                       QgsCategorizedSymbolRenderer, QgsSimpleMarkerSymbolLayer,
                       QgsLayoutManager, QgsLayout, QgsLayoutItemMap,
                       QgsLayoutItemLabel, QgsLayoutSize, QgsLayoutPoint,
                       QgsLayoutItemPicture, QgsUnitTypes, QgsProcessingContext)
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
    GENERAR_HTML = 'GENERAR_HTML'
    OUTPUT_SHAPEFILE = 'OUTPUT_SHAPEFILE'
    
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
        
        # Parámetro para generar reporte HTML
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_HTML,
                self.tr('Generar reporte HTML interactivo'),
                defaultValue=True
            )
        )
        
        # Archivo de salida shapefile
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT_SHAPEFILE,
                self.tr('Archivo shapefile de salida'),
                type=QgsProcessing.TypeVectorPolygon,
                optional=True,
                defaultValue=None
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
            generar_html = self.parameterAsBool(parameters, self.GENERAR_HTML, context)
            output_shapefile = self.parameterAsOutputLayer(parameters, self.OUTPUT_SHAPEFILE, context)
            
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
                cuencas_layer, resultados_elongacion, output_shapefile, context, feedback
            )
            
            # Calcular estadísticas
            estadisticas = self._calcular_estadisticas_elongacion(resultados_elongacion, feedback)
            
            # Generar reporte HTML si se solicita
            if generar_html:
                feedback.pushInfo("📄 Generando reporte HTML interactivo...")
                self._generar_reporte_html_elongacion(
                    resultados_elongacion, estadisticas, feedback
                )
            
            # Mostrar estadísticas en log
            self._mostrar_estadisticas_log(estadisticas, feedback)
            
            feedback.pushInfo("=" * 70)
            feedback.pushInfo("🎉 ELONGACIÓN V2.0 - PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            feedback.pushInfo(f"📊 Cuencas procesadas: {len(resultados_elongacion)}")
            feedback.pushInfo(f"📁 Archivo de salida: {output_path}")
            feedback.pushInfo("=" * 70)
            
            return {self.OUTPUT_SHAPEFILE: output_path}
            
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
    
    def _crear_capa_elongacion(self, input_layer, resultados, output_shapefile, context, feedback):
        """Crea nueva capa independiente con resultados de elongación"""
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
        
        # Determinar ubicación y formato de salida
        if output_shapefile:
            output_path = output_shapefile
            # Detectar formato por extensión
            if output_path.lower().endswith('.gpkg'):
                driver_name = "GPKG"
                feedback.pushInfo(f"📁 V2.0: Creando GeoPackage en: {output_path}")
            elif output_path.lower().endswith('.shp'):
                driver_name = "ESRI Shapefile"
                feedback.pushInfo(f"📁 V2.0: Creando Shapefile en: {output_path}")
            else:
                # Por defecto usar el formato que QGIS espera
                driver_name = "GPKG"
                if not output_path.lower().endswith('.gpkg'):
                    output_path = output_path + '.gpkg'
                feedback.pushInfo(f"📁 V2.0: Creando GeoPackage (por defecto) en: {output_path}")
        else:
            # Usar sink temporal que QGIS maneja automáticamente
            (sink, dest_id) = self.parameterAsSink(
                parameters, 
                self.OUTPUT_SHAPEFILE, 
                context, 
                fields, 
                QgsWkbTypes.Polygon, 
                input_layer.crs()
            )
            
            if sink is None:
                feedback.reportError("No se pudo crear sink temporal")
                return None
                
            feedback.pushInfo(f"📁 V2.0: Usando sink temporal de QGIS: {dest_id}")
            
            # Crear diccionario para mapear áreas a features originales
            area_to_feature = {}
            for feature in input_layer.getFeatures():
                area_val = feature[self._validar_campos_cuencas(input_layer)]
                if area_val is not None and area_val > 0:
                    area_to_feature[float(area_val)] = feature
            
            # Escribir features usando sink
            features_escritas = 0
            
            for resultado in resultados:
                try:
                    area_cuenca = resultado['area']
                    original_feature = area_to_feature.get(area_cuenca)
                    
                    if original_feature is None:
                        continue
                    
                    # Crear nueva feature
                    new_feature = QgsFeature(fields)
                    
                    # Copiar atributos originales
                    for field in input_layer.fields():
                        field_name = field.name()
                        valor_original = original_feature[field_name]
                        new_feature[field_name] = valor_original
                    
                    # Asignar valores calculados
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
                    
                    # Copiar geometría original
                    new_feature.setGeometry(original_feature.geometry())
                    
                    if sink.addFeature(new_feature):
                        features_escritas += 1
                    
                except Exception as e:
                    feedback.pushWarning(f"Error escribiendo feature: {e}")
                    continue
            
            feedback.pushInfo(f"✅ V2.0: Features escritas en sink: {features_escritas}/{len(resultados)}")
            return dest_id
        
        # Crear writer con el driver correcto (solo para rutas específicas)
        writer = QgsVectorFileWriter(
            output_path,
            "UTF-8",
            fields,
            QgsWkbTypes.Polygon,
            input_layer.crs(),
            driver_name
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
        
        # Escribir features
        features_escritas = 0
        
        for resultado in resultados:
            try:
                area_cuenca = resultado['area']
                original_feature = area_to_feature.get(area_cuenca)
                
                if original_feature is None:
                    continue
                
                # Crear nueva feature
                new_feature = QgsFeature(fields)
                
                # Copiar atributos originales
                for field in input_layer.fields():
                    field_name = field.name()
                    valor_original = original_feature[field_name]
                    new_feature[field_name] = valor_original
                
                # Asignar valores calculados
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
                
                # Copiar geometría original
                new_feature.setGeometry(original_feature.geometry())
                
                if writer.addFeature(new_feature):
                    features_escritas += 1
                
            except Exception as e:
                feedback.pushWarning(f"Error escribiendo feature: {e}")
                continue
        
        del writer
        
        feedback.pushInfo(f"✅ V2.0: Features escritas: {features_escritas}/{len(resultados)}")
        
        # Cargar al proyecto solo si es ruta específica
        layer_name = f"Elongacion_Cuencas_{datetime.now().strftime('%H%M%S')}"
        nueva_capa = QgsVectorLayer(output_path, layer_name, "ogr")
        
        if nueva_capa.isValid():
            # Aplicar simbología
            self._aplicar_simbologia_elongacion(nueva_capa, feedback)
            QgsProject.instance().addMapLayer(nueva_capa)
            feedback.pushInfo(f"✅ V2.0: Capa '{layer_name}' agregada correctamente")
        
        return output_path
    
    def _aplicar_simbologia_elongacion(self, capa, feedback):
        """Aplica simbología categorizada por clasificación de elongación"""
        try:
            # Colores por clasificación
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
            
            # Obtener valores únicos
            valores_unicos = set()
            for feature in capa.getFeatures():
                valor = feature['CLASIF_ELON']
                if valor:
                    valores_unicos.add(valor)
            
            # Crear categorías
            categorias = []
            for clasificacion in valores_unicos:
                if clasificacion in colores_clasificacion:
                    color = colores_clasificacion[clasificacion]
                    simbolo = QgsSymbol.defaultSymbol(capa.geometryType())
                    simbolo.setColor(color)
                    simbolo.setOpacity(0.7)
                    
                    categoria = QgsRendererCategory(clasificacion, simbolo, clasificacion)
                    categorias.append(categoria)
            
            if categorias:
                renderer = QgsCategorizedSymbolRenderer('CLASIF_ELON', categorias)
                capa.setRenderer(renderer)
                feedback.pushInfo("🎨 V2.0: Simbología aplicada correctamente")
            
        except Exception as e:
            feedback.pushWarning(f"Error aplicando simbología: {e}")
    
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
    
    def _generar_reporte_html_elongacion(self, resultados, estadisticas, feedback):
        """Genera reporte HTML completo en directorio temporal"""
        try:
            # Preparar datos
            tabla_cuencas = self._crear_tabla_html_cuencas(resultados)
            grafico_datos = self._preparar_datos_grafico_html(estadisticas)
            
            # Crear contenido HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reporte Elongación V2.0 - UTPL</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    * {{ box-sizing: border-box; }}
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
            
            # Guardar en directorio temporal
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = tempfile.gettempdir()
            ruta_html = os.path.join(temp_dir, f"reporte_elongacion_v2_interactivo_{timestamp}.html")
            
            with open(ruta_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Abrir en navegador
            webbrowser.open(f"file://{ruta_html}")
            feedback.pushInfo(f"📄 V2.0: Reporte HTML generado: {ruta_html}")
                
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
        """Prepara datos JavaScript para gráfico Plotly"""
        conteo = estadisticas['conteo_clasificaciones']
        porcentajes = estadisticas['porcentajes_clasificaciones']
        
        # Ordenar clasificaciones
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
        
        clasificaciones_existentes = [c for c in orden_clasificaciones if c in conteo]
        valores = [conteo[c] for c in clasificaciones_existentes]
        porcentajes_vals = [porcentajes[c] for c in clasificaciones_existentes]
        
        # Colores
        colores_profesionales = {
            "Muy alargada": "#8B0000",
            "Alargada": "#DC143C",
            "Ligeramente alargada": "#FF6347",
            "Ni alargada ni ensanchada": "#FFD700",
            "Ligeramente ensanchada": "#9ACD32",
            "Ensanchada": "#32CD32",
            "Muy ensanchada": "#1E90FF",
            "Rodeando el desagüe": "#4169E1"
        }
        
        colores = [colores_profesionales.get(c, "#808080") for c in clasificaciones_existentes]
        
        # Abreviaciones
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
            else:
                clasificaciones_abrev.append(c)
        
        script_js = f"""
        var clasificaciones_display = {clasificaciones_abrev};
        var valores = {valores};
        var porcentajes = {porcentajes_vals};
        var colores = {colores};
        
        // Gráfico de barras
        var trace_barras = {{
            x: clasificaciones_display,
            y: valores,
            type: 'bar',
            marker: {{
                color: colores,
                opacity: 0.85,
                line: {{ color: '#2F2F2F', width: 1.2 }}
            }},
            text: valores.map((v, i) => `${{v}} cuencas<br>(${{porcentajes[i].toFixed(1)}}%)`),
            textposition: 'outside',
            textfont: {{ family: 'Arial, sans-serif', size: 11, color: '#2F2F2F' }},
            name: 'Distribución Morfométrica'
        }};
        
        var layout_principal = {{
            title: {{
                text: 'Distribución Morfométrica de Cuencas Hidrográficas<br><sub>Índice de Elongación según Schumm (1956)</sub>',
                font: {{ family: 'Times New Roman, serif', size: 16, color: '#1f2937', weight: 'bold' }},
                x: 0.5, y: 0.95
            }},
            xaxis: {{
                title: {{ text: 'Clasificación Morfométrica', font: {{ family: 'Arial, sans-serif', size: 13 }} }},
                tickangle: -35,
                showgrid: false, showline: true, linecolor: '#D1D5DB'
            }},
            yaxis: {{
                title: {{ text: 'Número de Cuencas', font: {{ family: 'Arial, sans-serif', size: 13 }} }},
                showgrid: true, gridcolor: '#F3F4F6'
            }},
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            showlegend: false,
            margin: {{ l: 80, r: 40, t: 100, b: 120 }}
        }};
        
        Plotly.newPlot('grafico-barras', [trace_barras], layout_principal);
        
        // Gráfico circular
        var trace_circular = {{
            labels: clasificaciones_display,
            values: porcentajes,
            type: 'pie',
            marker: {{ colors: colores, line: {{ color: '#FFFFFF', width: 2 }} }},
            textinfo: 'label+percent',
            textposition: 'outside',
            hole: 0.3
        }};
        
        var layout_circular = {{
            title: {{ text: 'Distribución Porcentual<br><sub>Análisis Morfométrico Regional</sub>' }},
            showlegend: true,
            legend: {{ orientation: 'v', x: 1.02, y: 0.5 }},
            annotations: [{{
                text: 'Total:<br>{estadisticas.get("total_cuencas", 0)}<br>cuencas',
                showarrow: false, x: 0.5, y: 0.5
            }}]
        }};
        
        Plotly.newPlot('grafico-circular', [trace_circular], layout_circular);
        """
        
        return script_js
    
    def _generar_interpretacion_elongacion_html(self, estadisticas):
        """Genera interpretación geomorfológica automática"""
        try:
            indice_promedio = estadisticas.get('indice_promedio', 0)
            clasificacion_pred = estadisticas.get('clasificacion_predominante', '')
            porcentajes = estadisticas.get('porcentajes_clasificaciones', {})
            
            interpretacion = "<h3>Análisis Geomorfológico Automático:</h3><ul>"
            
            if indice_promedio < 0.30:
                interpretacion += "<li><strong>Cuencas Predominantemente Alargadas:</strong> El índice promedio indica que las cuencas tienden a ser alargadas, característica de sistemas fluviales con control estructural fuerte o topografía montañosa pronunciada.</li>"
            elif indice_promedio < 0.45:
                interpretacion += "<li><strong>Cuencas de Forma Intermedia:</strong> El índice promedio sugiere cuencas con formas equilibradas, típicas de terrenos con topografía moderada y desarrollo fluvial maduro.</li>"
            elif indice_promedio < 0.80:
                interpretacion += "<li><strong>Cuencas Tendiendo a Ensanchadas:</strong> El índice promedio indica cuencas con tendencia al ensanchamiento, características de terrenos con pendientes suaves y control litológico horizontal.</li>"
            else:
                interpretacion += "<li><strong>Cuencas Muy Ensanchadas:</strong> El índice promedio sugiere cuencas muy ensanchadas, típicas de zonas con topografía muy suave o control estructural particular.</li>"
            
            porcentaje_pred = porcentajes.get(clasificacion_pred, 0)
            interpretacion += f"<li><strong>Clasificación Predominante:</strong> {clasificacion_pred} ({porcentaje_pred:.1f}% de las cuencas), lo que sugiere un patrón geomorfológico dominante en la región de estudio.</li>"
            
            interpretacion += "</ul>"
            
            interpretacion += "<h3>Recomendaciones:</h3><ul>"
            interpretacion += "<li>Correlacionar los patrones de elongación con mapas geológicos para identificar controles litológicos.</li>"
            interpretacion += "<li>Analizar la relación entre elongación y características hidrográficas (orden de corrientes, densidad de drenaje).</li>"
            interpretacion += "<li>Considerar análisis complementarios de otros índices morfométricos para validación.</li>"
            interpretacion += "</ul>"
            
            return interpretacion
        except Exception:
            return "<p>No se pudo generar interpretación automática.</p>"
    
    def _mostrar_estadisticas_log(self, estadisticas, feedback):
        """Muestra estadísticas en el log"""
        if "error" in estadisticas:
            feedback.reportError("V2.0: No se pudieron calcular estadísticas válidas")
            return
        
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("📊 ESTADÍSTICAS ELONGACIÓN V2.0")
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
        feedback.pushInfo("")
        feedback.pushInfo("DISTRIBUCIÓN POR CLASIFICACIONES:")
        conteo = estadisticas['conteo_clasificaciones']
        porcentajes = estadisticas['porcentajes_clasificaciones']
        for clasif, count in conteo.items():
            porcentaje = porcentajes[clasif]
            feedback.pushInfo(f"  {clasif}: {count} ({porcentaje:.1f}%)")
        feedback.pushInfo("=" * 60)
    
    def name(self):
        return 'elongacion_v2'
        
    def displayName(self):
        return self.tr('Calcular Elongación V2.0')
        
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
        <li><strong>Shapefile de cuencas:</strong> Polígonos con análisis de elongación y simbología automática</li>
        <li><strong>Reporte HTML:</strong> Análisis estadístico interactivo con gráficos (opcional)</li>
        </ul>
        
        <h4>Campos de salida principales:</h4>
        <ul>
        <li><strong>VALOR_ELON:</strong> Índice de elongación calculado</li>
        <li><strong>CLASIF_ELON:</strong> Clasificación morfológica</li>
        <li><strong>DIST_MAX:</strong> Distancia máxima entre puntos extremos</li>
        <li><strong>MINPOINT/MAXPOINT:</strong> Coordenadas de puntos de elevación extrema</li>
        </ul>
        
        <h4>Clasificación:</h4>
        <p>El algoritmo clasifica las cuencas en 8 categorías desde "Muy alargada" (Re < 0.22) 
        hasta "Circular" (Re > 1.20) según los rangos establecidos por Schumm (1956).</p>
        
        <h4>Archivos de salida:</h4>
        <p>El shapefile se guarda en la ubicación especificada o en directorio temporal si no se especifica.<br>
        El reporte HTML siempre se genera en directorio temporal y se abre automáticamente.</p>
        
        <p><strong>Nota:</strong> El algoritmo identifica automáticamente los puntos de máxima y mínima 
        elevación dentro de cada cuenca para calcular la distancia máxima.</p>
        
        <p><em>Universidad Técnica Particular de Loja (UTPL)</em></p>
        ''')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return ElongacionAlgorithm()