# -*- coding: utf-8 -*-
"""
Plugin de Análisis de Gradiente Longitudinal de Ríos (SL-K) - Versión Corregida 3.0
Implementa metodología científica de Hack (1973) y estudios posteriores
Universidad Técnica Particular de Loja - UTPL

Correcciones principales:
1. Ordenamiento espacial siguiendo flujo natural del río
2. Cálculo de distancia 3D real
3. Aplicación correcta de la fórmula SL = (ΔH/ΔL) × L
4. Filtrado de valores anómalos
5. Validación de continuidad espacial
"""

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
    """
    Algoritmo corregido para cálculo del índice de gradiente longitudinal SL-K
    Basado en metodología científica de Hack (1973) y mejores prácticas actuales
    """
    
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    GENERAR_HTML = 'GENERAR_HTML'
    FILTRAR_ANOMALIAS = 'FILTRAR_ANOMALIAS'
    OUTPUT_SHAPEFILE = 'OUTPUT_SHAPEFILE'
    
    def initAlgorithm(self, config=None):
        """Inicializa los parámetros del algoritmo"""
        
        # Capa de entrada - puntos del río ordenados
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_PUNTOS,
                self.tr('Puntos del río (con campos X, Y, Z)'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )
        
        # Parámetro para filtrar anomalías
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FILTRAR_ANOMALIAS,
                self.tr('Filtrar valores anómalos (recomendado)'),
                defaultValue=True
            )
        )
        
        # Parámetro para generar reporte HTML
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_HTML,
                self.tr('Generar reporte HTML científico'),
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
        """Algoritmo principal con metodología corregida"""
        
        # ===== MARCADORES DE VERSIÓN =====
        feedback.pushInfo("=" * 80)
        feedback.pushInfo("🔬 ANÁLISIS DE GRADIENTE SL-K - METODOLOGÍA HACK (1973)")
        feedback.pushInfo("📊 Universidad Técnica Particular de Loja - UTPL")
        feedback.pushInfo("=" * 80)
        
        try:
            # Obtener parámetros
            puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
            generar_html = self.parameterAsBool(parameters, self.GENERAR_HTML, context)
            filtrar_anomalias = self.parameterAsBool(parameters, self.FILTRAR_ANOMALIAS, context)
            
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
            
            # PASO 1: Leer y ordenar puntos con metodología científica
            feedback.pushInfo("📊 Leyendo y ordenando puntos siguiendo flujo del río...")
            puntos_data = self._leer_puntos_ordenados_espacial(
                puntos_layer, campo_x, campo_y, campo_z, feedback
            )
            
            if len(puntos_data) < 3:
                raise QgsProcessingException(
                    self.tr("Se necesitan al menos 3 puntos para calcular el gradiente SL-K")
                )
            
            feedback.pushInfo(f"📐 Procesando {len(puntos_data)} puntos ordenados espacialmente...")
            
            # PASO 2: Validar continuidad espacial
            self._validar_continuidad_espacial(puntos_data, feedback)
            
            # PASO 3: Calcular distancias 3D acumuladas
            distancias = self._calcular_distancias_3d_acumuladas(puntos_data, feedback)
            
            # PASO 4: Calcular gradientes SL-K con fórmula de Hack (1973)
            gradientes_slk = self._calcular_gradiente_slk_hack(puntos_data, distancias, feedback)
            
            # PASO 5: Filtrar anomalías si se solicita
            if filtrar_anomalias:
                gradientes_slk = self._filtrar_anomalias_estadisticas(gradientes_slk, feedback)
            
            # PASO 6: Calcular métricas adicionales
            puntos_medios = self._calcular_puntos_medios(distancias)
            gradientes_normalizados = self._calcular_gradientes_normalizados(gradientes_slk, feedback)
            
            # PASO 7: Crear campos de salida preservando originales
            fields = QgsFields(puntos_layer.fields())
            fields.append(QgsField("SLK_HACK", QVariant.Double, "double", 20, 8))
            fields.append(QgsField("DIST_3D", QVariant.Double, "double", 20, 2))
            fields.append(QgsField("DIST_CABEC", QVariant.Double, "double", 20, 2))
            fields.append(QgsField("SLK_NORM", QVariant.Double, "double", 20, 8))
            fields.append(QgsField("ORDEN_RIO", QVariant.Int, "integer", 10, 0))
            fields.append(QgsField("PENDIENTE", QVariant.Double, "double", 20, 6))
            fields.append(QgsField("VALIDADO", QVariant.String, "string", 10, 0))
            
            # PASO 8: Crear sink con nombre personalizado
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            layer_name = f"gradiente_slk_{timestamp}"
            
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.OUTPUT_SHAPEFILE, context, fields,
                QgsWkbTypes.Point, puntos_layer.crs()
            )
            
            feedback.pushInfo(f"🔧 Creando capa: {layer_name}")
            
            # PASO 9: Escribir features al sink
            features_exitosas = self._escribir_features_al_sink(
                sink, puntos_data, distancias, gradientes_slk, 
                puntos_medios, gradientes_normalizados, puntos_layer, fields, feedback
            )
            
            # PASO 10: Calcular estadísticas científicas
            estadisticas = self._calcular_estadisticas_cientificas(
                gradientes_slk, distancias, puntos_data, feedback
            )
            
            # PASO 11: Generar reporte HTML científico si se solicita
            if generar_html:
                feedback.pushInfo("📄 Generando reporte científico HTML...")
                self._generar_reporte_cientifico_html(
                    puntos_data, distancias, gradientes_slk, estadisticas, feedback
                )
            
            # PASO 12: Mostrar estadísticas en log
            self._mostrar_estadisticas(estadisticas, feedback)
            
            feedback.pushInfo("=" * 80)
            feedback.pushInfo("🎉 PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            feedback.pushInfo(f"📊 Puntos procesados: {len(puntos_data)}")
            feedback.pushInfo(f"📁 Capa creada: {layer_name}")
            feedback.pushInfo("📚 Metodología: Hack (1973)")
            feedback.pushInfo("=" * 80)
            
            return {self.OUTPUT_SHAPEFILE: dest_id}
            
        except Exception as e:
            feedback.reportError(f"❌ Error durante el procesamiento: {str(e)}")
            import traceback
            feedback.pushInfo(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
            return {}
    
    def _detectar_campos_coordenadas(self, layer):
        """Detecta automáticamente los campos de coordenadas (sin cambios)"""
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
    
    def _leer_puntos_ordenados_espacial(self, layer, campo_x, campo_y, campo_z, feedback):
        """
        Lee los puntos y los ordena siguiendo el flujo natural del río
        CORREGIDO: Implementa ordenamiento espacial en lugar de por elevación
        Basado en metodología de Hack (1973)
        """
        puntos = []
        
        feedback.pushInfo("📊 Leyendo puntos con metodología espacial...")
        
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
                
                puntos.append({
                    'x': x, 
                    'y': y, 
                    'z': z, 
                    'feature': feature,
                    'id': feature.id()
                })
                
            except (ValueError, TypeError) as e:
                feedback.reportError(f"Error leyendo coordenadas en feature {feature.id()}: {e}")
                continue
        
        if len(puntos) < 3:
            raise QgsProcessingException("No se encontraron suficientes puntos válidos")
        
        feedback.pushInfo(f"📍 {len(puntos)} puntos leídos correctamente")
        
        # CORRECCIÓN PRINCIPAL: Ordenamiento espacial siguiendo flujo del río
        puntos_ordenados = self._ordenar_puntos_por_flujo_natural(puntos, feedback)
        
        # Validar rango de elevaciones
        elevaciones = [p['z'] for p in puntos_ordenados]
        feedback.pushInfo(f"📏 Rango de elevaciones: {min(elevaciones):.2f} - {max(elevaciones):.2f} m")
        
        return puntos_ordenados

    def _ordenar_puntos_por_flujo_natural(self, puntos, feedback):
        """
        Ordena los puntos siguiendo el flujo natural del río
        Implementa algoritmo de ordenamiento espacial
        """
        feedback.pushInfo("🔄 Aplicando ordenamiento espacial por flujo del río...")
        
        # Estrategia 1: Detectar si hay campo de orden
        if puntos and 'orden' in puntos[0]['feature'].fields().names():
            feedback.pushInfo("📋 Usando campo 'orden' existente")
            return sorted(puntos, key=lambda p: p['feature']['orden'])
        
        # Estrategia 2: Identificar cabecera (punto más alto)
        punto_cabecera = max(puntos, key=lambda p: p['z'])
        feedback.pushInfo(f"🏔️ Cabecera identificada en elevación {punto_cabecera['z']:.2f} m")
        
        # Estrategia 3: Algoritmo de vecino más cercano desde cabecera
        puntos_ordenados = []
        puntos_restantes = puntos.copy()
        
        # Comenzar desde la cabecera
        punto_actual = punto_cabecera
        puntos_ordenados.append(punto_actual)
        puntos_restantes.remove(punto_actual)
        
        # Ordenar por vecino más cercano siguiendo descenso topográfico
        while puntos_restantes:
            # Calcular distancias a puntos restantes
            distancias = []
            for punto in puntos_restantes:
                dist_horizontal = math.sqrt(
                    (punto['x'] - punto_actual['x'])**2 + 
                    (punto['y'] - punto_actual['y'])**2
                )
                
                # Penalizar ascensos (flujo debe descender)
                diferencia_elevacion = punto['z'] - punto_actual['z']
                if diferencia_elevacion > 0:
                    # Penalizar ascensos con factor 3
                    dist_corregida = dist_horizontal * 3.0
                else:
                    # Favorecer descensos
                    dist_corregida = dist_horizontal
                
                distancias.append((dist_corregida, punto))
            
            # Seleccionar el punto más cercano (considerando descenso)
            distancias.sort(key=lambda x: x[0])
            punto_siguiente = distancias[0][1]
            
            puntos_ordenados.append(punto_siguiente)
            puntos_restantes.remove(punto_siguiente)
            punto_actual = punto_siguiente
        
        feedback.pushInfo(f"✅ Puntos ordenados espacialmente: {len(puntos_ordenados)}")
        
        # Validar ordenamiento
        self._validar_ordenamiento_espacial(puntos_ordenados, feedback)
        
        return puntos_ordenados

    def _validar_ordenamiento_espacial(self, puntos_ordenados, feedback):
        """
        Valida que el ordenamiento espacial sea coherente
        Validación de continuidad espacial
        """
        feedback.pushInfo("🔍 Validando ordenamiento espacial...")
        
        saltos_grandes = 0
        ascensos_grandes = 0
        
        for i in range(len(puntos_ordenados) - 1):
            p1 = puntos_ordenados[i]
            p2 = puntos_ordenados[i + 1]
            
            # Calcular distancia horizontal
            dist_horizontal = math.sqrt(
                (p2['x'] - p1['x'])**2 + 
                (p2['y'] - p1['y'])**2
            )
            
            # Detectar saltos espaciales grandes (>2km)
            if dist_horizontal > 2000:
                saltos_grandes += 1
            
            # Detectar ascensos grandes (>50m)
            diferencia_elevacion = p2['z'] - p1['z']
            if diferencia_elevacion > 50:
                ascensos_grandes += 1
        
        if saltos_grandes > 0:
            feedback.pushWarning(f"⚠️ Detectados {saltos_grandes} saltos espaciales grandes")
        
        if ascensos_grandes > len(puntos_ordenados) * 0.3:
            feedback.pushWarning(f"⚠️ Detectados {ascensos_grandes} ascensos significativos")
        else:
            feedback.pushInfo(f"✅ Ordenamiento espacial validado correctamente")

    def _validar_continuidad_espacial(self, puntos_data, feedback):
        """
        Valida la continuidad espacial de los puntos del río
        NUEVA FUNCIÓN: Implementa validación de continuidad según mejores prácticas
        """
        feedback.pushInfo("🔍 V3.0: Validando continuidad espacial del perfil...")
        
        discontinuidades = []
        threshold_distancia = 1000  # metros
        
        for i in range(len(puntos_data) - 1):
            p1 = puntos_data[i]
            p2 = puntos_data[i + 1]
            
            # Calcular distancia 3D entre puntos consecutivos
            dist_3d = self._calcular_distancia_3d_entre_puntos(p1, p2)
            
            if dist_3d > threshold_distancia:
                discontinuidades.append({
                    'indice': i,
                    'distancia': dist_3d,
                    'punto1': p1['id'],
                    'punto2': p2['id']
                })
        
        if discontinuidades:
            feedback.pushWarning(f"⚠️ V3.0: Detectadas {len(discontinuidades)} discontinuidades espaciales")
            for disc in discontinuidades[:3]:  # Mostrar solo las primeras 3
                feedback.pushWarning(
                    f"   Discontinuidad: {disc['distancia']:.0f}m entre puntos {disc['punto1']}-{disc['punto2']}"
                )
        else:
            feedback.pushInfo("✅ V3.0: Continuidad espacial validada correctamente")

    def _calcular_distancia_3d_entre_puntos(self, p1, p2):
        """
        Calcula la distancia 3D real entre dos puntos
        NUEVA FUNCIÓN: Implementa cálculo de distancia 3D real
        """
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y'] 
        dz = p2['z'] - p1['z']
        
        return math.sqrt(dx**2 + dy**2 + dz**2)

    def _calcular_distancias_3d_acumuladas(self, puntos_data, feedback):
        """
        Calcula las distancias 3D acumuladas siguiendo el perfil real del río
        CORREGIDO: Implementa distancia 3D en lugar de solo horizontal
        Basado en metodología de Hack (1973)
        """
        feedback.pushInfo("📏 V3.0: Calculando distancias 3D acumuladas...")
        
        distancias = [0.0]
        distancia_total_horizontal = 0.0
        distancia_total_3d = 0.0
        
        for i in range(1, len(puntos_data)):
            p1 = puntos_data[i-1]
            p2 = puntos_data[i]
            
            # Calcular distancia 3D real
            dist_3d = self._calcular_distancia_3d_entre_puntos(p1, p2)
            
            # Calcular también distancia horizontal para comparación
            dx = p2['x'] - p1['x']
            dy = p2['y'] - p1['y']
            dist_horizontal = math.sqrt(dx**2 + dy**2)
            
            # Validar distancia mínima
            if dist_3d < 1e-6:
                feedback.pushWarning(f"⚠️ V3.0: Puntos muy cercanos entre índices {i-1} y {i}")
                dist_3d = 1e-6
            
            # Acumular distancias
            distancia_acumulada_3d = distancias[-1] + dist_3d
            distancias.append(distancia_acumulada_3d)
            
            distancia_total_horizontal += dist_horizontal
            distancia_total_3d += dist_3d
        
        # Estadísticas de distancias
        feedback.pushInfo(f"📐 V3.0: Distancia total horizontal: {distancia_total_horizontal:.2f} m")
        feedback.pushInfo(f"📐 V3.0: Distancia total 3D: {distancia_total_3d:.2f} m")
        diferencia_porcentual = ((distancia_total_3d - distancia_total_horizontal) / distancia_total_horizontal) * 100
        feedback.pushInfo(f"📊 V3.0: Diferencia 3D vs horizontal: {diferencia_porcentual:.1f}%")
        
        return distancias

    def _calcular_puntos_medios(self, distancias):
        """
        Calcula los puntos medios entre distancias consecutivas
        MANTIENE funcionalidad original validada
        """
        puntos_medios = [0.0]
        
        for i in range(1, len(distancias)):
            dist1 = distancias[i-1]
            dist2 = distancias[i]
            punto_medio = dist1 + (dist2 - dist1) / 2
            puntos_medios.append(punto_medio)
        
        return puntos_medios

    def _calcular_gradiente_slk_hack(self, puntos_data, distancias, feedback):
        """
        Calcula el gradiente SL-K usando la fórmula original de Hack (1973)
        CORREGIDO: Implementa SL = (ΔH/ΔL) × L donde L es distancia desde cabecera
        
        Fórmula de Hack (1973): SL = (pendiente del canal) × (longitud desde cabecera)
        """
        feedback.pushInfo("📐 V3.0: Calculando gradiente SL-K con fórmula de Hack (1973)...")
        
        gradientes = []
        
        for i in range(len(puntos_data) - 1):
            # Puntos consecutivos
            p1 = puntos_data[i]     # Punto aguas arriba
            p2 = puntos_data[i + 1] # Punto aguas abajo
            
            # Diferencia de elevación (ΔH)
            delta_h = p1['z'] - p2['z']  # Descenso positivo (cabecera hacia desembocadura)
            
            # Longitud del segmento (ΔL)
            delta_l = distancias[i + 1] - distancias[i]
            
            # Distancia desde cabecera hasta punto medio del segmento (L)
            L = (distancias[i] + distancias[i + 1]) / 2
            
            # Validar datos del segmento
            if abs(delta_l) < 1e-6:
                feedback.pushWarning(f"V3.0: Segmento muy corto entre puntos {i} y {i+1}")
                gradientes.append(0.0)
                continue
            
            if L < 1e-6:
                feedback.pushWarning(f"V3.0: Distancia desde cabecera muy pequeña en punto {i}")
                gradientes.append(0.0)
                continue
            
            # Aplicar fórmula de Hack (1973): SL = (ΔH/ΔL) × L
            pendiente_segmento = delta_h / delta_l
            slk_valor = pendiente_segmento * L
            
            # Validar resultado
            if not math.isfinite(slk_valor):
                feedback.pushWarning(f"V3.0: Valor SL-K inválido en segmento {i}, usando 0.0")
                slk_valor = 0.0
            
            gradientes.append(slk_valor)
        
        # Agregar valor final (mismo que penúltimo para mantener longitud)
        if gradientes:
            gradientes.append(gradientes[-1])
        else:
            gradientes.append(0.0)
        
        # Estadísticas básicas
        valores_validos = [g for g in gradientes if math.isfinite(g) and abs(g) > 1e-10]
        if valores_validos:
            feedback.pushInfo(f"📊 V3.0: SL-K calculado - Min: {min(valores_validos):.6f}, Max: {max(valores_validos):.6f}")
            feedback.pushInfo(f"📊 V3.0: Valores válidos: {len(valores_validos)}/{len(gradientes)}")
        
        return gradientes

    def _filtrar_anomalias_estadisticas(self, gradientes_slk, feedback):
        """
        Filtra anomalías estadísticas en los valores SL-K
        NUEVA FUNCIÓN: Implementa filtrado estadístico robusto
        """
        feedback.pushInfo("🔍 V3.0: Aplicando filtrado estadístico de anomalías...")
        
        # Obtener valores válidos para análisis estadístico
        valores_originales = [g for g in gradientes_slk if math.isfinite(g) and abs(g) > 1e-10]
        
        if len(valores_originales) < 5:
            feedback.pushWarning("V3.0: Insuficientes valores válidos para filtrado estadístico")
            return gradientes_slk
        
        # Calcular estadísticas robustas
        valores_np = np.array(valores_originales)
        
        # Usar percentiles para estadísticas robustas
        q25 = np.percentile(valores_np, 25)
        q75 = np.percentile(valores_np, 75)
        iqr = q75 - q25
        mediana = np.median(valores_np)
        
        # Definir límites usando método IQR (más robusto que desviación estándar)
        limite_inferior = q25 - 1.5 * iqr
        limite_superior = q75 + 1.5 * iqr
        
        # Aplicar límites más conservadores para valores extremos
        # Usar 3 * IQR para anomalías muy extremas
        limite_extremo_inf = q25 - 3.0 * iqr
        limite_extremo_sup = q75 + 3.0 * iqr
        
        feedback.pushInfo(f"📊 V3.0: Límites estadísticos - IQR: [{limite_inferior:.6f}, {limite_superior:.6f}]")
        feedback.pushInfo(f"📊 V3.0: Límites extremos - 3×IQR: [{limite_extremo_inf:.6f}, {limite_extremo_sup:.6f}]")
        
        # Filtrar gradientes
        gradientes_filtrados = []
        anomalias_detectadas = 0
        anomalias_extremas = 0
        
        for i, valor in enumerate(gradientes_slk):
            if not math.isfinite(valor) or abs(valor) <= 1e-10:
                # Mantener valores nulos/cero como están
                gradientes_filtrados.append(valor)
            elif valor < limite_extremo_inf or valor > limite_extremo_sup:
                # Anomalías extremas: reemplazar con mediana
                gradientes_filtrados.append(mediana)
                anomalias_extremas += 1
            elif valor < limite_inferior or valor > limite_superior:
                # Anomalías moderadas: suavizar hacia percentiles
                if valor < limite_inferior:
                    valor_suavizado = q25
                else:
                    valor_suavizado = q75
                gradientes_filtrados.append(valor_suavizado)
                anomalias_detectadas += 1
            else:
                # Valor dentro de rango normal
                gradientes_filtrados.append(valor)
        
        if anomalias_detectadas > 0 or anomalias_extremas > 0:
            feedback.pushInfo(f"🔧 V3.0: Anomalías corregidas - Moderadas: {anomalias_detectadas}, Extremas: {anomalias_extremas}")
        else:
            feedback.pushInfo("✅ V3.0: No se detectaron anomalías estadísticas")
        
        return gradientes_filtrados

    def _calcular_gradientes_normalizados(self, gradientes_slk, feedback):
        """
        Calcula los gradientes normalizados respecto a la mediana (más robusto que la media)
        CORREGIDO: Usa mediana en lugar de media para mayor robustez estadística
        """
        feedback.pushInfo("📊 V3.0: Calculando gradientes normalizados...")
        
        valores_validos = [g for g in gradientes_slk if math.isfinite(g) and abs(g) > 1e-10]
        
        if not valores_validos:
            feedback.pushWarning("V3.0: No hay gradientes válidos para normalizar, usando valores 0")
            return [0.0] * len(gradientes_slk)
        
        # Usar mediana en lugar de media (más robusta a outliers)
        mediana = np.median(valores_validos)
        feedback.pushInfo(f"📊 V3.0: Mediana de gradientes SL-K: {mediana:.6f}")
        
        gradientes_norm = []
        for g in gradientes_slk:
            if abs(mediana) > 1e-10 and math.isfinite(g):
                normalizado = g / mediana
                if math.isfinite(normalizado):
                    gradientes_norm.append(normalizado)
                else:
                    gradientes_norm.append(0.0)
            else:
                gradientes_norm.append(0.0)
        
        return gradientes_norm

    def _escribir_features_al_sink(self, sink, puntos_data, distancias, gradientes_slk, 
                                           puntos_medios, gradientes_norm, input_layer, fields, feedback):
        """
        Escribe las features al sink con campos validados
        """
        feedback.pushInfo("✍️ Escribiendo datos al sink...")
        
        features_exitosas = 0
        for i, punto in enumerate(puntos_data):
            try:
                new_feature = QgsFeature(fields)
                
                # Copiar TODOS los atributos originales
                for field in input_layer.fields():
                    field_name = field.name()
                    valor_original = punto['feature'][field_name]
                    new_feature[field_name] = valor_original
                
                # Calcular y validar nuevos valores con metodología Hack (1973)
                slk_val = float(gradientes_slk[i]) if i < len(gradientes_slk) and math.isfinite(gradientes_slk[i]) else 0.0
                dist_3d_val = float(distancias[i]) if i < len(distancias) and math.isfinite(distancias[i]) else 0.0
                dist_cabec_val = float(puntos_medios[i]) if i < len(puntos_medios) and math.isfinite(puntos_medios[i]) else 0.0
                slk_norm_val = float(gradientes_norm[i]) if i < len(gradientes_norm) and math.isfinite(gradientes_norm[i]) else 0.0
                
                # Calcular pendiente en porcentaje
                if i < len(puntos_data) - 1:
                    p1 = puntos_data[i]
                    p2 = puntos_data[i + 1]
                    delta_h = p1['z'] - p2['z']
                    delta_l = distancias[i + 1] - distancias[i] if i + 1 < len(distancias) else 1.0
                    pendiente_pct = abs(delta_h / delta_l) * 100 if abs(delta_l) > 1e-6 else 0.0
                else:
                    pendiente_pct = 0.0
                
                # Determinar estado de validación
                if abs(slk_val) < 1e-10:
                    estado_validacion = "NULO"
                elif abs(slk_val) > 1000:
                    estado_validacion = "ANOMALO"
                else:
                    estado_validacion = "VALIDO"
                
                orden_rio = i + 1
                
                # Asignar valores a campos
                new_feature["SLK_HACK"] = slk_val
                new_feature["DIST_3D"] = dist_3d_val
                new_feature["DIST_CABEC"] = dist_cabec_val
                new_feature["SLK_NORM"] = slk_norm_val
                new_feature["PENDIENTE"] = pendiente_pct
                new_feature["ORDEN_RIO"] = orden_rio
                new_feature["VALIDADO"] = estado_validacion
                
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
        
        feedback.pushInfo(f"✅ Features escritas exitosamente: {features_exitosas}/{len(puntos_data)}")
        
        return features_exitosas

    def _calcular_estadisticas_cientificas(self, gradientes_slk, distancias, puntos_data, feedback):
        """
        Calcula estadísticas científicas completas para el reporte
        CORREGIDO: Incluye métricas estadísticas robustas y validación científica
        """
        feedback.pushInfo("📊 V3.0: Calculando estadísticas científicas...")
        
        valores_validos = [g for g in gradientes_slk if math.isfinite(g) and abs(g) > 1e-10]
        elevaciones = [p['z'] for p in puntos_data]
        
        if not valores_validos:
            return {"error": "No hay gradientes válidos para análisis estadístico"}
        
        # Estadísticas básicas
        valores_np = np.array(valores_validos)
        
        estadisticas = {
            # Información general
            "n_puntos": len(puntos_data),
            "n_segmentos": len(puntos_data) - 1,
            "distancia_total_3d": distancias[-1] if distancias else 0,
            
            # Información altimétrica
            "elevacion_max": max(elevaciones),
            "elevacion_min": min(elevaciones),
            "desnivel_total": max(elevaciones) - min(elevaciones),
            
            # Estadísticas SL-K robustas
            "slk_mediana": float(np.median(valores_np)),
            "slk_media": float(np.mean(valores_np)),
            "slk_q25": float(np.percentile(valores_np, 25)),
            "slk_q75": float(np.percentile(valores_np, 75)),
            "slk_iqr": float(np.percentile(valores_np, 75) - np.percentile(valores_np, 25)),
            "slk_minimo": float(np.min(valores_np)),
            "slk_maximo": float(np.max(valores_np)),
            
            # Estadísticas de dispersión
            "slk_desviacion_std": float(np.std(valores_np)),
            "slk_coef_variacion": float(np.std(valores_np) / np.mean(valores_np)) if np.mean(valores_np) != 0 else 0,
            
            # Métricas de calidad
            "puntos_validos": len(valores_validos),
            "puntos_problematicos": len(gradientes_slk) - len(valores_validos),
            "porcentaje_validez": (len(valores_validos) / len(gradientes_slk)) * 100,
            
            # Información metodológica
            "metodologia": "Hack (1973) - Corregido V3.0",
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "distancia_3d": True,
            "filtrado_anomalias": True
        }
        
        # Calcular pendiente promedio
        if estadisticas["distancia_total_3d"] > 0:
            estadisticas["pendiente_promedio_pct"] = (estadisticas["desnivel_total"] / estadisticas["distancia_total_3d"]) * 100
        else:
            estadisticas["pendiente_promedio_pct"] = 0.0
        
        return estadisticas

    def _generar_reporte_cientifico_html(self, puntos_data, distancias, gradientes_slk, estadisticas, feedback):
        """
        Genera reporte HTML científico completo con metodología validada
        CORREGIDO: Incluye referencias científicas y metodología Hack (1973)
        """
        try:
            feedback.pushInfo("Generando reporte HTML con metodología científica...")
            
            # Extraer datos para gráficos científicos
            elevaciones = [p['z'] for p in puntos_data]
            
            # Convertir a listas simples para JSON
            distancias_list = [float(d) for d in distancias]
            elevaciones_list = [float(e) for e in elevaciones]
            gradientes_list = [float(g) if math.isfinite(g) else 0.0 for g in gradientes_slk]
            
            # Crear contenido HTML científico
            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Análisis Científico de Gradiente SL-K - Metodología Hack (1973)</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {{
                        font-family: 'Georgia', 'Times New Roman', serif;
                        line-height: 1.7;
                        margin: 0;
                        padding: 20px;
                        background-color: #fafafa;
                        color: #333;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #2E86AB;
                        padding-bottom: 25px;
                        margin-bottom: 40px;
                    }}
                    .header h1 {{
                        color: #2E86AB;
                        margin: 0;
                        font-size: 2.2em;
                        font-weight: 600;
                    }}
                    .methodology-badge {{
                        background: linear-gradient(135deg, #2E86AB, #A23B72);
                        color: white;
                        padding: 8px 20px;
                        border-radius: 25px;
                        font-size: 0.95em;
                        display: inline-block;
                        margin-top: 15px;
                        font-weight: 500;
                    }}
                    .section {{
                        margin: 35px 0;
                        padding: 25px;
                        background: linear-gradient(135deg, #f8f9fa, #ffffff);
                        border-radius: 10px;
                        border-left: 5px solid #2E86AB;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                    }}
                    .section h2 {{
                        color: #2E86AB;
                        margin-top: 0;
                        font-size: 1.4em;
                        font-weight: 600;
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                        gap: 20px;
                        margin: 25px 0;
                    }}
                    .stat-card {{
                        background: white;
                        padding: 20px;
                        border-radius: 10px;
                        border-left: 4px solid #A23B72;
                        box-shadow: 0 3px 12px rgba(0,0,0,0.08);
                        transition: transform 0.2s ease;
                    }}
                    .stat-card:hover {{
                        transform: translateY(-2px);
                    }}
                    .stat-value {{
                        font-size: 1.8em;
                        font-weight: bold;
                        color: #2E86AB;
                        margin: 0;
                        font-family: 'Monaco', monospace;
                    }}
                    .stat-label {{
                        color: #555;
                        margin: 8px 0 0 0;
                        font-size: 0.9em;
                        font-weight: 500;
                    }}
                    .stat-sublabel {{
                        color: #888;
                        font-size: 0.8em;
                        margin-top: 4px;
                    }}
                    .formula {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 6px;
                        font-family: 'Monaco', monospace;
                        text-align: center;
                        font-size: 1.1em;
                        margin: 15px 0;
                        border: 1px solid #dee2e6;
                    }}
                    .reference {{
                        background: #fff3cd;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #ffc107;
                        margin: 20px 0;
                        font-style: italic;
                    }}
                    .quality-indicator {{
                        display: inline-block;
                        padding: 4px 12px;
                        border-radius: 15px;
                        font-size: 0.8em;
                        font-weight: 600;
                        margin-left: 10px;
                    }}
                    .quality-excelente {{ background: #d4edda; color: #155724; }}
                    .quality-buena {{ background: #fff3cd; color: #856404; }}
                    .quality-regular {{ background: #f8d7da; color: #721c24; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Análisis Geomorfológico del Índice de Gradiente Longitudinal</h1>
                        <div class="methodology-badge">Metodología Hack (1973)</div>
                        <p style="margin-top: 15px; font-size: 1.1em;">Universidad Técnica Particular de Loja - UTPL</p>
                        <p>Fecha de análisis: {estadisticas.get('fecha_analisis', 'N/A')}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Metodología Científica Aplicada</h2>
                        <p><strong>Índice de Gradiente Longitudinal (SL)</strong> según Hack (1973): Herramienta geomorfométrica para detectar anomalías tectónicas, cambios litológicos y procesos erosivos activos en perfiles longitudinales de ríos.</p>
                        
                        <div class="formula">
                            SL = (ΔH/ΔL) × L
                        </div>
                        
                        <p><strong>Donde:</strong></p>
                        <ul>
                            <li><strong>ΔH:</strong> Diferencia de elevación entre puntos consecutivos</li>
                            <li><strong>ΔL:</strong> Distancia 3D real del segmento</li>
                            <li><strong>L:</strong> Distancia desde la cabecera hasta el punto medio del segmento</li>
                        </ul>
                        
                        <div class="reference">
                            <strong>Referencia científica:</strong> Hack, J.T. (1973). Stream-profile analysis and stream-gradient index. Journal of Research of the U.S. Geological Survey, 1(4), 421-429.
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Estadísticas del Análisis {self._obtener_indicador_calidad(estadisticas)}</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('n_puntos', 0)}</p>
                                <p class="stat-label">Puntos Analizados</p>
                                <p class="stat-sublabel">{estadisticas.get('n_segmentos', 0)} segmentos de río</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('distancia_total_3d', 0):.1f} m</p>
                                <p class="stat-label">Distancia Total 3D</p>
                                <p class="stat-sublabel">Siguiendo perfil real del cauce</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('slk_mediana', 0):.6f}</p>
                                <p class="stat-label">SL-K Mediana</p>
                                <p class="stat-sublabel">Valor central robusto</p>
                            </div>
                            <div class="stat-card">
                                <p class="stat-value">{estadisticas.get('porcentaje_validez', 0):.1f}%</p>
                                <p class="stat-label">Validez de Datos</p>
                                <p class="stat-sublabel">Control de calidad</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Gráfico Científico Interactivo</h2>
                        <div id="grafico-gradiente" style="width:100%;height:600px;"></div>
                        <p style="text-align: center; margin-top: 15px; color: #666; font-style: italic;">
                            Gráfico del perfil longitudinal y gradiente SL-K según metodología de Hack (1973)
                        </p>
                    </div>
                    
                    <div class="section">
                        <h2>Interpretación Geomorfológica</h2>
                        {self._generar_interpretacion_cientifica_html(estadisticas)}
                    </div>
                    
                    <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 2px solid #dee2e6; color: #666; font-size: 0.9em;">
                        <p><strong>Reporte Científico V3.0 - Plugin de Análisis Geomorfológico</strong></p>
                        <p>Universidad Técnica Particular de Loja - Metodología Hack (1973) Corregida</p>
                    </div>
                </div>
                
                <script>
                    // Datos del perfil longitudinal
                    var perfil = {{
                        x: {distancias_list},
                        y: {elevaciones_list},
                        name: 'Perfil Longitudinal del Río',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: {{color: '#2E86AB', width: 3}},
                        marker: {{size: 4, color: '#2E86AB'}},
                        yaxis: 'y1',
                        hovertemplate: 'Distancia: %{{x:.1f}} m<br>Elevación: %{{y:.1f}} m<extra></extra>'
                    }};
                    
                    // Datos del gradiente SL-K
                    var gradiente = {{
                        x: {distancias_list},
                        y: {gradientes_list},
                        name: 'Índice SL-K (Hack 1973)',
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: {{color: '#A23B72', width: 2}},
                        marker: {{size: 3, color: '#A23B72'}},
                        yaxis: 'y2',
                        hovertemplate: 'Distancia: %{{x:.1f}} m<br>SL-K: %{{y:.6f}}<extra></extra>'
                    }};
                    
                    var layout = {{
                        title: {{
                            text: 'Perfil Longitudinal y Gradiente SL-K (Hack 1973)<br><sub>Universidad Técnica Particular de Loja - UTPL</sub>',
                            font: {{size: 16, color: '#2E86AB'}}
                        }},
                        xaxis: {{
                            title: 'Distancia desde Cabecera (m)',
                            showgrid: true,
                            gridcolor: '#f0f0f0'
                        }},
                        yaxis: {{
                            title: 'Elevación (m)',
                            titlefont: {{color: '#2E86AB'}},
                            tickfont: {{color: '#2E86AB'}},
                            side: 'left'
                        }},
                        yaxis2: {{
                            title: 'Índice SL-K',
                            titlefont: {{color: '#A23B72'}},
                            tickfont: {{color: '#A23B72'}},
                            overlaying: 'y',
                            side: 'right'
                        }},
                        hovermode: 'x unified',
                        showlegend: true,
                        legend: {{
                            x: 0.02,
                            y: 0.98,
                            bgcolor: 'rgba(255,255,255,0.9)',
                            bordercolor: '#ccc',
                            borderwidth: 1
                        }},
                        plot_bgcolor: '#fafafa',
                        paper_bgcolor: 'white'
                    }};
                    
                    var config = {{
                        displayModeBar: true,
                        displaylogo: false,
                        toImageButtonOptions: {{
                            format: 'png',
                            filename: 'gradiente_slk_hack_1973',
                            height: 600,
                            width: 1200,
                            scale: 2
                        }}
                    }};
                    
                    Plotly.newPlot('grafico-gradiente', [perfil, gradiente], layout, config);
                </script>
            </body>
            </html>
            """
            
            # Guardar y abrir reporte
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_dir = tempfile.gettempdir()
            ruta_html = os.path.join(temp_dir, f"reporte_slk_hack_1973_v3_{timestamp}.html")
            
            with open(ruta_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            webbrowser.open(f"file://{ruta_html}")
            feedback.pushInfo(f"V3.0: Reporte científico generado: {ruta_html}")
                
        except Exception as e:
            feedback.reportError(f"V3.0: Error generando reporte: {str(e)}")

    def _obtener_indicador_calidad(self, estadisticas):
        """Determina el indicador de calidad del análisis"""
        porcentaje_validez = estadisticas.get('porcentaje_validez', 0)
        
        if porcentaje_validez >= 90:
            return '<span class="quality-indicator quality-excelente">EXCELENTE</span>'
        elif porcentaje_validez >= 75:
            return '<span class="quality-indicator quality-buena">BUENA</span>'
        else:
            return '<span class="quality-indicator quality-regular">REVISAR</span>'

    def _generar_interpretacion_cientifica_html(self, estadisticas):
        """Genera interpretación científica automática"""
        try:
            pendiente_pct = estadisticas.get('pendiente_promedio_pct', 0)
            coef_variacion = estadisticas.get('slk_coef_variacion', 0)
            
            interpretacion = "<h3>Análisis Geomorfológico:</h3>"
            
            if pendiente_pct < 2:
                interpretacion += "<p><strong>Régimen de Baja Energía:</strong> Pendiente suave, procesos de sedimentación dominantes.</p>"
            elif pendiente_pct < 8:
                interpretacion += "<p><strong>Régimen Moderado:</strong> Balance entre erosión y sedimentación.</p>"
            else:
                interpretacion += "<p><strong>Régimen de Alta Energía:</strong> Procesos erosivos intensos.</p>"
            
            if coef_variacion < 0.5:
                interpretacion += "<p><strong>Perfil Uniforme:</strong> Equilibrio geomorfológico relativo.</p>"
            else:
                interpretacion += "<p><strong>Perfil Variable:</strong> Posibles anomalías tectónicas o litológicas.</p>"
            
            return interpretacion
            
        except Exception:
            return "<p>Consulte las estadísticas para interpretación manual.</p>"

    def _mostrar_estadisticas(self, estadisticas, feedback):
        """Muestra estadísticas en el log"""
        if "error" in estadisticas:
            feedback.reportError("Error en estadísticas")
            return
        
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("ESTADÍSTICAS CIENTÍFICAS - METODOLOGÍA HACK (1973)")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"Metodología: {estadisticas['metodologia']}")
        feedback.pushInfo(f"Puntos: {estadisticas['n_puntos']}")
        feedback.pushInfo(f"Distancia 3D: {estadisticas['distancia_total_3d']:.2f} m")
        feedback.pushInfo(f"SL-K Mediana: {estadisticas['slk_mediana']:.6f}")
        feedback.pushInfo(f"Validez: {estadisticas['porcentaje_validez']:.1f}%")
        feedback.pushInfo("=" * 60)

    def name(self):
        return 'gradiente_slk_hack'
        
    def displayName(self):
        return self.tr('Calcular Gradiente SL-K (Hack 1973)')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
    
    def shortHelpString(self):
        return self.tr('''
        <h3>Análisis de Gradiente SL-K - Metodología Hack (1973)</h3>
        
        <p>Implementa la metodología científica original para el cálculo del índice de gradiente longitudinal SL-K.</p>
        
        <h4>Características:</h4>
        <ul>
        <li><b>Ordenamiento espacial:</b> Sigue flujo natural del río</li>
        <li><b>Distancia 3D real:</b> Considera topografía del perfil</li>
        <li><b>Fórmula de Hack (1973):</b> SL = (ΔH/ΔL) × L</li>
        <li><b>Filtrado estadístico:</b> Elimina anomalías robustamente</li>
        </ul>
        
        <h4>Referencia:</h4>
        <p>Hack, J.T. (1973). Stream-profile analysis and stream-gradient index.</p>
        
        <p><i>Universidad Técnica Particular de Loja - UTPL</i></p>
        ''')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return GradienteAlgorithm()