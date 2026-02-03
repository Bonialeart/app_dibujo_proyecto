import sys
import os
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat, QIcon
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt6.QtCore import QUrl, QFileSystemWatcher, QTimer, QObject
from PyQt6.QtWebEngineQuick import QtWebEngineQuick

# Import our custom Canvas Item
from ui.canvas_item import QCanvasItem

def main():
    # 1. Initialize WebEngine
    QtWebEngineQuick.initialize()
    
    # 2. Setup App
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ArtFlow Studio Pro")

    # 3. Register Custom Types
    qmlRegisterType(QCanvasItem, 'ArtFlow', 1, 0, 'QCanvasItem')

    # 4. Setup Engine
    engine = QQmlApplicationEngine()
    
    # 4b. Register Custom Icon Provider
    try:
        from icon_provider import IconProvider
        engine.addImageProvider("appicons", IconProvider())
        print("IconProvider registered successfully")
    except Exception as e:
        print(f"Error registering IconProvider: {e}")

    # 5. Load UI
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qml_path = os.path.join(script_dir, "ui", "qml", "main_pro.qml")
    
    if not os.path.exists(qml_path):
        print(f"Error: QML file not found at {qml_path}")
        return

    engine.load(QUrl.fromLocalFile(qml_path))
    
    if not engine.rootObjects():
        print("Error: UI failed to load.")
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
