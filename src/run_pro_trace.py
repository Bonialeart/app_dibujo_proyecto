import sys
import os
print("1. Starting imports")
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat, QIcon
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt6.QtCore import QUrl, QFileSystemWatcher, QTimer, QObject
from PyQt6.QtWebEngineQuick import QtWebEngineQuick
print("2. Imports done")

# Import our custom Canvas Item
from ui.canvas_item import QCanvasItem
print("3. Canvas item imported")

def main():
    print("4. Inside main")
    # 1. Initialize WebEngine
    QtWebEngineQuick.initialize()
    print("5. WebEngine initialized")
    
    # 2. Setup App
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ArtFlow Studio Pro")
    print("6. App created")

    # 3. Register Custom Types
    qmlRegisterType(QCanvasItem, 'ArtFlow', 1, 0, 'QCanvasItem')
    print("7. Type registered")

    # 4. Setup Engine
    engine = QQmlApplicationEngine()
    print("8. Engine created")
    
    # 4b. Register Custom Icon Provider
    try:
        from icon_provider import IconProvider
        engine.addImageProvider("appicons", IconProvider())
        print("9. IconProvider registered")
    except Exception as e:
        print(f"Error registering IconProvider: {e}")

    # 5. Load UI
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qml_path = os.path.join(script_dir, "ui", "qml", "main_pro.qml")
    print(f"10. Loading QML: {qml_path}")
    
    if not os.path.exists(qml_path):
        print(f"Error: QML file not found at {qml_path}")
        return

    engine.load(QUrl.fromLocalFile(qml_path))
    print("11. Engine load called")
    
    if not engine.rootObjects():
        print("Error: UI failed to load.")
        sys.exit(-1)

    print("12. Entering event loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
