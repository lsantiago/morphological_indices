# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ÍndicesMorfológicos
                                  A QGIS plugin
 Herramientas para calcular índices morfológicos de cuencas hidrográficas
                              -------------------
         begin                : 2025-06-29
         copyright            : (C) 2025 by UTPL
         email                : desarrollador@utpl.edu.ec
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# noinspection PyPep8Naming
def classFactory(iface):
    """Carga el plugin Índices Morfológicos.
    
    :param iface: Una instancia de la interfaz de QGIS.
    :type iface: QgsInterface
    """
    from .plugin import IndicesMorfologicosPlugin
    return IndicesMorfologicosPlugin(iface)
