"""
ArtFlow Studio - QCanvasItem
Links Python drawing logic with QML interface and manages Multiple Layers.
"""

from PyQt6.QtQuick import QQuickPaintedItem
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QBrush, QCursor, QGuiApplication, QTransform, QPixmap, QRadialGradient, QIcon, QPolygonF, QPainterPath, QRegion
import os
import json
import shutil
import base64
import zipfile
import threading
import tempfile
import time
import io
import cv2
import numpy as np
import math
import colorsys
from datetime import datetime
try:
    from psd_tools import PSDImage
    HAS_PSD_TOOLS = True
except ImportError:
    HAS_PSD_TOOLS = False
    print("psd-tools not installed. PSD support disabled.")

native = None
HAS_NATIVE = False
HAS_NATIVE_RENDER = False

try:
    import artflow_native as native_mod
    native = native_mod
    HAS_NATIVE = True
    # Only use native renderer if NOT in software mode
    if os.environ.get("QT_QUICK_BACKEND") != "software":
        HAS_NATIVE_RENDER = False # DISABLE NATIVE RENDER TO PREVENT CRASH FOR USER
        print("Native Rendering disabled for stability.")
    else:
        print("Software backend detected. Native GPU rendering disabled, but utilities (ABR, etc) are available.")
except ImportError:
    print("artflow_native not found. Falling back to slow software mode.")




try:
    from core.python.abr_parser import ABRParser as PyABRParser
    HAS_PY_ABR = True
except ImportError:
    HAS_PY_ABR = False
    print("Python ABR Parser not found.")

from PyQt6.QtCore import Qt, QPointF, pyqtSlot, QRectF, QRect, QSize, pyqtProperty, pyqtSignal, QObject, QByteArray, QBuffer, QIODevice, QUrl, QTimer
from PyQt6.QtGui import QTabletEvent, QInputDevice
from core.layer import Layer
from core.tools.fill_tool import FillToolMixin
from core.tools.selection_tool import SelectionToolMixin
from core.tools.transform_tool import TransformToolMixin
from core.tools.shape_tool import ShapeToolMixin
from core.brush_presets import BrushPresets
from core.drawing_engine import DrawingEngineMixin
from core.preferences_manager import PreferencesManager
from PyQt6.QtGui import QKeySequence


class ColorManager:
    """Helper for Professional Color Models (HCL, HSV corrections)."""
    @staticmethod
    def rgb_to_hcl(r, g, b):
        # Simplification of HCL (based on CIE Luv approximation for performance)
        # r, g, b in range 0-255
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        # Perceived Luminance (Standard Rec. 709)
        l = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        # Chroma is roughly Saturation * Value in this simplified model, 
        # basically how colorful it is relative to brightness.
        c = s * v
        return h * 360.0, c * 100.0, l * 100.0

    @staticmethod
    def hcl_to_rgb(h, c, l):
        # Convert back based on target luminance
        # This is an approximation algorithm for real-time UI
        # h in 0-360, c in 0-100, l in 0-100
        
        # 1. First calc simplistic HSV guess
        # H = h, S = ?, V = ?
        # We know L ~ V * (1 - S_sat_factor)? No, L is complex.
        # Let's use the USER's Formula which is a geometric approximation.
        
        h_rad = h * (math.pi / 180.0)
        
        # Normalize L and C to 0-1 range for math
        L_norm = l / 100.0
        C_norm = c / 100.0
        
        # User formula:
        # r = l + c * cos(h)
        # g = l - c * 0.5 
        # b = l + c * sin(h)
        # This looks like a cylindrical projection logic.
        
        # Adaptation of user formula normalized:
        r = L_norm + C_norm * math.cos(h_rad)
        g = L_norm - C_norm * 0.5 
        b = L_norm + C_norm * math.sin(h_rad)
        
        # Clamp
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
        
        return int(r * 255), int(g * 255), int(b * 255)

class QCanvasItem(QQuickPaintedItem, DrawingEngineMixin, FillToolMixin, SelectionToolMixin, TransformToolMixin, ShapeToolMixin):
    """Custom QML Item that allows drawing with QPainter from Python, supporting multiple layers."""
    
    # Signal to update QML Layer List
    layersChanged = pyqtSignal(list)
    activeLayerChanged = pyqtSignal(int)
    currentToolChanged = pyqtSignal(str)
    canvasWidthChanged = pyqtSignal(int)
    canvasHeightChanged = pyqtSignal(int)
    viewOffsetChanged = pyqtSignal()
    zoomLevelChanged = pyqtSignal(float)
    brushSizeChanged = pyqtSignal(int)
    brushColorChanged = pyqtSignal(str)
    brushOpacityChanged = pyqtSignal(float)
    brushSmoothingChanged = pyqtSignal(float)
    brushHardnessChanged = pyqtSignal(float)
    brushRoundnessChanged = pyqtSignal(float)
    brushAngleChanged = pyqtSignal(float)
    brushGrainChanged = pyqtSignal(float)
    brushGranulationChanged = pyqtSignal(float)
    brushDiffusionChanged = pyqtSignal(float)
    brushSpacingChanged = pyqtSignal(float)
    brushDynamicsChanged = pyqtSignal(bool)
    cursorPressureChanged = pyqtSignal(float)
    cursorRotationChanged = pyqtSignal(float)
    pressureCurveChanged = pyqtSignal()
    currentProjectNameChanged = pyqtSignal()
    currentProjectPathChanged = pyqtSignal()
    currentBrushNameChanged = pyqtSignal()

    def _prepare_magnetic_map(self):
        """Genera un mapa de bordes (Canny) de la capa activa."""
        if not self.layers: return
        if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers): return
        layer = self.layers[self._active_layer_index]
        
        # Convertir QImage a NumPy
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())
        arr = np.frombuffer(ptr, np.uint8).reshape((layer.image.height(), layer.image.width(), 4))
        
        # Detectar bordes
        gray = cv2.cvtColor(arr, cv2.COLOR_BGRA2GRAY)
        self._magnetic_map = cv2.Canny(gray, 100, 200)

    def _get_magnetic_pos_canvas(self, canvas_pos):
        """Ajusta la posición del canvas al borde más cercano en un radio de 20px (En Coords de Canvas)."""
        if self._magnetic_map is None: return canvas_pos
        
        ix, iy = int(canvas_pos.x()), int(canvas_pos.y())
        h, w = self._magnetic_map.shape
        r = 30 # Radio de búsqueda aumentado para mejor UX
        
        y1, y2 = max(0, iy-r), min(h, iy+r)
        x1, x2 = max(0, ix-r), min(w, ix+r)
        if y1 >= y2 or x1 >= x2: return canvas_pos

        roi = self._magnetic_map[y1:y2, x1:x2]
        edge_points = np.argwhere(roi > 0)
        
        if edge_points.size > 0:
            cy, cx = iy - y1, ix - x1
            distances = np.sum((edge_points - [cy, cx])**2, axis=1)
            closest = edge_points[np.argmin(distances)]
            return QPointF(x1 + closest[1], y1 + closest[0])
        
        return canvas_pos


    projectsLoaded = pyqtSignal(list)
    brushesChanged = pyqtSignal()
    availableBrushesChanged = pyqtSignal()
    activeBrushNameChanged = pyqtSignal(str)
    cursorPosChanged = pyqtSignal(float, float)
    brushTipImageChanged = pyqtSignal(str) # Data URL

    # Fill Tool Signals
    fillToleranceChanged = pyqtSignal(int)
    fillExpandChanged = pyqtSignal(int)
    fillModeChanged = pyqtSignal(str)
    fillSampleAllChanged = pyqtSignal(bool)
    isTransformingChanged = pyqtSignal(bool)
    selectionEmptyChanged = pyqtSignal(bool)
    brushStampModeChanged = pyqtSignal(bool)
    brushStreamlineChanged = pyqtSignal(int)
    canvasPreviewChanged = pyqtSignal()

    # Fill Tool Properties



    # Selection and tool status
    # isTransforming = pyqtProperty(bool, notify=isTransformingChanged) # Already defined elsewhere
    # selectionEmpty = pyqtProperty(bool, notify=selectionEmptyChanged) # Already defined elsewhere






    
    # Blend Mode Mapping
    BLEND_MODES = BrushPresets.BLEND_MODES
    BLEND_MODES_INV = BrushPresets.BLEND_MODES_INV

    BRUSH_PRESETS = BrushPresets.PRESETS

    def __init__(self, parent=None):
        # 0. EARLY INITIALIZATION OF LOCKS/CACHES (Prevent Slot Crashes)
        self._thumbnail_lock = threading.RLock()
        self._thumbnail_cache = {}
        self._timelapse_lock = threading.RLock()
        self._available_brushes = []
        
        print("QCanvasItem: initializing...", flush=True)
        super().__init__(parent)

        
        # Enable mouse tracking
        self.setAcceptedMouseButtons(Qt.MouseButton.AllButtons)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self._cursor_overridden = False
        self._cursor_pos = QPointF(0,0)
        self._is_hovering = False
        
        # Performance - Use Image for software backend compatibility


        if os.environ.get("QT_QUICK_BACKEND") == "software":
            self.setRenderTarget(QQuickPaintedItem.RenderTarget.Image)
        else:
            self.setRenderTarget(QQuickPaintedItem.RenderTarget.FramebufferObject)
        self.setAntialiasing(True)

        # 2. Native Engine (Deferred Init) - Will be initialized in paint()
        self._native_renderer = None
        self._stroke_renderer = None
        self._native_initialized = False 
        self._native_draw_queue = []

        # Timelapse State
        self._timelapse_stroke_count = 0
        self._timelapse_counter = 0
        self._timelapse_dir = ""
        # self._timelapse_lock = threading.RLock() # MOVED UP

        try:
             import tempfile, time
             self._timelapse_dir = os.path.join(tempfile.gettempdir(), "ArtFlow_Timelapse_" + str(int(time.time())))
             os.makedirs(self._timelapse_dir, exist_ok=True)
        except Exception as e:
             # print(f"Error initializing timelapse dir: {e}")
             pass
        
        # Canvas State
        self._canvas_width = 1920
        self._canvas_height = 1080
        self._fill_color = "#ffffff" # Default background fill color
        
        # Layer State
        self.layers = [] # List of Layer objects
        self._active_layer_index = 0
        
        # View State (Panning / Zoom)
        self._view_offset = QPointF(50, 50)
        self._zoom_level = 1.0
        self._is_saving = False # Guard for saving process
        
        # Brush/Tool State
        self._current_tool = "brush" 
        self._brush_size = 20
        
        home = os.path.expanduser("~")
        self._projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
        if not os.path.exists(self._projects_dir):
            os.makedirs(self._projects_dir, exist_ok=True)

        self._brush_color = QColor("#000000")
        self._brush_opacity = 1.0
        self._brush_smoothing = 0.5 
        self._brush_hardness = 0.8
        self._brush_blend_mode = QPainter.CompositionMode.CompositionMode_SourceOver
        self._current_brush_name = "Ink Pen"
        self._brush_spacing = 0.1
        self._brush_roundness = 1.0
        self._brush_angle = 0.0
        self._brush_dynamic_angle = False
        
        # Pressure Curve
        self._pressure_curve = [(0.25, 0.25), (0.75, 0.75)] 
        
        # Input/Tracing Tracking
        self._current_cursor_rotation = 0.0
        self._last_point = None
        self._drawing = False
        
        # S T A B I L I Z E R
        self._stabilizer_points = [] # Cola de posiciones
        self._last_stabilized_pos = QPointF(0, 0)
        self.stabilization_amount = 5 # Cuanto más alto, más suave (0-20)
        
        # Buffers for optimized painting
        self._group_buffer = None
        self._temp_buffer = None

        
        # Transform State
        self._is_transforming = False

        # Undo/Redo
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = PreferencesManager.instance().undoLevels
        PreferencesManager.instance().settingsChanged.connect(self._on_prefs_changed)
        
        
        # Initialize Drawing Engine (Textures, Brushes)
        self._init_drawing_engine()
        self._init_fill_tool()
        self._init_selection_tool()
        self._init_transform_tool()
        self._init_shape_tool()

        # --- SISTEMA DE SELECCIÓN (PREMIUM) ---
        self._selection_points = []      # Puntos del lazo
        self._selection_path = QPainterPath() 
        self._is_selecting = False
        self._marching_ants_offset = 0   # Para la animación
        self._magnetic_map = None        # Buffer de bordes para el imán
        self._lasso_closed = True        # Init safe state

        # Timer para la animación de la selección
        self._ants_timer = QTimer(self)
        self._ants_timer.timeout.connect(self._update_ants)
        self._ants_timer.start(100) # 10 FPS para la animación

    @pyqtSlot()
    def _on_prefs_changed(self):
        self._max_undo = PreferencesManager.instance().undoLevels

        self._native_failed = False # Flag to stop endless retries
        
        # --- INPUT STATE ---
        self._last_pos = None
        self._pressure_interp = 0.0

        print("QCanvasItem: fully initialized.", flush=True)

        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._on_render_tick)
        self._render_timer.start(16) # ~60 FPS
        
        # Thumbnail Cache (Restored)
        self._thumbnail_cache = {}
        self._thumbnail_lock = threading.Lock()

    @pyqtSlot()
    def _update_ants(self):
        if not self._selection_path.isEmpty() or (self._is_selecting and len(self._selection_points) > 1):
            self._marching_ants_offset = (self._marching_ants_offset + 1) % 12
            self.update()


    def _on_render_tick(self):
        """Called effectively at 60FPS to update the canvas."""
        # Notify preview update
        self.canvasPreviewChanged.emit()

    def _init_native_gl(self):
        """Initializes OpenGL resources on the GPU."""
        if not HAS_NATIVE_RENDER or self._native_initialized or self._native_failed: return
        try:
            # 0. Create native objects if not already created
            # This must happen here because it calls initGLFunctions()
            if self._native_renderer is None:
                self._native_renderer = native.Renderer(int(self._canvas_width), int(self._canvas_height))
            if self._stroke_renderer is None:
                self._stroke_renderer = native.StrokeRenderer()

            # 1. Initialize Shaders and Quads
            if not self._stroke_renderer.initialize():
                print("Failed to initialize StrokeRenderer OpenGL")
                self._native_failed = True
                return

            
            # 2. Upload Paper Texture
            # Convert numpy to bytes
            paper_bytes = self._paper_texture.tobytes() # It's float32? No, let's check
            # Real paper texture should be RGBA8 for the shader
            paper_rgba = (self._paper_texture * 255).astype(np.uint8)
            # Add alpha channel
            paper_rgba_full = np.dstack([paper_rgba, paper_rgba, paper_rgba, np.full_like(paper_rgba, 255)])
            self._stroke_renderer.setPaperTexture(paper_rgba_full.tobytes(), self._paper_texture_size, self._paper_texture_size)
            
            self._native_initialized = True
            print("Native OpenGL Resources Uploaded.")
        except Exception as e:
            print(f"Native GL Init Error: {e}")
            self._native_failed = True # Stop retrying

    def _sync_active_layer_from_native(self):
        """Pulls the result of the Ping-Pong FBO back to the active QImage."""
        if not HAS_NATIVE_RENDER or not self._native_initialized: return
        
        from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE
        
        active_layer = self.layers[self._active_layer_index]
        w, h = self._canvas_width, self._canvas_height
        
        # Pull from current Target FBO
        # self._native_renderer.beginFrame() # Already bound
        pixels = glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE)
        
        # Update QImage
        # OpenGL is bottom-up, QImage is top-down
        qimg = QImage(pixels, w, h, QImage.Format.Format_RGBA8888).mirrored()
        active_layer.image = qimg.convertToFormat(QImage.Format.Format_ARGB32)
                
        # self.update_cursor() # Removed as we handle it in hover now

    def _update_native_cursor(self):
        """Updates cursor state (Nuclear Compatible)."""
        if self._current_tool == "hand":
            # Restore standard cursor if we were overriding
            if getattr(self, "_cursor_overridden", False):
                QGuiApplication.restoreOverrideCursor()
                self._cursor_overridden = False
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        else:
            # Enforce Blank Override
            if self._is_hovering and not getattr(self, "_cursor_overridden", False):
                 QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
                 self._cursor_overridden = True
    # --- UNIFIED EVENT DISPATCHER ---
    # (Moved to end of file to keep initialization clean)
                
    def reset_canvas(self):
        w, h = int(self._canvas_width), int(self._canvas_height)
        if w <= 0 or h <= 0: return
        
        # Initialize with background and one layer
        self.layers = []
        
        # 1. Background Layer
        bg_layer = Layer(w, h, "Background", type="background")
        bg_layer.image.fill(QColor(self._fill_color))
        bg_layer.locked = True 
        self.layers.append(bg_layer)
        
        # 2. Initial Drawing Layer
        new_layer = Layer(w, h, "Layer 1")
        self.layers.append(new_layer)
        
        # Initial Centering
        self._view_offset = QPointF(50, 50)
        
        self._active_layer_index = 1
        
        # Reset Project Info
        self._current_project_name = "Untitled"
        self._current_project_path = ""
        self.currentProjectNameChanged.emit()
        self.currentProjectPathChanged.emit()
        
        # --- RESET TIMELAPSE SESSION ---
        with self._timelapse_lock:
             self._timelapse_counter = 0
             if self._timelapse_dir and os.path.exists(self._timelapse_dir):
                 try:
                     for f in os.listdir(self._timelapse_dir):
                         os.remove(os.path.join(self._timelapse_dir, f))
                 except Exception as e:
                     print(f"Error resetting timelapse dir: {e}")

        self.emit_layers_update()
        self.update()

    def emit_layers_update(self):
        """Emits signal with list of dicts for QML, handling group visibility."""
        data = []
        # Iterate REVERSED (Top-Down) for UI list construction with group filtering
        reversed_layers = list(enumerate(self.layers))[::-1]
        
        current_skip_depth = -1
        
        for i, layer in reversed_layers:
            # Check filtering by closed groups
            if current_skip_depth != -1:
                if layer.depth >= current_skip_depth:
                    continue # Skip hidden children
                else:
                    current_skip_depth = -1 # End skip
            
            mode_str = self.BLEND_MODES_INV.get(layer.blend_mode, "Normal")
            
            # Generate thumbnail only for visible layers or active layer to save CPU
            thumbnail = ""
            if layer.type != "group" and (layer.visible or i == self._active_layer_index):
                thumbnail = layer.get_thumbnail_base64(64)
                
            data.append({
                "layerId": i,
                "index": i,
                "name": layer.name,
                "type": layer.type,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "locked": layer.locked,
                "alpha_lock": layer.alpha_lock,
                "active": (i == self._active_layer_index),
                "blendMode": mode_str,
                "expanded": layer.expanded,
                "depth": layer.depth,
                "clipped": layer.clipped,
                "is_private": layer.is_private,
                "thumbnail": thumbnail
            })
            
            # If closed group, start skipping children (deeper layers immediately below)
            if layer.type == "group" and not layer.expanded:
                current_skip_depth = layer.depth + 1
        
        self.layersChanged.emit(data)

    # --- LAYER MANAGEMENT API (Called from QML) ---
    
    @pyqtSlot(int, str)
    def setLayerBlendMode(self, index, mode_str):
        """Sets the blend mode for a layer."""
        if 0 <= index < len(self.layers):
            if mode_str in self.BLEND_MODES:
                self.layers[index].blend_mode = self.BLEND_MODES[mode_str]
                self.emit_layers_update()
                self.update()

    @pyqtSlot(int, float)
    def setLayerOpacity(self, index, opacity):
        if 0 <= index < len(self.layers):
            self.layers[index].opacity = opacity
            self.emit_layers_update()
            self.update()

    @pyqtSlot(int)
    def toggleGroupExpanded(self, index):
        if 0 <= index < len(self.layers):
            layer = self.layers[index]
            if layer.type == "group":
                layer.expanded = not layer.expanded
                self.emit_layers_update()

    @pyqtSlot()
    def addGroup(self):
        w, h = self._canvas_width, self._canvas_height
        idx = min(len(self.layers), self._active_layer_index + 1)
        new_group = Layer(w, h, f"Group {len(self.layers)}", type="group")
        
        # Inherit depth
        if 0 <= self._active_layer_index < len(self.layers):
             new_group.depth = self.layers[self._active_layer_index].depth
        
        self.layers.insert(idx, new_group)
        self._active_layer_index = idx
        self.emit_layers_update()
        self.update()

    @pyqtSlot()
    def addLayer(self):
        w, h = self._canvas_width, self._canvas_height
        new_layer = Layer(w, h, f"Layer {len(self.layers)}")
        
        # Inherit depth logic
        if 0 <= self._active_layer_index < len(self.layers):
            active_layer = self.layers[self._active_layer_index]
            if active_layer.type == "group" and active_layer.expanded:
                new_layer.depth = active_layer.depth + 1
            else:
                new_layer.depth = active_layer.depth
        
        idx = min(len(self.layers), self._active_layer_index + 1)
        self.layers.insert(idx, new_layer)
        self._active_layer_index = idx
        self.emit_layers_update()
        self.update()

    @pyqtSlot(int)
    def setActiveLayer(self, real_index):
        # Now receives the REAL index directly from model.index property
        if 0 <= real_index < len(self.layers):
            self._active_layer_index = real_index
            self.emit_layers_update()

    @pyqtSlot(int)
    def toggleVisibility(self, real_index):
        # Now receives the REAL index directly from model.index property
        if 0 <= real_index < len(self.layers):
            self.layers[real_index].visible = not self.layers[real_index].visible
            print(f"Toggled layer {real_index}: {self.layers[real_index].name} -> visible={self.layers[real_index].visible}")
            self.emit_layers_update()
            self.update() # Redraw canvas

    @pyqtSlot(int, bool)
    def setLayerPrivate(self, real_index, is_private):
        """Sets whether a layer is private (hidden from timelapse)."""
        if 0 <= real_index < len(self.layers):
            self.layers[real_index].is_private = is_private
            print(f"Layer {real_index} private set to: {is_private}")
            self.emit_layers_update()

    @pyqtSlot(int)
    def removeLayer(self, real_index):
        # Now receives the REAL index directly from model.index property
        # Prevent deleting background (index 0)
        if real_index > 0 and real_index < len(self.layers):
            print(f"Removing layer {real_index}: {self.layers[real_index].name}")
            self.layers.pop(real_index)
            # Adjust active index
            if self._active_layer_index >= len(self.layers):
                self._active_layer_index = len(self.layers) - 1
            self.emit_layers_update()
            self.update()

    @pyqtSlot(int)
    def duplicateLayer(self, real_index):
        if 0 <= real_index < len(self.layers):
            src_layer = self.layers[real_index]
            print(f"Duplicating layer {real_index}: {src_layer.name}")
            new_layer = Layer(src_layer.image.width(), src_layer.image.height(), src_layer.name + " Copy", type=src_layer.type)
            new_layer.image = src_layer.image.copy()
            new_layer.visible = src_layer.visible
            new_layer.opacity = src_layer.opacity
            new_layer.blend_mode = src_layer.blend_mode
            new_layer.depth = src_layer.depth
            new_layer.expanded = src_layer.expanded
            
            # Insert above the original
            self.layers.insert(real_index + 1, new_layer)
            self._active_layer_index = real_index + 1
            self.emit_layers_update()
            self.update()

    @pyqtSlot(int, int, int)
    def moveLayer(self, from_index, to_index, new_depth):
        """Moves layer from from_index to to_index (Real Python Indices) and sets depth"""
        if not (0 <= from_index < len(self.layers) and 0 <= to_index <= len(self.layers)):
            return
        
        print(f"Moving layer {from_index} -> {to_index} (New Depth: {new_depth})")
        
        item = self.layers.pop(from_index)
        
        # Adjust insert index if shifting downwards
        insert_idx = to_index
        # if from_index < to_index:
        #    insert_idx -= 1 # This depends on how it's called from QML. 
        # For simplicity, if we use list.insert, it puts before the current item at index.
        
        if insert_idx > len(self.layers): insert_idx = len(self.layers)
        self.layers.insert(insert_idx, item)
        
        # Hierarchy depth
        if item.type == "background":
            item.depth = 0
        else:
            item.depth = max(0, new_depth)
        
        # Simple hack to update active layer index
        # The safest approach is just to check item identity, but using indices is fine for now
        # because the UI will refresh immediately after.
        
        self.emit_layers_update()
        self.update()

    @pyqtSlot(int, int)
    def setLayerDepth(self, index, delta):
        """Adjusts depth by delta (+1 or -1)"""
        if 0 <= index < len(self.layers):
            new_depth = max(0, self.layers[index].depth + delta)
            self.layers[index].depth = new_depth
            self.emit_layers_update()
            self.update()

    @pyqtSlot(int)
    def toggleLock(self, real_index):
        """Toggle lock state of a layer."""
        if 0 <= real_index < len(self.layers):
            self.layers[real_index].locked = not self.layers[real_index].locked
            print(f"Lock toggled for layer {real_index}: {self.layers[real_index].name} -> locked={self.layers[real_index].locked}")
            self.emit_layers_update()

    @pyqtSlot(int, str)
    def renameLayer(self, index, new_name):
        if 0 <= index < len(self.layers):
            self.layers[index].name = new_name
            self.emit_layers_update()

    @pyqtSlot(int)
    def clearLayer(self, index):
        if 0 <= index < len(self.layers):
            self.layers[index].clear()
            self.update()

    @pyqtSlot(int)
    def fillLayer(self, index):
        if 0 <= index < len(self.layers):
            self.layers[index].image.fill(self._brush_color)
            self.update()

    @pyqtSlot(int)
    def toggleAlphaLock(self, index):
        if 0 <= index < len(self.layers):
            self.layers[index].alpha_lock = not self.layers[index].alpha_lock
            print(f"Alpha Lock toggled for layer {index}: {self.layers[index].alpha_lock}")
            self.emit_layers_update()

    @pyqtSlot(int)
    def mergeDown(self, index):
        """Merges layer at index with the one below it."""
        if index > 0 and index < len(self.layers):
            top_layer = self.layers[index]
            bottom_layer = self.layers[index - 1]
            
            p = QPainter(bottom_layer.image)
            p.setCompositionMode(top_layer.blend_mode)
            p.setOpacity(top_layer.opacity)
            p.drawImage(0, 0, top_layer.image)
            p.end()
            
            self.layers.pop(index)
            self._active_layer_index = index - 1
            self.emit_layers_update()
            self.update()

    @pyqtSlot(int)
    def toggleClipping(self, index):
        """Toggles clipping mask status for a layer."""
        if 0 <= index < len(self.layers):
            # Background cannot be clipped
            if self.layers[index].type == "background": return
            # Bottom layer cannot be clipped (nothing to clip to)
            if index == 0: return # Actually internal index 0 is bg. index 1 is typical bottom.
            
            self.layers[index].clipped = not self.layers[index].clipped
            self.emit_layers_update()
            self.update()

    @pyqtSlot(str)
    def usePreset(self, name):
        """Carga un pincel y configura sus dinámicas."""
        print(f"Cargando Pincel: {name}")
        
        # 1. Buscar pincel
        p = self.BRUSH_PRESETS.get(name) or self._custom_brushes.get(name)
        
        # Búsqueda difusa si falla la exacta
        if not p:
            for k in self._custom_brushes.keys():
                if name in k: 
                    p = self._custom_brushes[k]
                    name = k
                    break
        
        if not p:
             print(f"No se encontró el pincel: {name}")
             return

        self._current_brush_name = name
        self.activeBrushNameChanged.emit(name)
        
        # 2. !!! REINICIO TOTAL DE CACHÉ !!! (Arregla que no cambien de forma/textura)
        self._brush_texture_params = None 
        self._brush_texture_cache = None
        self._last_stamp = None
        self._last_stamp_params = None
        if hasattr(self, '_last_native_stamp_params'):
            self._last_native_stamp_params = None

        # 3. Cargar propiedades físicas mediante SETTERS (para emitir señales a la UI)
        self.brushSize = int(p.get("size", 20))
        self.brushOpacity = float(p.get("opacity", 1.0))
        self.brushHardness = float(p.get("hardness", 0.5))
        self.brushSmoothing = float(p.get("smoothing", 0.1))
        
        # Estas llamadas aseguran que los sliders en la UI se muevan solos
        self.brushGrain = float(p.get("grain", 0.0))
        self.brushRoundness = float(p.get("roundness", 1.0))
        
        # Espaciado (Vital para que no se vean puntos)
        if "spacing" in p:
            self.brushSpacing = float(p.get("spacing"))
        else:
            self.brushSpacing = 0.1

        # 4. Configurar Comportamiento (Dinámicas)
        if p.get("is_custom", False):
            # Es un ABR importado
            self._brush_grain = 0.0 
            
            # Detect target based on name EVEN for custom brushes
            target_tool = "brush"
            if "Eraser" in name: target_tool = "eraser"
            elif "Water" in name or "Wash" in name: target_tool = "water"
            else: target_tool = "brush"
            
            self.currentTool = target_tool
            
            # Si el espaciado es pequeño, rotamos el pincel con el trazo
            if self.brushSpacing < 0.15:
                self.brushDynamicAngle = True
            else:
                self.brushDynamicAngle = False
        else:
            # Es un pincel estándar (generado)
            self.brushGrain = p.get("grain", 0.0)
            self.brushDynamicAngle = False
            
            # Determine target tool based on name
            target_tool = "brush"
            if "Eraser" in name: target_tool = "eraser"
            elif "Water" in name or "Wash" in name: target_tool = "water" 
            elif "Pen" in name or "Ink" in name or "Marker" in name or "Maru" in name: target_tool = "pen"
            elif "Pencil" in name or "HB" in name or "6B" in name: target_tool = "pencil"
            elif "Airbrush" in name or "Soft" in name or "Hard" in name: target_tool = "airbrush"
            elif "Oil" in name or "Acrylic" in name: target_tool = "brush"
            
            # Smart Tool Switch (Sticky Logic to prevent UI jumps)
            if self._current_tool == target_tool:
                pass # Already correct
            elif target_tool == "water" or self._current_tool == "water":
                # NEVER be sticky for Water. Water is a physical mode.
                # If we are going to/from water, we MUST switch tool to activate/deactivate physics.
                self.currentTool = target_tool
            elif target_tool == "brush" and self._current_tool in ["pen", "pencil", "airbrush"]:
                # Sticky for Inking tools: if we are in Pen/Pencil and select a generic brush, stay put.
                pass
            else:
                self.currentTool = target_tool

        # 5. Modo de Mezcla
        blend_str = p.get("blend", "Normal")
        self._brush_blend_mode = self.BLEND_MODES.get(blend_str, QPainter.CompositionMode.CompositionMode_SourceOver)
             
        self.update()

    @pyqtSlot(str)
    def loadBrush(self, name):
        """Loads a brush by name (Preset or Custom)."""
        self.usePreset(name)

    @pyqtSlot(str, int, int, int, int, result=str)
    def sampleColorFromImage(self, image_path, x, y, displayed_width, displayed_height):
        """Allows QML to sample a color from an external image file (e.g. Reference Window)."""
        try:
            path = QUrl(image_path).toLocalFile() if "://" in image_path else image_path
            if not os.path.exists(path): return "#000000"
            
            # Load with QImage (fast C++ access)
            # Optimization: could cache this if called frequently for same image
            img = QImage(path)
            if img.isNull(): return "#000000"
            
            # Map displayed coordinates to actual image coordinates
            if displayed_width <= 0 or displayed_height <= 0: return "#000000"
            
            # Assuming 'PreserveAspectFit', we need to calculate the actual rect
            img_ratio = img.width() / img.height()
            display_ratio = displayed_width / displayed_height
            
            actual_w, actual_h = displayed_width, displayed_height
            offset_x, offset_y = 0, 0
            
            if img_ratio > display_ratio:
                # Image is wider than display area (fit by width)
                actual_w = displayed_width
                actual_h = displayed_width / img_ratio
                offset_y = (displayed_height - actual_h) / 2
            else:
                # Image is taller/same (fit by height)
                actual_h = displayed_height
                actual_w = displayed_height * img_ratio
                offset_x = (displayed_width - actual_w) / 2
            
            # Check if point is inside the image rect
            if x < offset_x or x > (offset_x + actual_w) or y < offset_y or y > (offset_y + actual_h):
                return "#000000" # Clicked on letterbox black bars
                
            # Normalize coordinates relative to image rect
            rel_x = (x - offset_x) / actual_w
            rel_y = (y - offset_y) / actual_h
            
            # Map to Source Pixels
            src_x = int(rel_x * img.width())
            src_y = int(rel_y * img.height())
            
            # Clamp
            src_x = max(0, min(src_x, img.width() - 1))
            src_y = max(0, min(src_y, img.height() - 1))
            
            # Get Color
            c = img.pixelColor(src_x, src_y)
            return c.name()
            
        except Exception as e:
            print(f"Sample Error: {e}")
            return "#000000"

    @pyqtSlot(str, result=int)
    def importABR(self, file_url):
        """
        Reads an .abr file, extracts brushes, and generates white masks with transparency.
        Restored from backup for robustness.
        """
        path = QUrl(file_url).toLocalFile() if "://" in file_url else file_url
        if not os.path.exists(path):
            print(f"Error: File not found at {path}")
            return 0

        try:
            print(f"--- STARTING ABR IMPORT: {os.path.basename(path)} ---")
            
            if not globals().get('HAS_PY_ABR', False):
                 print("Error: PyABRParser not available.")
                 return 0
                 
            parser_results = PyABRParser.parse(path)
            if not hasattr(parser_results, 'brushes'): return 0
                
            brushes_extracted = 0
            
            for i, brush_data in enumerate(parser_results.brushes):
                try:
                    # 1. Name Decoding
                    raw_name = getattr(brush_data, 'name', None)
                    if isinstance(raw_name, bytes):
                        try:
                            brush_name = raw_name.decode('utf-16-be', errors='ignore').strip().replace('\x00','')
                        except:
                            brush_name = raw_name.decode('latin-1', errors='ignore').strip().replace('\x00','')
                    else:
                        brush_name = str(raw_name) if raw_name else f"Brush {i+1}"

                    brush_name = brush_name.strip() or f"Brush {i+1}"

                    final_name = brush_name
                    dup_count = 1
                    while final_name in self._custom_brushes or final_name in self.BRUSH_PRESETS:
                        final_name = f"{brush_name} ({dup_count})"
                        dup_count += 1
                    
                    tip_image = brush_data.get_image()
                    if tip_image:
                        from PIL import Image, ImageOps, ImageStat
                        
                        mask = None
                        if tip_image.mode == 'RGBA':
                             alpha_ch = tip_image.split()[-1]
                             extrema = alpha_ch.getextrema()
                             if extrema[0] < extrema[1]: 
                                 mask = alpha_ch
                        
                        if mask is None:
                            mask = tip_image.convert("L")
                            if ImageStat.Stat(mask).mean[0] > 128:
                                mask = ImageOps.invert(mask)

                        mask = ImageOps.autocontrast(mask, cutoff=1)
                        new_rgba = Image.new("RGBA", mask.size, (255, 255, 255, 0))
                        new_rgba.putalpha(mask)

                        ptr = new_rgba.tobytes("raw", "RGBA")
                        qimg = QImage(ptr, new_rgba.width, new_rgba.height, QImage.Format.Format_RGBA8888).copy()

                        spacing = getattr(brush_data, 'spacing', 0.1)
                        if spacing > 1.0: spacing /= 100.0
                        spacing = max(0.02, min(1.0, spacing))

                        self._custom_brushes[final_name] = {
                            "is_custom": True, 
                            "category": os.path.basename(path).replace(".abr", ""),
                            "size": getattr(brush_data, 'size', 100), 
                            "opacity": 1.0,
                            "hardness": 0.8,
                            "smoothing": 0.2,
                            "spacing": spacing,
                            "cached_stamp": qimg
                        }
                        brushes_extracted += 1
                        print(f"Imported Brush: {final_name}")

                except Exception as e:
                    print(f"Error importing specific brush {i}: {e}")
                    continue

            print(f"--- IMPORT FINISHED: {brushes_extracted} brushes imported. ---")
            
            if brushes_extracted > 0:
                self._current_brush_name = final_name # Select last imported
                self._update_available_brushes() # Refresh QML list
                
            return brushes_extracted

        except Exception as e:
            print(f"Global ABR Import Error: {e}")
            return 0


    def _update_available_brushes(self):
        self._available_brushes = list(self.BRUSH_PRESETS.keys()) + list(self._custom_brushes.keys())
        print(f"DEBUG: Available brushes updated. Total: {len(self._available_brushes)}", flush=True)
        self.availableBrushesChanged.emit()

    # Legacy properties moved to appropriate sections



    @pyqtSlot(int, result=bool)
    def isLayerClipped(self, index):
        """Returns whether a layer is currently clipped."""
        if 0 <= index < len(self.layers):
            return self.layers[index].clipped
        return False

    @pyqtSlot()
    def flattenCanvas(self):
        """Flattens all layers into the background."""
        if len(self.layers) <= 1: return
        
        bg = self.layers[0]
        p = QPainter(bg.image)
        for i in range(1, len(self.layers)):
            layer = self.layers[i]
            if not layer.visible: continue
            p.setCompositionMode(layer.blend_mode)
            p.setOpacity(layer.opacity)
            p.drawImage(0, 0, layer.image)
        p.end()
        
        self.layers = [bg]
        self._active_layer_index = 0
        self.emit_layers_update()
        self.update()

    @pyqtSlot()
    def fitToView(self):
        """Centers and scales the canvas to fit within the current view dimensions."""
        if not self.layers: return
        
        view_w, view_h = self.width(), self.height()
        canvas_w, canvas_h = self.canvasWidth, self.canvasHeight
        
        if view_w <= 0 or view_h <= 0: return
        
        # Calculate best zoom to fit (with 15% padding)
        padding = 0.85
        zoom_w = (view_w / canvas_w) * padding
        zoom_h = (view_h / canvas_h) * padding
        self.zoomLevel = min(zoom_w, zoom_h)
        
        # Center the canvas
        # offset = (view_size - (canvas_size * zoom)) / 2
        off_x = (view_w - (canvas_w * self._zoom_level)) / 2
        off_y = (view_h - (canvas_h * self._zoom_level)) / 2
        self.viewOffset = QPointF(off_x, off_y)

    @pyqtSlot(int, int)
    def resizeCanvas(self, w, h):
        """Resizes the actual drawing area and fits it to view."""
        w, h = int(w), int(h)
        print(f"Resizing canvas to {w}x{h}")
        self._canvas_width = w
        self._canvas_height = h
        
        # Reset Project Metadata to prevent overwriting previous ones
        self._current_project_name = "Untitled"
        self._current_project_path = ""
        self.currentProjectNameChanged.emit()
        self.currentProjectPathChanged.emit()

        self.layers = []
        
        # Background layer
        bg = Layer(w, h, "Background", type="background")
        bg.image.fill(QColor(self._fill_color))
        bg.locked = True
        self.layers.append(bg)
        
        # Initial Drawing Layer
        l1 = Layer(w, h, "Layer 1")
        self.layers.append(l1)
        self._active_layer_index = 1
        
        self.emit_layers_update()
        self.update()

    @pyqtSlot(QColor)
    def setBackgroundColor(self, color):
        """Sets the background fill color and updates the background layer."""
        self._fill_color = color.name()
        if self.layers and self.layers[0].type == "background":
            self.layers[0].image.fill(color)
            self.update()

    @pyqtSlot(int)
    def setProjectDpi(self, dpi):
        """Sets the project DPI metadata."""
        self._project_dpi = dpi
        # print(f"Project DPI set to: {dpi}")

    @pyqtSlot(int, str, 'QVariantMap')
    def applyEffect(self, index, effect_type, params):
        """Applies a professional effect to a layer using OpenCV (the Skia-like effect gallery)."""
        if index < 0 or index >= len(self.layers): return
        layer = self.layers[index]
        if layer.locked: return

        # Bridge: QImage -> Numpy (OpenCV)
        # Format is ARGB32. In OpenCV it's usually BGRA
        try:
            width, height = layer.image.width(), layer.image.height()
            ptr = layer.image.bits()
            ptr.setsize(height * width * 4)
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4)).copy()
            
            if effect_type == "gaussian_blur":
                sigma = params.get("sigma", 5)
                if sigma > 0:
                    arr = cv2.GaussianBlur(arr, (0, 0), sigma)
            
            elif effect_type == "hsl":
                # OpenCV handles BGR/HSV better. 
                # Our array is BGRA (on Windows) or RGBA. Format_ARGB32 is usually BGRA internally on Little Endian.
                h_adj = params.get("hue", 0) # -180 to 180
                s_adj = params.get("saturation", 1.0) # 0 to 2
                l_adj = params.get("lightness", 1.0) # 0 to 2
                
                # Split alpha
                alpha = arr[:, :, 3].copy()
                bgr = arr[:, :, 0:3].copy()
                hls = cv2.cvtColor(bgr, cv2.COLOR_BGR2HLS).astype(np.float32)
                
                hls[:, :, 0] = np.mod(hls[:, :, 0] + h_adj/2.0, 180.0)
                hls[:, :, 1] = np.clip(hls[:, :, 1] * l_adj, 0, 255)
                hls[:, :, 2] = np.clip(hls[:, :, 2] * s_adj, 0, 255)
                
                bgr = cv2.cvtColor(hls.astype(np.uint8), cv2.COLOR_HLS2BGR)
                arr[:, :, 0:3] = bgr
                arr[:, :, 3] = alpha

            elif effect_type == "sharpen":
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                arr = cv2.filter2D(arr, -1, kernel)

            # Bridge: Numpy -> QImage
            new_img = QImage(arr.data, width, height, width * 4, QImage.Format.Format_ARGB32).copy()
            layer.image = new_img
            self.update()
            self.emit_layers_update()
            
        except Exception as e:
            print(f"Effect Error: {e}")
        
        # Initial empty layer
        self.layers.append(Layer(w, h, "Layer 1"))
        
        self._active_layer_index = 1
        self.canvasWidthChanged.emit(w)
        self.canvasHeightChanged.emit(h)
        
        self.fitToView()
        self.emit_layers_update()
        self.update()

    @pyqtSlot(str, result=bool)
    def saveProject(self, project_name_or_path):
        """Saves project. If it's a full path (starting with file:/// or drive letter), uses that. 
           Otherwise defaults to Documents/ArtFlowProjects."""
        path = project_name_or_path
        if path.startswith("file:///"):
            path = QUrl(path).toLocalFile()
        elif path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        
        # Windows patch
        if os.name == 'nt' and path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path.lstrip("/")
            
        # If it's a .png or .jpg (Sketchbook page), we save it as a flattened image
        if path.lower().endswith((".png", ".jpg", ".jpeg")):
            print(f"Sketchbook page detected: saving as flat image to {path}", flush=True)
            try:
                # Create composite image
                composite = QImage(int(self.canvasWidth), int(self.canvasHeight), QImage.Format.Format_ARGB32_Premultiplied)
                composite.fill(Qt.GlobalColor.white) # White bg
                p = QPainter(composite)
                for layer in self.layers:
                    if layer.visible:
                        p.setCompositionMode(layer.blend_mode)
                        p.setOpacity(layer.opacity)
                        p.drawImage(0, 0, layer.image)
                p.end()
                return composite.save(path)
            except Exception as e:
                print(f"Error saving sketchbook page: {e}")
                return False

        # If just a name is given, save to default legacy folder structure (for auto-save/quick save)
        # OR if it doesn't end in .aflow, assume it's a quick save name.
        if not os.path.isabs(path) and not path.lower().endswith(".aflow"):
            home = os.path.expanduser("~")
            projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
            os.makedirs(projects_dir, exist_ok=True)
            # Default new projects to .aflow format (Single File)
            if not path.lower().endswith(".aflow"):
                path += ".aflow"
            
            # UNIQUE NAME LOGIC: If path exists and it's a "quick save" from a new canvas,
            # don't overwrite Untitled.aflow, instead increment.
            if os.path.exists(os.path.join(projects_dir, path)) and self._current_project_path == "":
                 base = path.replace(".aflow", "")
                 i = 1
                 while os.path.exists(os.path.join(projects_dir, f"{base}_{i}.aflow")):
                     i += 1
                 path = f"{base}_{i}.aflow"

            path = os.path.join(projects_dir, path)

            
        if self._is_saving:
             print("Save already in progress, skipping...", flush=True)
             return False
        
        self._is_saving = True
        try:
            with self._timelapse_lock:
                 return self._save_internal(path)
        finally:
            self._is_saving = False

    @pyqtSlot(str, result=bool)
    def saveProjectAs(self, file_url):
        """Save project as .aflow file from File Dialog, or export as PSD."""
        path = QUrl(file_url).toLocalFile()
        
        # Check based on extension
        if path.lower().endswith(".psd"):
            print("Saving as PSD (Exporting flattened image)...")
            return self.exportImage(file_url, "PSD")
            
        # Default to .aflow if no extension or unknown
        if not path.lower().endswith(".aflow") and not path.lower().endswith(".psd"):
            path += ".aflow"
            
        if self._is_saving:
             print("Save already in progress, skipping...", flush=True)
             return False
             
        self._is_saving = True
        try:
            with self._timelapse_lock:
                 return self._save_internal(path)
        finally:
            self._is_saving = False

    def _save_internal(self, path):
        """Internal save logic supporting both Folder (Legacy) and Zip (.aflow)."""
        try:
            self._current_project_name = os.path.basename(path).replace(".aflow", "")
            self.currentProjectNameChanged.emit()
            
            self._current_project_path = path
            self.currentProjectPathChanged.emit()
            
            # Prepare Metadata
            metadata = {
                "version": "1.0",
                "width": self.canvasWidth,
                "height": self.canvasHeight,
                "created": datetime.now().isoformat(),
                "layers": []
            }
            
            # Prepare Layer Data
            layer_buffers = []
            for i, layer in enumerate(self.layers):
                # Save image to buffer
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                layer.image.save(buf, "PNG")
                filename = f"layer_{i}.png"
                layer_buffers.append((filename, bytes(ba)))
                print(f"  - Prepared buffer for layer {i} ({len(ba)} bytes)", flush=True)
                
                metadata["layers"].append({
                    "index": i,
                    "name": layer.name,
                    "type": layer.type,
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "blend_mode": self.BLEND_MODES_INV.get(layer.blend_mode, "Normal"),
                    "depth": layer.depth,
                    "expanded": layer.expanded,
                    "locked": layer.locked,
                    "alpha_lock": layer.alpha_lock,
                    "clipped": layer.clipped,
                    "alpha_lock": layer.alpha_lock,
                    "clipped": layer.clipped,
                    "is_private": layer.is_private,
                    "filename": filename
                })
            print(f"Prepared {len(layer_buffers)} layer buffers.", flush=True)

            # Create Preview
            preview_ba = QByteArray()
            preview_buf = QBuffer(preview_ba)
            preview_buf.open(QIODevice.OpenModeFlag.WriteOnly)
            
            preview_img = QImage(int(self.canvasWidth), int(self.canvasHeight), QImage.Format.Format_ARGB32)
            preview_img.fill(Qt.GlobalColor.white) # White bg for preview
            p = QPainter(preview_img)
            visible_layers_count = 0
            for layer in self.layers:
                if layer.visible:
                    p.setCompositionMode(layer.blend_mode)
                    p.setOpacity(layer.opacity)
                    p.drawImage(0, 0, layer.image)
                    visible_layers_count += 1
            p.end()
            preview_img.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio).save(preview_buf, "PNG")
            print(f"Preview image prepared: {visible_layers_count} visible layers, buffer size: {len(preview_ba)} bytes.", flush=True)

            # Determine Mode: Folder or Zip?
            if path.endswith(".aflow"):
                # ZIP MODE
                temp_zip_path = path + ".tmp"
                print(f"Starting ZIP creation to: {temp_zip_path}", flush=True)
                try:
                    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr("project.json", json.dumps(metadata, indent=4))
                        zf.writestr("preview.png", bytes(preview_ba))
                        for fname, data in layer_buffers:
                            zf.writestr(fname, data)
                            
                        # Save Timelapse Frames
                        print(f"Adding timelapse frames from: {self._timelapse_dir}", flush=True)
                        try:
                            with self._timelapse_lock:
                                if self._timelapse_dir and os.path.exists(self._timelapse_dir):
                                    frames = sorted([f for f in os.listdir(self._timelapse_dir) if f.endswith(".jpg")])
                                    for frame in frames:
                                        src_p = os.path.join(self._timelapse_dir, frame)
                                        target_p = f"timelapse/{frame}"
                                        if os.path.exists(src_p):
                                            zf.write(src_p, target_p)
                                            print(f"  - Added timelapse frame: {frame}", flush=True)
                                    if frames:
                                        print(f"Saved {len(frames)} timelapse frames to zip.", flush=True)
                                else:
                                    print("Timelapse directory not found or not set, skipping timelapse save.", flush=True)
                        except Exception as tle:
                            print(f"Timelapse save warning: {tle}", flush=True)
                    
                    # Success, move to final path
                    if os.path.exists(path):
                        print(f"Removing existing file at {path} for atomic save.", flush=True)
                        os.remove(path)
                    os.rename(temp_zip_path, path)
                    print(f"Project saved successfully to: {path}", flush=True)
                    return True
                except Exception as ze:
                    print(f"Zip creation error: {ze}", flush=True)
                    if os.path.exists(temp_zip_path):
                        try: 
                            os.remove(temp_zip_path)
                            print(f"Cleaned up temporary zip file: {temp_zip_path}", flush=True)
                        except Exception as cle:
                            print(f"Error cleaning up temporary zip file {temp_zip_path}: {cle}", flush=True)
                    return False
            else:
                # FOLDER MODE (Legacy)
                print(f"Starting FOLDER save to: {path}", flush=True)
                os.makedirs(path, exist_ok=True)
                with open(os.path.join(path, "project.json"), 'w') as f:
                    json.dump(metadata, f, indent=4)
                print("  - project.json written.", flush=True)
                with open(os.path.join(path, "preview.png"), 'wb') as f:
                    f.write(bytes(preview_ba))
                print("  - preview.png written.", flush=True)
                for fname, data in layer_buffers:
                    with open(os.path.join(path, fname), 'wb') as f:
                        f.write(data)
                    print(f"  - {fname} written.", flush=True)

                # Save Timelapse Frames (Folder Mode)
                print(f"Adding timelapse frames from: {self._timelapse_dir}", flush=True)
                tl_dir = os.path.join(path, "timelapse")
                os.makedirs(tl_dir, exist_ok=True)
                try:
                     with self._timelapse_lock:
                         if self._timelapse_dir and os.path.exists(self._timelapse_dir):
                             frames = sorted([f for f in os.listdir(self._timelapse_dir) if f.endswith(".jpg")])
                             for frame in frames:
                                 src_p = os.path.join(self._timelapse_dir, frame)
                                 target_p = os.path.join(tl_dir, frame)
                                 if os.path.exists(src_p):
                                     shutil.copy2(src_p, target_p)
                                     print(f"  - Added timelapse frame: {frame}", flush=True)
                     print(f"Saved timelapse frames to folder: {tl_dir}", flush=True)
                except Exception as tle:
                     print(f"Timelapse save warning (Folder Mode): {tle}", flush=True)

                print(f"Project saved successfully to: {path}", flush=True)
                return True
            
        except Exception as e:
            print(f"Error saving project: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    @pyqtSlot(str, result=bool)
    def exportImage(self, file_url, format_str):
        """Export the current canvas as a flat image (PNG/JPG)."""
        try:
            path = QUrl(file_url).toLocalFile()
            
            # Create flattened image
            flat_img = QImage(int(self.canvasWidth), int(self.canvasHeight), QImage.Format.Format_ARGB32)
            
            # Fill background?
            # If JPG, we need white background. If PNG, transparent (unless bg is white).
            # Our canvas has a background layer usually.
            flat_img.fill(Qt.GlobalColor.transparent)
            
            p = QPainter(flat_img)
            # Iterate layers
            for layer in self.layers:
                if layer.visible:
                    p.setCompositionMode(layer.blend_mode)
                    p.setOpacity(layer.opacity)
                    p.drawImage(0, 0, layer.image)
            p.end()
            
            if format_str.upper() in ["JPG", "JPEG"]:
                # Composite over white for JPG
                bg = QImage(flat_img.size(), QImage.Format.Format_RGB32)
                bg.fill(Qt.GlobalColor.white)
                p = QPainter(bg)
                p.drawImage(0, 0, flat_img)
                p.end()
                success = bg.save(path, "JPG", 90)
            elif format_str.upper() == "PSD":
                # Save as flattened PSD (using simple write support if available in Qt or just save as PNG/BMP disguised?
                # Actually Qt doesn't support writing PSD natively.
                # We can use minimal coding or just save as TIFF/PNG and rename? No that's bad.
                # Use PIL if easier?
                try:
                    from PIL import Image
                    # Convert QImage to PIL
                    buf = QBuffer()
                    buf.open(QIODevice.OpenModeFlag.ReadWrite)
                    flat_img.save(buf, "PNG")
                    buf.seek(0)
                    pil_img = Image.open(io.BytesIO(buf.data()))
                    pil_img.save(path, "PSD")
                    success = True
                except ImportError:
                    print("PIL (Pillow) not installed. Cannot save PSD.")
                    success = False
                except Exception as ex:
                    print(f"PSD Export error: {ex}")
                    success = False
            else:
                success = flat_img.save(path, "PNG")
                
            return success
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def _scan_projects_thread(self):
        """Worker thread to scan projects without blocking UI."""
        projects = []
        try:
            home = os.path.expanduser("~")
            projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
            if not os.path.exists(projects_dir):
                self.projectsLoaded.emit([])
                return
            
            # List both directories and .aflow files
            entries = list(os.scandir(projects_dir))
            all_entries = sorted(entries, key=lambda e: e.stat().st_mtime, reverse=True)
            
            # Optimization: Limit to top 20 recent projects
            all_entries = all_entries[:20]

            for entry in all_entries:
                try:
                    # Skip files larger than 50MB during quick scan to avoid freeze
                    if entry.is_file() and entry.stat().st_size > 50 * 1024 * 1024:
                         continue

                    meta = {}
                    preview_path = ""
                    
                    if entry.is_dir():
                        json_path = os.path.join(entry.path, "project.json")
                        img_p = os.path.join(entry.path, "preview.png")
                        if os.path.exists(json_path):
                            with open(json_path, 'r') as f:
                                meta = json.load(f)
                            if os.path.exists(img_p):
                                mtime = entry.stat().st_mtime
                                preview_path = "file:///" + img_p.replace("\\", "/") + f"?t={mtime}"
                                
                    elif entry.is_file() and entry.name.endswith(".aflow"):
                        # Read zip metadata
                        # Wrap in try-except block for bad zips
                         try:
                            with zipfile.ZipFile(entry.path, 'r') as zf:
                                with zf.open("project.json") as f:
                                    meta = json.load(f)
                                
                                import tempfile
                                temp_dir = os.path.join(tempfile.gettempdir(), "ArtFlowPreviews")
                                os.makedirs(temp_dir, exist_ok=True)
                                temp_preview = os.path.join(temp_dir, entry.name + ".png")
                                
                                mtime = entry.stat().st_mtime
                                if not os.path.exists(temp_preview) or os.path.getmtime(temp_preview) < mtime:
                                    try:
                                        with zf.open("preview.png") as src, open(temp_preview, "wb") as dst:
                                            dst.write(src.read())
                                    except KeyError:
                                        pass # No preview
                                        
                                preview_path = "file:///" + temp_preview.replace("\\", "/") + f"?t={mtime}"
                         except (zipfile.BadZipFile, OSError):
                             print(f"Skipping corrupted project file: {entry.name}")
                             continue

                    if meta:
                        projects.append({
                            "name": meta.get("name", entry.name.replace(".aflow", "")),
                            "fileName": entry.name,
                            "width": meta.get("width", 1920),
                            "height": meta.get("height", 1080),
                            "preview": preview_path,
                            "path": "file:///" + entry.path.replace("\\", "/"),
                            "created": meta.get("created", ""),
                            "type": meta.get("type", "drawing"),
                            "title": meta.get("title", entry.name.replace(".aflow", "")),
                            "cover_color": meta.get("cover_color", "#1c1c1e")
                        })
                except Exception as ex:
                    print(f"Skipping entry {entry.name}: {ex}")
                    continue
                    
        except Exception as e:
            print(f"Error listing projects: {e}")
            
        # Emit result back to main thread
        self.projectsLoaded.emit(projects)

    @pyqtSlot()
    def loadRecentProjectsAsync(self):
        """Loads projects in a separate thread."""
        if not hasattr(self, "_current_gallery_path"):
            home = os.path.expanduser("~")
            self._current_gallery_path = os.path.join(home, "Documents", "ArtFlowProjects")
            
        print(f"DEBUG: Scanning gallery path: {self._current_gallery_path}")
        self._projects_thread = threading.Thread(target=self._scan_projects_worker)
        self._projects_thread.start()

    def _scan_projects_worker(self):
        try:
            projects = self.get_project_list()
            self.projectsLoaded.emit(projects)
        except Exception as e:
            print(f"Error scanning projects: {e}")
            self.projectsLoaded.emit([])

    @pyqtSlot(result=list)
    def getRecentProjects(self):
        """
        Función requerida por DashboardView.qml.
        Devuelve los 5 proyectos más recientes.
        """
        # Llamamos a la función principal que ya busca y ordena
        try:
            full_list = self.get_project_list()
            if not full_list:
                return []
            return full_list[:5]
        except Exception as e:
            print(f"Error in getRecentProjects: {e}")
            return []

    # --- GESTIÓN DE GALERÍA Y SKETCHBOOKS (Restored & Integrated) ---

    @pyqtSlot(result=list)
    def get_project_list(self):
        """
        Escanea la carpeta de proyectos.
        IMPORTANTE: Siempre debe devolver una lista [], nunca None.
        """
        projects = []
        try:
            if not hasattr(self, "_projects_dir"):
                home = os.path.expanduser("~")
                self._projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
                
            if not os.path.exists(self._projects_dir):
                os.makedirs(self._projects_dir, exist_ok=True)

            print("--- ESCANEANDO PROYECTOS ---")

            for entry in os.scandir(self._projects_dir):
                try:
                    # 1. RUTA BASE LIMPIA (Para abrir el archivo)
                    clean_path = entry.path.replace("\\", "/")
                    
                    # 2. RUTA URL (Para que QML muestre la imagen)
                    url_path = f"file:///{clean_path}" 
                    
                    item = {
                        "name": entry.name,
                        "path": clean_path, 
                        "preview": url_path, # Por defecto, el mismo archivo es su preview
                        "date": entry.stat().st_mtime,
                        "title": entry.name,
                        "thumbnails": [], # Lista vacía por defecto
                        "type": "drawing" # Por defecto
                    }
                
                    if entry.is_dir():
                        # Intentar leer metadatos de Carpeta o Sketchbook
                        meta_path = os.path.join(entry.path, "meta.json")
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    item.update(data)
                            except: pass
                        else:
                            item["type"] = "folder"
                    
                        # BUSCAR IMÁGENES DENTRO PARA EL EFECTO "STACK"
                        try:
                            # Buscamos archivos dentro (PNG o AFLOW)
                            with os.scandir(entry.path) as subentries:
                                files = sorted([s for s in subentries if s.is_file() and s.name.lower().endswith(('.aflow', '.png', '.jpg', '.jpeg'))], 
                                              key=lambda x: x.stat().st_mtime, reverse=True)
                            
                            if len(files) > 0:
                                # La primera imagen es la portada
                                first_entry = files[0]
                                if first_entry.name.endswith(".aflow"):
                                    try:
                                        temp_preview = os.path.join(tempfile.gettempdir(), "ArtFlowPreviews", first_entry.name + ".png")
                                        if not os.path.exists(temp_preview) or os.path.getmtime(temp_preview) < first_entry.stat().st_mtime:
                                            os.makedirs(os.path.dirname(temp_preview), exist_ok=True)
                                            with zipfile.ZipFile(first_entry.path, 'r') as zf:
                                                with zf.open("preview.png") as src, open(temp_preview, "wb") as dst:
                                                    dst.write(src.read())
                                        item["preview"] = "file:///" + temp_preview.replace("\\", "/")
                                    except: pass
                                else:
                                    item["preview"] = "file:///" + first_entry.path.replace("\\", "/")

                                # Llenar thumbnails (Max 3)
                                for f_entry in files[:3]:
                                    p_path = ""
                                    if f_entry.name.endswith(".aflow"):
                                        try:
                                            temp_preview = os.path.join(tempfile.gettempdir(), "ArtFlowPreviews", f_entry.name + ".png")
                                            if not os.path.exists(temp_preview) or os.path.getmtime(temp_preview) < f_entry.stat().st_mtime:
                                                os.makedirs(os.path.dirname(temp_preview), exist_ok=True)
                                                with zipfile.ZipFile(f_entry.path, 'r') as zf:
                                                    with zf.open("preview.png") as src, open(temp_preview, "wb") as dst:
                                                        dst.write(src.read())
                                            p_path = "file:///" + temp_preview.replace("\\", "/")
                                        except: pass
                                    else:
                                        p_path = "file:///" + f_entry.path.replace("\\", "/")
                                    if p_path: item["thumbnails"].append(p_path)
                            else:
                                item["preview"] = ""
                        except Exception as e:
                            print(f"Error leyendo carpeta {entry.name}: {e}")
                    
                    else:
                        # Archivo suelto
                        if entry.name.endswith(".json"): continue
                        if not entry.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            # Si es .aflow, intentar extraer preview
                            if entry.name.endswith(".aflow"):
                                try:
                                    temp_preview = os.path.join(tempfile.gettempdir(), "ArtFlowPreviews", entry.name + ".png")
                                    if not os.path.exists(temp_preview) or os.path.getmtime(temp_preview) < entry.stat().st_mtime:
                                        os.makedirs(os.path.dirname(temp_preview), exist_ok=True)
                                        with zipfile.ZipFile(entry.path, 'r') as zf:
                                            with zf.open("preview.png") as src, open(temp_preview, "wb") as dst:
                                                dst.write(src.read())
                                    item["preview"] = "file:///" + temp_preview.replace("\\", "/")
                                except: 
                                    item["preview"] = ""
                            else:
                                # Buscar un .png con el mismo nombre
                                thumb_candidate = os.path.splitext(entry.path)[0] + ".png"
                                if os.path.exists(thumb_candidate):
                                    item["preview"] = f"file:///{thumb_candidate.replace('\\', '/')}"
                                else:
                                    item["preview"] = ""
                    
                    projects.append(item)
                except Exception as e:
                    print(f"Error processing {entry.name}: {e}")
        except Exception as e:
            print(f"Error in get_project_list: {e}")
            return []

        return sorted(projects, key=lambda x: x['date'], reverse=True)
                
    @pyqtSlot(str, str, result=bool)
    def create_folder_from_merge(self, path_item_dropped, path_item_target):
        """Combina dos proyectos en una carpeta nueva."""
        try:
            # Clean paths
            if path_item_dropped.startswith("file:///"): path_item_dropped = QUrl(path_item_dropped).toLocalFile()
            if path_item_target.startswith("file:///"): path_item_target = QUrl(path_item_target).toLocalFile()
            
            # Windows patch
            if os.name == 'nt':
                if path_item_dropped.startswith("/") and ":" in path_item_dropped: path_item_dropped = path_item_dropped.lstrip("/")
                if path_item_target.startswith("/") and ":" in path_item_target: path_item_target = path_item_target.lstrip("/")

            # 1. Crear carpeta física
            group_name = "Group " + datetime.now().strftime("%H%M%S")
            group_path = os.path.join(self._projects_dir, group_name)
            os.makedirs(group_path, exist_ok=True)
            
            # 2. Mover archivos
            name_dropped = os.path.basename(path_item_dropped)
            name_target = os.path.basename(path_item_target)
            
            shutil.move(path_item_dropped, os.path.join(group_path, name_dropped))
            shutil.move(path_item_target, os.path.join(group_path, name_target))
            
            # 3. Crear meta.json
            meta = {"type": "folder", "title": group_name, "cover_color": "#1c1c1e"}
            with open(os.path.join(group_path, "meta.json"), "w", encoding='utf-8') as f:
                json.dump(meta, f, indent=4)
                
            self.loadRecentProjectsAsync()
            return True
        except Exception as e:
            print(f"Error merging: {e}")
            import traceback
            traceback.print_exc()
            return False

    @pyqtSlot(str, str, result=str)
    def create_new_sketchbook(self, title, cover_color):
        """Crea un directorio con estructura de Sketchbook."""
        safe_name = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip()
        
        # Ensure we have a valid path
        if not hasattr(self, "_current_gallery_path"):
            home = os.path.expanduser("~")
            self._current_gallery_path = os.path.join(home, "Documents", "ArtFlowProjects")
            
        folder_path = os.path.join(self._current_gallery_path, safe_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        # Crear metadatos
        meta = {
            "type": "sketchbook",
            "title": title,
            "created_at": time.time(),
            "cover_color": cover_color,
            "pages": [] # Lista vacía de páginas
        }
        
        with open(os.path.join(folder_path, "meta.json"), 'w', encoding='utf-8') as f:
            json.dump(meta, f)
            
        print(f"Sketchbook created at: {folder_path}")
        self.loadRecentProjectsAsync() # Refresh UI
        return folder_path
            


    @pyqtSlot(str, result=bool)
    def enter_folder(self, path):
        """Navigates into a folder in the gallery."""
        if path.startswith("file:///"): path = QUrl(path).toLocalFile()
        if os.path.isdir(path):
            self._current_gallery_path = path
            self.loadRecentProjectsAsync()
            return True
        return False

    @pyqtSlot(result=bool)
    def go_back_gallery(self):
        """Navigates up one level in the gallery."""
        home = os.path.expanduser("~")
        base_dir = os.path.join(home, "Documents", "ArtFlowProjects")
        
        if self._current_gallery_path == base_dir:
            return False
            
        parent = os.path.dirname(self._current_gallery_path)
        if os.path.exists(parent):
            self._current_gallery_path = parent
            self.loadRecentProjectsAsync()
            return True
        return False

    @pyqtSlot(str)
    def load_file_path(self, file_path):
        """Carga una imagen o proyecto en el lienzo principal."""
        if file_path.startswith("file:///"): file_path = QUrl(file_path).toLocalFile()
        # Windows patch
        if os.name == 'nt' and file_path.startswith("/") and ":" in file_path:
             file_path = file_path.lstrip("/")
             
        if not os.path.exists(file_path):
            print(f"Error: Archivo no encontrado {file_path}")
            return

        # CHECK FOR PROJECT FORMATS (Folder, .aflow, .psd)
        if os.path.isdir(file_path) or file_path.lower().endswith((".aflow", ".psd")):
            print(f"Detected project file: {file_path}. Delegating to loadProject...", flush=True)
            self.loadProject(file_path)
            return

        # Limpiar capas actuales
        self.layers = []
        
        # Cargar imagen usando QImage
        loaded_image = QImage(file_path)
        if loaded_image.isNull():
            print("Error cargando imagen")
            return
            
        # Convertir a formato editable (ARGB32)
        loaded_image = loaded_image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        
        # Crear capa base con esa imagen
        new_layer = Layer(loaded_image.width(), loaded_image.height())
        new_layer.image = loaded_image
        new_layer.name = "Background"
        
        self.layers.append(new_layer)
        self._active_layer_index = 0
        
        # Guardar ruta para saber dónde guardar después
        self._current_project_path = file_path 
        self._current_project_name = os.path.basename(file_path).replace(".aflow", "").replace(".png", "")
        self.currentProjectPathChanged.emit()
        self.currentProjectNameChanged.emit()
        
        self.update() # Refrescar visualización
        print(f"Cargado: {file_path}")

    @pyqtSlot()
    def save_current_work(self):
        """Guarda los cambios en el archivo abierto actualmente."""
        if hasattr(self, 'current_file_path') and self.layers and self.current_file_path:
            # Simplificación: guardar la primera capa (o composición)
            # Para producción deberíamos componer todas las capas visibles
            
            # Create a composite image
            final_image = QImage(self.layers[0].image.size(), QImage.Format.Format_ARGB32_Premultiplied)
            final_image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(final_image)
            for layer in self.layers:
                if layer.visible:
                    painter.setOpacity(layer.opacity)
                    painter.drawImage(0, 0, layer.image)
            painter.end()
            
            final_image.save(self.current_file_path)
            print(f"Guardado automático en {self.current_file_path}")

    @pyqtSlot(str, result=list)
    def get_sketchbook_pages(self, sketchbook_path):
        """Devuelve la lista de páginas (imágenes) dentro de un sketchbook."""
        if sketchbook_path.startswith("file:///"): sketchbook_path = QUrl(sketchbook_path).toLocalFile()
        # Windows patch
        if os.name == 'nt' and sketchbook_path.startswith("/") and ":" in sketchbook_path:
             sketchbook_path = sketchbook_path.lstrip("/")
             
        if not os.path.exists(sketchbook_path):
            return []
            
        pages = []
        # Buscar imágenes en el directorio
        with os.scandir(sketchbook_path) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg', '.aflow')):
                    if entry.name == "preview.png": continue # Skip cover preview if separated
                    
                    p_path = "file:///" + entry.path.replace("\\", "/")
                    
                    # If it is an .aflow file, we need to extract the internal preview.png
                    if entry.name.endswith(".aflow"):
                        try:
                            import tempfile
                            import zipfile
                            temp_dir = os.path.join(tempfile.gettempdir(), "ArtFlowPreviews")
                            os.makedirs(temp_dir, exist_ok=True)
                            temp_preview = os.path.join(temp_dir, entry.name + ".png")
                            if not os.path.exists(temp_preview) or os.path.getmtime(temp_preview) < entry.stat().st_mtime:
                                with zipfile.ZipFile(entry.path, 'r') as zf:
                                    with zf.open("preview.png") as src, open(temp_preview, "wb") as dst:
                                        dst.write(src.read())
                            p_path = "file:///" + temp_preview.replace("\\", "/")
                        except: pass

                    pages.append({
                        "name": entry.name,
                        "path": p_path,
                        "realPath": "file:///" + entry.path.replace("\\", "/"), # To open the actual file
                        "date": entry.stat().st_mtime
                    })
                     
        # Ordenar por nombre o fecha
        return sorted(pages, key=lambda x: x['name'])

    @pyqtSlot(str, str, result=str)
    def create_new_page(self, sketchbook_path, page_name="Page"):
        """Crea una nueva página en blanco dentro del sketchbook."""
        if sketchbook_path.startswith("file:///"): sketchbook_path = QUrl(sketchbook_path).toLocalFile()
        # Windows patch
        if os.name == 'nt' and sketchbook_path.startswith("/") and ":" in sketchbook_path:
             sketchbook_path = sketchbook_path.lstrip("/")
             
        if not os.path.exists(sketchbook_path):
             return ""
             
        # Add timestamp to avoid collisions
        filename = f"{page_name}_{int(time.time())}.png"
        full_path = os.path.join(sketchbook_path, filename)
        
        # Create blank white image (e.g. A4 size or screen size)
        img = QImage(2000, 2000, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.white)
        img.save(full_path)
        
        return "file:///" + full_path.replace("\\", "/")

    @pyqtSlot(str, str, result=bool)
    def create_folder_from_merge(self, path_item_dropped, path_item_target):
        """Lógica 'Drag & Drop': Crea una carpeta y mueve ambos proyectos dentro."""
        # Clean URLs if they come from QML
        if path_item_dropped.startswith("file:///"): path_item_dropped = QUrl(path_item_dropped).toLocalFile()
        if path_item_target.startswith("file:///"): path_item_target = QUrl(path_item_target).toLocalFile()
        
        # Windows patch
        if os.name == 'nt':
            if path_item_dropped.startswith("/") and len(path_item_dropped) > 2 and path_item_dropped[2] == ":":
                path_item_dropped = path_item_dropped[1:]
            if path_item_target.startswith("/") and len(path_item_target) > 2 and path_item_target[2] == ":":
                path_item_target = path_item_target[1:]
        
        # Force use of current gallery path
        if not hasattr(self, "_current_gallery_path"):
            home = os.path.expanduser("~")
            self._current_gallery_path = os.path.join(home, "Documents", "ArtFlowProjects")

        if not os.path.exists(path_item_dropped) or not os.path.exists(path_item_target):
            print(f"Merge error: one or more paths do not exist. Dropped: {path_item_dropped}, Target: {path_item_target}")
            return False
            
        if path_item_dropped == path_item_target:
            return False

        # 1. Crear nombre de carpeta "Grupo Nuevo"
        group_name = "Group " + datetime.now().strftime("%Y%m%d_%H%M%S")
        group_path = os.path.join(self._current_gallery_path, group_name)
        os.makedirs(group_path, exist_ok=True)
        
        # 2. Mover los archivos originales dentro
        try:
            shutil.move(path_item_dropped, group_path)
            shutil.move(path_item_target, group_path)
            
            # 3. Crear meta.json para la carpeta
            meta = {
                "type": "folder",
                "title": group_name,
                "cover_color": "#95a5a6"
            }
            with open(os.path.join(group_path, "meta.json"), "w", encoding='utf-8') as f:
                json.dump(meta, f)
                
            return True
        except Exception as e:
            print(f"Error creando carpeta: {e}")
            return False

    @pyqtSlot(str, result=bool)
    def loadProject(self, file_url):
        """Loads a project from folder or .aflow zip."""
        try:
            path = QUrl(file_url).toLocalFile()
            if not os.path.exists(path):
                # Try raw path just in case
                if os.path.exists(file_url): path = file_url
                else: 
                     # Check relative path
                    if not os.path.isabs(path):
                         home = os.path.expanduser("~")
                         projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
                         check_path = os.path.join(projects_dir, path)
                         if os.path.exists(check_path): path = check_path
                         elif os.path.exists(check_path + ".aflow"): path = check_path + ".aflow"
                         else:
                            print(f"Project not found: {path} (and checked {check_path})")
                            return False
                    else:
                        print(f"Project not found: {path}")
                        return False
            
            meta = {}
            layer_images = {} # map filename -> QImage
            
            if os.path.isdir(path):
                # Legacy Folder
                json_path = os.path.join(path, "project.json")
                with open(json_path, 'r') as f:
                    meta = json.load(f)
                
                for lm in meta.get("layers", []):
                    fname = lm.get("filename", "")
                    img_path = os.path.join(path, fname)
                    if os.path.exists(img_path):
                        img = QImage(img_path)
                        layer_images[fname] = img
                        
            elif zipfile.is_zipfile(path):
                # .aflow File
                with zipfile.ZipFile(path, 'r') as zf:
                    with zf.open("project.json") as f:
                        meta = json.load(f)

                    # Extract Timelapse Frames to temp dir for continuity
                    try:
                        # Clear current temp dir first
                        if self._timelapse_dir and os.path.exists(self._timelapse_dir):
                            for f in os.listdir(self._timelapse_dir):
                                try: 
                                    fp = os.path.join(self._timelapse_dir, f)
                                    # Retry loop for file deletion
                                    for _ in range(3):
                                        try:
                                            os.remove(fp)
                                            break
                                        except OSError:
                                            import time
                                            time.sleep(0.01)
                                except Exception as e: 
                                    print(f"Cleanup error: {e}")
                        
                        else:
                            # Re-init if missing
                             try:
                                 import tempfile
                                 import time
                                 self._timelapse_dir = os.path.join(tempfile.gettempdir(), "ArtFlow_Timelapse_" + str(int(time.time())))
                                 os.makedirs(self._timelapse_dir, exist_ok=True)
                             except Exception as e:
                                 print(f"Error re-initializing timelapse dir: {e}")
                            
                        # Extract loop
                        frames_found = 0
                        for member in zf.namelist():
                            if member.startswith("timelapse/") and member.endswith(".jpg"):
                                target_name = os.path.basename(member) # frame_XXXXX.jpg
                                if target_name:
                                    with zf.open(member) as src, open(os.path.join(self._timelapse_dir, target_name), "wb") as dst:
                                        dst.write(src.read())
                                    frames_found += 1
                        
                        if frames_found > 0:
                            print(f"Restored {frames_found} timelapse frames.")
                            self._timelapse_counter = frames_found
                        else:
                            self._timelapse_counter = 0

                    except Exception as tle:
                        print(f"Timelapse restore warning: {tle}")
                    
                    for lm in meta.get("layers", []):
                        fname = lm.get("filename", "")
                        with zf.open(fname) as img_file:
                             data = img_file.read()
                             img = QImage.fromData(data)
                             layer_images[fname] = img
                             
            elif path.lower().endswith(".psd"):
                if not HAS_PSD_TOOLS:
                    print("PSD Tools not installed.")
                    return False
                return self._load_psd(path)

            # --- Reconstruction Logic (Common) ---
            print("Entering Reconstruction Logic...", flush=True)
            self._current_project_name = meta.get("name", os.path.basename(path).replace(".aflow", ""))
            self.currentProjectNameChanged.emit()
            
            self._current_project_path = path
            self.currentProjectPathChanged.emit()
            
            new_w = int(meta.get("width", 1920))
            new_h = int(meta.get("height", 1080))
            print(f"Canvas Size: {new_w}x{new_h}", flush=True)
            
            self._canvas_width = new_w
            self._canvas_height = new_h
            
            self.layers = []
            layer_data = meta.get("layers", [])
            print(f"Found {len(layer_data)} layers in metadata.", flush=True)
            
            for lm in layer_data:
                layer = Layer(new_w, new_h, lm.get("name", "Layer"), lm.get("type", "normal"))
                layer.visible = bool(lm.get("visible", True))
                layer.opacity = float(lm.get("opacity", 1.0))
                blend_name = lm.get("blend_mode", "Normal")
                layer.blend_mode = self.BLEND_MODES.get(blend_name, QPainter.CompositionMode.CompositionMode_SourceOver)
                layer.locked = bool(lm.get("locked", False))
                layer.alpha_lock = bool(lm.get("alpha_lock", False))
                layer.depth = int(lm.get("depth", 0))
                layer.clipped = bool(lm.get("clipped", False))
                layer.expanded = bool(lm.get("expanded", True))
                layer.is_private = bool(lm.get("is_private", False))
                
                fname = lm.get("filename", "")
                if fname in layer_images:
                    layer.image = layer_images[fname]
                    print(f"  - Loaded image for layer '{layer.name}': {layer.image.width()}x{layer.image.height()}", flush=True)
                else:
                    print(f"  - WARNING: No image found for layer '{layer.name}' (filename: {fname})", flush=True)
                
                self.layers.append(layer)
            
            if not self.layers: 
                print("No layers loaded, resetting canvas.", flush=True)
                self.reset_canvas()
            
            self._active_layer_index = 0
            self._undo_stack = []
            self._redo_stack = []
            
            print(f"Reconstruction complete. Total layers: {len(self.layers)}", flush=True)
            
            self.canvasWidthChanged.emit(new_w)
            self.canvasHeightChanged.emit(new_h)
            self.activeLayerChanged.emit(0)
            self.emit_layers_update()
            
            # Force update
            QTimer.singleShot(0, self.fitToView)
            self.update()
            return True
            
        except Exception as e:
            print(f"Error loading project: {e}")
            import traceback
            traceback.print_exc()
            return False
    @pyqtSlot(str, result=bool)
    def deleteProject(self, file_url):
        """Permanently deletes a project folder or file."""
        try:
            path = file_url
            if path.startswith("file:///"):
                path = QUrl(file_url).toLocalFile()
            elif ":" not in path[:3]: # Not an absolute path likely
                 path = QUrl(file_url).toLocalFile()
                 
            # Windows patch
            if os.name == 'nt' and path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path.lstrip("/")
                
            if not os.path.exists(path): 
                print(f"Delete error: path does not exist: {path}")
                return False
                
            import shutil
            import time
            
            for i in range(3):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    print(f"Project deleted: {path}")
                    return True
                except OSError as e:
                    print(f"OSError deleting (attempt {i+1}): {e}")
                    time.sleep(0.2)
            return False
        except Exception as e:
            print(f"Error deleting: {e}")
            return False

    def _load_psd(self, path):
        """Helper to load PSD files."""
        try:
            psd = PSDImage.open(path)
            
            new_w = psd.width
            new_h = psd.height
            self._canvas_width = new_w
            self._canvas_height = new_h
            
            self._canvas_height = new_h
            
            self._current_project_name = os.path.basename(path).replace(".psd", "")
            self.currentProjectNameChanged.emit()
            
            self._current_project_path = path
            self.currentProjectPathChanged.emit()
            
            self.layers = []
            
            # Recursive function to process layers
            def process_layers(layers_list, depth=0):
                # Iterate in standard order (top to bottom usually in PSD iterator?)
                # We want Bottom to Top for our painter, but PSD list is usually Top to Bottom.
                # So we will reverse the list processing or append and then reverse self.layers?
                # Let's iterate normally and then reverse self.layers at the end.
                
                for layer in layers_list:
                    if layer.is_group():
                        # Create Group Layer
                        l_obj = Layer(new_w, new_h, layer.name, "group")
                        l_obj.visible = layer.visible
                        l_obj.opacity = layer.opacity / 255.0
                        l_obj.blend_mode = self._map_psd_blend_mode(layer.blend_mode)
                        l_obj.depth = depth
                        self.layers.append(l_obj)
                        
                        # Recurse
                        process_layers(layer, depth + 1)
                    else:
                        # Raster Layer
                        l_obj = Layer(new_w, new_h, layer.name, "normal")
                        l_obj.visible = layer.visible
                        l_obj.opacity = layer.opacity / 255.0
                        l_obj.blend_mode = self._map_psd_blend_mode(layer.blend_mode)
                        l_obj.depth = depth
                        
                        # Extract Image
                        pil_img = layer.composite()
                        if pil_img:
                            # Convert PIL to QImage
                            # Ensure RGBA
                            pil_img = pil_img.convert("RGBA")
                            data = pil_img.tobytes("raw", "RGBA")
                            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
                            
                            # Draw into full canvas size image at correct offset
                            full_img = QImage(new_w, new_h, QImage.Format.Format_ARGB32)
                            full_img.fill(Qt.GlobalColor.transparent)
                            p = QPainter(full_img)
                            p.drawImage(layer.left, layer.top, qimg)
                            p.end()
                            
                            l_obj.image = full_img
                            
                        self.layers.append(l_obj)

            process_layers(psd)
            
            # PSD iterator is usually Top -> Bottom.
            # Our engine draws 0 -> N (Bottom -> Top).
            # So we need to reverse the list so index 0 is Background/Bottom.
            self.layers.reverse()
            
            if not self.layers: self.reset_canvas()
            
            self._active_layer_index = 0 # Top layer (now last index? No, usually active is user choice)
            self._undo_stack = []
            self._redo_stack = []
            
            self.canvasWidthChanged.emit(new_w)
            self.canvasHeightChanged.emit(new_h)
            self.activeLayerChanged.emit(len(self.layers) - 1) # Select top layer
            self.emit_layers_update()
            self.fitToView()
            self.update()
            return True
            
        except Exception as e:
            print(f"Error loading PSD: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _map_psd_blend_mode(self, mode_str):
        # PSD Tools modes: 'norm', 'mul ', 'scrn', 'over', etc. (4 chars usually)
        # Or human readable strings? psd-tools usually uses specific enums or strings.
        # Let's handle common strings.
        ms = str(mode_str).lower()
        if 'multiply' in ms: return QPainter.CompositionMode.CompositionMode_Multiply
        if 'screen' in ms: return QPainter.CompositionMode.CompositionMode_Screen
        if 'overlay' in ms: return QPainter.CompositionMode.CompositionMode_Overlay
        if 'darken' in ms: return QPainter.CompositionMode.CompositionMode_Darken
        if 'lighten' in ms: return QPainter.CompositionMode.CompositionMode_Lighten
        if 'add' in ms: return QPainter.CompositionMode.CompositionMode_Plus
        if 'hard_light' in ms: return QPainter.CompositionMode.CompositionMode_HardLight
        if 'soft_light' in ms: return QPainter.CompositionMode.CompositionMode_SoftLight
        if 'difference' in ms: return QPainter.CompositionMode.CompositionMode_Difference
        if 'exclusion' in ms: return QPainter.CompositionMode.CompositionMode_Exclusion
        if 'color_dodge' in ms: return QPainter.CompositionMode.CompositionMode_ColorDodge
        if 'color_burn' in ms: return QPainter.CompositionMode.CompositionMode_ColorBurn
        
        return QPainter.CompositionMode.CompositionMode_SourceOver

    # --- DRAWING ---

    def _draw_checkerboard(self, painter, width, height, tile_size=20):
        """Draws a checkerboard pattern to indicate transparency."""
        light = QColor("#e0e0e0")
        dark = QColor("#c0c0c0")
        
        for y in range(0, height, tile_size):
            for x in range(0, width, tile_size):
                is_light = ((x // tile_size) + (y // tile_size)) % 2 == 0
                painter.fillRect(x, y, tile_size, tile_size, light if is_light else dark)

        painter.end()


    @pyqtProperty(str, notify=canvasPreviewChanged)
    def canvas_preview(self):
        """Returns a lightweight preview of the full canvas composition for the Navigator."""
        if not self.layers: return ""
        
        # Create a composition image
        comp = QImage(self._canvas_width, self._canvas_height, QImage.Format.Format_ARGB32_Premultiplied)
        comp.fill(Qt.GlobalColor.transparent)
        painter = QPainter(comp)
        
        for layer in self.layers:
            if layer.visible and layer.opacity > 0:
                painter.setOpacity(layer.opacity)
                painter.drawImage(0, 0, layer.image)
        painter.end()
        
        # Scale for performance
        preview = comp.scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        preview.save(buffer, "PNG")
        return "data:image/png;base64," + buffer.data().toBase64().data().decode()

    @pyqtSlot(str, result=str)
    def loadReference(self, file_url):
        """Loads an image (PNG, JPG, PSD) and returns a Base64 string for QML."""
        path = QUrl(file_url).toLocalFile() if "://" in file_url else file_url
        if not os.path.exists(path): return ""
        
        try:
            # 1. PSD Support
            if path.lower().endswith(".psd"):
                try:
                    from psd_tools import PSDImage
                    psd = PSDImage.open(path)
                    pil_img = psd.composite()
                    if pil_img:
                        pil_img = pil_img.convert("RGBA")
                        # Convert to QImage then Base64
                        data = pil_img.tobytes("raw", "RGBA")
                        qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
                        # Scale down if too huge for a reference window
                        if qimg.width() > 1000 or qimg.height() > 1000:
                            qimg = qimg.scaled(1000, 1000, Qt.AspectRatioMode.KeepAspectRatio)
                            
                        buffer = QBuffer()
                        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                        qimg.save(buffer, "PNG")
                        return "data:image/png;base64," + buffer.data().toBase64().data().decode()
                except ImportError:
                    print("psd_tools not installed.")
                except Exception as e:
                    print(f"PSD Ref Error: {e}")
                    
            # 2. Standard Image Support
            img = QImage(path)
            if img.isNull(): return ""
            
            # Auto-scale optimization
            if img.width() > 1200 or img.height() > 1200:
                 img = img.scaled(1200, 1200, Qt.AspectRatioMode.KeepAspectRatio)

            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            img.save(buffer, "PNG") # PNG is safe, JPG might lose quality but faster?
            return "data:image/png;base64," + buffer.data().toBase64().data().decode()
            
        except Exception as e:
            print(f"LoadRef Error: {e}")
            return ""

    def paint(self, painter):
        # --- PRO ENGINE INITIALIZATION ---
        # Must be called with a valid context. If RenderTarget is FBO, paint() has it.
        if HAS_NATIVE_RENDER and not self._native_initialized and not getattr(self, '_native_failed', False):
             print(f"QCanvasItem: Initializing native GL in paint context... (HAS_NATIVE_RENDER={HAS_NATIVE_RENDER})", flush=True)
             self._init_native_gl()
             if self._native_initialized:
                 print("QCanvasItem: Native GL initialized successfully.", flush=True)
             else:
                 print("QCanvasItem: Native GL initialization failed.", flush=True)

        w, h = int(self.width()), int(self.height())
        
        # --- PROCESS NATIVE DRAWING QUEUE ---
        if HAS_NATIVE_RENDER and self._native_initialized and self._native_draw_queue:
             painter.beginNativePainting()
             try:
                 # 1. Prepare Renderer (Binds FBOs)
                 self._native_renderer.beginFrame()
                 
                 # 2. Prepare Stroke Renderer (Set Shaders/Projection)
                 self._stroke_renderer.beginFrame(int(self._canvas_width), int(self._canvas_height))
                 
                 # 3. Sync Brush State
                 c = QColor(self.brushColor)
                 color_vec = [c.redF(), c.greenF(), c.blueF(), self.brushOpacity]
                 
                 # 4. Drain Queue
                 while self._native_draw_queue:
                      pos, pres = self._native_draw_queue.pop(0)
                      # Simple draw for now (mode 0 = normal)
                      self._stroke_renderer.drawDab(
                          pos.x(), pos.y(), 
                          self.brushSize, 
                          self._brush_angle,
                          color_vec,
                          self.brushHardness,
                          pres,
                          0
                      )
                 
                 self._stroke_renderer.endFrame()
                 self._native_renderer.endFrame()
             except Exception as e:
                 print(f"Native Draw Error: {e}")
             finally:
                 painter.endNativePainting()

        
        # Apply transformation (Panning/Zoom)
        painter.save()
        painter.translate(self._view_offset)
        painter.scale(self._zoom_level, self._zoom_level)

        
        # Check if background layer is visible
        bg_visible = self.layers[0].visible if self.layers else True
        
        # If background is hidden, draw checkerboard
        if not bg_visible:
            # Shift checkerboard with offset? No, usually it stays fixed or moves.
            # Let's keep it fixed to the background
            self._draw_checkerboard(painter, w, h)
        
        # Iterate from bottom (0) to top
        i = 0
        while i < len(self.layers):
            layer = self.layers[i]
            
            # Check if this is a clipping base (next layer is clipped)
            is_base = False
            if i + 1 < len(self.layers) and self.layers[i+1].clipped:
                is_base = True
                
            if is_base and layer.visible:
                # CLIPPING STACK: Base + following clipped layers
                # We need a buffer to compose them separately, then draw to canvas
                
                # Get canvas/layer size
                lw, lh = layer.image.width(), layer.image.height()
                
                # Check/Create group buffer
                if self._group_buffer is None or self._group_buffer.width() != lw or self._group_buffer.height() != lh:
                    self._group_buffer = QImage(lw, lh, QImage.Format.Format_ARGB32)
                
                self._group_buffer.fill(Qt.GlobalColor.transparent)
                gp = QPainter(self._group_buffer)
                
                # 1. Draw Base Layer to buffer
                gp.setOpacity(layer.opacity)
                gp.drawImage(0, 0, layer.image)
                
                # 2. Draw following clipped layers
                j = i + 1
                while j < len(self.layers) and self.layers[j].clipped:
                    clayer = self.layers[j]
                    if clayer.visible:
                        # For each clipper, we need its pixels masked by BASE layer
                        # Most efficient way for QPainter: 
                        # - Use a smaller temp buffer if possible, or just the same size
                        if self._temp_buffer is None or self._temp_buffer.width() != lw or self._temp_buffer.height() != lh:
                            self._temp_buffer = QImage(lw, lh, QImage.Format.Format_ARGB32)
                        
                        self._temp_buffer.fill(Qt.GlobalColor.transparent)
                        tp = QPainter(self._temp_buffer)
                        tp.drawImage(0, 0, clayer.image)
                        # Mask temp by BASE layer alpha
                        tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                        tp.drawImage(0, 0, layer.image) # Use Base image as mask
                        tp.end()
                        
                        # Blend the masked clipper into the group buffer
                        gp.setCompositionMode(clayer.blend_mode)
                        gp.setOpacity(clayer.opacity)
                        gp.drawImage(0, 0, self._temp_buffer)
                        
                    j += 1
                
                gp.end()
                
                # 3. Draw result to main canvas
                painter.setCompositionMode(layer.blend_mode)
                painter.setOpacity(1.0)
                painter.drawImage(0, 0, self._group_buffer)
                
                i = j # Move to next chain
                continue

            elif not layer.clipped and layer.visible:
                # Normal layer
                painter.setCompositionMode(layer.blend_mode)
                painter.setOpacity(layer.opacity)
                painter.drawImage(0, 0, layer.image)
                
            i += 1
            painter.setOpacity(1.0)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    
        # Draw Paper Border for clarity
        painter.setPen(QPen(QColor("#3a3a3c"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.layers:
            img_w, img_h = self.layers[0].image.width(), self.layers[0].image.height()
            painter.drawRect(0, 0, img_w, img_h)
        
        # Draw Selection and Transform Visuals
        # Draw Selection and Transform Visuals
        self._draw_selection_overlay(painter) # Base mask tint
        
        # DIBUJAR SELECCIÓN (Hormigas marchando - PREMIUM)
        if not self._selection_path.isEmpty() or (self._is_selecting and len(self._selection_points) > 1 and self._current_tool in ["lasso", "magnetic_lasso"]):
            painter.save()
            # Resetear transformaciones para dibujar en coordenadas de pantalla si el path es de pantalla?
            # NO. self._selection_path debe guardarse en coordenadas de CANVAS para que el zoom funcione.
            # Pero en la implementación del usuario dice:
            # painter.setWorldTransform(QTransform())
            # Esto implica que DRAWPATH usa Coordenadas de Pantalla.
            # Vamos a asumir que _selection_path (final) es CANVAS coords, pero _selection_points (temp) son SCREEN coords?
            # En mousePress/Move usamos event.position() que son SCREEN.
            
            # Así que mientras "selecting", points son SCREEN.
            # Al finalizar, path es... ¿Canvas?
            
            # Si usamos SCREEN coords para todo, el zoom desalineará la selección.
            # Correcto: Guardar puntos en CANVAS coords desde el principio o transformar al pintar.
            
            # IMPL: Usar puntos de pantalla "temporales" en selección, pero transformar.
            
            # AQUI: Si _is_selecting, usamos puntos de pantalla.
            # Si NO _is_selecting (path cerrado), el path DEBE ser Canvas Coords.
            
            # Para simplificar "Cosmetic Mode" (ancho constante), reseteamos transform para el PEN, pero no para el PATH?
            # QPen cosmtic (width=0) hace eso automatico.
            
            draw_path = QPainterPath()
            
            if self._is_selecting and len(self._selection_points) > 1:
                # Puntos are already in CANVAS coords (standardized now)
                draw_path.moveTo(self._selection_points[0])
                for p in self._selection_points[1:]:
                    draw_path.lineTo(p)
                # Keep the current transformation (Zoom/Pan) active
            else:
                # Path is CANVAS coords (finalized)
                draw_path = self._selection_path
            
            # Efecto de dos colores (marching ants)
            pen = QPen(QColor("black"), 0) # 0 = 1px cosmetic (constant width regardless of zoom)
            pen.setDashPattern([4, 4])
            pen.setDashOffset(self._marching_ants_offset)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(draw_path)
            
            pen.setColor(QColor("white"))
            pen.setDashOffset(self._marching_ants_offset + 4)
            painter.setPen(pen)
            painter.drawPath(draw_path)
            
            painter.restore()
        self._draw_transform_preview(painter)
        self._draw_shape_preview(painter)
        
        painter.restore()

        # --- GHOST CURSOR ---
        if getattr(self, "_is_hovering", False):
            if self._current_tool == "fill" and getattr(self, "_fill_mode", "bucket") == "bucket":
                # Draw Bucket Icon
                if not hasattr(self, "_bucket_pixmap") or self._bucket_pixmap is None:
                    try:
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        icon_path = os.path.join(os.path.dirname(script_dir), "assets", "icons", "paint-bucket.svg")
                        if not os.path.exists(icon_path):
                             icon_path = os.path.join(script_dir, "assets", "icons", "paint-bucket.svg")

                        # Load original (usually white/light)
                        original = QIcon(icon_path).pixmap(32, 32)
                        
                        # Create a black version by tinting
                        black_version = QPixmap(original.size())
                        black_version.fill(Qt.GlobalColor.transparent)
                        lp = QPainter(black_version)
                        lp.drawPixmap(0, 0, original)
                        lp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                        lp.fillRect(black_version.rect(), Qt.GlobalColor.black)
                        lp.end()
                        self._bucket_pixmap = black_version
                    except Exception as e:
                        print(f"Error loading bucket icon: {e}")
                        self._bucket_pixmap = None

                if self._bucket_pixmap:
                    pos = getattr(self, "_cursor_pos", QPointF(0,0))
                    # Offset so the tip of the bucket (center-bottom-ish) is at the point
                    painter.setOpacity(0.9)
                    painter.drawPixmap(int(pos.x() - 4), int(pos.y() - 28), self._bucket_pixmap)
            else:
                stamp = self._get_brush_stamp(self._brush_size, self._brush_color)
                if stamp and not stamp.isNull():
                    # While drawing, we make it even more subtle (30% vs 50%)
                    c_opacity = 0.3 if self._drawing else 0.5
                    painter.setOpacity(c_opacity)
                    pos = getattr(self, "_cursor_pos", QPointF(0,0))
                    # Draw centered
                    painter.drawImage(QRectF(pos.x() - self._brush_size/2, pos.y() - self._brush_size/2, self._brush_size, self._brush_size), stamp)

        # --- LASSO FILL OVERLAY ---
        if self._current_tool == "fill" and self._fill_mode == "lasso":
             if getattr(self, "_lasso_points", None) and len(self._lasso_points) > 1:
                 # No painter.resetTransform() needed if using canvas_pos
                 poly = QPolygonF(self._lasso_points)
                 
                 # Draw Fill Preview
                 painter.setPen(QPen(QColor("#00AAFF"), 1, Qt.PenStyle.DashLine))
                 painter.setBrush(QColor(0, 100, 255, 30))
                 painter.drawPolygon(poly)
                 painter.restore()

    @pyqtSlot(str)
    def setBackgroundColor(self, color_str):

        """Changes the background layer color in real-time."""
        if not self.layers:
            return
        
        bg_layer = self.layers[0]
        new_color = QColor(color_str)
        bg_layer.image.fill(new_color)
        print(f"Background color changed to: {color_str}")
        self.update()  # Immediate visual update

    def _draw_point(self, point, pressure=1.0):
        if not self.layers: return
        if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers): return
        target_layer = self.layers[self._active_layer_index]
        if not target_layer.visible or target_layer.locked: return

        # Dynamic width
        width = self._brush_size * pressure
        color = QColor(self._brush_color)
        
        # USE TEXTURED ENGINE or User Requested Dab
        # USE TEXTURED ENGINE (Unified Physics)
        if self._current_tool in ["brush", "pencil", "water", "pen", "airbrush", "eraser"]:
            # _draw_textured_line expects Raw screen points
            self._draw_textured_line(point, point, width, color, pressure)
        else:
            # Consistent with user request
            self._apply_brush(point, pressure)
            
        self.update()

    def _draw_line(self, p1, p2, pressure=1.0):
        try:
            if not self.layers: return
            if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers): return
            target_layer = self.layers[self._active_layer_index]
            if not target_layer.visible or target_layer.locked: return

            width = self._brush_size * pressure
            color = QColor(self._brush_color)
            
            # REGLA DE ORO: Si es pincel ABR, si tiene grano, o si es agua -> MOTOR AVANZADO
            # REGLA DE ORO: Use advanced engine for everything except maybe basic testing
            # This ensures Hardness, Grain, and Textures work consistently.
            is_custom = getattr(self, "_current_brush_name", "") in self._custom_brushes
            # Force advanced for all standard drawing tools
            use_advanced = is_custom or (self._current_tool in ["brush", "pencil", "water", "pen", "airbrush", "eraser"])

            if use_advanced:
                self._draw_textured_line(p1, p2, width, color, pressure)
            else:
                # Pinceles básicos (Ink Pen, Marker)
                diff = p2 - p1
                dist = (diff.x()**2 + diff.y()**2)**0.5
                if dist < 0.5: return # Skip tiny movements

                spacing = getattr(self, "_brush_spacing", 0.1)
                step_size = max(1.0, width * spacing)
                steps = int(dist / step_size)
                
                if steps > 0:
                    for i in range(1, steps + 1):
                        self._apply_brush(p1 + diff * (i / steps), pressure)
                else:
                    self._apply_brush(p2, pressure)
            
            self.update()
        except Exception as e:
            print(f"Error en _draw_line: {e}")

    # This method is now in DrawingEngineMixin
    # def _draw_brush_dab(self, point, pressure): ...

    # This method is now in DrawingEngineMixin
    # def _generate_pencil_stamp(self, size, color): ...

    # This method is now in DrawingEngineMixin
    # def _draw_pencil_line_traditional(self, lp1, lp2, width, color, pressure): ...

    # This method is now in DrawingEngineMixin
    # def _draw_inking_line_vector(self, lp1, lp2, width, color, pressure): ...

    # This method is now in DrawingEngineMixin
    # def _draw_textured_line(self, p1, p2, width, color, segment_pressure=1.0): ...

    # This method is now in DrawingEngineMixin
    # def _draw_textured_line_software_fallback(self, painter, p1, p2, width, color, pressure=1.0): ...

    # This method is now in DrawingEngineMixin
    # def _generate_seamless_paper(self, size): ...

    # This method is now in DrawingEngineMixin
    # def _get_paper_patch(self, x, y, w, h): ...


    @pyqtProperty(int, notify=brushSizeChanged)
    def brushSize(self): return self._brush_size
    @brushSize.setter
    def brushSize(self, size):
        if self._brush_size != size:
            self._brush_size = size
            self.brushSizeChanged.emit(size)

    @pyqtProperty(str, notify=brushColorChanged)
    def brushColor(self): return self._brush_color.name()
    @brushColor.setter
    def brushColor(self, color_str):
        if self._brush_color.name() != color_str:
            self._brush_color = QColor(color_str)
            self.brushColorChanged.emit(color_str)

    @pyqtProperty(float, notify=brushOpacityChanged)
    def brushOpacity(self): return self._brush_opacity
    @brushOpacity.setter
    def brushOpacity(self, opacity):
        if self._brush_opacity != opacity:
            self._brush_opacity = opacity
            self.brushOpacityChanged.emit(opacity)

    @pyqtProperty(str, notify=currentToolChanged)
    def currentTool(self): return self._current_tool
    @currentTool.setter
    def currentTool(self, tool):
        if tool == "BUCKET":
            tool = "fill"
            self.fillMode = "bucket"
        elif tool == "LASSO_FILL":
            tool = "fill"
            self.fillMode = "lasso"
            
        if self._current_tool != tool:
            self._current_tool = tool
            self._update_native_cursor()
            self.currentToolChanged.emit(tool)
            self.availableBrushesChanged.emit()

    @pyqtProperty(bool, notify=isTransformingChanged)
    def isTransforming(self): return self._is_transforming

    @pyqtProperty(bool, notify=selectionEmptyChanged)
    def selectionEmpty(self): 
        return not getattr(self, "_selection_active", False)

    @pyqtProperty(float, notify=brushSmoothingChanged)
    def brushSmoothing(self): return self._brush_smoothing
    @brushSmoothing.setter
    def brushSmoothing(self, val):
        if self._brush_smoothing != val:
            self._brush_smoothing = val
            self.brushSmoothingChanged.emit(val)

    @pyqtProperty(bool, notify=brushStampModeChanged)
    def brushStampMode(self): return getattr(self, "_brush_stamp_mode", False)
    @brushStampMode.setter
    def brushStampMode(self, val):
        if getattr(self, "_brush_stamp_mode", False) != val:
            self._brush_stamp_mode = val
            self.brushStampModeChanged.emit(val)

    @pyqtProperty(int, notify=brushStreamlineChanged)
    def brushStreamline(self): return getattr(self, "stabilization_amount", 5)
    @brushStreamline.setter
    def brushStreamline(self, val):
        val = max(0, min(50, val))
        if getattr(self, "stabilization_amount", 5) != val:
            self.stabilization_amount = val
            self.brushStreamlineChanged.emit(val)

    @pyqtProperty(str, notify=activeBrushNameChanged)
    def activeBrushName(self): return getattr(self, "_current_brush_name", "")
    @activeBrushName.setter
    def activeBrushName(self, name): self.usePreset(name)

    @pyqtProperty(list, notify=availableBrushesChanged)
    def availableBrushes(self):
        return list(self.BRUSH_PRESETS.keys()) + list(self._custom_brushes.keys())

    @pyqtProperty(list, notify=availableBrushesChanged)
    def brushFolders(self):
        if not hasattr(self, "BRUSH_PRESETS"): return []
        keywords = []
        if self._current_tool == "pen": keywords = ["Pen", "Ink", "Marker", "G-Pen", "Maru"]
        elif self._current_tool == "pencil": keywords = ["Pencil", "HB", "6B", "Mechanical"]
        elif self._current_tool in ["brush", "water"]: keywords = ["Water", "Oil", "Acrylic", "Wash", "Blend", "Mineral"]
        elif self._current_tool == "airbrush": keywords = ["Soft", "Hard"]
        elif self._current_tool == "eraser": keywords = ["Eraser"]
        else: return []

        folders = {}
        def get_category(name):
            if any(k in name for k in ["Watercolor", "Wash", "Blend"]): return "Watercolor"
            if any(k in name for k in ["Oil", "Acrylic"]): return "Painting"
            if any(k in name for k in ["Pen", "Ink", "Marker", "G-Pen", "Maru"]): return "Inking"
            if "Pencil" in name: return "Sketching"
            if "Eraser" in name: return "Erasers"
            if any(k in name for k in ["Soft", "Hard"]): return "Airbrushing"
            return "Standard"

        for name in self.BRUSH_PRESETS.keys():
            match = any(k in name for k in keywords)
            if not match and self._current_tool in ["brush", "water"]:
                is_other = any(k in name for k in ["Pen", "Ink", "Marker", "Pencil", "HB", "6B", "Airbrush", "Eraser"])
                if not is_other: match = True
            
            if match:
                cat = get_category(name)
                if self._current_tool in ["brush", "water"] and cat == "Airbrushing": match = False
                if match:
                    if cat not in folders: folders[cat] = []
                    folders[cat].append(name)

        for name, data in getattr(self, "_custom_brushes", {}).items():
            cat = data.get("category", "Imported")
            if cat not in folders: folders[cat] = []
            folders[cat].append(name)
            
        result = []
        priority = ["Inking", "Sketching", "Painting", "Watercolor", "Airbrushing", "Erasers", "Imported"]
        for p in priority:
            if p in folders and folders[p]: result.append({"name": p, "brushes": sorted(folders.pop(p))})
        for cat in sorted(folders.keys()):
             if folders[cat]: result.append({"name": cat, "brushes": sorted(folders[cat])})
             
        return result

    @pyqtProperty(float, notify=brushHardnessChanged)
    def brushHardness(self): return self._brush_hardness
    @brushHardness.setter
    def brushHardness(self, val):
        if self._brush_hardness != val:
            self._brush_hardness = val
            self.brushHardnessChanged.emit(val)

    @pyqtProperty(float, notify=brushRoundnessChanged)
    def brushRoundness(self): return self._brush_roundness
    @brushRoundness.setter
    def brushRoundness(self, val):
        if self._brush_roundness != val:
            self._brush_roundness = max(0.01, min(val, 1.0))
            self.brushRoundnessChanged.emit(self._brush_roundness)

    @pyqtProperty(float, notify=brushAngleChanged)
    def brushAngle(self): return self._brush_angle
    @brushAngle.setter
    def brushAngle(self, val):
        if self._brush_angle != val:
            self._brush_angle = val
            self.brushAngleChanged.emit(val)

    @pyqtProperty(bool, notify=brushDynamicsChanged)
    def brushDynamicAngle(self): return self._brush_dynamic_angle
    @brushDynamicAngle.setter
    def brushDynamicAngle(self, val):
        if self._brush_dynamic_angle != val:
            self._brush_dynamic_angle = val
            self.brushDynamicsChanged.emit(val)

    @pyqtProperty(float, notify=brushGrainChanged)
    def brushGrain(self): return getattr(self, '_brush_grain', 0.0)
    @brushGrain.setter
    def brushGrain(self, val):
        if getattr(self, '_brush_grain', 0.0) != val:
            self._brush_grain = val
            self.brushGrainChanged.emit(val)

    @pyqtProperty(float, notify=cursorRotationChanged)
    def cursorRotation(self): return getattr(self, '_current_cursor_rotation', 0.0)

    @pyqtProperty(float, notify=brushGranulationChanged)
    def brushGranulation(self): return getattr(self, '_brush_granulation', 0.0)
    @brushGranulation.setter
    def brushGranulation(self, val):
        if getattr(self, '_brush_granulation', 0.0) != val:
            self._brush_granulation = val
            self.brushGranulationChanged.emit(val)

    @pyqtProperty(float, notify=brushDiffusionChanged)
    def brushDiffusion(self): return getattr(self, '_brush_diffusion', 0.0)
    @brushDiffusion.setter
    def brushDiffusion(self, val):
        if getattr(self, '_brush_diffusion', 0.0) != val:
            self._brush_diffusion = val
            self.brushDiffusionChanged.emit(val)

    @pyqtProperty(float, notify=brushSpacingChanged)
    def brushSpacing(self): return getattr(self, '_brush_spacing', 0.1)
    @brushSpacing.setter
    def brushSpacing(self, val):
        if getattr(self, '_brush_spacing', 0.1) != val:
            self._brush_spacing = val
            self.brushSpacingChanged.emit(val)

    @pyqtProperty(str, notify=brushTipImageChanged)
    def brushTip(self):
        stamp = self._get_brush_stamp(64, self._brush_color)
        if stamp and not stamp.isNull():
             ba = QByteArray()
             buffer = QBuffer(ba)
             buffer.open(QIODevice.OpenModeFlag.WriteOnly)
             stamp.save(buffer, "PNG")
             return "data:image/png;base64," + base64.b64encode(ba.data()).decode()
        return ""
    
    @pyqtProperty(int)
    def cursorX(self): return int(self._cursor_pos.x())
    @pyqtProperty(int)
    def cursorY(self): return int(self._cursor_pos.y())
    @pyqtProperty(float, notify=cursorPressureChanged)
    def cursorPressure(self): return getattr(self, '_current_pressure', 1.0)

    @pyqtProperty(int, notify=canvasWidthChanged)
    def canvasWidth(self): return self._canvas_width
    @pyqtProperty(int, notify=canvasHeightChanged)
    def canvasHeight(self): return self._canvas_height

    @pyqtProperty(int, notify=fillToleranceChanged)
    def fillTolerance(self): return getattr(self, "_fill_tolerance", 30)
    @fillTolerance.setter
    def fillTolerance(self, val):
        if getattr(self, "_fill_tolerance", 30) != val:
            self._fill_tolerance = val
            self.fillToleranceChanged.emit(val)

    @pyqtProperty(int, notify=fillExpandChanged)
    def fillExpand(self): return getattr(self, "_fill_expand", 0)
    @fillExpand.setter
    def fillExpand(self, val):
        if getattr(self, "_fill_expand", 0) != val:
            self._fill_expand = val
            self.fillExpandChanged.emit(val)

    @pyqtProperty(str, notify=fillModeChanged)
    def fillMode(self): return getattr(self, "_fill_mode", "bucket")
    @fillMode.setter
    def fillMode(self, val):
        if getattr(self, "_fill_mode", "bucket") != val:
            self._fill_mode = val
            self.fillModeChanged.emit(val)

    @pyqtProperty(bool, notify=fillSampleAllChanged)
    def fillSampleAll(self): return getattr(self, "_fill_sample_all", False)
    @fillSampleAll.setter
    def fillSampleAll(self, val):
        if getattr(self, "_fill_sample_all", False) != val:
            self._fill_sample_all = val
            self.fillSampleAllChanged.emit(val)

    @pyqtProperty(str, notify=currentProjectNameChanged)
    def currentProjectName(self): return getattr(self, "_current_project_name", "Untitled")

    @pyqtProperty(str, notify=currentProjectPathChanged)
    def currentProjectPath(self): return getattr(self, "_current_project_path", "")

    @pyqtProperty(list, notify=pressureCurveChanged)
    def pressureCurve(self):
        pts = getattr(self, "_pressure_curve", [(0.25, 0.25), (0.75, 0.75)])
        return [pts[0][0], pts[0][1], pts[1][0], pts[1][1]]

    @pyqtProperty(QPointF, notify=viewOffsetChanged)
    def viewOffset(self): return self._view_offset
    @viewOffset.setter
    def viewOffset(self, val):
        self._view_offset = val
        self.viewOffsetChanged.emit()
        self.update()

    @pyqtProperty(float, notify=zoomLevelChanged)
    def zoomLevel(self): return self._zoom_level
    @zoomLevel.setter
    def zoomLevel(self, val):
        if self._zoom_level != val:
            self._zoom_level = max(0.01, min(val, 10.0))
            self.zoomLevelChanged.emit(self._zoom_level)
            self.update()


    @pyqtSlot(int, int)
    def handle_shortcuts(self, key, modifiers):
        """Handle keyboard shortcuts sent from QML."""
        # Helper to check matches
        # modifiers: 0x02000000 = Shift, 0x04000000 = Ctrl, 0x08000000 = Alt (approx in Qt6 QML)
        # But QML modifiers are Qt::KeyboardModifiers.
        
        # Simplified mapping:
        is_ctrl = (modifiers & Qt.KeyboardModifier.ControlModifier)
        is_shift = (modifiers & Qt.KeyboardModifier.ShiftModifier)
        is_alt = (modifiers & Qt.KeyboardModifier.AltModifier)
        
        # We should ideally use QKeySequence matching but that requires constructing it from int
        # For this prototype, we'll implement the logic explicitly for the requested actions
        # and lookup the generic key in the preferences.
        
        prefs = PreferencesManager.instance()
        
        # UNDO (Default Ctrl+Z)
        undo_sc = prefs.getShortcut("undo")
        if (key == Qt.Key.Key_Z and is_ctrl) or (undo_sc == "Ctrl+Z" and key == Qt.Key.Key_Z and is_ctrl):
            self.undo()
            return

        # REDO (Default Ctrl+Y or Ctrl+Shift+Z)
        redo_sc = prefs.getShortcut("redo")
        if (key == Qt.Key.Key_Y and is_ctrl) or (key == Qt.Key.Key_Z and is_ctrl and is_shift):
            self.redo()
            return
            
        # SAVE (Ctrl+S)
        if key == Qt.Key.Key_S and is_ctrl:
            return

        # NEW LAYER (Ctrl+Shift+N)
        new_layer_sc = prefs.getShortcut("new_layer")
        # Loose match for internal defaults
        if (key == Qt.Key.Key_N and is_ctrl and is_shift):
             self.addNewLayer()
             return

        # TOOLS
        if key == Qt.Key.Key_B: self.currentTool = "brush"
        if key == Qt.Key.Key_E: self.currentTool = "eraser"
        if key == Qt.Key.Key_H: self.currentTool = "hand"
        if key == Qt.Key.Key_P:
            if is_shift:
                self.currentTool = "pencil"
                self.activeBrushName = "HB Pencil" # Explicitly switch brush preset
            else:
                self.currentTool = "brush" 
                self.activeBrushName = "Ink Pen"   # Explicitly switch to Pen preset
        
        # ZOOM
        if key == Qt.Key.Key_Plus and is_ctrl: self.zoomLevel = self.zoomLevel * 1.2
        if key == Qt.Key.Key_Minus and is_ctrl: self.zoomLevel = self.zoomLevel * 0.8
        if key == Qt.Key.Key_0 and is_ctrl: self.fitToView()

    @pyqtSlot(int, int)
    def handle_key_release(self, key):
        """Handle key release (e.g. for temp tool switching)."""
        # Logic for switch_tool_temporarily could go here
        pass

    def _capture_timelapse_frame(self):
        """Captures a snapshot of the current canvas for timelapse."""
        if not self.layers: return

        # capture logic
        def save_worker(layers_copy, width, height, frame_num, save_dir):
            try:
                # Create small composite
                # Scale down to reasonable size (e.g. max 720p)
                scale = min(1280 / width, 720 / height)
                if scale > 1: scale = 1
                
                target_w = int(width * scale)
                target_h = int(height * scale)
                
                img = QImage(target_w, target_h, QImage.Format.Format_RGB32)
                img.fill(Qt.GlobalColor.white)
                
                p = QPainter(img)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                
                for layer in layers_copy:
                    if layer.visible:
                        p.setCompositionMode(layer.blend_mode)
                        p.setOpacity(layer.opacity)
                        # We need to draw the full res layer scaled down
                        p.drawImage(QRect(0, 0, target_w, target_h), layer.image)
                p.end()
                
                path = os.path.join(save_dir, f"frame_{frame_num:05d}.jpg")
                img.save(path, "JPG", 80)
            except Exception as e:
                print(f"Timelapse save error: {e}")

        # Clone simple layer data to pass to thread (deep copy of images is slow, 
        # but we can't access QImage safely from another thread if main thread draws to it).
        # SOLUTION: We must copy the current composition NOW on main thread, then SAVE on bg thread.
        # Copying full res 4k is slow. 
        # Let's simple-composite on main thread to a small image, then save on bg thread.
        
        try:
             # Check if dir exists
             if not self._timelapse_dir: return

             # Fast Scaling Composite - Improved Quality (Up to 1080p target for premium output)
             scale = min(1920 / self._canvas_width, 1080 / self._canvas_height) 
             if scale > 1.0: scale = 1.0
             
             tw = int(self._canvas_width * scale)
             th = int(self._canvas_height * scale)
             
             snapshot = QImage(tw, th, QImage.Format.Format_RGB32)
             snapshot.fill(Qt.GlobalColor.white)
             
             p = QPainter(snapshot)
             p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
             
             for layer in self.layers:
                 if layer.visible and not layer.is_private:
                     p.setCompositionMode(layer.blend_mode)
                     p.setOpacity(layer.opacity)
                     p.drawImage(QRect(0, 0, tw, th), layer.image)
             p.end()
        
             self._timelapse_counter += 1
             fnum = self._timelapse_counter
             sdir = self._timelapse_dir
             
             # Define worker to run in thread
             def save_snapshot(img, path, lock):
                 try:
                     with lock:
                        img.save(path, "JPG", 70)
                 except Exception as err:
                     print(f"Async Save Error: {err}")

             # IMPORTANT: Pass a COPY to the thread to avoid sharing the same underlying data 
             # if the main thread were to somehow reuse or delete this QImage.
             snapshot_copy = snapshot.copy()
             
             t = threading.Thread(target=save_snapshot, args=(snapshot_copy, os.path.join(sdir, f"frame_{fnum:05d}.jpg"), self._timelapse_lock))
             t.start()
             
        except Exception as e:
             print(f"Timelapse capture error: {e}")

    @pyqtSlot(list)
    def updatePressureCurve(self, points):
        """Updates the pressure curve control points. Expects list of 4 floats [p1x, p1y, p2x, p2y]"""
        if len(points) == 4:
            self._pressure_curve = [(points[0], points[1]), (points[2], points[3])]
            self.pressureCurveChanged.emit()
            print(f"Pressure curve updated: {self._pressure_curve}")

    def _apply_pressure_curve(self, raw_pressure):
        """Calculates output pressure using Cubic Bezier with cached control points."""
        # Simple Cubic Bezier 1D approximation for Y given X is complex analytically if X is not time.
        # But for pressure settings, usually we map input (X) to output (Y).
        # A standard Bezier defined by P0(0,0), P1, P2, P3(1,1) is parametric: B(t).
        # We need Y where B_x(t) = raw_pressure. Then return B_y(t).
        # Solving cubic for t is expensive per-pixel/event.
        # APPROXIMATION:
        # Since pressure curves are usually monotonic increasing, we can assume t ~= x or just use the
        # Y value of the bezier at t = raw_pressure, which is technically "Bezier Easing".
        # Let's use the explicit Bezier formula for Y using t=raw_pressure as a good-enough approximation for now,
        # or implement Newton-Raphson if precision is needed. For Art apps, t=x is often used for simplicity 
        # unless extreme curves are drawn.
        
        t = raw_pressure
        # Clamp
        t = max(0.0, min(1.0, t))
        
        p0 = (0, 0)
        p3 = (1, 1)
        p1 = self._pressure_curve[0]
        p2 = self._pressure_curve[1]
        
        # Cubic Bezier Formula:
        # B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
        
        # Since we want a mapping X -> Y, and we approximate t=X:
        # y = 3(1-t)^2*t*p1y + 3(1-t)*t^2*p2y + t^3
        
        # NOTE: This assumes the curve control points don't backtrack in X.
        
        mt = 1 - t
        mt2 = mt * mt
        t2 = t * t
        
        y = 3 * mt2 * t * p1[1] + 3 * mt * t2 * p2[1] + t * t2 * 1.0
        
        return max(0.0, min(1.0, y))

    @pyqtSlot(float, float, result=str)
    @pyqtSlot(float, float, int, result=str)
    def sampleColor(self, x, y, mode=0):
        """
        Samples color from the canvas.
        mode 0: Composite color (all visible layers)
        mode 1: Current layer color
        """
        if not self.layers: return "#000000"
        
        # 1. Coordinate conversion
        pt = QPointF(x, y)
        canvas_pt = (pt - self._view_offset) / self._zoom_level
        cx, cy = int(canvas_pt.x()), int(canvas_pt.y())
        
        # Bounds check
        if cx < 0 or cy < 0 or cx >= self._canvas_width or cy >= self._canvas_height:
            return "#000000"
            
        # 2. Sampling
        if mode == 1:
            # Current Layer Only
            if 0 <= self._active_layer_index < len(self.layers):
                layer = self.layers[self._active_layer_index]
                sampled = layer.image.pixelColor(cx, cy)
                # If transparent, return black or background? 
                # Usually current layer pick means exactly what's on that layer.
                return sampled.name()
            return "#000000"
        else:
            # Composite sampling (Mode 0)
            comp = QImage(1, 1, QImage.Format.Format_ARGB32)
            comp.fill(Qt.GlobalColor.transparent)
            painter = QPainter(comp)
            
            for layer in self.layers:
                if layer.visible and layer.opacity > 0:
                    painter.setOpacity(layer.opacity)
                    painter.setCompositionMode(layer.blend_mode)
                    painter.drawImage(0, 0, layer.image, cx, cy, 1, 1)
            
            painter.end()
            sampled = comp.pixelColor(0, 0)
            return sampled.name()

    # --- COORDINATE HELPERS ---
    def _map_to_canvas(self, point):
        """Converts screen position to canvas coordinates based on zoom and offset."""
        return (point - self._view_offset) / self._zoom_level

    # --- LASSO & SELECTION ENGINE ---
    def _prepare_magnetic_map(self):
        """Generates an edge map for the active layer so the lasso can 'snap' to edges."""
        if not self.layers or self._active_layer_index < 0: return
        
        layer = self.layers[self._active_layer_index]
        # Convert QImage to NumPy array for OpenCV
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())
        arr = np.frombuffer(ptr, np.uint8).reshape((layer.image.height(), layer.image.width(), 4))
        
        # Convert to Grayscale and detect edges using Canny
        gray = cv2.cvtColor(arr, cv2.COLOR_BGRA2GRAY)
        self._canny_edges = cv2.Canny(gray, 50, 150)

    def _get_magnetic_point(self, pos):
        """Finds the closest edge pixel within a 20px radius of the mouse."""
        if self._canny_edges is None: return pos
        
        h, w = self._canny_edges.shape
        ix, iy = int(pos.x()), int(pos.y())
        
        # Define ROI (Region of Interest)
        r = 20
        x_start, x_end = max(0, ix-r), min(w, ix+r)
        y_start, y_end = max(0, iy-r), min(h, iy+r)
        
        roi = self._canny_edges[y_start:y_end, x_start:x_end]
        points = np.argwhere(roi > 0) # Edge pixels
        
        if len(points) > 0:
            # Find closest to mouse center
            distances = np.sqrt((points[:,0]-r)**2 + (points[:,1]-r)**2)
            closest = points[np.argmin(distances)]
            return QPointF(x_start + closest[1], y_start + closest[0])
        
        return pos

    # --- LEGACY METHODS REMOVED (Moved to Mixins) ---
    # start_transformation, commit_transformation, cancel_transformation
    # _draw_selection_visuals, _draw_transform_gizmo
    # clear_selection -> Use clearSelection()

    # --- UNDO LOGIC ---
    def save_undo_state(self):
        """Saves current state of active layer before a change."""
        if not self.layers: return
        if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers): return
        layer = self.layers[self._active_layer_index]
        # Store a copy of the image and the layer index
        state = (self._active_layer_index, layer.image.copy())
        self._undo_stack.append(state)
        # Clear redo stack on new action
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    @pyqtSlot()
    def undo(self):
        if not self._undo_stack: return
        layer_idx, prev_image = self._undo_stack.pop()
        
        if 0 <= layer_idx < len(self.layers):
            # Save current as redo state
            self._redo_stack.append((layer_idx, self.layers[layer_idx].image.copy()))
            
            self.layers[layer_idx].image = prev_image
            self.update()
            self.emit_layers_update()
            print("Undo successful")

    @pyqtSlot()
    def redo(self):
        if not self._redo_stack: return
        layer_idx, next_image = self._redo_stack.pop()
        
        if 0 <= layer_idx < len(self.layers):
            # Save current as undo state
            self._undo_stack.append((layer_idx, self.layers[layer_idx].image.copy()))
            
            self.layers[layer_idx].image = next_image
            self.update()
            self.emit_layers_update()
            print("Redo successful")

    # --- EVENTS ---
    def wheelEvent(self, event):
        # Zooming relative to mouse position
        p_delta = event.angleDelta().y()
        zoom_factor = 1.1 if p_delta > 0 else 0.9
        
        mouse_pos = event.position()
        
        # Calculate new zoom
        new_zoom = self._zoom_level * zoom_factor
        new_zoom = max(0.01, min(new_zoom, 10.0))
        
        # To zoom towards mouse:
        # offset' = mouse - (mouse - offset) * (new_zoom / old_zoom)
        ratio = new_zoom / self._zoom_level
        self._view_offset = mouse_pos - (mouse_pos - self._view_offset) * ratio
        self._zoom_level = new_zoom
        
        self.zoomLevelChanged.emit(self._zoom_level)
        self.viewOffsetChanged.emit()
        self.update()
        event.accept()



    # --- UNIFIED INPUT HANDLING ---
    def _apply_pressure_curve(self, pressure):
        """Applies user-defined pressure curve."""
        # TODO: Use actual curve settings (e.g. cubic bezier)
        # For now, simple linear or gamma
        return pressure

    def _handle_input(self, pos, pressure, rotation, is_press=False):
        """Central method for processing pointer input (Mouse/Tablet)."""
        if not self._drawing: return

        # 1. Apply Pressure Curve
        adj_pressure = self._apply_pressure_curve(pressure)
        self._current_pressure = adj_pressure
        self._current_cursor_rotation = rotation

        # 2. Draw
        if self._last_point is None:
            self._last_point = pos
        
        # If press, we might want a dot, but _draw_textured_line handles distance check.
        # Ensure we draw if it's a press even if distance is 0
        if is_press:
             self._draw_textured_line(pos, pos, self._brush_size, self._brush_color, adj_pressure)
        else:
             self._draw_textured_line(self._last_point, pos, self._brush_size, self._brush_color, adj_pressure)
        
        self._last_point = pos

    def _finalize_input(self):
        """Called on Release."""
        self._spacing_residue = 0.0
        # Reset pressure for hover
        self._current_pressure = 0.0 if self.isTabletActive() else 1.0

    @pyqtSlot(int, result=bool)
    def isTabletActive(self, dummy=0):
        # Helper to check if we received tablet events recently
        # Not strictly needed but useful for debugging
        return True

    def tabletEvent(self, event):
        """Handles Tablet Events (Pressure, Tilt, Rotation) explicitly."""
        print(f"TabletEvent: type={event.type()} pres={event.pressure()}", flush=True) # DEBUG
        
        # Extract Tablet Data
        pressure = event.pressure()
        rotation = event.rotation() # Degrees, depends on device
        pos = event.position()
        
        # Update Cursor State
        self._cursor_pos = pos
        self.cursorPosChanged.emit(pos.x(), pos.y())
        
        # Map input to drawing actions
        # Check event type
        t = event.type()
        
        if t == QTabletEvent.Type.TabletPress:
            self._drawing = True
            self._last_point = pos
            self._stabilizer_points = []
            # Use unified handler
            self._handle_input(pos, pressure, rotation, is_press=True)
            event.accept()
            
        elif t == QTabletEvent.Type.TabletMove:
            pos = self.get_stabilized_pos(pos)
            self._handle_input(pos, pressure, rotation, is_press=False)
            event.accept()
            
        elif t == QTabletEvent.Type.TabletRelease:
            self._drawing = False
            self._last_point = None
            self._finalize_input()
            self.emit_layers_update()
            
            # Timelapse Trigger
            self._timelapse_stroke_count += 1
            if self._timelapse_stroke_count % 1 == 0:
                self._capture_timelapse_frame()
                
            event.accept()
            
        # Update Cursor Feedback (Pressure/Rotation)
        applied_pressure = self._apply_pressure_curve(pressure)
        if self._current_pressure != applied_pressure:
            self._current_pressure = applied_pressure
            self.cursorPressureChanged.emit(applied_pressure)
            
        # NOTE: If we accept the event, Qt won't synthesize a mouse event.
        # This is exactly what we want to avoid double drawing.

    def mousePressEvent(self, event):
        """Fallback for Mouse Input (or if Tablet Event was ignored)."""
        # 1. Check for Tool Interception
        tool = getattr(self, "_current_tool", "brush")
        
        # SHAPES (Mapped from 'shapes' generic or specific tools)
        if tool in ["line", "rect", "ellipse", "shapes"]:
             # If tool is generic 'shapes', defaulting to rect? 
             # QML allows subtypes. Let's assume tool is specific like 'rect'
             # If tool == 'shapes', we might be in a bad state or default.
             if tool == "shapes": tool = "rect" 
             
             self._shape_start_pos = event.position()
             self._shape_current_pos = event.position()
             self._shape_preview_active = True
             self.update()
             return

        # SELECTION (Rect)
        if tool == "select_rect":
             self._selection_start_pos = event.position()
             self._selection_rect = QRectF()
             return
             
        # SELECTION (Lasso)
        if tool in ["lasso", "magnetic_lasso"]:
             self._is_selecting = True
             self._lasso_closed = False
             
             # Init points
             pos = event.position()
             # Logic Magnética
             if tool == "magnetic_lasso":
                 self._prepare_magnetic_map()
                 pos = self._get_magnetic_pos(pos)
                 
             self._selection_points = [pos]
             self.update()
             return

        # SELECTION (Wand)
        if tool == "select_wand":
             p = event.position()
             # Translate to canvas
             cp = (p - self._view_offset) / self._zoom_level
             # self.selectWand(cp.x(), cp.y(), tolerance=30) # TODO: Implement Wand in Mixin
             return

        # Default Drawing Logic
        self._drawing = True
        self._last_point = event.position()
        self._stabilizer_points = []
        
        # RESET STROKE STATE
        self._paint_load = 1.0 # Refill brush with paint
        self._brush_pickup_color = None # Clean the dirty part (optional, or keep generic dirty?)
        # Let's start fresh for now
        
        # Detect functionality
        dev_type = event.device().type()
        is_stylus = (dev_type == QInputDevice.DeviceType.Stylus)
        
        # Default pressure: 1.0 for Mouse, but use current/detected for Stylus to avoid "blob" on tap
        pressure = 1.0 if not is_stylus else self._current_pressure
        
        # 1. Try to get deep pressure info from points (QT6)
        if hasattr(event, "points") and len(event.points()) > 0:
            p = event.points()[0].pressure()
            # Trust the point pressure if it's valid (even 0.0 for stylus)
            if is_stylus:
                 pressure = p
            elif p > 0:
                 pressure = p

        # 2. Fallback check
        if is_stylus and pressure == 0.0:
             if hasattr(event, "pressure") and event.pressure() > 0:
                 pressure = event.pressure()
        
        # If we still have 0.0 for a "Press" event on Stylus, it implies the driver reported 0.
        # But we need to draw SOMETHING. Let's use a minimum threshold or keep it 0 (which draws tiny).
        # Actually, let's allow it. if pressure is 0, _draw_point makes a 0 size dot?
        # Let's ensure non-zero for visibility if it's a press
        if is_stylus and pressure <= 0.0:
            pressure = 0.1 # Minimum visibility for valid tap

        print(f"MousePress Pres: {pressure} (Stylus={is_stylus})", flush=True)
        
        self._cursor_pos = event.position()
        self.cursorPosChanged.emit(self._cursor_pos.x(), self._cursor_pos.y())
        self._handle_input(event.position(), pressure, self._brush_angle, is_press=True)
        event.accept()

    def mouseMoveEvent(self, event):
        """Fallback for Mouse Input."""
        tool = getattr(self, "_current_tool", "brush")
        
        # SHAPES
        if tool in ["line", "rect", "ellipse", "shapes"] and self._shape_preview_active:
             self._shape_current_pos = event.position()
             self.update()
             return
             
        # SELECTION (Rect)
        if tool == "select_rect" and hasattr(self, "_selection_start_pos"):
             # Update Selection Mask on Drag
             p1 = (self._selection_start_pos - self._view_offset) / self._zoom_level
             p2 = (event.position() - self._view_offset) / self._zoom_level
             
             x, y, w, h = int(p1.x()), int(p1.y()), int(p2.x() - p1.x()), int(p2.y() - p1.y())
             self._selection_rect = QRectF(p1, p2).normalized()
             # We assume replace mode for now
             self.selectRect(x, y, w, h, "replace") 
             return

        # SELECTION (Lasso)
        if tool in ["lasso", "magnetic_lasso"] and self._is_selecting:
             pos = event.position()
             if tool == "magnetic_lasso":
                 pos = self._get_magnetic_pos(pos)
                 
             # Optimización: Solo si se movió > 2px
             if not self._selection_points or (pos - self._selection_points[-1]).manhattanLength() > 2:
                 self._selection_points.append(pos)
                 self.update()
             return

        if not self._drawing: return # Only track drag
        
        current_point = self.get_stabilized_pos(event.position())
        self._cursor_pos = current_point
        self.cursorPosChanged.emit(current_point.x(), current_point.y())
        
        dev_type = event.device().type()
        is_stylus = (dev_type == QInputDevice.DeviceType.Stylus)
        
        # Default to 1.0 only for mouse
        pressure = 1.0 if not is_stylus else 0.5 # Default fallback
        
        # 1. Try Points
        valid_pressure_found = False
        if hasattr(event, "points") and len(event.points()) > 0:
            p = event.points()[0].pressure()
            # For move, 0.0 is valid (lifting off), but usually we drag.
            # If p is effectively 0 but we are drawing, use it.
            if is_stylus:
                 pressure = p
                 valid_pressure_found = True
            elif p > 0:
                 pressure = p
                 valid_pressure_found = True

        # 2. Fallback
        if not valid_pressure_found:
             if is_stylus:
                  if hasattr(event, "pressure"):
                      pressure = event.pressure()
        
        self._handle_input(current_point, pressure, self._brush_angle, is_press=False)
        
        # Update Pressure Feedback (Reset to 1.0 if it looks like a mouse)
        if not is_stylus and self._current_pressure != 1.0 and pressure == 1.0:
            self._current_pressure = 1.0
            self.cursorPressureChanged.emit(1.0)
            
        event.accept()


    def hoverEnterEvent(self, event):
        self._is_hovering = True
        # FORCE NULL CURSOR GLOBALLY (Nuclear Option)
        if self._current_tool != "hand" and not getattr(self, "_cursor_overridden", False):
            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
            self._cursor_overridden = True
        event.accept()

    def hoverLeaveEvent(self, event):
        self._is_hovering = False
        # Restore cursor
        if getattr(self, "_cursor_overridden", False):
            QGuiApplication.restoreOverrideCursor()
            self._cursor_overridden = False
        self.update()
        event.accept()

    def hoverMoveEvent(self, event):
        self._cursor_pos = event.position()
        self._is_hovering = True
        
        # Ensure cursor remains dead
        if self._current_tool != "hand" and not getattr(self, "_cursor_overridden", False):
             QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
             self._cursor_overridden = True
             
        self.update() # Draw ghost
        self.cursorPosChanged.emit(self._cursor_pos.x(), self._cursor_pos.y())
        event.accept()

    def mouseReleaseEvent(self, event):
        tool = getattr(self, "_current_tool", "brush")
        
        # SHAPES
        if tool in ["line", "rect", "ellipse", "shapes"] and self._shape_preview_active:
             self._shape_current_pos = event.position()
             self.commit_shape_to_layer()
             self._shape_preview_active = False
             return
             
        # SELECTION (Rect)
        if tool == "select_rect" and hasattr(self, "_selection_start_pos"):
             del self._selection_start_pos
             if hasattr(self, "_selection_rect"): del self._selection_rect
             return
             
        # SELECTION (Lasso)
        if tool in ["lasso", "magnetic_lasso"] and self._is_selecting:
             self._is_selecting = False
             
             # 1. Convert Screen Points to Canvas Points for Backend
             canvas_points = []
             self._selection_path = QPainterPath() # Reset visual path
             
             if len(self._selection_points) > 2:
                 # Start Path
                 p0_canvas = (self._selection_points[0] - self._view_offset) / self._zoom_level
                 self._selection_path.moveTo(p0_canvas)
                 canvas_points.append(p0_canvas)
                 
                 for p in self._selection_points[1:]:
                     cp = (p - self._view_offset) / self._zoom_level
                     canvas_points.append(cp)
                     self._selection_path.lineTo(cp)
                     
                 self._selection_path.closeSubpath()
             
                 # 2. Commit to Backend (Mask)
                 self.selectLasso(canvas_points, "replace")
             
             self.update()
             return

        self._drawing = False
        self._last_point = None
        self._finalize_input()
        self.emit_layers_update() 
        
        # Timelapse Trigger
        self._timelapse_stroke_count += 1
        if self._timelapse_stroke_count % 1 == 0:
            self._capture_timelapse_frame()
            
        event.accept()

    def _finalize_input(self):
        """Finalizes current tool interaction (Unified for Mouse/Tablet)."""
        # LASSO FILL TRIGGER
        if self._current_tool == "fill" and self._fill_mode == "lasso":
            self.apply_lasso_fill()
            self._lasso_points = []
            self.update()

        try:
            # SELECTION FINALIZE
            if self._current_tool in ["selection", "lasso", "magnetic_lasso"] and self._is_selecting:
                self._is_selecting = False
                self._lasso_closed = True
                
                if len(self._selection_points) > 1:
                    # Filter duplicates (Manhattan dist=0) to prevent QPainterPath bad alloc or warnings
                    unique_points = []
                    if self._selection_points:
                        unique_points.append(self._selection_points[0])
                        for p in self._selection_points[1:]:
                            if (p - unique_points[-1]).manhattanLength() > 0.1:
                                unique_points.append(p)

                    if len(unique_points) > 1:
                        self._selection_path = QPainterPath()
                        if self._current_tool == "selection":
                            # Rectangle mode
                            p1 = unique_points[0]
                            p2 = unique_points[-1]
                            self._selection_path.addRect(QRectF(p1, p2).normalized())
                        else:
                            # Lasso mode
                            self._selection_path.moveTo(unique_points[0])
                            for p in unique_points[1:]:
                                self._selection_path.lineTo(p)
                            self._selection_path.closeSubpath()
                
                self._selection_points = []
                self.selectionEmptyChanged.emit(self._selection_path.isEmpty())
                self.update()
        except Exception as e:
            print(f"CRITICAL ERROR in finalize_input: {e}", flush=True)
            # Reset state to safe defaults
            self._is_selecting = False
            self._lasso_closed = True
            self._selection_points = []
            self._selection_points = []
            self.update()

    def get_stabilized_pos(self, new_pos):
        self._stabilizer_points.append(new_pos)
        if len(self._stabilizer_points) > self.stabilization_amount:
            self._stabilizer_points.pop(0)

        # Promedio ponderado de los últimos puntos (Moving Average)
        if not self._stabilizer_points: return new_pos
        avg_x = sum(p.x() for p in self._stabilizer_points) / len(self._stabilizer_points)
        avg_y = sum(p.y() for p in self._stabilizer_points) / len(self._stabilizer_points)
        return QPointF(avg_x, avg_y)

    def _handle_input(self, current_point, pressure, rotation, is_press=False):
        """Unified Input Handler for Tablet and Mouse."""
        canvas_pos = self._map_to_canvas(current_point)

        # 1. TRANSFORMATION MODE
        if self._is_transforming:
            if is_press:
                self._transform_start_pos = canvas_pos
                # Determine mode based on position (very simple: center=move, others=rotate for now)
                dist_to_center = (canvas_pos - self._transform_rect.center()).manhattanLength()
                if dist_to_center < 50 / self._zoom_level:
                    self._transform_mode = "move"
                else:
                    self._transform_mode = "rotate"
            else:
                delta = canvas_pos - self._transform_start_pos
                self.handle_transform_interaction(delta, canvas_pos, mode=self._transform_mode)
            return

        # 2. HAND / PANNING
        if self._current_tool == "hand" or getattr(self, "_space_pressed", False):
             if is_press: 
                 self._last_point = current_point # Important to reset anchor
                 return 
             if self._last_point:
                 delta = current_point - self._last_point
                 self.viewOffset = self._view_offset + delta
                 self._last_point = current_point
             return

        # 3. SELECTION TOOLS (Lasso, etc)
        if self._current_tool in ["selection", "lasso", "magnetic_lasso"]:
            if is_press:
                self._is_selecting = True
                self._lasso_closed = False
                if self._current_tool == "magnetic_lasso":
                    self._prepare_magnetic_map()
                    canvas_pos = self._get_magnetic_pos_canvas(canvas_pos)
                self._selection_points = [canvas_pos]
            else:
                if self._current_tool == "magnetic_lasso":
                    canvas_pos = self._get_magnetic_pos_canvas(canvas_pos)
                
                # Avoid duplicates
                if not self._selection_points or (canvas_pos - self._selection_points[-1]).manhattanLength() > 2:
                    self._selection_points.append(canvas_pos)
            
            self.update()
            return

        # 4. FILL TOOLS
        if self._current_tool == "fill":
             if self._fill_mode == "lasso":
                 if is_press:
                     self._lasso_points = [current_point]
                 else:
                     self._lasso_points.append(current_point)
                 self.update() # For visual feedback
                 return
             # Bucket Mode
             if is_press:
                 self.apply_color_drop(current_point.x(), current_point.y(), self._brush_color)
             return



        # Apply Pressure Curve
        final_pressure = self._apply_pressure_curve(pressure)
        
        # Handle Rotation
        if self._brush_dynamic_angle:
             # Calculate from direction if dynamic
             import math
             if self._last_point and (current_point != self._last_point):
                 delta = current_point - self._last_point
                 dx = delta.x(); dy = delta.y()
                 if abs(dx) > 0.1 or abs(dy) > 0.1:
                     angle_rad = math.atan2(dy, dx)
                     new_rot = math.degrees(angle_rad)
                     self._current_cursor_rotation = new_rot
                     self.cursorRotationChanged.emit(new_rot)
        else:
             if self._current_cursor_rotation != self._brush_angle:
                 self._current_cursor_rotation = self._brush_angle
                 self.cursorRotationChanged.emit(self._brush_angle)

        if is_press:
            # Reset spacing accumulator
            self._spacing_residue = 0.0
            
            self.save_undo_state()
            self._draw_point(current_point, final_pressure)

            # --- BEZIER SMOOTHING INIT ---
            self._last_point = current_point
            self._prev_point = current_point
            self._mid_point = current_point
            
        else:
            # 5. STAMP MODE: Skip movement processing
            if getattr(self, "_brush_stamp_mode", False):
                return
            
            # --- STEP 2: STROKE INTERPOLATION ---
            # Instead of Line(Last, Current), we use a midpoint approach.
            # Curve from old_mid to new_mid, using old_point as control.
            
            if self._last_point:
                # 1. Stabilizer (Simple Weighted Moving Average for input)
                stabilized_point = current_point
                if self._brush_smoothing > 0.01:
                    weight = 1.0 - (self._brush_smoothing * 0.8)
                    smooth_x = self._last_point.x() * (1.0 - weight) + current_point.x() * weight
                    smooth_y = self._last_point.y() * (1.0 - weight) + current_point.y() * weight
                    stabilized_point = QPointF(smooth_x, smooth_y)

                # 2. Geometric Midpoint Smoothing (The "Silk Ribbon" Effect)
                # Calculate mid point between last processed point and new input
                new_mid = (self._last_point + stabilized_point) / 2.0
                
                # We draw a Quadratic Bezier from the PREVIOUS mid point to the NEW mid point
                # using the PREVIOUS point as the Control Point.
                # Since _draw_textured_line takes a straight line, we must sub-sample properly.
                # However, your current engine stamps along the line path.
                # To support curves, we treat the curve as many small straight segments.
                
                # Check distance to avoid massive processing on tiny jitter
                dist = (stabilized_point - self._last_point).manhattanLength()
                if dist < 2.0:
                     # Too small for spline, just line it
                     self._draw_line(self._last_point, stabilized_point, final_pressure)
                     self._mid_point = new_mid # Keep advancing mid
                else:
                     # Approximate Bezier with simplified segments
                     # Start: self._mid_point
                     # End: new_mid
                     # Control: self._last_point
                     
                     start = self._mid_point
                     end = new_mid
                     control = self._last_point
                     
                     # Subdivide curve into linear segments (e.g. 4 steps)
                     steps = max(2, int(dist / 5)) 
                     last_sub = start
                     
                     for i in range(1, steps + 1):
                         t = i / float(steps)
                         # Quadratic formula: (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
                         mt = 1.0 - t
                         bx = (mt**2 * start.x()) + (2 * mt * t * control.x()) + (t**2 * end.x())
                         by = (mt**2 * start.y()) + (2 * mt * t * control.y()) + (t**2 * end.y())
                         sub_point = QPointF(bx, by)
                         
                         self._draw_line(last_sub, sub_point, final_pressure)
                         last_sub = sub_point
                      
                     # Store state
                     self._mid_point = new_mid
    
                # OPTIMIZED UPDATE: Only refresh the stroke area
                if self._last_point:
                     margin = self._brush_size * 2
                     update_rect = QRectF(self._last_point, current_point).normalized().adjusted(-margin, -margin, margin, margin)
                     self.update(update_rect.toRect())
                else:
                     self.update()
                     
                self._last_point = stabilized_point
    


                
    def _generate_bristle_mask(self, size):
        """Generates a realistic bristle height map using NumPy (Optimized). Returns floats 0..1"""
        size = int(max(1, size))
        if size % 2 == 1: size += 1 
        center = size / 2.0
        
        # 1. Base Shape (Elliptical falloff - Oil flattens)
        y, x = np.ogrid[:size, :size]
        # Squashed Ellipse (70% Height)
        dist_from_center = np.sqrt((x - center)**2 + ((y - center)/0.7)**2)
        norm_dist = np.clip(dist_from_center / center, 0, 1)
        # Smoother falloff for thick paint
        circle_mask = np.power(1.0 - norm_dist, 0.5) 
        
        # 2. Bristle Clumps (Low Frequency)
        # Coherent noise would be best, but we'll approximate with blurred blocks
        noise_base = np.random.rand(size // 4, size // 4).astype(np.float32)
        noise_base = cv2.resize(noise_base, (size, size), interpolation=cv2.INTER_CUBIC)
        
        # 3. Fine Bristles (High Frequency)
        noise_fine = np.random.rand(size, size).astype(np.float32)
        
        # Mix
        bristles = noise_base * 0.7 + noise_fine * 0.3
        
        # 4. Long Streaks (Simulate dragging hairs)
        # Heavy horizontal blur
        k_sz = max(5, int(size * 0.3))
        kernel = np.zeros((k_sz, k_sz))
        kernel[int(k_sz/2), :] = 1.0 
        kernel /= k_sz 
        
        bristles = cv2.filter2D(bristles, -1, kernel)
        
        # Normalize
        b_max = np.max(bristles)
        if b_max > 0: bristles /= b_max
            
        # 5. Threshold (Cutoff to make individual clumps)
        # Power curve pushes values down, making it 'stringy'
        bristles = np.power(bristles, 2.0)
        
        # 6. Final Height Map
        height_map = bristles * circle_mask
        
        return height_map.astype(np.float32)

    def _generate_oil_mask_with_impasto(self, size, pressure):
        """Generates a realistic oil paint mask with hard edges and impasto relief."""
        size = int(max(4, size))
        if size % 2 == 1: size += 1
        center = size / 2.0
        
        # 1. Base Density (Thick Paint Body)
        # Random noise for internal texture
        mask = np.random.normal(0.8, 0.1, (size, size)).astype(np.float32)
        
        # Shape: Squashed Ellipse
        y, x = np.ogrid[:size, :size]
        dist_sq = ((x - center)**2 / (center**2)) + ((y - center)**2 / (center*0.8)**2)
        
        # BORDE DURO: Threshold based on pressure
        # Low pressure = ragged edge. High pressure = fuller stroke.
        threshold = 0.92 + (pressure * 0.05)
        # Binary-ish cut
        mask[dist_sq > threshold] = 0
        mask[dist_sq <= threshold] *= 1.1 # Boost density
        
        # Clip
        mask = np.clip(mask, 0, 1)
        
        # 2. Impasto Relief (Sobel-ish kernel for heavy ridges)
        # [[-3, -2, 0], 
        #  [-2,  1, 2], 
        #  [ 0,  2, 3]]
        kernel = np.array([[-3, -2, 0], [-2, 1, 2], [0, 2, 3]], dtype=np.float32)
        emboss = cv2.filter2D(mask, -1, kernel)
        
        return mask, emboss

    def _generate_watercolor_mask(self, size):
        """Generates an organic watercolor stain mask proceduraly."""
        size = int(max(1, size))
        if size % 2 == 1: size += 1
        center = size / 2.0
        
        # 1. Base Gradient (Soft circle)
        y, x = np.ogrid[:size, :size]
        dist = np.sqrt((x - center)**2 + (y - center)**2)
        norm_dist = np.clip(dist / center, 0, 1)
        
        # 2. Turbulence (Noise) for shape distortion
        # Generate low-res noise and upscale to create "blobby" shapes
        noise_sz = max(4, size // 8)
        noise = np.random.rand(noise_sz, noise_sz).astype(np.float32)
        noise = cv2.resize(noise, (size, size), interpolation=cv2.INTER_CUBIC)
        
        # Distort the distance field with noise
        distortion_strength = 0.3
        distorted_dist = norm_dist + (noise - 0.5) * distortion_strength
        distorted_dist = np.clip(distorted_dist, 0, 1)
        
        # 3. Fringe Effect (Edge Darkening)
        # Watercolor accumulates at edges. 
        # Inverted curve: Dark at edge (dist->1), Light at center (dist->0)
        # But actually, center is usually wet (transparent) and edge dries opaque.
        # Let's make a "donut" profile modulated by noise.
        
        # Opacity curve: High at center, dip, High at edge.
        # Simple Soft Round: (1 - dist)
        # Watercolor: (1 - dist)^0.5 * (1 + 2*dist^4) ?
        
        base_alpha = np.power(1.0 - distorted_dist, 0.5) # Soft falloff
        edge_accent = np.power(distorted_dist, 4.0) * 0.5 # Darker edge
        mask = base_alpha + edge_accent
        
        # 4. Pigment Granulation (New Realism Feature)
        # Create a high-frequency noise mask to simulate pigment settling
        grain_sz = max(4, size // 2)
        grain = np.random.rand(grain_sz, grain_sz).astype(np.float32)
        grain = cv2.resize(grain, (size, size), interpolation=cv2.INTER_LINEAR)
        # Contrast the grain
        grain = np.clip((grain - 0.4) * 2.5 + 0.5, 0, 1)
        
        mask = np.clip(mask * grain * noise, 0, 1) # Combine all factors
        
        # Smooth boundaries
        mask *= (1.0 - np.power(norm_dist, 10.0)) # Hard clip at pure circle edge
        
        # Normalize to 0..255
        return (mask * 255).astype(np.uint8)
    
    def _generate_fast_bristle_texture(self, size):
        """Generates a rapid noise texture for tool tips."""
        # Low-res noise scaled up = soft organic noise
        small_size = max(4, size // 4)
        noise = np.random.randint(0, 255, (small_size, small_size), dtype=np.uint8)
        noise_img = QImage(noise.data, small_size, small_size, small_size, QImage.Format.Format_Grayscale8)
        return noise_img.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _mix_colors_fresco(self, brush_color, canvas_color, ratio):
        """Mezcla colores manteniendo la saturación para evitar el 'barro'."""
        if canvas_color.alpha() < 10:
            return brush_color

        # Mezcla en espacio de color para simular pigmento
        r = brush_color.redF() * (1 - ratio) + canvas_color.redF() * ratio
        g = brush_color.greenF() * (1 - ratio) + canvas_color.greenF() * ratio
        b = brush_color.blueF() * (1 - ratio) + canvas_color.blueF() * ratio
        
        # Boost saturation slightly
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s = min(1.0, s * 1.1) # Pop saturation
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        return QColor.fromRgbF(min(1.0, r), min(1.0, g), min(1.0, b), brush_color.alphaF())

    def update_brush_cache(self):
        """Regenerate the brush stamp only when properties change."""
        self._cached_stamp = self._get_brush_stamp(self._brush_size, self._brush_color)

    def _generate_pro_watercolor_stamp(self, size, color):
        """Generates a professional watercolor stain with fringing and granulation."""
        size = int(max(4, size))
        if size % 2 == 1: size += 1
        
        # 1. Base organic noise mask
        noise_sz = max(4, size // 4)
        noise = np.random.rand(noise_sz, noise_sz).astype(np.float32)
        mask = cv2.resize(noise, (size, size), interpolation=cv2.INTER_CUBIC)
        
        # 2. Distance field with distortion
        y, x = np.ogrid[:size, :size]
        center = size/2
        dist = np.sqrt((x-center)**2 + (y-center)**2) / center
        dist = np.clip(dist + (mask - 0.5) * 0.4, 0, 1)
        
        # 3. FRINGE EFFECT: Pigment accumulates at edges
        # Inverted curve: Peaks at dist=0.9
        fringe = np.exp(-100 * (dist - 0.9)**2) * 0.5
        
        # 4. GRANULATION: Pigment settling
        gran = (mask - 0.5) * 0.2
        
        # Combine: Fill + Fringe + Granulation
        alpha_map = (1.0 - dist**2) * 0.6 + fringe + gran
        alpha_map = np.clip(alpha_map, 0, 1)
        
        # Soften boundaries
        alpha_map *= (1.0 - np.power(dist, 8.0))
        
        # Colorize
        c_r, c_g, c_b, c_a = color.red(), color.green(), color.blue(), color.alpha()
        alpha_ch = (alpha_map * c_a).astype(np.uint8)
        
        # Construct Image
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        
        # For performance, we can skip pixel-by-pixel if size is large
        # Use QImage bits if possible
        ptr = img.bits()
        ptr.setsize(size * size * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((size, size, 4))
        
        # Qt ARGB: BGRA
        arr[..., 0] = (c_b * (alpha_ch.astype(np.float32)/255.0)).astype(np.uint8)
        arr[..., 1] = (c_g * (alpha_ch.astype(np.float32)/255.0)).astype(np.uint8)
        arr[..., 2] = (c_r * (alpha_ch.astype(np.float32)/255.0)).astype(np.uint8)
        arr[..., 3] = alpha_ch
        
        return img

    def _generate_pro_oil_stamp(self, size, color):
        """Generates a professional 3D oil stamp with bristle streaks and impasto."""
        size = int(max(4, size))
        if size % 2 == 1: size += 1
        
        # 1. BRISTLE STREAKS (Motion blur noise)
        noise = np.random.normal(0.5, 0.15, (size, size)).astype(np.float32)
        # Apply directional blur to simulate bristles
        kernel_sz = max(3, size // 3)
        kernel = np.zeros((kernel_sz, kernel_sz))
        kernel[kernel_sz//2, :] = 1.0 # Horizontal streak
        kernel /= kernel_sz
        streaks = cv2.filter2D(noise, -1, kernel)
        
        # 2. BODY MASK (Hard Ellipse)
        y, x = np.ogrid[:size, :size]
        center = size/2
        # Distorted circle
        dist_sq = ((x-center)**2/(center**2)) + ((y-center)**2/(center*0.8)**2)
        body = np.where(dist_sq < 0.95, 1.0, 0.0).astype(np.float32)
        
        # Apply streaks to body to get height map
        height = streaks * body
        
        # 3. LIGHTING (Impasto)
        # Differential calculation for normals
        h_pad = np.pad(height, 1, mode='edge')
        dx = h_pad[1:-1, 2:] - h_pad[1:-1, :-2]
        dy = h_pad[2:, 1:-1] - h_pad[:-2, 1:-1]
        
        # Light from top-left (-1, -1)
        lighting = (-dx - dy) * 120.0 # Multiplier for intensity
        
        # 4. COLOR CONSTRUCTION
        c_r, c_g, c_b = color.red(), color.green(), color.blue()
        
        r_ch = np.clip(c_r + lighting, 0, 255).astype(np.uint8)
        g_ch = np.clip(c_g + lighting, 0, 255).astype(np.uint8)
        b_ch = np.clip(c_b + lighting, 0, 255).astype(np.uint8)
        
        alpha_ch = (body * 255).astype(np.uint8)
        
        # Build Image
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        ptr = img.bits()
        ptr.setsize(size * size * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((size, size, 4))
        
        # Premultiply
        a_norm = alpha_ch.astype(np.float32)/255.0
        arr[..., 0] = (b_ch * a_norm).astype(np.uint8)
        arr[..., 1] = (g_ch * a_norm).astype(np.uint8)
        arr[..., 2] = (r_ch * a_norm).astype(np.uint8)
        arr[..., 3] = alpha_ch
        
        return img

    def _get_brush_stamp(self, size, color):
        """Unified optimized stamp generator for professional looks."""
        size = int(max(1, size))
        if size > 1024: size = 1024 # Buffer safety
        
        brush_name = getattr(self, "activeBrushName", "Standard")
        hardness = getattr(self, "_brush_hardness", 0.8)
        grain = getattr(self, "_brush_grain", 0.0)
        roundness = getattr(self, "_brush_roundness", 1.0)
        
        # Cache key includes everything that changes the visual tip
        param_key = (size, color.rgba(), hardness, grain, roundness, brush_name)
        
        if self._brush_texture_params == param_key and self._brush_texture_cache:
            return self._brush_texture_cache
            
        # --- 0. CUSTOM BRUSHES (ABR) ---
        if brush_name in self._custom_brushes:
            brush_data = self._custom_brushes[brush_name]
            raw_img = brush_data.get("cached_stamp")
            if raw_img and not raw_img.isNull():
                stamp = raw_img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                final_stamp = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
                final_stamp.fill(Qt.GlobalColor.transparent)
                p = QPainter(final_stamp)
                dx, dy = (size-stamp.width())//2, (size-stamp.height())//2
                p.drawImage(dx, dy, stamp)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                p.fillRect(final_stamp.rect(), color)
                p.end()
                self._brush_texture_cache = final_stamp
                self._brush_texture_params = param_key
                return final_stamp

        # --- 1. PROCEDURAL GENERATION ---
        is_oil = "Oil" in brush_name or "Acrylic" in brush_name
        is_water = ("Water" in brush_name or "Wash" in brush_name) and "Blend" not in brush_name
        
        if is_oil:
            img = self._generate_pro_oil_stamp(size, color)
        elif is_water:
            img = self._generate_pro_watercolor_stamp(size, color)
        else:
            # --- STANDARD & SKETCHING ENGINE ---
            img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)

            # 1. INKING CASE (Sharp Solid)
            is_pen = any(k in brush_name for k in ["Pen", "Ink", "Maru", "G-Pen", "Pluma", "Marker"])
            if is_pen:
                p.setBrush(QBrush(color))
                p.drawEllipse(0, 0, size, size)
                p.end()
            else:
                # 2. PENCIL & SOFT CASE (Lead Chip Engine)
                seed = sum(ord(c) for c in brush_name) + size
                np.random.seed(seed)
                # Particles concentrated towards center
                num_particles = 12 + int(grain * 35)
                for _ in range(num_particles):
                    px = np.random.normal(size/2, size*0.19)
                    py = np.random.normal(size/2, size*0.19)
                    ps = np.random.uniform(0.5, max(1.0, size * 0.35))
                    dist = ((px-size/2)**2 + (py-size/2)**2)**0.5
                    p_alpha = int(255 * (1.1 - (dist/(size/1.7))))
                    p_alpha = max(0, min(255, p_alpha))
                    c = QColor(color)
                    c.setAlpha(p_alpha)
                    p.setBrush(QBrush(c))
                    p.drawEllipse(QRectF(px-ps/2, py-ps/2, ps, ps))

                # 3. Grain Carving
                if grain > 0.1:
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                    noise_small = np.random.randint(0, 255, (size//2 + 1, size//2 + 1), dtype=np.uint8)
                    noise = cv2.resize(noise_small, (size, size), interpolation=cv2.INTER_NEAREST)
                    noise = cv2.GaussianBlur(noise, (3, 3), 0)
                    thresh = 255 - int(grain * 210)
                    noise_mask = np.where(noise > thresh, 255, 110).astype(np.uint8)
                    noise_img = QImage(noise_mask.data, size, size, size, QImage.Format.Format_Grayscale8)
                    p.drawImage(0, 0, noise_img)
                p.end()
                np.random.seed(int(time.time() * 1000) % (2**32))
            
        self._brush_texture_cache = img
        self._brush_texture_params = param_key
        return img

    @pyqtSlot(str, result=str)
    def get_brush_preview(self, brush_name):
        """Generates an artistic S-curve preview for the brush and returns Base64 (Restored)."""
        # Safety check for premature QML calls
        if not hasattr(self, "_thumbnail_lock") or not hasattr(self, "_thumbnail_cache"):
             return ""
             
        # 1. Thread-safe Cache Check
        with self._thumbnail_lock:
            if brush_name in self._thumbnail_cache:
                return self._thumbnail_cache[brush_name]


        # 2. Setup Canvas
        preview_size = QSize(220, 100)
        img = QImage(preview_size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 3. Path Generation (Artistic S-Curve)
        path = QPainterPath()
        path.moveTo(30, 70)
        path.cubicTo(80, 10, 140, 90, 190, 30)
        
        # 4. Drawing Engine (Simulate authentic stroke)
        p = self.BRUSH_PRESETS.get(brush_name) or self._custom_brushes.get(brush_name)
        if not p:
            painter.setPen(QPen(QColor("#555"), 2))
            painter.drawPath(path)
            painter.end()
        else:
            preview_color = QColor("#ffffff")
            preview_size_val = min(30, int(p.get("size", 20)))
            
            old_name = self._current_brush_name
            self._current_brush_name = brush_name
            stamp = self._get_brush_stamp(preview_size_val, preview_color)
            self._current_brush_name = old_name
            
            if stamp and not stamp.isNull():
                step = 0.005
                t = 0.0
                while t <= 1.0:
                    pt = path.pointAtPercent(t)
                    # Simulate pressure: Heavy start, light tail (tapering)
                    press = 1.0 - (abs(t - 0.5) * 0.8) 
                    
                    # Stamp drawing logic (simplified)
                    painter.setOpacity(press) # Simple opacity pressure
                    # Draw stamp centered
                    painter.drawImage(int(pt.x() - stamp.width()/2), int(pt.y() - stamp.height()/2), stamp)
                    t += step
            painter.end()

        # 5. Conversion and Caching
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        b64 = "data:image/png;base64," + str(ba.toBase64().data(), 'utf-8')
        
        with self._thumbnail_lock:
             self._thumbnail_cache[brush_name] = b64
             
        return b64

    # --- SHORTCUT & GESTURE SYSTEM (Centralized) ---

    @pyqtSlot(str)
    def set_tool(self, tool_id):
        """Helper to switch tools programmatically."""
        # Simple sticky logic handled in usePreset/property setter, so direct set here is fine
        self.currentTool = tool_id

    @pyqtSlot(int, int)
    def handle_shortcuts(self, key, modifiers):
        """Standardized shortcut handler called from QML."""
        # Qt.KeyboardModifier.ControlModifier = 0x04000000
        ctrl = modifiers & 0x04000000
        shift = modifiers & 0x02000000

        # CTRL + Z (Undo)
        if ctrl and key == Qt.Key.Key_Z:
            if shift: self.redo()
            else: self.undo()
        
        # CTRL + T (Transform Selection)
        elif ctrl and key == Qt.Key.Key_T:
             self.startTransform()
        
        # CTRL + D (Deselect)
        elif ctrl and key == Qt.Key.Key_D:
             self.clearSelection()

        # SPACE (Hand/Pan) - Hold to move
        elif key == Qt.Key.Key_Space:
            if not getattr(self, "_space_pressed", False):
                self._space_pressed = True
                QGuiApplication.setOverrideCursor(Qt.CursorShape.OpenHandCursor)
                self._cursor_overridden = True

        # B (Brush) / E (Eraser) / etc
        elif key == Qt.Key.Key_B:
            self.set_tool("brush")
        elif key == Qt.Key.Key_E:
            self.set_tool("eraser")
        elif key == Qt.Key.Key_L:
             self.set_tool("lasso")
        elif key == Qt.Key.Key_V:
             self.set_tool("move")

    @pyqtSlot(int)
    def handle_key_release(self, key):
        """Handle key release events."""
        if key == Qt.Key.Key_Space:
            self._space_pressed = False
            if getattr(self, "_cursor_overridden", False):
                QGuiApplication.restoreOverrideCursor()
                self._cursor_overridden = False
    
    @pyqtSlot(float, float)
    def pan_canvas(self, dx, dy):
        """Pan the canvas by delta."""
        self.viewOffset = self._view_offset + QPointF(dx, dy)
        self.update()






    @pyqtSlot(float, float, float, result=str)
    def hclToHex(self, h, c, l):
        """Convert HCL inputs to Hex Color String for QML."""
        r, g, b = ColorManager.hcl_to_rgb(h, c, l)
        return QColor(r, g, b).name()

    @pyqtSlot(str, result=list)
    def hexToHcl(self, hex_color):
        """Get HCL values from Hex String. Returns [h, c, l]."""
        if not hex_color or not isinstance(hex_color, str): return [0, 0, 0]
        c = QColor(hex_color)
        if not c.isValid(): return [0, 0, 0]
        return list(ColorManager.rgb_to_hcl(c.red(), c.green(), c.blue()))

    @pyqtSlot(str, result=str)
    def getHexFromHsv(self, h, s, v):
        """Helper for standard HSV sliders if needed."""
        # h 0-1, s 0-1, v 0-1
        c = QColor.fromHsvF(h, s, v)
        return c.name()




    def getLayersList(self):
        # Helper to construct layer dicts for QML
        # Assuming this logic exists in layersChanged emission elsewhere, simplified version:
        data = []
        for i, lyr in enumerate(self.layers):
           data.append({
               "name": lyr.name,
               "opacity": lyr.opacity,
               "visible": lyr.visible,
               "active": (i == self._active_layer_index),
               # "thumbnail": lyr.get_thumbnail_base64() # Expensive, maybe skip or optimize
               "divider": False
           })
        return data  # Placeholder, usually mainCanvas already has this logic. 
        # Actually I should rely on the existing logic or just call update().
        # Re-emitting layersChanged with full data involves thumbnails which is heavy.
        # For now, just update() draws the canvas. Thumbnails might lag but canvas is instant.
        pass
