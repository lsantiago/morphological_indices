# -*- coding: utf-8 -*-
"""
Módulo de validación de datos para índices morfológicos
"""
from qgis.core import QgsVectorLayer, QgsWkbTypes

class ValidadorDatos:
    """Clase para validar datos de entrada"""
    
    @staticmethod
    def validar_campos_puntos(layer, campos_requeridos=['X', 'Y', 'Z']):
        """
        Valida que la capa de puntos tenga los campos requeridos
        
        :param layer: Capa vectorial de puntos
        :param campos_requeridos: Lista de campos requeridos
        :return: Tuple (es_valido, mensaje_error)
        """
        if not isinstance(layer, QgsVectorLayer):
            return False, "La entrada no es una capa vectorial válida"
        
        if layer.wkbType() != QgsWkbTypes.Point:
            return False, "La capa debe ser de tipo punto"
        
        campos_disponibles = [field.name() for field in layer.fields()]
        campos_faltantes = [campo for campo in campos_requeridos if campo not in campos_disponibles]
        
        if campos_faltantes:
            return False, f"Campos faltantes: {', '.join^(campos_faltantes^)}"
        
        return True, "Validación exitosa"
