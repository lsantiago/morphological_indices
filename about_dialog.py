# -*- coding: utf-8 -*-
import os

from qgis.PyQt import QtGui, QtWidgets
from qgis.PyQt.QtCore import QCoreApplication, Qt

class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(AboutDialog, self).__init__(parent)
        # Configurar el diálogo
        self.setWindowTitle(self.tr("Acerca de Índices Morfológicos"))
        self.resize(450, 350)
        
        # Crear el layout
        layout = QtWidgets.QVBoxLayout()
        
        # Añadir título
        title_label = QtWidgets.QLabel(self.tr("Índices Morfológicos"))
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Añadir versión
        version_label = QtWidgets.QLabel(self.tr("Versión 1.0"))
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Añadir espacio
        layout.addSpacing(20)
        
        # Añadir descripción
        description = self.tr(
            "Este plugin proporciona herramientas especializadas para el cálculo "
            "de índices morfológicos en cuencas hidrográficas. Incluye algoritmos "
            "para calcular la elongación de cuencas y el gradiente longitudinal "
            "de ríos con visualización gráfica integrada."
        )
        desc_label = QtWidgets.QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Añadir características
        layout.addSpacing(15)
        features_title = QtWidgets.QLabel(self.tr("Características principales:"))
        features_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(features_title)
        
        features = self.tr(
            "• Cálculo de elongación con clasificación automática\n"
            "• Análisis de gradiente longitudinal ^(SL-K^)\n"
            "• Generación de gráficos y reportes\n"
            "• Validación automática de datos\n"
            "• Integración completa con QGIS"
        )
        features_label = QtWidgets.QLabel(features)
        layout.addWidget(features_label)
        
        # Añadir espacio
        layout.addSpacing(20)
        
        # Añadir institución
        institution_label = QtWidgets.QLabel(self.tr("Universidad Técnica Particular de Loja"))
        institution_label.setAlignment(Qt.AlignCenter)
        institution_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(institution_label)
        
        # Añadir autores
        authors_label = QtWidgets.QLabel(self.tr("Basado en el trabajo de:"))
        authors_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(authors_label)
        
        authors_names = QtWidgets.QLabel(self.tr("Ing. Santiago Quiñones, Ing. María Fernanda Guarderas, Nelson Aranda"))
        authors_names.setAlignment(Qt.AlignCenter)
        authors_names.setStyleSheet("font-size: 10px;")
        layout.addWidget(authors_names)
        
        # Añadir espacio expansible
        layout.addStretch()
        
        # Añadir botón Cerrar
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Establecer el layout
        self.setLayout(layout)
    
    def tr(self, string):
        return QCoreApplication.translate('AboutDialog', string)
