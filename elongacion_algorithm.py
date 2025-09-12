# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterNumber,
                       QgsProcessingException,
                       QgsProject, QgsVectorLayer,
                       QgsField, QgsFields,
                       QgsFeature, QgsGeometry,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem)
from qgis.PyQt.QtCore import QVariant
import processing
import os
import math
import tempfile

class ElongacionAlgorithm(QgsProcessingAlgorithm):
    INPUT_CUENCAS = 'INPUT_CUENCAS'
    INPUT_PUNTOS = 'INPUT_PUNTOS'
    OUTPUT = 'OUTPUT'
    
    def initAlgorithm(self, config=None):
        # Capa de entrada - polígonos de cuencas
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_CUENCAS,
                self.tr('Capa de cuencas (polígonos)'),
                [QgsProcessing.TypeVectorPolygon],
                defaultValue=None
            )
        )
        
        # Capa de entrada - puntos con elevación
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_PUNTOS,
                self.tr('Capa de puntos con elevación'),
                [QgsProcessing.TypeVectorPoint],
                defaultValue=None
            )
        )
        
        # Capa de salida
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Cuencas con índices de elongación'),
                type=QgsProcessing.TypeVectorPolygon,
                optional=False
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        # Obtener parámetros
        cuencas_layer = self.parameterAsVectorLayer(parameters, self.INPUT_CUENCAS, context)
        puntos_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PUNTOS, context)
        output_file = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        
        # Validar capas
        if not cuencas_layer.isValid():
            raise QgsProcessingException(self.tr("Capa de cuencas no válida"))
        
        if not puntos_layer.isValid():
            raise QgsProcessingException(self.tr("Capa de puntos no válida"))
        
        feedback.pushInfo("Iniciando cálculo de elongación...")
        
        # TODO: Implementar la lógica de cálculo basada en tu código original
        # Aquí va la adaptación de CalculoElongacion.py, LecturaElongacion.py, etc.
        
        feedback.pushInfo("Procesamiento completado")
        
        return {self.OUTPUT: output_file}
    
    def name(self):
        return 'elongacion'
        
    def displayName(self):
        return self.tr('Calcular Elongación')
        
    def group(self):
        return self.tr('Índices Morfológicos')
        
    def groupId(self):
        return 'morfologia'
        
    def shortHelpString(self):
        return self.tr('Calcula el índice de elongación de cuencas hidrográficas. '
                      'Analiza la relación entre el área de la cuenca y la distancia '
                      'máxima, clasificando automáticamente el resultado según rangos '
                      'estándar. Universidad Técnica Particular de Loja - UTPL')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return ElongacionAlgorithm()
