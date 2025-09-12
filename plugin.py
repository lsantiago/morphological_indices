# -*- coding: utf-8 -*-
import os.path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsApplication
import processing

from .elongacion_algorithm import ElongacionAlgorithm
from .gradiente_algorithm import GradienteAlgorithm
from .about_dialog import AboutDialog

# Algoritmos globales
ELONGACION_ALGORITHM = ElongacionAlgorithm()
GRADIENTE_ALGORITHM = GradienteAlgorithm()

class IndicesMorfologicosPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'IndicesMorfologicos_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = 'Índices Morfológicos'

    def initGui(self):
        # Icono principal
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        
        # Acción para calcular elongación
        self.action_elongacion = QAction(QIcon(icon_path), 'Calcular Elongación', self.iface.mainWindow())
        self.action_elongacion.triggered.connect(self.run_elongacion)
        self.iface.addPluginToMenu(self.menu, self.action_elongacion)
        self.actions.append(self.action_elongacion)
        
        # Acción para calcular gradiente
        self.action_gradiente = QAction(QIcon(icon_path), 'Calcular Gradiente', self.iface.mainWindow())
        self.action_gradiente.triggered.connect(self.run_gradiente)
        self.iface.addPluginToMenu(self.menu, self.action_gradiente)
        self.actions.append(self.action_gradiente)
        
        # Acción para mostrar información "Acerca de"
        self.action_about = QAction(QIcon(icon_path), 'Acerca de', self.iface.mainWindow())
        self.action_about.triggered.connect(self.show_about)
        self.iface.addPluginToMenu(self.menu, self.action_about)
        self.actions.append(self.action_about)
        
    def tr(self, string):
        """Método para traducir textos"""
        return QCoreApplication.translate('IndicesMorfologicosPlugin', string)

    def unload(self):
        # Quitar acciones del menú de complementos
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def run_elongacion(self):
        # Ejecutar el algoritmo de elongación
        processing.execAlgorithmDialog(ELONGACION_ALGORITHM, {})
        
    def run_gradiente(self):
        # Ejecutar el algoritmo de gradiente
        processing.execAlgorithmDialog(GRADIENTE_ALGORITHM, {})
        
    def show_about(self):
        # Mostrar el diálogo "Acerca de"
        dlg = AboutDialog()
        dlg.exec_()