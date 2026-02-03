import sys
import os
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication


# Force software rendering for UI to avoid driver conflicts on Windows
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

# Disable OpenGL for now to ensure stability
# os.environ["QSG_RHI_BACKEND"] = "opengl"
# os.environ["QT_OPENGL"] = "desktop"







# Add path to native module
current_dir = os.path.dirname(os.path.abspath(__file__))
native_dir = os.path.join(current_dir, "core", "cpp")
if native_dir not in sys.path:
    sys.path.append(native_dir)
# Also try the specific build dir just in case setup.py left it there
# But we saw it copied it to src/core/cpp

from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterType, QQmlComponent
from PyQt6.QtCore import QUrl, QFileSystemWatcher, QTimer, QObject

# from PyQt6.QtWebEngineQuick import QtWebEngineQuick # Removed to prevent conflicts

# Import our custom Canvas Item
from ui.canvas_item import QCanvasItem

# Global references
app = None
engine = None
watcher = None

def load_ui():
    global engine
    engine.clearComponentCache()
    root_objects = list(engine.rootObjects())
    for obj in root_objects:
        obj.close()
        obj.deleteLater()
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qml_path = os.path.join(script_dir, "ui/qml/main_pro.qml")
    
    if os.path.exists(qml_path):
        engine.load(QUrl.fromLocalFile(qml_path))

def on_file_changed(path):
    QTimer.singleShot(100, load_ui)

def main():
    global app, engine, watcher
    
    print("Starting application...", flush=True)
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("ArtFlow Studio Pro")

        print("Registering types...", flush=True)
        qmlRegisterType(QCanvasItem, 'ArtFlow', 1, 0, 'QCanvasItem')

        print("Importing IconProvider...", flush=True)
        from icon_provider import IconProvider
        engine = QQmlApplicationEngine()
        
        # Catch QML warnings/errors
        def on_warning(warnings):
            for w in warnings:
                print(f"QML WARNING: {w.toString()}", flush=True)
                
        engine.warnings.connect(on_warning)
        
        print("Adding image provider...", flush=True)
        engine.addImageProvider("icons", IconProvider())

        # Setup Timelapse System
        from timelapse_system import TimelapseController, TimelapseProvider
        timelapse_controller = TimelapseController()
        timelapse_provider = TimelapseProvider(timelapse_controller)
        
        engine.rootContext().setContextProperty("timelapseController", timelapse_controller)
        engine.addImageProvider("timelapse", timelapse_provider)

        
        # 5. Context Properties (Absolute paths for reliable icon loading in Windows)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(script_dir, "assets", "icons")
        icons_url = QUrl.fromLocalFile(icons_dir).toEncoded().data().decode('utf-8')
        if not icons_url.endswith('/'):
            icons_url += '/'
        engine.rootContext().setContextProperty("iconsUrl", icons_url)
        print(f"Icons folder URL: {icons_url}", flush=True)

        # 6. Default Video Path
        from PyQt6.QtCore import QStandardPaths
        video_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation)
        video_url = QUrl.fromLocalFile(video_path).toString()
        engine.rootContext().setContextProperty("defaultVideoPath", video_url)
        
        # 7. Preferences Manager
        from core.preferences_manager import PreferencesManager
        prefs_manager = PreferencesManager.instance()
        engine.rootContext().setContextProperty("preferencesManager", prefs_manager)

        # 8. Initial Load
        print("Loading UI...", flush=True)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qml_path = os.path.join(script_dir, "ui/qml/main_pro.qml")
        
        # Use QQmlComponent for better error handling
        component = QQmlComponent(engine, QUrl.fromLocalFile(qml_path))
        if component.isLoading():
            print("Component is loading...", flush=True)
            # You might need to wait or connect to statusChanged, but for synchronous load from local file it should be ready
        
        if component.isError():
            print("CRITICAL QML ERRORS:", flush=True)
            for error in component.errors():
                print(f" - {error.toString()}", flush=True)
            sys.exit(-1)
            
        obj = component.create()
        if not obj:
            print("Failed to create root object (returned None).", flush=True)
            if component.isError():
                for error in component.errors():
                    print(f" - {error.toString()}", flush=True)
            sys.exit(-1)
            
        print("Executing app...", flush=True)
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR: {e}", flush=True)

if __name__ == "__main__":
    main()
