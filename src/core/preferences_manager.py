
import json
import os
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QStandardPaths

class PreferencesManager(QObject):
    settingsChanged = pyqtSignal()
    shortcutChanged = pyqtSignal(str, str) # action, new_key
    
    _instance = None

    def __init__(self):
        super().__init__()
        # Use StandardPaths for correct storage on Windows/Mac/Linux
        data_loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        if not os.path.exists(data_loc):
            os.makedirs(data_loc)
        self.config_path = os.path.join(data_loc, "user_preferences.json")
        print(f"Preferences Path: {self.config_path}")
        
        self.defaults = {
            "gpu_acceleration": True,
            "undo_levels": 50,
            "memory_limit": 70, 
            "theme_mode": "Dark",
            "theme_accent": "#6366f1",
            "language": "es", 
            "cursor_outline": True,
            "cursor_crosshair": True,
            "switch_tool_temp": True,
            "switch_tool_temp_delay": 500,
            "shortcuts": {
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Y",
                "save": "Ctrl+S",
                "new_project": "Ctrl+N",
                "open_project": "Ctrl+O",
                "new_layer": "Ctrl+Shift+N",
                "brush_tool": "B",
                "eraser_tool": "E",
                "tool_pen": "P",
                "tool_pencil": "Shift+P",
                "hand_tool": "H",
                "move_canvas": "Space",
                "zoom_in": "Ctrl++",
                "zoom_out": "Ctrl+-",
                "fit_screen": "Ctrl+0"
            }
        }
        self.config = self.defaults.copy()
        self.load()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = PreferencesManager()
        return cls._instance

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Deep update for shortcuts dict to preserve defaults not present in file
                    if "shortcuts" in data and isinstance(data["shortcuts"], dict):
                        self.config["shortcuts"].update(data["shortcuts"])
                        del data["shortcuts"]
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading preferences: {e}")

    def save(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving preferences: {e}")

    @pyqtSlot(str, result='QVariant')
    def get(self, key):
        return self.config.get(key, self.defaults.get(key))

    @pyqtSlot(str, 'QVariant')
    def set(self, key, value):
        if self.config.get(key) != value:
            self.config[key] = value
            self.save()
            self.settingsChanged.emit()

    @pyqtSlot(str, result=str)
    def getShortcut(self, action_name):
        return self.config["shortcuts"].get(action_name, "")

    @pyqtSlot(str, str)
    def setShortcut(self, action_name, key_sequence):
        # Check for conflicts? For now just overwrite.
        self.config["shortcuts"][action_name] = key_sequence
        self.save()
        self.shortcutChanged.emit(action_name, key_sequence)
        self.settingsChanged.emit()

    # --- Properties for QML Binding Simplification ---
    
    @pyqtProperty(bool, notify=settingsChanged)
    def gpuAcceleration(self): return self.config.get("gpu_acceleration", True)
    @gpuAcceleration.setter
    def gpuAcceleration(self, val): self.set("gpu_acceleration", val)

    @pyqtProperty(int, notify=settingsChanged)
    def undoLevels(self): return self.config.get("undo_levels", 50)
    @undoLevels.setter
    def undoLevels(self, val): self.set("undo_levels", val)

    @pyqtProperty(str, notify=settingsChanged)
    def themeMode(self): return self.config.get("theme_mode", "Dark")
    @themeMode.setter
    def themeMode(self, val): self.set("theme_mode", val)

    @pyqtProperty(str, notify=settingsChanged)
    def themeAccent(self): return self.config.get("theme_accent", "#6366f1")
    @themeAccent.setter
    def themeAccent(self, val): self.set("theme_accent", val)

    @pyqtProperty(str, notify=settingsChanged)
    def language(self): return self.config.get("language", "es")
    @language.setter
    def language(self, val): self.set("language", val)

