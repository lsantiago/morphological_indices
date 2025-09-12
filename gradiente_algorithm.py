# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingException,
                       QgsProject, QgsVectorLayer)
import processing
import os
import math
import matplotlib.pyplot as plt
import tempfile

class GradienteAlgorithm(QgsProcessingAlgorithm):
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    OUTPUT = 'OUTPUT'
    GENERAR_GRAFICO = 'GENERAR_GRAFICO'
    LIMITE_Y_MIN = 'LIMITE_Y_MIN'
    LIMITE_Y_MAX = 'LIMITE_Y_MAX'
    LIMITE_SLK_MIN = 'LIMITE_SLK_MIN'
    LIMITE_SLK_MAX = 'LIMITE_SLK_MAX'
    
    def initAlgorithm(self, config=None):
        # Capa de entrada - puntos del río ordenados
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_PUNTOS,
                self.tr('Puntos del río (ordenados por elevación)'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )
        
        # Parámetro para generar gráfico
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GENERAR_GRAFICO,
                self.tr('Generar gráfico de perfil y gradiente'),
                defaultValue=True
            )
        )
        
        # Límites para el gráfico - Eje Y (elevación)
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_Y_MIN,
                self.tr('Límite inferior eje Y (elevación)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMITE_Y_MAX,
                self.tr('Límite superior eje Y (elevación)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=4000,
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
        
        # Capa de salida
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Puntos con índices de gradiente'),
                type=QgsProcessing.TypeVectorPoint,
                optional=False
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        # Obtener parámetros
        puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
        output_file = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        generar_grafico = self.parameterAsBool(parameters, self.GENERAR_GRAFICO, context)
        limite_y_min = self.parameterAsDouble(parameters, self.LIMITE_Y_MIN, context)
        limite_y_max = self.parameterAsDouble(parameters, self.LIMITE_Y_MAX, context)
        limite_slk_min = self.parameterAsDouble(parameters, self.LIMITE_SLK_MIN, context)
        limite_slk_max = self.parameterAsDouble(parameters, self.LIMITE_SLK_MAX, context)
        
        # Validar capa
        if not puntos_layer.isValid():
            raise QgsProcessingException(self.tr("Capa de puntos no válida"))
        
        feedback.pushInfo("Iniciando cálculo de gradiente...")
        feedback.pushInfo(f"Generar gráfico: {generar_grafico}")
        
        # TODO: Implementar la lógica de cálculo basada en tu código original
        # Aquí va la adaptación de CalculoGradiente.py, Graficar.py, etc.
        
        if generar_grafico:
            feedback.pushInfo("Generando gráfico de perfil y gradiente...")
            # TODO: Implementar generación de gráfico con matplotlib
        
        feedback.pushInfo("Procesamiento completado")
        
        return {self.OUTPUT: output_file}
    
    def name(self):
        return 'gradiente'
        
    def displayName(self):
        return self.tr('Calcular Gradiente')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
        
    def shortHelpString(self):
        return self.tr('Calcula el gradiente longitudinal de ríos utilizando el índice SL-K. '
                      'Genera automáticamente gráficos de perfil longitudinal y gradiente '
                      'con parámetros personalizables. Incluye análisis estadístico de '
                      'pendientes y puntos medios. Universidad Técnica Particular de Loja - UTPL')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return GradienteAlgorithm()
