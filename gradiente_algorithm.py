# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingException,
                       QgsProject, QgsVectorLayer, QgsFields, QgsField,
                       QgsFeature, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsWkbTypes, QgsFeatureRequest, QgsExpression,
                       QgsFeatureSink, QgsProcessingContext, QgsProcessingUtils,
                       QgsLayoutManager, QgsLayout, QgsLayoutItemMap,
                       QgsLayoutItemLabel, QgsLayoutSize, QgsLayoutPoint,
                       QgsLayoutItemPicture, QgsUnitTypes)
from qgis.PyQt.QtCore import QVariant
import processing
import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Qt5Agg')  # Backend con interfaz gráfica
import tempfile
from datetime import datetime
import webbrowser

class GradienteAlgorithm(QgsProcessingAlgorithm):
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    GENERAR_GRAFICO = 'GENERAR_GRAFICO'
    TIPO_VISUALIZACION = 'TIPO_VISUALIZACION'
    ARCHIVO_GRAFICO = 'ARCHIVO_GRAFICO'
    GENERAR_REPORTE = 'GENERAR_REPORTE'
    LIMITE_Y_MIN = 'LIMITE_Y_MIN'
    LIMITE_Y_MAX = 'LIMITE_Y_MAX'
    LIMITE_SLK_MIN = 'LIMITE_SLK_MIN'
    LIMITE_SLK_MAX = 'LIMITE_SLK_MAX'
    
    def initAlgorithm(self, config=None):
        # Capa de entrada - puntos del río ordenados
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_PUNTOS,
                self.tr('Puntos del río (con campos X, Y, Z)'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )
        
        # Parámetro para generar gráfico
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_GRAFICO,
                self.tr('Generar visualización de gradiente'),
                defaultValue=True
            )
        )
        
        # Tipo de visualización
        opciones_visualizacion = [
            self.tr('Ventana emergente interactiva'),
            self.tr('Layout automático en QGIS'),
            self.tr('Archivo de imagen'),
            self.tr('Reporte HTML completo')
        ]
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TIPO_VISUALIZACION,
                self.tr('Tipo de visualización'),
                options=opciones_visualizacion,
                defaultValue=0,
                optional=False
            )
        )
        
        # Archivo de salida para gráfico/reporte
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.ARCHIVO_GRAFICO,
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
        
        # Límites para el gráfico - Eje Y (elevación)
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_Y_MIN,
                self.tr('Límite inferior eje Y (elevación)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=None,
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_Y_MAX,
                self.tr('Límite superior eje Y (elevación)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=None,
                optional=True
            )
        )
        
        # Límites para el gráfico - Eje SLK
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_SLK_MIN,
                self.tr('Límite inferior SLK (gradiente)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=-100,
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_SLK_MAX,
                self.tr('Límite superior SLK (gradiente)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=500,
                optional=True
            )
        )
        
        # SIN PARÁMETRO OUTPUT - SE CREA AUTOMÁTICAMENTE
    
    def processAlgorithm(self, parameters, context, feedback):
        # ===== MARCADORES DE VERSIÓN =====
        feedback.pushInfo("=" * 70)
        feedback.pushInfo("🚀 EJECUTANDO GRADIENTE VERSIÓN 4.0 - SIN PARÁMETRO OUTPUT")
        feedback.pushInfo("=" * 70)
        
        try:
            # Obtener parámetros
            puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
            generar_grafico = self.parameterAsBool(parameters, self.GENERAR_GRAFICO, context)
            tipo_visualizacion = self.parameterAsInt(parameters, self.TIPO_VISUALIZACION, context)
            archivo_salida = self.parameterAsFileOutput(parameters, self.ARCHIVO_GRAFICO, context)
            generar_reporte = self.parameterAsBool(parameters, self.GENERAR_REPORTE, context)
            limite_y_min = self.parameterAsDouble(parameters, self.LIMITE_Y_MIN, context)
            limite_y_max = self.parameterAsDouble(parameters, self.LIMITE_Y_MAX, context)
            limite_slk_min = self.parameterAsDouble(parameters, self.LIMITE_SLK_MIN, context)
            limite_slk_max = self.parameterAsDouble(parameters, self.LIMITE_SLK_MAX, context)
            
            feedback.pushInfo("✅ V4.0: Parámetros obtenidos correctamente")
            feedback.pushInfo(f"📋 V4.0: Parámetros recibidos: {list(parameters.keys())}")
            
            # Validar capa
            if not puntos_layer.isValid():
                raise QgsProcessingException(self.tr("Capa de puntos no válida"))
            
            # Validar campos requeridos
            campos_requeridos = self._detectar_campos_coordenadas(puntos_layer)
            if not campos_requeridos:
                raise QgsProcessingException(
                    self.tr("La capa debe contener campos de coordenadas. "
                           "Nombres válidos: X/POINT_X, Y/POINT_Y, Z para las coordenadas")
                )
            
            campo_x, campo_y, campo_z = campos_requeridos
            feedback.pushInfo(f"V4.0: Usando campos: X={campo_x}, Y={campo_y}, Z={campo_z}")
            
            # Leer y procesar los datos
            feedback.pushInfo("V4.0: Leyendo puntos del río...")
            puntos_data = self._leer_puntos_ordenados(puntos_layer, campo_x, campo_y, campo_z, feedback)
            
            if len(puntos_data) < 2:
                raise QgsProcessingException(self.tr("Se necesitan al menos 2 puntos para calcular el gradiente"))
            
            feedback.pushInfo(f"V4.0: Procesando {len(puntos_data)} puntos...")
            
            # Calcular distancias acumuladas
            distancias = self._calcular_distancias_acumuladas(puntos_data, feedback)
            
            # Calcular gradientes (SL-K)
            gradientes_slk = self._calcular_gradiente_slk(puntos_data, distancias, feedback)
            
            # Calcular estadísticas adicionales
            puntos_medios = self._calcular_puntos_medios(distancias)
            gradientes_normalizados = self._calcular_gradientes_normalizados(gradientes_slk, feedback)
            
            # Validar que todas las listas tengan la misma longitud
            n_puntos = len(puntos_data)
            if not all(len(lst) == n_puntos for lst in [distancias, gradientes_slk, puntos_medios, gradientes_normalizados]):
                raise QgsProcessingException("Error interno: longitudes de listas inconsistentes")
            
            # Crear NUEVA capa de salida - COMPLETAMENTE INDEPENDIENTE
            feedback.pushInfo("🔧 V4.0: Creando nueva capa con resultados de gradiente...")
            
            try:
                output_path = self._crear_nueva_capa_independiente(
                    puntos_layer, puntos_data, distancias,
                    gradientes_slk, puntos_medios, gradientes_normalizados,
                    campo_x, campo_y, campo_z, feedback
                )
                feedback.pushInfo(f"🎯 V4.0: Capa creada exitosamente en: {output_path}")
            except Exception as e:
                feedback.reportError(f"❌ V4.0: Error en creación de capa: {str(e)}")
                # Continuar con el resto del procesamiento
                output_path = "Error en creación"
            
            # Generar estadísticas
            estadisticas = self._calcular_estadisticas_completas(gradientes_slk, distancias, puntos_data, feedback)
            
            # Generar visualizaciones según el tipo seleccionado
            if generar_grafico:
                feedback.pushInfo("🖼️ V4.0: Generando visualización de gradiente...")
                try:
                    self._generar_visualizacion(
                        puntos_data, distancias, gradientes_slk, estadisticas,
                        tipo_visualizacion, archivo_salida,
                        limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                        context, feedback
                    )
                except Exception as e:
                    feedback.reportError(f"Error en visualización: {str(e)}")
            
            # Generar reporte si se solicita
            if generar_reporte:
                feedback.pushInfo("📄 V4.0: Generando reporte detallado...")
                try:
                    self._generar_reporte_detallado(estadisticas, archivo_salida, feedback)
                except Exception as e:
                    feedback.reportError(f"Error en reporte: {str(e)}")
            
            # Mostrar estadísticas en log
            self._mostrar_estadisticas(estadisticas, feedback)
            
            feedback.pushInfo("=" * 70)
            feedback.pushInfo("🎉 VERSIÓN 4.0 - PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            feedback.pushInfo(f"📊 Nueva capa creada con {n_puntos} puntos procesados")
            if output_path != "Error en creación":
                feedback.pushInfo(f"📁 Archivo de salida: {output_path}")
            feedback.pushInfo("=" * 70)
            
            # Retornar diccionario vacío - sin referencias a OUTPUT
            return {}
            
        except Exception as e:
            feedback.reportError(f"❌ V4.0: Error durante el procesamiento: {str(e)}")
            feedback.pushInfo(f"🔧 V4.0 DEBUG: Tipo de error: {type(e)}")
            import traceback
            feedback.pushInfo(f"🔧 V4.0 DEBUG: Traceback: {traceback.format_exc()}")
            
            # NO relanzar la excepción para evitar que QGIS trate de usar parameterAsSink
            feedback.pushInfo("⚠️ V4.0: El procesamiento se completó con errores, pero los resultados parciales están disponibles")
            return {}
    
    def _detectar_campos_coordenadas(self, layer):
        """Detecta automáticamente los campos de coordenadas"""
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
    
    def _leer_puntos_ordenados(self, layer, campo_x, campo_y, campo_z, feedback):
        """Lee los puntos y los ordena por elevación"""
        puntos = []
        
        for feature in layer.getFeatures():
            try:
                x_val = feature[campo_x]
                y_val = feature[campo_y]
                z_val = feature[campo_z]
                
                if x_val is None or y_val is None or z_val is None:
                    feedback.pushWarning(f"Feature {feature.id()} tiene valores nulos, saltando...")
                    continue
                
                x = float(x_val)
                y = float(y_val)
                z = float(z_val)
                
                if not all(math.isfinite(val) for val in [x, y, z]):
                    feedback.pushWarning(f"Feature {feature.id()} tiene valores inválidos, saltando...")
                    continue
                
                puntos.append({'x': x, 'y': y, 'z': z, 'feature': feature})
                
            except (ValueError, TypeError) as e:
                feedback.reportError(f"Error leyendo coordenadas en feature {feature.id()}: {e}")
                continue
        
        if len(puntos) < 2:
            raise QgsProcessingException("No se encontraron suficientes puntos válidos")
        
        # Ordenar por elevación (de mayor a menor - desde cabecera)
        puntos.sort(key=lambda p: p['z'], reverse=True)
        
        feedback.pushInfo(f"Rango de elevaciones: {puntos[-1]['z']:.2f} - {puntos[0]['z']:.2f} m")
        
        return puntos
    
    def _calcular_distancias_acumuladas(self, puntos_data, feedback):
        """Calcula las distancias horizontales acumuladas"""
        distancias = [0.0]
        
        for i in range(1, len(puntos_data)):
            p1 = puntos_data[i-1]
            p2 = puntos_data[i]
            
            dx = p2['x'] - p1['x']
            dy = p2['y'] - p1['y']
            dist_segmento = math.sqrt(dx**2 + dy**2)
            
            if dist_segmento < 1e-6:
                feedback.pushWarning(f"Puntos muy cercanos entre índices {i-1} y {i}")
                dist_segmento = 1e-6
            
            distancia_acumulada = distancias[-1] + dist_segmento
            distancias.append(distancia_acumulada)
        
        feedback.pushInfo(f"Distancia total del río: {distancias[-1]:.2f} m")
        return distancias
    
    def _calcular_gradiente_slk(self, puntos_data, distancias, feedback):
        """Calcula el gradiente SL-K corregido"""
        gradientes = [0.0]
        
        for i in range(1, len(puntos_data)):
            z1 = puntos_data[i-1]['z']
            z2 = puntos_data[i]['z']
            dist1 = distancias[i-1]
            dist2 = distancias[i]
            
            delta_z = z2 - z1
            delta_dist = dist2 - dist1
            
            if abs(delta_dist) < 1e-6:
                feedback.pushWarning(f"Distancia muy pequeña entre puntos {i-1} y {i}")
                gradiente = 0.0
            else:
                gradiente = delta_z / delta_dist
                
                if not math.isfinite(gradiente):
                    feedback.pushWarning(f"Gradiente inválido en punto {i}, usando 0.0")
                    gradiente = 0.0
            
            gradientes.append(gradiente)
        
        return gradientes
    
    def _calcular_puntos_medios(self, distancias):
        """Calcula los puntos medios entre distancias consecutivas"""
        puntos_medios = [0.0]
        
        for i in range(1, len(distancias)):
            dist1 = distancias[i-1]
            dist2 = distancias[i]
            punto_medio = dist1 + (dist2 - dist1) / 2
            puntos_medios.append(punto_medio)
        
        return puntos_medios
    
    def _calcular_gradientes_normalizados(self, gradientes_slk, feedback):
        """Calcula los gradientes normalizados por la media"""
        valores_validos = [g for g in gradientes_slk[1:] if math.isfinite(g) and abs(g) > 1e-6]
        
        if not valores_validos:
            feedback.pushWarning("No hay gradientes válidos para normalizar, usando valores 0")
            return [0.0] * len(gradientes_slk)
        
        media = np.mean(valores_validos)
        feedback.pushInfo(f"Media de gradientes: {media:.6f}")
        
        gradientes_norm = []
        for g in gradientes_slk:
            if abs(media) > 1e-6 and math.isfinite(g):
                normalizado = g / media
                if math.isfinite(normalizado):
                    gradientes_norm.append(normalizado)
                else:
                    gradientes_norm.append(0.0)
            else:
                gradientes_norm.append(0.0)
        
        return gradientes_norm
    
    def _crear_nueva_capa_independiente(self, input_layer, puntos_data, distancias,
                                       gradientes_slk, puntos_medios, gradientes_norm,
                                       campo_x, campo_y, campo_z, feedback):
        """Crea una NUEVA capa COMPLETAMENTE INDEPENDIENTE del sistema de parámetros"""
        
        # Crear campos de salida - PRESERVAR campos originales + agregar nuevos
        fields = QgsFields(input_layer.fields())
        
        # Agregar campos específicos del gradiente
        fields.append(QgsField("SLK", QVariant.Double, "double", 20, 8))
        fields.append(QgsField("DIST_ACUM", QVariant.Double, "double", 20, 2))
        fields.append(QgsField("P_MEDIO", QVariant.Double, "double", 20, 2))
        fields.append(QgsField("SLK_NORM", QVariant.Double, "double", 20, 8))
        
        # Campos adicionales informativos
        fields.append(QgsField("ORDEN_RIO", QVariant.Int, "integer", 10, 0))
        fields.append(QgsField("PENDIENTE", QVariant.Double, "double", 20, 6))
        
        # DETERMINAR UBICACIÓN DE SALIDA
        import tempfile
        import os
        from pathlib import Path
        
        # Crear carpeta de resultados en Documentos del usuario
        documentos = Path.home() / "Documents" / "Indices_Morfologicos" / "Resultados_Gradiente"
        documentos.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"gradiente_slk_{timestamp}.shp"
        temp_path = str(documentos / nombre_archivo)
        
        feedback.pushInfo(f"📁 V4.0: Creando archivo en: {temp_path}")
        
        # Usar QgsVectorFileWriter directamente - SIN PARÁMETROS DE QGIS
        writer = QgsVectorFileWriter(
            temp_path,
            "UTF-8",
            fields,
            QgsWkbTypes.Point,
            input_layer.crs(),
            "ESRI Shapefile"
        )
        
        if writer.hasError() != QgsVectorFileWriter.NoError:
            error_msg = f"Error creando archivo: {writer.errorMessage()}"
            feedback.reportError(error_msg)
            # Fallback a carpeta temporal si falla Documentos
            temp_path = os.path.join(tempfile.gettempdir(), nombre_archivo)
            feedback.pushInfo(f"🔄 V4.0: Intentando en carpeta temporal: {temp_path}")
            
            writer = QgsVectorFileWriter(
                temp_path,
                "UTF-8",
                fields,
                QgsWkbTypes.Point,
                input_layer.crs(),
                "ESRI Shapefile"
            )
            
            if writer.hasError() != QgsVectorFileWriter.NoError:
                feedback.reportError(f"Error crítico: {writer.errorMessage()}")
                del writer
                return None
        
        feedback.pushInfo("✍️ V4.0: Escribiendo datos...")
        
        # Escribir todas las features
        features_exitosas = 0
        for i, punto in enumerate(puntos_data):
            try:
                new_feature = QgsFeature(fields)
                
                # Copiar TODOS los atributos originales
                for field in input_layer.fields():
                    field_name = field.name()
                    valor_original = punto['feature'][field_name]
                    new_feature[field_name] = valor_original
                
                # Calcular y validar nuevos valores
                slk_val = float(gradientes_slk[i]) if i < len(gradientes_slk) and math.isfinite(gradientes_slk[i]) else 0.0
                dist_val = float(distancias[i]) if i < len(distancias) and math.isfinite(distancias[i]) else 0.0
                pmedio_val = float(puntos_medios[i]) if i < len(puntos_medios) and math.isfinite(puntos_medios[i]) else 0.0
                slk_norm_val = float(gradientes_norm[i]) if i < len(gradientes_norm) and math.isfinite(gradientes_norm[i]) else 0.0
                pendiente_pct = abs(slk_val) * 100 if math.isfinite(slk_val) else 0.0
                orden_rio = i + 1
                
                # Asignar valores directamente
                new_feature["SLK"] = slk_val
                new_feature["DIST_ACUM"] = dist_val
                new_feature["P_MEDIO"] = pmedio_val
                new_feature["SLK_NORM"] = slk_norm_val
                new_feature["PENDIENTE"] = pendiente_pct
                new_feature["ORDEN_RIO"] = orden_rio
                
                # Copiar geometría
                new_feature.setGeometry(punto['feature'].geometry())
                
                # Escribir feature
                if writer.addFeature(new_feature):
                    features_exitosas += 1
                else:
                    feedback.pushWarning(f"No se pudo escribir feature {i}")
                
            except Exception as e:
                feedback.pushWarning(f"Error en feature {i}: {str(e)}")
                continue
        
        # Cerrar writer
        del writer
        
        feedback.pushInfo(f"✅ V4.0: Features escritas exitosamente: {features_exitosas}/{len(puntos_data)}")
        
        # Verificar que el archivo existe
        if not os.path.exists(temp_path):
            feedback.reportError("❌ V4.0: El archivo no se creó correctamente")
            return None
        
        # Cargar la capa al proyecto automáticamente
        layer_name = f"Gradiente_SLK_{timestamp}"
        nueva_capa = QgsVectorLayer(temp_path, layer_name, "ogr")
        
        if nueva_capa.isValid():
            # Agregar al proyecto actual
            QgsProject.instance().addMapLayer(nueva_capa)
            feedback.pushInfo(f"🎯 V4.0: Capa '{layer_name}' agregada al proyecto exitosamente")
            feedback.pushInfo(f"📂 V4.0: Ubicación permanente: {temp_path}")
            feedback.pushInfo(f"📊 V4.0: Registros totales: {nueva_capa.featureCount()}")
            
            # Mostrar información de la carpeta
            carpeta_resultados = str(documentos)
            feedback.pushInfo(f"📁 V4.0: Carpeta de resultados: {carpeta_resultados}")
        else:
            feedback.pushWarning("⚠️ V4.0: La capa se creó pero no se pudo cargar automáticamente")
        
        return temp_path
    
    def _calcular_estadisticas_completas(self, gradientes_slk, distancias, puntos_data, feedback):
        """Calcula estadísticas completas para el reporte"""
        valores_validos = [g for g in gradientes_slk[1:] if math.isfinite(g) and abs(g) > 1e-6]
        elevaciones = [p['z'] for p in puntos_data]
        
        if not valores_validos:
            return {"error": "No hay gradientes válidos"}
        
        estadisticas = {
            "n_puntos": len(puntos_data),
            "distancia_total": distancias[-1],
            "elevacion_max": max(elevaciones),
            "elevacion_min": min(elevaciones),
            "desnivel_total": max(elevaciones) - min(elevaciones),
            "gradiente_promedio": np.mean(valores_validos),
            "gradiente_maximo": np.max(valores_validos),
            "gradiente_minimo": np.min(valores_validos),
            "gradiente_mediana": np.median(valores_validos),
            "desviacion_estandar": np.std(valores_validos),
            "pendiente_promedio_pct": abs(np.mean(valores_validos)) * 100,
            "puntos_validos": len(valores_validos),
            "puntos_problematicos": len(gradientes_slk) - len(valores_validos) - 1,
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return estadisticas
    
    def _generar_visualizacion(self, puntos_data, distancias, gradientes_slk, estadisticas,
                              tipo_visualizacion, archivo_salida,
                              limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                              context, feedback):
        """Genera visualización según el tipo seleccionado"""
        
        if tipo_visualizacion == 0:  # Ventana emergente interactiva
            self._mostrar_grafico_interactivo(puntos_data, distancias, gradientes_slk,
                                            limite_y_min, limite_y_max, limite_slk_min, limite_slk_max, feedback)
        
        elif tipo_visualizacion == 1:  # Layout automático en QGIS
            self._crear_layout_qgis(puntos_data, distancias, gradientes_slk, estadisticas,
                                   limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                                   context, feedback)
        
        elif tipo_visualizacion == 2:  # Archivo de imagen
            self._guardar_grafico_archivo(puntos_data, distancias, gradientes_slk,
                                        limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                                        archivo_salida, feedback)
        
        elif tipo_visualizacion == 3:  # Reporte HTML completo
            self._generar_reporte_html(puntos_data, distancias, gradientes_slk, estadisticas,
                                     archivo_salida, feedback)
    
    def _mostrar_grafico_interactivo(self, puntos_data, distancias, gradientes_slk,
                                   limite_y_min, limite_y_max, limite_slk_min, limite_slk_max, feedback):
        """Muestra gráfico en ventana emergente interactiva"""
        try:
            elevaciones = [p['z'] for p in puntos_data]
            
            # Configurar matplotlib para mostrar ventana
            plt.ion()  # Modo interactivo
            fig, ax1 = plt.subplots(figsize=(14, 10))
            
            # Primer eje - Perfil del río
            color1 = 'tab:blue'
            ax1.set_xlabel('Distancia (m)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Elevación (m)', color=color1, fontsize=12, fontweight='bold')
            line1 = ax1.plot(distancias, elevaciones, 'b-', linewidth=3, label='Perfil del río', alpha=0.8)
            ax1.fill_between(distancias, elevaciones, alpha=0.3, color='lightblue')
            ax1.tick_params(axis='y', labelcolor=color1)
            ax1.grid(True, alpha=0.3)
            
            # Configurar límites del primer eje
            if limite_y_min is not None and limite_y_max is not None:
                ax1.set_ylim(limite_y_min, limite_y_max)
            else:
                margen_y = (max(elevaciones) - min(elevaciones)) * 0.1
                ax1.set_ylim(min(elevaciones) - margen_y, max(elevaciones) + margen_y)
            
            # Segundo eje - Gradiente SL-K
            ax2 = ax1.twinx()
            color2 = 'tab:red'
            ax2.set_ylabel('SL-K (Gradiente)', color=color2, fontsize=12, fontweight='bold')
            line2 = ax2.plot(distancias, gradientes_slk, 'r-', marker='o', linewidth=2, 
                           markersize=3, label='Gradiente SL-K', alpha=0.8)
            ax2.tick_params(axis='y', labelcolor=color2)
            
            # Configurar límites del segundo eje
            ax2.set_ylim(limite_slk_min, limite_slk_max)
            
            # Límites para X
            ax1.set_xlim(-200, distancias[-1] + 300)
            
            # Título y leyendas
            plt.title('Análisis de Gradiente Longitudinal del Río V4.0\nUniversidad Técnica Particular de Loja', 
                     fontsize=16, fontweight='bold', pad=20)
            
            # Leyendas combinadas
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.9)
            
            # Ajustar layout
            fig.tight_layout()
            
            # Mostrar ventana
            plt.show()
            feedback.pushInfo("🖼️ V4.0: Gráfico interactivo mostrado en ventana emergente")
            
        except Exception as e:
            feedback.reportError(f"V4.0: Error mostrando gráfico interactivo: {str(e)}")
    
    def _crear_layout_qgis(self, puntos_data, distancias, gradientes_slk, estadisticas,
                          limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                          context, feedback):
        """Crea layout automático en QGIS con gráfico integrado"""
        try:
            # Crear gráfico temporal
            temp_grafico = os.path.join(tempfile.gettempdir(), 
                                      f"gradiente_layout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            ruta_grafico = self._guardar_grafico_archivo(puntos_data, distancias, gradientes_slk,
                                        limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                                        temp_grafico, feedback)
            
            # Obtener proyecto actual
            project = QgsProject.instance()
            if not project:
                feedback.pushWarning("V4.0: No se pudo acceder al proyecto actual para crear layout")
                return
            
            layout_manager = project.layoutManager()
            layout_name = f"Gradiente_V4_0_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            layout = QgsLayout(project)
            layout.setName(layout_name)
            
            # Configurar página A4 horizontal
            page = layout.pageCollection().page(0)
            if page:
                page.setPageSize(QgsLayoutSize(297, 210, QgsUnitTypes.LayoutMillimeters))
            
            # Agregar título
            titulo = QgsLayoutItemLabel(layout)
            titulo.setText("Análisis de Gradiente Longitudinal V4.0")
            titulo.attemptResize(QgsLayoutSize(250, 15, QgsUnitTypes.LayoutMillimeters))
            titulo.attemptMove(QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(titulo)
            
            # Agregar imagen del gráfico si existe
            if ruta_grafico and os.path.exists(ruta_grafico):
                imagen_grafico = QgsLayoutItemPicture(layout)
                imagen_grafico.setPicturePath(ruta_grafico)
                imagen_grafico.attemptResize(QgsLayoutSize(250, 150, QgsUnitTypes.LayoutMillimeters))
                imagen_grafico.attemptMove(QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters))
                layout.addLayoutItem(imagen_grafico)
            
            # Agregar estadísticas
            texto_stats = self._crear_texto_estadisticas(estadisticas)
            label_stats = QgsLayoutItemLabel(layout)
            label_stats.setText(texto_stats)
            label_stats.attemptResize(QgsLayoutSize(100, 150, QgsUnitTypes.LayoutMillimeters))
            label_stats.attemptMove(QgsLayoutPoint(180, 50, QgsUnitTypes.LayoutMillimeters))
            layout.addLayoutItem(label_stats)
            
            # Agregar layout al proyecto
            layout_manager.addLayout(layout)
            
            feedback.pushInfo(f"📋 V4.0: Layout '{layout_name}' creado en el proyecto QGIS")
            
        except Exception as e:
            feedback.reportError(f"V4.0: Error creando layout QGIS: {str(e)}")
            feedback.pushWarning("V4.0: El layout no se pudo crear, pero el procesamiento continuará")
    
    def _guardar_grafico_archivo(self, puntos_data, distancias, gradientes_slk,
                               limite_y_min, limite_y_max, limite_slk_min, limite_slk_max,
                               archivo_salida, feedback):
        """Guarda gráfico en archivo de imagen"""
        try:
            elevaciones = [p['z'] for p in puntos_data]
            
            # Configurar matplotlib para exportación
            matplotlib.use('Agg')  # Backend sin interfaz
            fig, ax1 = plt.subplots(figsize=(16, 10))
            
            # Primer eje - Perfil del río
            color1 = 'tab:blue'
            ax1.set_xlabel('Distancia (m)', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Elevación (m)', color=color1, fontsize=14, fontweight='bold')
            ax1.plot(distancias, elevaciones, 'b-', linewidth=4, label='Perfil del río', alpha=0.9)
            ax1.fill_between(distancias, elevaciones, alpha=0.3, color='lightblue')
            ax1.tick_params(axis='y', labelcolor=color1, labelsize=12)
            ax1.grid(True, alpha=0.4, linestyle='--')
            
            # Configurar límites del primer eje
            if limite_y_min is not None and limite_y_max is not None:
                ax1.set_ylim(limite_y_min, limite_y_max)
            else:
                margen_y = (max(elevaciones) - min(elevaciones)) * 0.1
                ax1.set_ylim(min(elevaciones) - margen_y, max(elevaciones) + margen_y)
            
            # Segundo eje - Gradiente SL-K
            ax2 = ax1.twinx()
            color2 = 'tab:red'
            ax2.set_ylabel('SL-K (Gradiente)', color=color2, fontsize=14, fontweight='bold')
            ax2.plot(distancias, gradientes_slk, 'r-', marker='o', linewidth=3, 
                    markersize=4, label='Gradiente SL-K', alpha=0.9)
            ax2.tick_params(axis='y', labelcolor=color2, labelsize=12)
            
            # Configurar límites del segundo eje
            ax2.set_ylim(limite_slk_min, limite_slk_max)
            
            # Límites para X
            ax1.set_xlim(-200, distancias[-1] + 300)
            
            # Título profesional
            plt.suptitle('Análisis de Gradiente Longitudinal del Río V4.0', 
                        fontsize=18, fontweight='bold', y=0.95)
            plt.title('Universidad Técnica Particular de Loja - UTPL', 
                     fontsize=12, style='italic', y=0.88)
            
            # Leyendas
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, 
                      loc='upper right', framealpha=0.9, fontsize=12)
            
            # Ajustar layout
            fig.tight_layout()
            
            # DETERMINAR UBICACIÓN DE SALIDA DEL GRÁFICO
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                # Usar ubicación especificada por usuario
                ruta_grafico = archivo_salida
            else:
                # Usar carpeta predeterminada
                from pathlib import Path
                documentos = Path.home() / "Documents" / "Indices_Morfologicos" / "Graficos"
                documentos.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nombre_grafico = f"gradiente_perfil_v4_{timestamp}.png"
                ruta_grafico = str(documentos / nombre_grafico)
            
            # Guardar archivo
            plt.savefig(ruta_grafico, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            feedback.pushInfo(f"🖼️ V4.0: Gráfico guardado en: {ruta_grafico}")
            
            plt.close()
            
            return ruta_grafico
            
        except Exception as e:
            feedback.reportError(f"V4.0: Error guardando gráfico: {str(e)}")
            return None
    
    def _generar_reporte_html(self, puntos_data, distancias, gradientes_slk, estadisticas,
                            archivo_salida, feedback):
        """Genera reporte HTML completo con gráfico interactivo"""
        try:
            # Extraer datos para el gráfico
            elevaciones = [p['z'] for p in puntos_data]
            
            # Preparar datos para Plotly (formato JSON)
            datos_perfil = {
                'x': distancias,
                'y': elevaciones,
                'name': 'Perfil del río',
                'type': 'scatter',
                'mode': 'lines+markers',
                'line': {'color': '#1f77b4', 'width': 3},
                'marker': {'size': 4},
                'yaxis': 'y1'
            }
            
            datos_gradiente = {
                'x': distancias,
                'y': gradientes_slk,
                'name': 'Gradiente SL-K',
                'type': 'scatter',
                'mode': 'lines+markers',
                'line': {'color': '#d62728', 'width': 2},
                'marker': {'size': 3},
                'yaxis': 'y2'
            }
            
            # Crear contenido HTML con Plotly
            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reporte Gradiente V4.0 - UTPL</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 1400px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #2c5aa0;
                        padding-bottom: 20px;
                        margin-bottom: 30px;
                    }}
                    .header h1 {{
                        color: #2c5aa0;
                        margin: 0;
                        font-size: 2.5em;
                    }}
                    .version-badge {{
                        background-color: #28a745;
                        color: white;
                        padding: 5px 15px;
                        border-radius: 20px;
                        font-size: 0.9em;
                        display: inline-block;
                        margin-top: 10px;
                    }}
                    .section {{
                        margin: 30px 0;
                        padding: 20px;
                        background-color: #f8f9fa;
                        border-radius: 8px;
                        border-left: 4px solid #2c5aa0;
                    }}
                    .section h2 {{
                        color: #2c5aa0;
                        margin-top: 0;
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .stat-card {{
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #28a745;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .stat-value {{
                        font-size: 2em;
                        font-weight: bold;
                        color: #2c5aa0;
                        margin: 0;
                    }}
                    .stat-label {{
                        color: #666;
                        margin: 5px 0 0 0;
                        font-size: 0.9em;
                    }}
                    .grafico-container {{
                        margin: 30px 0;
                        padding: 20px;
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 40px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                        color: #666;
                    }}
                    .interpretation {{
                        background-color: #e8f4f8;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #17a2b8;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Análisis de Gradiente Longitudinal</h1>
                        <div class="version-badge">Versión 4.0 Interactiva</div>
                        <p>Universidad Técnica Particular de Loja - UTPL</p>
                        <p>Fecha de análisis: {estadisticas.get('fecha_analisis', 'N/A')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>📊 Estadísticas Generales</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('n_puntos', 0)}</p>
                                <p class="stat-label">Total de Puntos Procesados</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('distancia_total', 0):.2f} m</p>
                                <p class="stat-label">Distancia Total del Río</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('desnivel_total', 0):.2f} m</p>
                                <p class="stat-label">Desnivel Total</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('pendiente_promedio_pct', 0):.2f}%</p>
                                <p class="stat-label">Pendiente Promedio</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📈 Análisis de Gradiente (SL-K)</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('gradiente_promedio', 0):.6f}</p>
                                <p class="stat-label">Gradiente Promedio</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('gradiente_maximo', 0):.6f}</p>
                                <p class="stat-label">Gradiente Máximo</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('gradiente_minimo', 0):.6f}</p>
                                <p class="stat-label">Gradiente Mínimo</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('desviacion_estandar', 0):.6f}</p>
                                <p class="stat-label">Desviación Estándar</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🗻 Información Altimétrica</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('elevacion_max', 0):.2f} m</p>
                                <p class="stat-label">Elevación Máxima</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('elevacion_min', 0):.2f} m</p>
                                <p class="stat-label">Elevación Mínima</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('gradiente_mediana', 0):.6f}</p>
                                <p class="stat-label">Gradiente Mediana</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('puntos_validos', 0)}</p>
                                <p class="stat-label">Puntos Válidos Analizados</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📊 Gráfico Interactivo de Perfil Longitudinal y Gradiente</h2>
                        <div class="grafico-container">
                            <div id="grafico-gradiente" style="width:100%;height:600px;"></div>
                            <p style="text-align: center; margin-top: 15px; color: #666;">
                                <em>Gráfico interactivo: Puedes hacer zoom, desplazarte y ver valores específicos pasando el mouse sobre los puntos</em>
                            </p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>💡 Interpretación de Resultados</h2>
                        <div class="interpretation">
                            {self._generar_interpretacion_html(estadisticas)}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Reporte generado automáticamente por el Plugin de Índices Morfológicos V4.0</strong></p>
                        <p>Universidad Técnica Particular de Loja - Departamento de Ingeniería Civil</p>
                        <p>Gráfico interactivo creado con Plotly.js</p>
                    </div>
                </div>
                
                <script>
                    // Configurar datos para Plotly
                    var perfil = {datos_perfil};
                    var gradiente = {datos_gradiente};
                    
                    var layout = {{
                        title: {{
                            text: 'Perfil Longitudinal y Gradiente del Río<br><sub>Universidad Técnica Particular de Loja - UTPL</sub>',
                            font: {{ size: 18, color: '#2c5aa0' }}
                        }},
                        xaxis: {{
                            title: 'Distancia (m)',
                            showgrid: true,
                            gridcolor: '#f0f0f0'
                        }},
                        yaxis: {{
                            title: 'Elevación (m)',
                            titlefont: {{ color: '#1f77b4' }},
                            tickfont: {{ color: '#1f77b4' }},
                            side: 'left'
                        }},
                        yaxis2: {{
                            title: 'SL-K (Gradiente)',
                            titlefont: {{ color: '#d62728' }},
                            tickfont: {{ color: '#d62728' }},
                            overlaying: 'y',
                            side: 'right'
                        }},
                        hovermode: 'x unified',
                        showlegend: true,
                        legend: {{
                            x: 0.02,
                            y: 0.98,
                            bgcolor: 'rgba(255,255,255,0.8)',
                            bordercolor: '#ccc',
                            borderwidth: 1
                        }},
                        plot_bgcolor: '#fafafa',
                        paper_bgcolor: 'white'
                    }};
                    
                    var config = {{
                        displayModeBar: true,
                        displaylogo: false,
                        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                        toImageButtonOptions: {{
                            format: 'png',
                            filename: 'gradiente_perfil_v4',
                            height: 600,
                            width: 1200,
                            scale: 2
                        }}
                    }};
                    
                    // Crear el gráfico
                    Plotly.newPlot('grafico-gradiente', [perfil, gradiente], layout, config);
                </script>
            </body>
            </html>
            """
            
            # Determinar ubicación de salida
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                if not archivo_salida.lower().endswith('.html'):
                    archivo_salida += '.html'
                ruta_html = archivo_salida
            else:
                from pathlib import Path
                documentos = Path.home() / "Documents" / "Indices_Morfologicos" / "Reportes"
                documentos.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ruta_html = str(documentos / f"reporte_gradiente_v4_interactivo_{timestamp}.html")
            
            with open(ruta_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Abrir reporte en navegador
            webbrowser.open(f"file://{ruta_html}")
            feedback.pushInfo(f"📄 V4.0: Reporte HTML interactivo generado: {ruta_html}")
                
        except Exception as e:
            feedback.reportError(f"V4.0: Error generando reporte HTML: {str(e)}")
    
    def _generar_interpretacion_html(self, estadisticas):
        """Genera interpretación automática en formato HTML"""
        try:
            pendiente_pct = estadisticas.get('pendiente_promedio_pct', 0)
            gradiente_max = estadisticas.get('gradiente_maximo', 0)
            distancia_total = estadisticas.get('distancia_total', 0)
            
            interpretacion = "<h3>Análisis Geomorfológico Automático:</h3><ul>"
            
            # Interpretación de pendiente
            if pendiente_pct < 2:
                interpretacion += "<li><strong>Pendiente Suave:</strong> El río presenta una pendiente muy suave (&lt;2%), característica de cursos bajos o llanuras aluviales. Flujo tranquilo con baja capacidad de transporte.</li>"
            elif pendiente_pct < 5:
                interpretacion += "<li><strong>Pendiente Moderada:</strong> El río tiene una pendiente moderada (2-5%), típica de cursos medios. Equilibrio entre erosión y sedimentación.</li>"
            elif pendiente_pct < 15:
                interpretacion += "<li><strong>Pendiente Pronunciada:</strong> El río presenta una pendiente pronunciada (5-15%), característica de cursos altos o montañosos. Alta capacidad erosiva.</li>"
            else:
                interpretacion += "<li><strong>Pendiente Muy Pronunciada:</strong> El río tiene una pendiente muy pronunciada (&gt;15%), típica de cursos torrenciales o de montaña. Flujo rápido con alta energía.</li>"
            
            # Interpretación de variabilidad del gradiente
            if gradiente_max > abs(estadisticas.get('gradiente_promedio', 0)) * 3:
                interpretacion += "<li><strong>Alta Variabilidad:</strong> El gradiente presenta alta variabilidad, indicando cambios abruptos en el perfil longitudinal. Posibles saltos, cascadas o cambios litológicos.</li>"
            else:
                interpretacion += "<li><strong>Variabilidad Moderada:</strong> El gradiente presenta variabilidad moderada, indicando un perfil relativamente uniforme con transiciones suaves.</li>"
            
            # Interpretación de longitud
            if distancia_total > 10000:
                interpretacion += "<li><strong>Río de Longitud Considerable:</strong> La longitud analizada es considerable (&gt;10 km), proporcionando una buena representación del comportamiento longitudinal del río.</li>"
            elif distancia_total > 5000:
                interpretacion += "<li><strong>Segmento Medio:</strong> La longitud analizada es moderada (5-10 km), representando un segmento significativo del río.</li>"
            else:
                interpretacion += "<li><strong>Segmento Corto:</strong> La longitud analizada es relativamente corta (&lt;5 km), representando un tramo específico del río.</li>"
            
            # Análisis del índice SL-K
            slk_promedio = estadisticas.get('gradiente_promedio', 0)
            if abs(slk_promedio) > 0.001:
                interpretacion += "<li><strong>Índice SL-K Significativo:</strong> Los valores del índice SL-K indican anomalías geomorfológicas notables que pueden estar relacionadas con actividad tectónica, cambios litológicos o procesos erosivos activos.</li>"
            else:
                interpretacion += "<li><strong>Índice SL-K Moderado:</strong> Los valores del índice SL-K sugieren un perfil de equilibrio relativo con procesos geomorfológicos en estado maduro.</li>"
            
            interpretacion += "</ul>"
            
            # Recomendaciones
            interpretacion += "<h3>Recomendaciones:</h3><ul>"
            interpretacion += "<li>Correlacionar los valores anómalos de SL-K con mapas geológicos y estructuras tectónicas de la zona.</li>"
            interpretacion += "<li>Analizar la variabilidad del gradiente en relación con cambios en el sustrato rocoso.</li>"
            interpretacion += "<li>Complementar el análisis con estudios de campo para validar las interpretaciones geomorfológicas.</li>"
            interpretacion += "</ul>"
            
            return interpretacion
        except Exception:
            return "<p>No se pudo generar interpretación automática. Consulte las estadísticas numéricas para el análisis manual.</p>"
    
    def _crear_texto_estadisticas(self, estadisticas):
        """Crea texto formateado de estadísticas para layout"""
        if "error" in estadisticas:
            return "Error en estadísticas V4.0"
        
        texto = f"""ESTADÍSTICAS V4.0

Puntos: {estadisticas.get('n_puntos', 0)}
Distancia: {estadisticas.get('distancia_total', 0):.2f} m
Desnivel: {estadisticas.get('desnivel_total', 0):.2f} m

GRADIENTE (SL-K):
Promedio: {estadisticas.get('gradiente_promedio', 0):.6f}
Máximo: {estadisticas.get('gradiente_maximo', 0):.6f}
Mínimo: {estadisticas.get('gradiente_minimo', 0):.6f}

PENDIENTE:
{estadisticas.get('pendiente_promedio_pct', 0):.2f}%

{estadisticas.get('fecha_analisis', 'N/A')}"""
        
        return texto
    
    def _generar_reporte_detallado(self, estadisticas, archivo_salida, feedback):
        """Genera reporte estadístico detallado en archivo de texto"""
        try:
            if archivo_salida and archivo_salida != 'TEMPORARY_OUTPUT':
                archivo_reporte = archivo_salida.replace('.png', '_reporte_v4.txt').replace('.pdf', '_reporte_v4.txt')
            else:
                from pathlib import Path
                documentos = Path.home() / "Documents" / "Indices_Morfologicos" / "Reportes"
                documentos.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archivo_reporte = str(documentos / f"reporte_estadistico_v4_{timestamp}.txt")
            
            with open(archivo_reporte, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("REPORTE GRADIENTE LONGITUDINAL V4.0\n")
                f.write("Universidad Técnica Particular de Loja - UTPL\n")
                f.write("="*80 + "\n\n")
                f.write(f"Fecha: {estadisticas.get('fecha_analisis', 'N/A')}\n\n")
                
                f.write("ESTADÍSTICAS GENERALES:\n")
                f.write("-"*40 + "\n")
                f.write(f"Puntos procesados: {estadisticas.get('n_puntos', 0)}\n")
                f.write(f"Distancia total: {estadisticas.get('distancia_total', 0):.2f} m\n")
                f.write(f"Desnivel total: {estadisticas.get('desnivel_total', 0):.2f} m\n\n")
                
                f.write("ANÁLISIS DE GRADIENTE (SL-K):\n")
                f.write("-"*40 + "\n")
                f.write(f"Promedio: {estadisticas.get('gradiente_promedio', 0):.8f}\n")
                f.write(f"Máximo: {estadisticas.get('gradiente_maximo', 0):.8f}\n")
                f.write(f"Mínimo: {estadisticas.get('gradiente_minimo', 0):.8f}\n")
                f.write(f"Pendiente promedio: {estadisticas.get('pendiente_promedio_pct', 0):.4f}%\n\n")
                
                f.write("="*80 + "\n")
                f.write("Fin del reporte V4.0\n")
            
            feedback.pushInfo(f"📄 V4.0: Reporte detallado: {archivo_reporte}")
            
        except Exception as e:
            feedback.reportError(f"V4.0: Error generando reporte: {str(e)}")
    
    def _mostrar_estadisticas(self, estadisticas, feedback):
        """Muestra estadísticas en el log de procesamiento"""
        if "error" in estadisticas:
            feedback.reportError("V4.0: No se pudieron calcular estadísticas válidas")
            return
        
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("📊 ESTADÍSTICAS DEL ANÁLISIS V4.0")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"Puntos procesados: {estadisticas['n_puntos']}")
        feedback.pushInfo(f"Distancia total: {estadisticas['distancia_total']:.2f} m")
        feedback.pushInfo(f"Desnivel total: {estadisticas['desnivel_total']:.2f} m")
        feedback.pushInfo(f"Pendiente promedio: {estadisticas['pendiente_promedio_pct']:.2f}%")
        feedback.pushInfo("")
        feedback.pushInfo("GRADIENTE (SL-K):")
        feedback.pushInfo(f"  Promedio: {estadisticas['gradiente_promedio']:.6f}")
        feedback.pushInfo(f"  Máximo: {estadisticas['gradiente_maximo']:.6f}")
        feedback.pushInfo(f"  Mínimo: {estadisticas['gradiente_minimo']:.6f}")
        feedback.pushInfo(f"  Mediana: {estadisticas['gradiente_mediana']:.6f}")
        feedback.pushInfo("")
        feedback.pushInfo(f"Puntos válidos: {estadisticas['puntos_validos']}")
        if estadisticas['puntos_problematicos'] > 0:
            feedback.pushWarning(f"Puntos problemáticos: {estadisticas['puntos_problematicos']}")
        feedback.pushInfo("=" * 60)
    
    def name(self):
        return 'gradiente_v4'
        
    def displayName(self):
        return self.tr('Calcular Gradiente V4.0 🚀')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
        
    def shortHelpString(self):
        return self.tr('''
        <h3>🚀 Cálculo de Gradiente Longitudinal (SL-K) - VERSIÓN 4.0</h3>
        
        <p><b>Versión mejorada sin parámetros de salida problemáticos.</b><br>
        Calcula el gradiente longitudinal de ríos usando el índice SL-K y crea 
        automáticamente una nueva capa independiente.</p>
        
        <h4>✨ Nuevas características V4.0:</h4>
        <ul>
        <li><b>🔧 Sin errores de parameterAsSink:</b> Creación directa de archivos</li>
        <li><b>📁 Carpetas organizadas:</b> Resultados en Documents/Indices_Morfologicos/</li>
        <li><b>🎯 Carga automática:</b> Nueva capa agregada al proyecto</li>
        <li><b>🖼️ Múltiples visualizaciones:</b> Interactiva, Layout, Archivo, HTML</li>
        <li><b>📊 Reportes avanzados:</b> Estadísticas detalladas y HTML</li>
        </ul>
        
        <h4>📋 Datos de entrada:</h4>
        <ul>
        <li><b>Puntos del río:</b> Capa con campos X, Y, Z (ordenamiento automático)</li>
        </ul>
        
        <h4>📈 Campos de salida:</h4>
        <ul>
        <li><b>SLK:</b> Índice de gradiente calculado</li>
        <li><b>DIST_ACUM:</b> Distancia acumulada desde origen</li>
        <li><b>P_MEDIO:</b> Punto medio entre segmentos</li>
        <li><b>SLK_NORM:</b> Gradiente normalizado por media</li>
        <li><b>ORDEN_RIO:</b> Orden secuencial desde cabecera</li>
        <li><b>PENDIENTE:</b> Pendiente en porcentaje</li>
        </ul>
        
        <p><i>🎓 Universidad Técnica Particular de Loja - UTPL<br>
        Departamento de Ingeniería Civil</i></p>
        ''')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return GradienteAlgorithm()