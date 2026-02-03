print("Importing...")
import sys
import os
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat, QIcon
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt6.QtCore import QUrl, QFileSystemWatcher, QTimer, QObject
from PyQt6.QtWebEngineQuick import QtWebEngineQuick
print("Base imports done.")
from ui.canvas_item import QCanvasItem
print("All imports done.")
