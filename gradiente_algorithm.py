# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterFeatureSink,
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

class GradienteAlgorithm(QgsProcessingAlgorithm):
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    GENERAR_HTML = 'GENERAR_HTML'
    OUTPUT_SHAPEFILE = 'OUTPUT_SHAPEFILE'
    
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
        
        # Parámetro para generar reporte HTML
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_HTML,
                self.tr('Generar reporte HTML interactivo'),
                defaultValue=True
            )
        )
        
        # Usar FeatureSink para manejo nativo de capas temporales de QGIS
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_SHAPEFILE,
                self.tr('Gradiente SL-K'),
                type=QgsProcessing.TypeVectorPoint,
                createByDefault=True
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        # ===== MARCADORES DE VERSIÓN =====
        feedback.pushInfo("=" * 70)
        feedback.pushInfo("🚀 EJECUTANDO GRADIENTE V2.0 - ANÁLISIS GEOMORFOLÓGICO QGIS")
        feedback.pushInfo("=" * 70)
        
        try:
            # Obtener parámetros
            puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
            generar_html = self.parameterAsBool(parameters, self.GENERAR_HTML, context)
            
            feedback.pushInfo("✅ Parámetros obtenidos correctamente")
            
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
            feedback.pushInfo(f"Usando campos: X={campo_x}, Y={campo_y}, Z={campo_z}")
            
            # Leer y procesar los datos
            feedback.pushInfo("📊 Leyendo puntos del río...")
            puntos_data = self._leer_puntos_ordenados(puntos_layer, campo_x, campo_y, campo_z, feedback)
            
            if len(puntos_data) < 2:
                raise QgsProcessingException(self.tr("Se necesitan al menos 2 puntos para calcular el gradiente"))
            
            feedback.pushInfo(f"📐 Procesando {len(puntos_data)} puntos...")
            
            # Calcular distancias acumuladas
            distancias = self._calcular_distancias_acumuladas(puntos_data, feedback)
            
            # Calcular gradientes (SL-K)
            gradientes_slk = self._calcular_gradiente_slk(puntos_data, distancias, feedback)
            
            # Calcular estadísticas adicionales
            puntos_medios = self._calcular_puntos_medios(distancias)
            gradientes_normalizados = self._calcular_gradientes_normalizados(gradientes_slk, feedback)
            
            # Crear campos de salida - PRESERVAR campos originales + agregar nuevos
            fields = QgsFields(puntos_layer.fields())
            fields.append(QgsField("SLK", QVariant.Double, "double", 20, 8))
            fields.append(QgsField("DIST_ACUM", QVariant.Double, "double", 20, 2))
            fields.append(QgsField("P_MEDIO", QVariant.Double, "double", 20, 2))
            fields.append(QgsField("SLK_NORM", QVariant.Double, "double", 20, 8))
            fields.append(QgsField("ORDEN_RIO", QVariant.Int, "integer", 10, 0))
            fields.append(QgsField("PENDIENTE", QVariant.Double, "double", 20, 6))
            
            # Crear sink con nombre personalizado usando timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            layer_name = f"gradiente_slk_{timestamp}"
            
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.OUTPUT_SHAPEFILE, context, fields,
                QgsWkbTypes.Point, puntos_layer.crs()
            )
            
            feedback.pushInfo(f"🔧 Creando capa temporal: {layer_name}")
            
            # Escribir features al sink
            self._escribir_features_al_sink(
                sink, puntos_data, distancias, gradientes_slk, 
                puntos_medios, gradientes_normalizados, puntos_layer, fields, feedback
            )
            
            # Calcular estadísticas
            estadisticas = self._calcular_estadisticas_completas(gradientes_slk, distancias, puntos_data, feedback)
            
            # Generar reporte HTML si se solicita
            if generar_html:
                feedback.pushInfo("📄 Generando reporte HTML interactivo...")
                self._generar_reporte_html(puntos_data, distancias, gradientes_slk, estadisticas, feedback)
            
            # Mostrar estadísticas en log
            self._mostrar_estadisticas(estadisticas, feedback)
            
            feedback.pushInfo("=" * 70)
            feedback.pushInfo("🎉 GRADIENTE V2.0 - PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            feedback.pushInfo(f"📊 Puntos procesados: {len(puntos_data)}")
            feedback.pushInfo(f"📁 Capa creada: {layer_name}")
            feedback.pushInfo("=" * 70)
            
            return {self.OUTPUT_SHAPEFILE: dest_id}
            
        except Exception as e:
            feedback.reportError(f"❌ Error durante el procesamiento: {str(e)}")
            import traceback
            feedback.pushInfo(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
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
    
    def _escribir_features_al_sink(self, sink, puntos_data, distancias, gradientes_slk, 
                                   puntos_medios, gradientes_norm, input_layer, fields, feedback):
        """Escribe las features directamente al sink de QGIS"""
        
        feedback.pushInfo("✍️ V2.0: Escribiendo datos al sink temporal...")
        
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
                
                # Escribir feature al sink
                if sink.addFeature(new_feature):
                    features_exitosas += 1
                else:
                    feedback.pushWarning(f"No se pudo escribir feature {i}")
                
            except Exception as e:
                feedback.pushWarning(f"Error en feature {i}: {str(e)}")
                continue
        
        feedback.pushInfo(f"✅ V2.0: Features escritas exitosamente al sink: {features_exitosas}/{len(puntos_data)}")
        
        return features_exitosas
    
    def _generar_reporte_html(self, puntos_data, distancias, gradientes_slk, estadisticas, feedback):
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
                <title>Reporte Gradiente V2.0 - UTPL</title>
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
                        <div class="version-badge">Versión 2.0 Temporal Nativa</div>
                        <p>Universidad Técnica Particular de Loja - UTPL</p>
                        <p>Fecha de análisis: {estadisticas.get('fecha_analisis', 'N/A')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Estadísticas Generales</h2>
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
                        <h2>Análisis de Gradiente (SL-K)</h2>
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
                        <h2>Información Altimétrica</h2>
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
                        <h2>Gráfico Interactivo de Perfil Longitudinal y Gradiente</h2>
                        <div class="grafico-container">
                            <div id="grafico-gradiente" style="width:100%;height:600px;"></div>
                            <p style="text-align: center; margin-top: 15px; color: #666;">
                                <em>Gráfico interactivo: Puedes hacer zoom, desplazarte y ver valores específicos pasando el mouse sobre los puntos</em>
                            </p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Interpretación de Resultados</h2>
                        <div class="interpretation">
                            {self._generar_interpretacion_html(estadisticas)}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Reporte generado automáticamente por el Plugin de Índices Morfológicos V2.0</strong></p>
                        <p>Universidad Técnica Particular de Loja - Departamento de Ingeniería Civil</p>
                        <p>Desarrollado por: Santiago Quiñones - Docente Investigador</p>
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
                            filename: 'gradiente_perfil_v2',
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = tempfile.gettempdir()
            ruta_html = os.path.join(temp_dir, f"reporte_gradiente_v2_temporal_{timestamp}.html")
            
            with open(ruta_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Abrir reporte en navegador
            webbrowser.open(f"file://{ruta_html}")
            feedback.pushInfo(f"V2.0: Reporte HTML interactivo generado: {ruta_html}")
                
        except Exception as e:
            feedback.reportError(f"V2.0: Error generando reporte HTML: {str(e)}")
            
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
    
    def _mostrar_estadisticas(self, estadisticas, feedback):
        """Muestra estadísticas en el log de procesamiento"""
        if "error" in estadisticas:
            feedback.reportError("V2.0: No se pudieron calcular estadísticas válidas")
            return
        
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("Estadísticas del Análisis V2.0 - Sistema Temporal Nativo")
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
        return 'gradiente_v2_temporal'
        
    def displayName(self):
        return self.tr('Calcular Gradiente V2.0')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
        
    def shortHelpString(self):
        return self.tr('''
        <h3>Análisis de Gradiente Longitudinal de Ríos (SL-K)</h3>
        
        <p>Calcula el índice de gradiente longitudinal SL-K para análisis geomorfológico de perfiles fluviales. Útil para detectar anomalías tectónicas, cambios litológicos y procesos erosivos activos en cuencas hidrográficas.</p>
        
        <h4>Funcionalidades:</h4>
        <ul>
        <li><b>Cálculo automático del índice SL-K</b> a partir de puntos del perfil longitudinal</li>
        <li><b>Análisis estadístico completo</b> con gradientes normalizados y métricas de variabilidad</li>
        <li><b>Reporte HTML interactivo</b> con gráficos dinámicos del perfil y gradiente</li>
        <li><b>Interpretación geomorfológica automática</b> de los resultados obtenidos</li>
        </ul>
        
        <h4>Datos requeridos:</h4>
        <ul>
        <li><b>Capa de puntos del río:</b> Debe contener coordenadas X, Y y elevación Z</li>
        <li><b>Campos necesarios:</b> POINT_X/X, POINT_Y/Y, Z/elevation (detección automática)</li>
        </ul>
        
        <h4>Resultados generados:</h4>
        <ul>
        <li><b>SLK:</b> Valor del índice de gradiente longitudinal</li>
        <li><b>DIST_ACUM:</b> Distancia acumulada desde la cabecera</li>
        <li><b>P_MEDIO:</b> Punto medio del segmento</li>
        <li><b>SLK_NORM:</b> Gradiente normalizado respecto a la media</li>
        <li><b>ORDEN_RIO:</b> Secuencia ordenada desde cabecera a desembocadura</li>
        <li><b>PENDIENTE:</b> Pendiente del segmento expresada en porcentaje</li>
        </ul>
        
        <h4>Aplicaciones:</h4>
        <p>Análisis de actividad tectónica, estudios de incisión fluvial, caracterización 
        geomorfológica de cuencas, y evaluación de procesos erosivos en ríos.</p>
        
        <p><i>Universidad Técnica Particular de Loja - UTPL<br>
        Departamento de Ingeniería Civil</i></p>
        ''')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return GradienteAlgorithm()