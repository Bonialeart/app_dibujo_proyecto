"""
ArtFlow Studio - QCanvasItem
Links Python drawing logic with QML interface and manages Multiple Layers.
"""

from PyQt6.QtQuick import QQuickPaintedItem
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QBrush, QCursor, QGuiApplication, QTransform, QPixmap, QRadialGradient
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

from PyQt6.QtCore import Qt, QPointF, pyqtSlot, QRectF, QRect, pyqtProperty, pyqtSignal, QObject, QByteArray, QBuffer, QIODevice, QUrl
from PyQt6.QtGui import QTabletEvent, QInputDevice

class Layer:
    """Represents a single layer in the drawing."""
    def __init__(self, width, height, name="Layer", type="normal"):
        self.name = name
        self.type = type # 'normal', 'background', 'group'
        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.blend_mode = QPainter.CompositionMode.CompositionMode_SourceOver # Default Normal
        self.expanded = True # For groups
        self.expanded = True # For groups
        self.depth = 0 # Indentation level
        self.clipped = False # Clipping mask
        self.alpha_lock = False
        self.is_private = False # If true, ignored in timelapse
        self.image = QImage(width, height, QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)

    def clear(self):
        self.image.fill(Qt.GlobalColor.transparent)

    def get_thumbnail_base64(self, size=80):
        """Generates a base64 encoded thumbnail for QML."""
        # Fast scaling
        thumb = self.image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        thumb.save(buffer, "PNG")
        return "data:image/png;base64," + base64.b64encode(ba.data()).decode()

class QCanvasItem(QQuickPaintedItem):
    """Custom QML Item that allows drawing with QPainter from Python, supporting multiple layers."""
    
    # Signal to update QML Layer List
    layersChanged = pyqtSignal(list, arguments=['layers'])
    activeLayerChanged = pyqtSignal(int, arguments=['index'])
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

    projectsLoaded = pyqtSignal(list, arguments=['projects'])
    brushesChanged = pyqtSignal()
    availableBrushesChanged = pyqtSignal()
    activeBrushNameChanged = pyqtSignal(str, arguments=['name'])
    cursorPosChanged = pyqtSignal(float, float, arguments=['x', 'y'])
    brushTipImageChanged = pyqtSignal(str, arguments=['source']) # Data URL

    # Fill Tool Signals
    fillToleranceChanged = pyqtSignal(int)
    fillExpandChanged = pyqtSignal(int)
    fillModeChanged = pyqtSignal(str)
    fillSampleAllChanged = pyqtSignal(bool)


    # Fill Tool Signals
    fillToleranceChanged = pyqtSignal(int)
    fillExpandChanged = pyqtSignal(int)
    fillModeChanged = pyqtSignal(str)
    fillSampleAllChanged = pyqtSignal(bool)

    
    # Blend Mode Mapping
    BLEND_MODES = {
        "Normal": QPainter.CompositionMode.CompositionMode_SourceOver,
        "Multiply": QPainter.CompositionMode.CompositionMode_Multiply,
        "Screen": QPainter.CompositionMode.CompositionMode_Screen,
        "Overlay": QPainter.CompositionMode.CompositionMode_Overlay,
        "Darken": QPainter.CompositionMode.CompositionMode_Darken,
        "Lighten": QPainter.CompositionMode.CompositionMode_Lighten,
        "Color Dodge": QPainter.CompositionMode.CompositionMode_ColorDodge,
        "Color Burn": QPainter.CompositionMode.CompositionMode_ColorBurn,
        "Add": QPainter.CompositionMode.CompositionMode_Plus,
        "Soft Light": QPainter.CompositionMode.CompositionMode_SoftLight,
        "Hard Light": QPainter.CompositionMode.CompositionMode_HardLight,
        "Difference": QPainter.CompositionMode.CompositionMode_Difference,
        "Exclusion": QPainter.CompositionMode.CompositionMode_Exclusion
    }
    
    BRUSH_PRESETS = {
        "Pencil HB": {"size": 4, "opacity": 0.5, "hardness": 0.1, "smoothing": 0.2, "blend": "Multiply", "grain": 0.6, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.05},
        "Pencil 6B": {"size": 15, "opacity": 0.85, "hardness": 0.4, "smoothing": 0.1, "blend": "Multiply", "grain": 0.9, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.05},
        "Ink Pen": {"size": 12, "opacity": 1.0, "hardness": 1.0, "smoothing": 0.7, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Marker": {"size": 25, "opacity": 0.4, "hardness": 0.9, "smoothing": 0.1, "blend": "Multiply", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        
        # --- PRO INKING PRESETS ---
        "G-Pen": {"size": 15, "opacity": 1.0, "hardness": 0.98, "smoothing": 0.7, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Maru Pen": {"size": 8, "opacity": 1.0, "hardness": 1.0, "smoothing": 0.5, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        
        # --- WATERCOLOR PRESETS ---
        "Watercolor":      {"size": 45, "opacity": 0.35, "hardness": 0.25, "smoothing": 0.4, "blend": "Multiply", "grain": 0.05, "granulation": 0.1, "diffusion": 0.4},
        "Watercolor Wet":  {"size": 55, "opacity": 0.3, "hardness": 0.1, "smoothing": 0.5, "blend": "Multiply", "grain": 0.0, "granulation": 0.0, "diffusion": 0.9},
        "Mineral Wash":    {"size": 40, "opacity": 0.4, "hardness": 0.3, "smoothing": 0.4, "blend": "Multiply", "grain": 0.15, "granulation": 0.8, "diffusion": 0.2}, 
        "Water Blend":     {"size": 60, "opacity": 1.0, "hardness": 0.1, "smoothing": 0.4, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.8},

        # --- PAINTING PRESETS (Updated for Realism) ---
        "Oil Paint":       {"size": 35, "opacity": 1.0, "hardness": 0.8, "smoothing": 0.3, "blend": "Normal", "grain": 0.5, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.02, "impasto": 0.8},
        "Acrylic":         {"size": 35, "opacity": 0.95, "hardness": 0.9, "smoothing": 0.2, "blend": "Normal", "grain": 0.5, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.02, "impasto": 0.6},
        
        # --- AIRBRUSH PRESETS ---
        "Soft":            {"size": 60, "opacity": 0.15, "hardness": 0.0, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Hard":            {"size": 40, "opacity": 0.2, "hardness": 0.85, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},

        # --- PENCIL PRESETS ---
        "Mechanical":      {"size": 2, "opacity": 0.8, "hardness": 0.8, "smoothing": 0.4, "blend": "Multiply", "grain": 0.2, "granulation": 0.0, "diffusion": 0.0},

        "Eraser Soft": {"size": 40, "opacity": 1.0, "hardness": 0.2, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Eraser Hard": {"size": 20, "opacity": 1.0, "hardness": 0.95, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0}
    }
    
    BLEND_MODES_INV = {v: k for k, v in BLEND_MODES.items()}

    def __init__(self, parent=None):
        print("QCanvasItem: initializing...", flush=True)
        super().__init__(parent)
        
        # Enable mouse tracking
        self.setAcceptedMouseButtons(Qt.MouseButton.AllButtons)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        self._cursor_pos = QPointF(0,0)
        self._is_hovering = False
        self._cursor_overridden = False
        # self.setAcceptTouchEvents(True)
        
        # Performance - Use Image for software backend compatibility
        if os.environ.get("QT_QUICK_BACKEND") == "software":
            self.setRenderTarget(QQuickPaintedItem.RenderTarget.Image)
        else:
            self.setRenderTarget(QQuickPaintedItem.RenderTarget.FramebufferObject)
        self.setAntialiasing(True)


        print("QCanvasItem: generating paper...", flush=True)
        # 1. Texture Generation
        self._paper_texture_size = 1024
        self._paper_texture = self._generate_seamless_paper(self._paper_texture_size)
        
        # 2. Native Engine (Deferred Init) - Will be initialized in paint()
        self._native_renderer = None
        self._stroke_renderer = None
        self._native_initialized = False 

        
        # Timelapse State
        self._timelapse_stroke_count = 0
        self._timelapse_counter = 0
        self._timelapse_dir = ""
        self._timelapse_lock = threading.RLock()
        try:
             self._timelapse_dir = os.path.join(tempfile.gettempdir(), "ArtFlow_Timelapse_" + str(int(time.time())))
             os.makedirs(self._timelapse_dir, exist_ok=True)
        except Exception as e:
             print(f"Error initializing timelapse dir: {e}")
        
        # Canvas State
        self._canvas_width = 1920
        self._canvas_height = 1080
        self._fill_color = "#ffffff" # Default background fill color
        
        # Layer State
        self.layers = [] # List of Layer objects
        self._active_layer_index = 0
        
        # View State (Panning)
        self._view_offset = QPointF(50, 50)
        self._zoom_level = 1.0
        self._is_saving = False # Guard for saving process
        
        # Brush/Tool State
        self._current_tool = "brush" 
        self._brush_size = 20
        self._brush_color = QColor("#000000")
        self._brush_opacity = 1.0
        self._brush_smoothing = 0.5 # Default stabilizer
        self._brush_hardness = 0.8
        self._brush_blend_mode = QPainter.CompositionMode.CompositionMode_SourceOver # Default Normal
        
        # Pressure Curve (Cubic Bezier Control Points: P1x, P1y, P2x, P2y)
        # Default is Linear: P1=(0.25, 0.25), P2=(0.75, 0.75) roughly
        # We store normalized control points. Origin (0,0) and End (1,1) are implied.
        self._pressure_curve = [(0.25, 0.25), (0.75, 0.75)] 
        
        self._brush_roundness = 1.0 # 1.0 = Circle, <1.0 = Oval
        self._brush_angle = 0.0 # Fixed angle in degrees
        self._brush_roundness = 1.0 # 1.0 = Circle, <1.0 = Oval
        self._brush_angle = 0.0 # Fixed angle in degrees
        self._brush_roundness = 1.0 # 1.0 = Circle, <1.0 = Oval
        self._brush_angle = 0.0 # Fixed angle in degrees
        self._brush_dynamic_angle = False # Rotate with stroke?
        
        # Fill Tool State
        self._fill_tolerance = 30
        self._fill_expand = 0 
        self._fill_mode = "bucket" 
        self._fill_sample_all = False
        self._lasso_points = []


        # Fill Tool State
        self._fill_tolerance = 30
        self._fill_expand = 0
        self._fill_mode = "bucket" 
        self._fill_sample_all = False
        self._lasso_points = []


        # Fill Tool State
        self._fill_tolerance = 30
        self._fill_expand = 0 # Expand in pixels (Gap Closing / Overfill)
        self._fill_mode = "bucket" # "bucket" or "lasso"
        self._fill_sample_all = False
        self._lasso_points = [] # For Lasso Fill

        self._brush_grain = 0.0 # Graphite grain texture
        self._brush_granulation = 0.0 # Pigment settling in valleys (Watercolor)
        self._brush_diffusion = 0.5 # How far pigment spreads in wet map
        self._brush_texture_cache = None # Cached dab image
        self._brush_texture_params = None # Parameters for cached dab
        self._cached_stamp = None # High-performance stamp cache
        self._current_pressure = 1.0
        
        # --- CUSTOM BRUSHES ---
        self._custom_brushes = {} # name -> {params, stamp_path}
        self._available_brushes = list(self.BRUSH_PRESETS.keys())
    

        
        # --- GLOBAL PAPER TEXTURE (Premium Realism) ---
        # We generate a seamless noise texture to simulate watercolor paper grain
        # This texture is static on the canvas, unlike brush tip noise.
        print("Generating Professional Paper Texture...")
        self._paper_texture_size = 1024
        self._paper_texture = self._generate_seamless_paper(self._paper_texture_size)
        self._current_cursor_rotation = 0.0
        self._last_point = None
        self._drawing = False
        
        # Viewport State
        self._view_offset = QPointF(50, 50) # Initial offset
        self._zoom_level = 1.0
        
        # Buffers for optimized painting (clipping masks)
        self._group_buffer = None # Reuse buffer for clipping masks
        self._temp_buffer = None
        
        # Undo/Redo
        self._undo_stack = []
        self._redo_stack = []
        
        self._current_brush_name = "Ink Pen"
        self._brush_spacing = 0.1 # 10%
        self._brush_spacing = 0.1 # 10%
        self._spacing_residue = 0.0 # Track distance between calls
        
        # --- OIL / REALISM STATE ---
        self._paint_load = 1.0 # 1.0 = Full, 0.0 = Dry
        self._brush_pickup_color = None # Color picked up from canvas (Dirty Brush)
        
        self._max_undo = 50 

        
        # --- PRO STRUCTURE: PERSISTENT MAPS ---
        # 1. WET MAP: Grayscale buffer (0=Dry, 1=Soaked)
        self._wet_map = np.zeros((self._canvas_height, self._canvas_width), dtype=np.float32)
        
        # 2. PIGMENT MAP: High-precision color density (R, G, B, Density)
        # This allows "lifting" paint and re-wetting dry areas.
        self._pigment_map = np.zeros((self._canvas_height, self._canvas_width, 4), dtype=np.float32)
        
        # 2. Drying Timer: Gradually dries the canvas
        from PyQt6.QtCore import QTimer
        self._dry_timer = QTimer(self)
        self._dry_timer.timeout.connect(self._evaporate_wet_map)
        self._dry_timer.start(3000) # Every 3 seconds
        self._native_initialized = False
        self._native_draw_queue = []
        if HAS_NATIVE_RENDER:
            # We delay object creation until _init_native_gl because the Renderer 
            # constructor calls initGLFunctions(), which requires an active context.
            self._native_renderer = None
            self._stroke_renderer = None
            print("Native Engine setup deferred to first frame.", flush=True)
        
        self._native_failed = False # Flag to stop endless retries
        print("QCanvasItem: fully initialized.", flush=True)

                
        # --- INPUT STATE ---
        self._last_pos = None
        self._drawing = False
        self._pressure_interp = 0.0
        
        # Habilitar eventos de ratón y tableta
        self.setAcceptedMouseButtons(Qt.MouseButton.AllButtons)
        self.setAcceptHoverEvents(True) # Para ver el cursor antes de pintar

        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._on_render_tick)
        self._render_timer.start(16) # ~60 FPS

    def _on_render_tick(self):
        """Called effectively at 60FPS to update the canvas."""
        # Placeholder for main loop logic if needed. 
        pass

    def _evaporate_wet_map(self):
        """Simulates drying of the canvas over time."""
        if hasattr(self, '_wet_map'):
             # Reduce wetness by 5% every 3 seconds
             self._wet_map *= 0.95
             # Clamp small values to 0 to avoid denormal numbers
             self._wet_map[self._wet_map < 0.01] = 0.0

    def _init_native_gl(self):
        """Initializes OpenGL resources on the GPU. Must be called with a valid context."""
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
                
        # Cursor behavior
        self.setAcceptHoverEvents(True)
        self.cursor_pos = QPointF(0, 0)
        self._is_hovering = False
        self._is_cursor_hidden = False
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

    # [Previous importABR removed as it was obsolete]

    def _update_available_brushes(self):
        self._available_brushes = list(self.BRUSH_PRESETS.keys()) + list(self._custom_brushes.keys())
        print(f"DEBUG: Available brushes updated. Total: {len(self._available_brushes)}", flush=True)
        self.availableBrushesChanged.emit()

    @pyqtProperty(str, notify=activeBrushNameChanged)
    def activeBrushName(self):
        return getattr(self, "_current_brush_name", "Pencil HB")

    @pyqtProperty(list, notify=availableBrushesChanged)
    def availableBrushes(self): 
        # Kept for backward compatibility
        return list(self.BRUSH_PRESETS.keys()) + list(self._custom_brushes.keys())
        return self._available_brushes


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
        
        # Calculate best zoom to fit (with 10% padding)
        padding = 0.9
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
        self.layers = []
        
        # Background layer
        bg = Layer(w, h, "Background", type="background")
        bg.image.fill(QColor(self._fill_color))
        bg.locked = True
        self.layers.append(bg)
        self.emit_layers_update()
        self.update()

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
            
        # If just a name is given, save to default legacy folder structure (for auto-save/quick save)
        # OR if it doesn't end in .aflow, assume it's a quick save name.
        if not os.path.isabs(path) and not path.lower().endswith(".aflow"):
            home = os.path.expanduser("~")
            projects_dir = os.path.join(home, "Documents", "ArtFlowProjects")
            os.makedirs(projects_dir, exist_ok=True)
            # Default new projects to .aflow format (Single File)
            if not path.lower().endswith(".aflow"):
                path += ".aflow"
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
            for layer in self.layers:
                if layer.visible:
                    p.setCompositionMode(layer.blend_mode)
                    p.setOpacity(layer.opacity)
                    p.drawImage(0, 0, layer.image)
            p.end()
            preview_img.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio).save(preview_buf, "PNG")
            print(f"Preview image prepared ({len(preview_ba)} bytes).", flush=True)

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

    @pyqtSlot(str, str, result=bool)
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
                            "created": meta.get("created", "")
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
        """Starts background thread to load recent projects."""
        print("Starting async project load...")
        thread = threading.Thread(target=self._scan_projects_thread)
        thread.daemon = True # Daemon so it doesn't block exit
        thread.start()

    @pyqtSlot(result=list)
    def getRecentProjects(self):
        # Legacy stub to prevent crashes if QML calls getting removed
        print("WARNING: getRecentProjects called synchronously. Use loadRecentProjectsAsync instead.")
        return []

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
            self._current_project_name = meta.get("name", os.path.basename(path).replace(".aflow", ""))
            self.currentProjectNameChanged.emit()
            
            self._current_project_path = path
            self.currentProjectPathChanged.emit()
            
            new_w = int(meta.get("width", 1920))
            new_h = int(meta.get("height", 1080))
            self._canvas_width = new_w
            self._canvas_height = new_h
            
            self.layers = []
            for lm in meta.get("layers", []):
                layer = Layer(new_w, new_h, lm.get("name", "Layer"), lm.get("type", "normal"))
                layer.visible = bool(lm.get("visible", True))
                layer.opacity = float(lm.get("opacity", 1.0))
                layer.blend_mode = self.BLEND_MODES.get(lm.get("blend_mode", "Normal"), QPainter.CompositionMode.CompositionMode_SourceOver)
                layer.locked = bool(lm.get("locked", False))
                layer.alpha_lock = bool(lm.get("alpha_lock", False))
                layer.depth = int(lm.get("depth", 0))
                layer.clipped = bool(lm.get("clipped", False))
                layer.clipped = bool(lm.get("clipped", False))
                layer.expanded = bool(lm.get("expanded", True))
                layer.is_private = bool(lm.get("is_private", False))
                
                fname = lm.get("filename", "")
                if fname in layer_images:
                    layer.image = layer_images[fname]
                
                self.layers.append(layer)
            
            if not self.layers: self.reset_canvas()
            
            self._active_layer_index = 0
            self._undo_stack = []
            self._redo_stack = []
            
            self.canvasWidthChanged.emit(new_w)
            self.canvasHeightChanged.emit(new_h)
            self.activeLayerChanged.emit(0)
            self.emit_layers_update()
            self.fitToView()
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
            path = QUrl(file_url).toLocalFile()
            if not os.path.exists(path): return False
            
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
                except OSError:
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
        
        painter.restore()

        # --- GHOST CURSOR ---
        if getattr(self, "_is_hovering", False):
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
                 painter.save()
                 # Reset transform to identity (Screen Space) because points are from event.pos
                 painter.resetTransform()
                 
                 from PyQt6.QtGui import QPolygonF
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

    def _apply_brush(self, point, pressure):
        """
        Dibuja una huella suave (Dab) en la posición indicada.
        Usa gradiente radial para bordes suaves y mezcla correcta.
        """
        if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers):
            return
            
        layer = self.layers[self._active_layer_index]
        if layer.locked: return

        # 1. Transformar coordenadas de Pantalla -> Lienzo
        # Es vital restar el offset y dividir por el zoom
        canvas_point = (point - self._view_offset) / self._zoom_level

        # 2. Calcular tamaño real
        # Mínimo 0.5px para evitar errores de renderizado
        rad = (self._brush_size * pressure) / 2.0
        if rad < 0.5: rad = 0.5
        
        painter = QPainter(layer.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 3. Configurar Modo de Composición
        if self._current_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        elif layer.alpha_lock:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        else:
            # USAR EL MODO DEL PINCEL (Ej: Multiply para Acuarela)
            painter.setCompositionMode(self._brush_blend_mode)

        # 4. Crear el Gradiente (Punta suave)
        grad = QRadialGradient(canvas_point, rad)
        color = QColor(self._brush_color)
        
        # La opacidad se maneja en el canal Alfa del color
        alpha = int(self._brush_opacity * 255)
        color.setAlpha(alpha)
        
        hardness = getattr(self, "_brush_hardness", 0.5)
        # Evitar dureza 0 o 1 absolutos para prevenir artefactos
        hardness = max(0.05, min(0.95, hardness))
        
        grad.setColorAt(0, color)         # Centro sólido
        grad.setColorAt(hardness, color)  # Hasta donde llega la dureza
        grad.setColorAt(1, QColor(0, 0, 0, 0)) # Borde transparente
        
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(canvas_point, rad, rad)
        painter.end()

    def _mix_kubelka_munk(self, canvas_patch_qimg, brush_patch_qimg, paper_patch, wet_patch, pigment_patch, opacity, pressure):
        """
        VIBRANT RMS MIXING ENGINE (The "Secret Sauce")
        Uses Root Mean Square in Inverse Space to preserve luminosity and punch.
        """
        w, h = canvas_patch_qimg.width(), canvas_patch_qimg.height()
        if w <= 0 or h <= 0: return canvas_patch_qimg, None
        
        # 1. Get Data (Float 0-1)
        # Using direct buffer access is fast
        c_ptr = canvas_patch_qimg.constBits()
        c_ptr.setsize(h * w * 4)
        bg_arr = np.frombuffer(c_ptr, dtype=np.uint8).reshape((h, w, 4)).astype(np.float32) / 255.0
        
        b_ptr = brush_patch_qimg.constBits()
        b_ptr.setsize(h * w * 4)
        fg_arr = np.frombuffer(b_ptr, dtype=np.uint8).reshape((h, w, 4)).astype(np.float32) / 255.0
        
        # Extract components
        bg_rgb = bg_arr[:,:,:3]
        bg_a = bg_arr[:,:,3:4]
        fg_rgb = fg_arr[:,:,:3]
        fg_a = fg_arr[:,:,3:4] * opacity # Apply brush opacity here
        
        # 2. PHYSICS: Paper Texture & Granulation
        # Instead of turning pixels black, we mask where paint CAN go.
        flow_mask = np.ones((h, w, 1), dtype=np.float32)
        
        if paper_patch is not None:
             if paper_patch.ndim == 2: paper_patch = paper_patch[:, :, np.newaxis]
             
             # Granulation: Pigment prefers valleys (low height)
             gran_intensity = getattr(self, '_brush_granulation', 0.0)
             
             if gran_intensity > 0.0:
                 # Calculate valley "attraction"
                 valley = 1.0 - paper_patch
                 # Noise texture for particulate look
                 noise = np.random.rand(h, w, 1).astype(np.float32)
                 
                 # The mask allows pigment in deep valleys, rejects on peaks
                 # (This preserves color luminosity, unlike adding black noise)
                 texture_allowance = 1.0 - (paper_patch * gran_intensity * 0.8) 
                 texture_noise = 1.0 - (noise * gran_intensity * 0.4)
                 
                 flow_mask = texture_allowance * texture_noise
        
        effective_brush_a = fg_a * flow_mask
        
        # 3. VIBRANT RMS MIXING
        # Treat transparent canvas as white (crucial for punchy colors)
        bg_rgb_effective = bg_rgb * bg_a + (1.0 - bg_a) * 1.0
        
        # Density (Dry vs Wet)
        diffusion = getattr(self, '_brush_diffusion', 0.0)
        density = np.clip(effective_brush_a * pressure, 0.0, 1.0)
        
        # CORE: RMS Subtractive (Mixing in Inverse Square Space)
        # Result = 1.0 - sqrt( (1-bg)^2 * (1-d) + (1-fg)^2 * d )
        bg_inv = 1.0 - bg_rgb_effective
        fg_inv = 1.0 - fg_rgb
        
        mixed_inv_sq = (bg_inv**2 * (1.0 - density)) + (fg_inv**2 * density)
        mix_rgb = 1.0 - np.sqrt(np.clip(mixed_inv_sq, 0.0, 1.0))

        # 4. Fluid Dynamics (Body/Smudge)
        if diffusion > 0.05:
              body_ratio = density * diffusion * 0.4
              mix_rgb = mix_rgb * (1.0 - body_ratio) + fg_rgb * body_ratio

        # 5. Output Alpha Update
        out_a = np.clip(bg_a + effective_brush_a, 0.0, 1.0)
        
        # Assembler
        out_arr = np.dstack((mix_rgb, out_a))
        out_arr = (np.clip(out_arr * 255.0, 0, 255)).astype(np.uint8)
        
        return QImage(out_arr.data, w, h, w * 4, QImage.Format.Format_ARGB32).copy(), None

    def _draw_inking_line_vector(self, lp1, lp2, width, color, pressure):
        """
        DEDICATED INKING ENGINE: Bypasses GPU/Splatting motors for pure sharp vectors.
        This provides 'Clip Studio' quality lines with 0 ghosting/blur.
        """
        if not self.layers: return
        active_layer = self.layers[self._active_layer_index]
        active_name = self.activeBrushName
        
        painter = QPainter(active_layer.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(self._brush_blend_mode)
        painter.setOpacity(self._brush_opacity)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        diff = lp2 - lp1
        dist = (diff.x()**2 + diff.y()**2)**0.5
        steps = int(dist) # 1px steps
        if steps < 1: steps = 1

        for i in range(steps + 1):
            t = i / steps
            pt = lp1 + diff * t
            
            # Apply Tool-Specific Pressure Curve
            if "G-Pen" in active_name:
                curr_size = width * (pressure ** 1.5)
            elif "Maru" in active_name:
                curr_size = (width * 0.5) * (0.8 + pressure * 0.2)
            else:
                curr_size = width * (0.3 + pressure * 0.7) if pressure < 1.0 else width
            
            curr_size = max(0.5, curr_size)
            painter.drawEllipse(pt, curr_size/2, curr_size/2)
        
        painter.end()
        self.update()

    def _generate_pencil_stamp(self, size, color):
        """Generates a high-quality granular lead stamp mimicking carbon dust."""
        size = int(max(2, size))
        
        param_key = (size, color.rgba())
        if getattr(self, "_last_pstamp_key", None) == param_key:
             return self._last_pstamp
             
        stamp = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        stamp.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(stamp)
        # 1. Ultra-Soft Base (Essential to avoid 'dots' when stacking)
        grad = QRadialGradient(size/2, size/2, size/2)
        # We use much lower alpha at center to allow overlap without 'beading'
        grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 160)) 
        grad.setColorAt(0.4, QColor(color.red(), color.green(), color.blue(), 80))
        grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # 2. Salt-and-Pepper Grain Carving
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        np.random.seed(size)
        noise = np.random.rand(size, size)
        # Porous lead mask
        lead_mask = (noise > 0.45).astype(np.uint8) * 255
        
        noise_img = QImage(lead_mask.data, size, size, size, QImage.Format.Format_Grayscale8)
        painter.drawImage(0, 0, noise_img)
        painter.end()
        
        np.random.seed(int(time.time() * 1000) % 2**32)
        self._last_pstamp_key = param_key
        self._last_pstamp = stamp
        return stamp

    def _draw_pencil_line_traditional(self, lp1, lp2, width, color, pressure):
        """
        DEDICATED PENCIL ENGINE: Analogue Lead Simulation.
        Features paper-tooth interaction and porous carbon accumulation.
        """
        if not self.layers: return
        active_layer = self.layers[self._active_layer_index]
        
        painter = QPainter(active_layer.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Multiply is essential for graphite dark-on-dark stacking
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        
        diff = lp2 - lp1
        dist = (diff.x()**2 + diff.y()**2)**0.5
        
        # Optimized Step: 5% of width for perfect grain layering
        step_dist = max(0.4, width * 0.05)
        steps = int(dist / step_dist)
        if steps < 1: steps = 1

        for i in range(steps + 1):
            t = i / steps
            pt = lp1 + diff * t
            
            # 1. Paper Tooth Physics (Lead Deposits only on raised fibers)
            paper_mod = 1.0
            if self._paper_texture is not None:
                try:
                    tx, ty = int(pt.x()) % self._paper_texture_size, int(pt.y()) % self._paper_texture_size
                    tooth = self._paper_texture[ty, tx]
                    # Soft Threshold: Smoothly fade in/out based on paper peaks
                    p_threshold = 1.0 - (pressure * 0.8)
                    paper_mod = np.clip((tooth - p_threshold) * 5.0, 0.2, 1.0)
                except: pass

            # 2. Sensorial Jitter (Reduced to avoid clustering)
            jitter = (width * 0.02) * (1.1 - pressure)
            jx = (np.random.normal(0, jitter))
            jy = (np.random.normal(0, jitter))
            
            # 3. Layering Logic: Balanced opacity for smooth accumulation
            curr_size = width * (0.6 + pressure * 0.4)
            # Reduced opacity for better blend-in
            curr_opacity = (0.15 + pressure * 0.45) * paper_mod
            
            painter.save()
            painter.setOpacity(curr_opacity)
            painter.translate(pt.x() + jx, pt.y() + jy)
            # Hide noise patterns by rotating every dab
            painter.rotate(np.random.randint(0, 360))
            
            stamp = self._generate_pencil_stamp(curr_size, color)
            painter.drawImage(QRectF(-curr_size/2, -curr_size/2, curr_size, curr_size), stamp)
            painter.restore()
        
        painter.end()
        self.update()

    def _draw_textured_line(self, p1, p2, width, color, segment_pressure=1.0):
        """Main Drawing Router: Directs tools to their specific motors."""
        
        # 0. Common Setup and Transformation
        active_name = self.activeBrushName
        lp1 = (p1 - self._view_offset) / self._zoom_level
        lp2 = (p2 - self._view_offset) / self._zoom_level
        
        # TRAFFIC CONTROLLER: Absolute Segregation of Engines
        # 1. Detect Pencil/Charcoal/Graphite FIRST (Higher priority to avoid "pencil" matching "pen")
        is_pencil = any(k in active_name.lower() or k in self._current_tool.lower() for k in ["pencil", "lapiz", "charcoal", "hb", "6b", "graphite"])
        
        # 2. Detect Inking Tools (Ink, Maru, G-Pen)
        # We explicitly exclude "pencil" from the pen check for safety
        is_pen = not is_pencil and any(k in active_name.lower() or k in self._current_tool.lower() for k in ["ink", "maru", "g-pen", "pluma", "marker", "entintado"])
        # Special case: "Pen" alone (but not in Pencil)
        if not is_pen and not is_pencil:
             is_pen = "pen" in active_name.lower() or "pen" in self._current_tool.lower()

        # --- DISPATCH TO ENGINES ---
        
        # 1. MODE: PENCIL (Graphite Texture, Multiply, Paper Tooth)
        if is_pencil:
            self._draw_pencil_line_traditional(lp1, lp2, width, color, segment_pressure)
            return

        # 2. MODE: INKING (Sharp Vectors, Hard Edge, Solid)
        elif is_pen:
            self._draw_inking_line_vector(lp1, lp2, width, color, segment_pressure)
            return

        # 3. MODE: OIL / ACQUARELLE (Native/Software)
        if not (HAS_NATIVE_RENDER and self._native_initialized):
            # Software Fallback for Pencils/Oil/Water
            active_layer = self.layers[self._active_layer_index]
            painter = QPainter(active_layer.image)
            res = self._draw_textured_line_software_fallback(painter, lp1, lp2, width, color, segment_pressure)
            painter.end()
            return res

        # NATIVE PING-PONG ENGINE (For Realistic Oil/Watercolor)
        # Upload Brush Tip if changed
        stamp = self._get_brush_stamp(int(self._brush_size), color)
        param_key = (self._brush_size, color.rgba(), self._brush_grain, self._brush_hardness, self._current_tool)
        
        if getattr(self, '_last_native_stamp_params', None) != param_key:
             qimg = stamp.convertToFormat(QImage.Format.Format_RGBA8888)
             ptr = qimg.constBits()
             ptr.setsize(qimg.sizeInBytes())
             self._stroke_renderer.setBrushTip(bytes(ptr), qimg.width(), qimg.height())
             self._last_native_stamp_params = param_key

        diff = lp2 - lp1
        dist = (diff.x()**2 + diff.y()**2)**0.5
        is_wet = (self._brush_diffusion > 0.1) or ("Water" in active_name) or (self._current_tool == "water")
        is_oil = "Oil" in active_name or "Acrylic" in active_name
        
        if is_wet:
            step_dist = max(2.0, width * 0.08)
        elif is_oil:
            step_dist = max(1.0, width * 0.02)
        else:
            density = 0.10 if width >= 5 else 0.2
            step_dist = max(0.5, width * density)
            
        steps = int(dist / step_dist)
        if steps < 1: steps = 1
        
        self._native_renderer.beginFrame() 
        self._stroke_renderer.beginFrame(self._canvas_width, self._canvas_height)
        c_vec = [color.redF(), color.greenF(), color.blueF(), self._brush_opacity]
        
        ldiff = lp2 - lp1
        for i in range(steps + 1):
            t = i / steps
            pt = lp1 + ldiff * t
            lx, ly = pt.x(), pt.y()
            pressure = segment_pressure
            if steps > 5:
                if i < 3: pressure *= (i / 3.0)
                if (steps - i) < 3: pressure *= ((steps - i) / 3.0)

            self._native_renderer.swapBuffers()
            self._stroke_renderer.drawDabPingPong(
                lx, ly, width, self._current_cursor_rotation,
                c_vec, self._brush_hardness, pressure, 1,
                self._native_renderer.getSourceTexture(), 0
            )
            
        self._stroke_renderer.endFrame()
        self._native_renderer.endFrame()
        self._sync_active_layer_from_native()
        self.update()

    def _sync_active_layer_to_native(self):
        """Uploads the current layer's pixels to the GPU."""
        if not HAS_NATIVE_RENDER or not self._native_initialized: return
        active_layer = self.layers[self._active_layer_index]
        mirrored = active_layer.image.mirrored().convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = mirrored.constBits()
        ptr.setsize(mirrored.sizeInBytes())
        self._native_renderer.setBufferData(bytes(ptr))
        # print("Sync Layer -> Native")

    def _draw_textured_line_software_fallback(self, painter, p1, p2, width, color, pressure=1.0):
        """Software fallback logic - Ultra-Stable Ribbon Engine."""
        if not self.layers or self._active_layer_index >= len(self.layers): return
        
        diff = p2 - p1
        dist = (diff.x()**2 + diff.y()**2)**0.5
        if dist < 0.1: return # Ignore micro-moves
        
        # 1. Dynamic Spacing & Step Throttling (STABILITY FIRST)
        spacing_val = getattr(self, "_brush_spacing", 0.1)
        active_name = self.activeBrushName
        is_wet = (self._brush_diffusion > 0.1) or ("Water" in active_name) or (self._current_tool == "water")
        is_oil = "Oil" in active_name or "Acrylic" in active_name
        
        # Adaptive step distance to prevent OOM
        if is_wet:
            base_s = 0.08 if width > 60 else 0.06
            step_dist = max(2.0, width * base_s) 
        elif is_oil:
            base_s = 0.03 if width > 100 else 0.015
            step_dist = max(1.0, width * base_s)
        else:
            # PROFESSIONAL INKING: Minimal spacing for smooth line art (Step 1.0)
            is_pen = any(k in active_name for k in ["Pen", "Ink", "Maru", "G-Pen", "Pluma", "Marker", "Inking"])
            if is_pen:
                step_dist = 1.0 # Force 1px step for perfect continuity
            else:
                step_dist = max(0.5, width * spacing_val)
        
        # 2. Accumulate distance
        prev_residue = self._spacing_residue
        total_dist = prev_residue + dist
        if total_dist < step_dist:
            self._spacing_residue = total_dist
            return
            
        # DYNAMIC LIMIT: Prevents crashes while maintaining detail
        if width > 300: limit = 15
        elif width > 150: limit = 40
        elif width > 50: limit = 100
        else: limit = 300
        
        steps = min(int(total_dist / step_dist), limit)
        self._spacing_residue = total_dist % step_dist
        
        t_batch_start = time.time()
        dab_size = int(max(1, width))

        for i in range(steps):
            # Strict safety break (0.1s total per segment)
            if time.time() - t_batch_start > 0.1: break 
            
            t = np.clip(((i + 1) * step_dist - prev_residue) / dist, 0.0, 1.0)
            pt = p1 + diff * t
            
            # --- A. WATERCOLOR / WET ENGINE (Optimized) ---
            if is_wet:
                 try:
                     dx, dy = int(pt.x() - dab_size/2), int(pt.y() - dab_size/2)
                     d_rect = QRect(dx, dy, dab_size, dab_size).intersected(QRect(0, 0, self._canvas_width, self._canvas_height))
                     if d_rect.width() < 2 or d_rect.height() < 2: continue

                     img_ref = self.layers[self._active_layer_index].image
                     canvas_patch = img_ref.copy(d_rect).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
                     
                     w, h = d_rect.width(), d_rect.height()
                     composite = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
                     composite.fill(Qt.GlobalColor.transparent)
                     cp = QPainter(composite)
                     
                     p_bits = canvas_patch.bits()
                     p_bits.setsize(h * w * 4)
                     arr = np.frombuffer(p_bits, np.uint8).reshape((h, w, 4))
                     
                     if np.max(arr) > 0:
                          blur_k = max(3, int(width * 0.1) | 1)
                          if blur_k > 31: blur_k = 31 
                          blurred_arr = cv2.GaussianBlur(arr, (blur_k, blur_k), 0)
                          blurred_img = QImage(blurred_arr.data, w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()
                          cp.drawImage(0, 0, blurred_img)
                          
                          cp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                          soft_tip = self._get_brush_stamp(w, QColor(255, 255, 255))
                          cp.drawImage(0, 0, soft_tip)
                     
                     if "Blend" not in active_name:
                          cp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                          colored_tip = self._get_brush_stamp(w, self._brush_color)
                          cp.setOpacity(0.35) 
                          cp.drawImage(0, 0, colored_tip)
                     cp.end()
                     
                     painter.save()
                     painter.setOpacity(min(1.0, self._brush_opacity * pressure * 0.2))
                     painter.drawImage(d_rect.topLeft(), composite)
                     painter.restore()
                     if self._current_tool == "water": continue 
                 except: pass

            # --- B. OIL ENGINE ---
            elif is_oil:
                 s_pt = QPoint(int(pt.x()), int(pt.y()))
                 draw_color = color
                 self._paint_load = max(0.1, self._paint_load - 0.001)
                 mod_opacity = (self._brush_opacity * pressure) * (self._paint_load * 0.8 + 0.2)
                 
                 if 0 <= s_pt.x() < self._canvas_width and 0 <= s_pt.y() < self._canvas_height:
                        cv = self.layers[self._active_layer_index].image.pixelColor(s_pt)
                        if cv.alpha() > 20:
                            draw_color = self._mix_colors_fresco(draw_color, cv, 0.4 * (1.1 - self._paint_load))

                 painter.save()
                 painter.translate(pt.x(), pt.y())
                 angle_deg = 0
                 if dist > 0.5:
                    import math
                    angle_deg = math.degrees(math.atan2(diff.y(), diff.x()))
                 painter.rotate(angle_deg + np.random.uniform(-5, 5))
                 painter.setOpacity(mod_opacity) 
                 stamp = self._get_brush_stamp(dab_size, draw_color)
                 painter.drawImage(QRectF(-dab_size/2, -dab_size/2, dab_size, dab_size), stamp)
                 painter.restore()

            # --- C. INKING ENGINE (Vector Sharp) ---
            elif is_pen:
                # 1. Physical Style Selection
                if "G-Pen" in active_name:
                    # Sensitive pressure curve (exponencial)
                    ink_size = self._brush_size * (pressure ** 1.5)
                elif "Maru" in active_name:
                    # Precise and rigid
                    ink_size = (self._brush_size * 0.5) * (0.8 + pressure * 0.2)
                else:
                    # Standard Marker / Ink Pen
                    ink_size = width
                
                # Minimum size to maintain line integrity
                ink_size = max(0.5, ink_size)

                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setCompositionMode(self._brush_blend_mode)
                # Inking is ALWAYS opaque in its core
                painter.setOpacity(self._brush_opacity) 
                
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                
                # Draw sharp circle directly (Vector feel)
                painter.drawEllipse(pt, ink_size/2, ink_size/2)
                painter.restore()

            # --- D. SKETCHING ENGINE (Pencils HB, 6B) ---
            elif "Pencil" in active_name:
                # Organic Graphite Logic
                eff_opacity = self._brush_opacity * (0.2 + pressure * 0.8)
                eff_width = width
                
                # Jitter: Break the perfect line for more organic feel
                jx = (np.random.rand() - 0.5) * (width * 0.05) if self._brush_grain > 0.1 else 0
                jy = (np.random.rand() - 0.5) * (width * 0.05) if self._brush_grain > 0.1 else 0

                # Paper Interaction: Graphite catches more on peaks
                if self._paper_texture is not None and self._brush_grain > 0.1:
                    try:
                        tx, ty = int(pt.x()) % self._paper_texture_size, int(pt.y()) % self._paper_texture_size
                        paper_val = self._paper_texture[ty, tx]
                        # At low pressure, only peaks (white) get lead. At high pressure, valleys fill too.
                        eff_opacity *= (paper_val * (1.5 - pressure) + pressure)
                    except: pass

                painter.save()
                painter.translate(pt.x() + jx, pt.y() + jy)
                painter.setOpacity(eff_opacity)
                # Pencils always blend in Multiply for realistic stacking
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                
                # Random rotation helps hide texture repetition
                painter.rotate(np.random.uniform(0, 360))
                
                stamp = self._get_brush_stamp(dab_size, color)
                painter.drawImage(QRectF(-dab_size/2, -dab_size/2, dab_size, dab_size), stamp)
                painter.restore()

            # --- E. STANDARD (Soft brushes, Airbrushes, etc) ---
            else:
                f_op = self._brush_opacity * pressure
                # Restoration of organic jitter for pencils
                jx, jy = 0, 0
                if self._brush_grain > 0.1:
                    jitter_amt = width * 0.05
                    jx = (np.random.rand() - 0.5) * jitter_amt
                    jy = (np.random.rand() - 0.5) * jitter_amt

                painter.save()
                painter.translate(pt.x() + jx, pt.y() + jy)
                
                angle = 0
                if getattr(self, "brushDynamicAngle", False):
                    import math
                    angle = math.atan2(diff.y(), diff.x()) * 180 / math.pi
                
                # Organic Rotation Jitter
                if self._brush_grain > 0.1:
                    angle += np.random.uniform(0, 360)
                
                if angle != 0: painter.rotate(angle)
                
                # Enhanced Texture Modulation (Pencils only)
                if self._paper_texture is not None and self._brush_grain > 0.05:
                    try:
                        tx, ty = int(pt.x()) % self._paper_texture_size, int(pt.y()) % self._paper_texture_size
                        paper_val = self._paper_texture[ty, tx]
                        f_op *= (0.2 + paper_val * 1.3 * self._brush_grain)
                    except: pass
                
                painter.setOpacity(f_op)
                painter.setCompositionMode(self._brush_blend_mode)
                
                stamp = self._get_brush_stamp(dab_size, color)
                # Respect Brush Roundness (Squash)
                s_width = dab_size
                s_height = int(dab_size * getattr(self, "_brush_roundness", 1.0))
                painter.drawImage(QRectF(-s_width/2, -s_height/2, s_width, s_height), stamp)
                painter.restore()

    def _generate_seamless_paper(self, size):
        """Generates a high-contrast 'Gritty Fiber' paper texture for pencils."""
        try:
            # 1. Base Structural Fibers (Low Frequency)
            noise_small = np.random.randint(100, 200, (size//16, size//16), dtype=np.uint8)
            fiber_layer = cv2.resize(noise_small, (size, size), interpolation=cv2.INTER_CUBIC)
            fiber_layer = cv2.GaussianBlur(fiber_layer, (31, 31), 0)
            
            # 2. High-Frequency Tooth (The 'Grit')
            grit_layer = np.random.randint(0, 255, (size, size), dtype=np.uint8)
            grit_layer = cv2.GaussianBlur(grit_layer, (3, 3), 0)
            
            # 3. Mix & Sculpt (Combine layers)
            paper = (fiber_layer.astype(np.float32) * grit_layer.astype(np.float32)) / 255.0
            
            # 4. Final Normalization with aggressive contrast for 'tooth'
            # We want peaks to be near 1.0 and valleys much darker
            paper_f = paper / 255.0
            paper_f = np.clip((paper_f - 0.45) * 2.8, 0.0, 1.0)
            
            # Soften only the harsh edges
            paper_f = cv2.GaussianBlur(paper_f, (3, 3), 0)
            
            return paper_f
        except Exception as e:
            print(f"Texture Gen Error: {e}")
            return np.ones((size, size), dtype=np.float32)

    def _get_paper_patch(self, x, y, w, h):
        """Extracts a patch from the seamless paper texture with wrapping."""
        if self._paper_texture is None:
             return np.ones((h, w), dtype=np.float32)
             
        # Texture Size
        ts = self._paper_texture_size
        
        # Coordinates wrapped
        tx = x % ts
        ty = y % ts
        
        # Output buffer
        patch = np.zeros((h, w), dtype=np.float32)
        
        # Copy logic handling wrap-around for X and Y in one go is complex with pure slicing
        # because we might cross the boundary 0, 1, or 2 times (if patch > size, unlikely)
        # Simplified: Copy row by row or block by block? 
        # Actually, numpy.roll is expensive.
        # Let's use simple logic:
        # If fits in one block, just slice.
        # If crosses edge, slice two parts and concat.
        
        # Y-axis logic
        y_remaining = h
        y_curr = 0
        src_y = ty
        
        while y_remaining > 0:
            copy_h = min(y_remaining, ts - src_y)
            
            # X-axis logic inside Y loop
            x_remaining = w
            x_curr = 0
            src_x = tx
            
            while x_remaining > 0:
                copy_w = min(x_remaining, ts - src_x)
                
                # Copy block
                patch[y_curr:y_curr+copy_h, x_curr:x_curr+copy_w] = \
                    self._paper_texture[src_y:src_y+copy_h, src_x:src_x+copy_w]
                
                x_curr += copy_w
                src_x = (src_x + copy_w) % ts
                x_remaining -= copy_w
                
            y_curr += copy_h
            src_y = (src_y + copy_h) % ts
            y_remaining -= copy_h
            
        return patch

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
        if self._current_tool != tool:
            self._current_tool = tool
            self._update_native_cursor()
            self.currentToolChanged.emit(tool)
            # Trigger refresh of brush list
            self.availableBrushesChanged.emit()
    @pyqtProperty(float, notify=brushSmoothingChanged)
    def brushSmoothing(self): return self._brush_smoothing
    @brushSmoothing.setter
    def brushSmoothing(self, val):
        if self._brush_smoothing != val:
            self._brush_smoothing = val
            self.brushSmoothingChanged.emit(val)

    @pyqtProperty(str, notify=activeBrushNameChanged)
    def activeBrushName(self): return getattr(self, "_current_brush_name", "")
    @activeBrushName.setter
    def activeBrushName(self, name): self.usePreset(name)

    @pyqtProperty(list, notify=availableBrushesChanged)
    def brushFolders(self):
        """Returns brushes grouped by category for QML UI, filtered by Active Tool."""
        print(f"DEBUG: brushFolders called for tool '{self._current_tool}'. Custom brushes: {len(self._custom_brushes)}", flush=True)
        if not hasattr(self, "BRUSH_PRESETS"): return []
        
        # 1. Define Filter Keywords based on Tool
        keywords = []
        if self._current_tool == "pen":
            keywords = ["Pen", "Ink", "Marker", "G-Pen", "Maru"]
        elif self._current_tool == "pencil":
            keywords = ["Pencil", "HB", "6B", "Mechanical"]
        elif self._current_tool in ["brush", "water"]: # Unified category for Paint + Water
            keywords = ["Water", "Oil", "Acrylic", "Wash", "Blend", "Mineral"]
        elif self._current_tool == "airbrush":
            keywords = ["Soft", "Hard"] # Be careful with Eraser Hard
        elif self._current_tool == "eraser":
            keywords = ["Eraser"]
        else:
            # For other tools (hand, etc), maybe show nothing or all?
            # User wants "well divided", so maybe show nothing if tool has no brushes.
            return []

        # 2. Build Category Map
        folders = {}
        
        # Helper to categorize
        def get_category(name):
            if "Watercolor" in name or "Wash" in name or "Blend" in name: return "Watercolor"
            if "Oil" in name or "Acrylic" in name: return "Painting"
            if "Pen" in name or "Ink" in name or "Marker" in name: return "Inking"
            if "Pencil" in name: return "Sketching"
            if "Eraser" in name: return "Erasers"
            if "Soft" in name or "Hard" in name: return "Airbrushing"
            if "G-Pen" in name or "Maru" in name: return "Inking"
            return "Standard"

        # Filter Presets
        for name in self.BRUSH_PRESETS.keys():
            # Exclude Erasers from Airbrush "Hard" match logic if needed, but handled by keywords.
            
            # Logic:
            # If tool is specific (Pen, Pencil, Airbrush, Eraser), look for strict match.
            # If tool is generic (Brush/Water), show strict matches AND anything that doesn't belong to others.
            
            should_include = False
            
            # 1. Check strict keyword match
            strict_match = False
            for k in keywords:
                if k in name: 
                    strict_match = True
                    break
            
            if strict_match:
                should_include = True
            elif self._current_tool in ["brush", "water"]:
                # 2. Fallback for Brush Tool: Include if it doesn't look like a Pen/Pencil/Airbrush/Eraser
                # This prevents "Round Brush" from disappearing.
                is_other = False
                other_keywords = ["Pen", "Ink", "Marker", "Pencil", "HB", "6B", "Airbrush", "Eraser"]
                for ok in other_keywords:
                    if ok in name:
                        is_other = True
                        break
                if not is_other:
                    should_include = True
            
            if should_include:
                cat = get_category(name)
                
                # Exclude Airbrushes from the Painting/Water view (keep them in Airbrush tool)
                if self._current_tool in ["brush", "water"] and cat == "Airbrushing":
                    should_include = False
            
            if should_include:
                if cat not in folders: folders[cat] = []
                folders[cat].append(name)

        # Filter Custom Brushes
        for name, data in getattr(self, "_custom_brushes", {}).items():
            cat = data.get("category", "Imported")
            # If tool is generic, show all? No, strive for relevance.
            # Showing all custom brushes might be noise.
            # For now, let's include Custom Brushes ONLY if they match the tool context 
            # OR if we assume all imported ABRs are generally useful.
            # User request: "appear... pens when I press pen". 
            # Let's show all imported brushes in their own folders for now, as we can't easily auto-classify them by tool type yet without metadata.
            # OPTIONAL: Filter by name too if possible?
            
            # Let's just add them.
            if cat not in folders: folders[cat] = []
            folders[cat].append(name)
            
        # 3. Format result
        result = []
        
        # Priority sort
        priority = ["Inking", "Sketching", "Painting", "Watercolor", "Airbrushing", "Erasers", "Imported"]
        
        for p in priority:
            if p in folders and folders[p]:
                result.append({"name": p, "brushes": sorted(folders.pop(p))})
        
        # Others
        for cat in sorted(folders.keys()):
             if folders[cat]:
                 result.append({"name": cat, "brushes": sorted(folders[cat])})
                 
        print(f"DEBUG: brushFolders computed: {[r['name'] for r in result]}", flush=True)
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
    def brushGrain(self): return self._brush_grain
    @brushGrain.setter
    def brushGrain(self, val):
        if self._brush_grain != val:
            self._brush_grain = val
            self._last_stamp_params = None # Force Texture Update
            self.brushGrainChanged.emit(val)

    @pyqtProperty(float, notify=cursorRotationChanged)
    def cursorRotation(self): return self._current_cursor_rotation

    @pyqtProperty(float, notify=brushGranulationChanged)
    def brushGranulation(self): return getattr(self, '_brush_granulation', 0.0)
    @brushGranulation.setter
    def brushGranulation(self, val):
        val = max(0.0, min(val, 1.0))
        if getattr(self, '_brush_granulation', 0.0) != val:
            self._brush_granulation = val
            self.brushGranulationChanged.emit(val)

    @pyqtProperty(float, notify=brushDiffusionChanged)
    def brushDiffusion(self): return getattr(self, '_brush_diffusion', 0.0)
    @brushDiffusion.setter
    def brushDiffusion(self, val):
        val = max(0.0, min(val, 1.0))
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
        """Returns base64 encoded png of current brush tip for Ghost Cursor."""
        # Use a moderate size for preview (64px)
        stamp = self._get_brush_stamp(64, QColor(0, 0, 0))
        if stamp and not stamp.isNull():
             ba = QByteArray()
             buffer = QBuffer(ba)
             buffer.open(QIODevice.OpenModeFlag.WriteOnly)
             stamp.save(buffer, "PNG")
             return "data:image/png;base64," + base64.b64encode(ba.data()).decode()
        return ""
    
    @pyqtProperty(int)
    def cursorX(self): return int(self.cursor_pos.x()) if hasattr(self, 'cursor_pos') else 0
    
    @pyqtProperty(int)
    def cursorY(self): return int(self.cursor_pos.y()) if hasattr(self, 'cursor_pos') else 0

    @pyqtProperty(float, notify=cursorPressureChanged)
    def cursorPressure(self): return self._current_pressure

    # --- FILL TOOL PROPERTIES ---
    @pyqtProperty(int, notify=fillToleranceChanged)
    def fillTolerance(self): return self._fill_tolerance
    @fillTolerance.setter
    def fillTolerance(self, val):
        if self._fill_tolerance != val:
            self._fill_tolerance = val
            self.fillToleranceChanged.emit(val)

    @pyqtProperty(int, notify=fillExpandChanged)
    def fillExpand(self): return self._fill_expand
    @fillExpand.setter
    def fillExpand(self, val):
        if self._fill_expand != val:
            self._fill_expand = val
            self.fillExpandChanged.emit(val)

    @pyqtProperty(str, notify=fillModeChanged)
    def fillMode(self): return self._fill_mode
    @fillMode.setter
    def fillMode(self, val):
        if self._fill_mode != val:
            self._fill_mode = val
            self.fillModeChanged.emit(val)

    @pyqtProperty(bool, notify=fillSampleAllChanged)
    def fillSampleAll(self): return self._fill_sample_all
    @fillSampleAll.setter
    def fillSampleAll(self, val):
        if self._fill_sample_all != val:
            self._fill_sample_all = val
            self.fillSampleAllChanged.emit(val)



    @pyqtProperty(QPointF, notify=viewOffsetChanged)
    def viewOffset(self):
        return self._view_offset

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
            # Constrain zoom
            self._zoom_level = max(0.01, min(val, 10.0))
            self.zoomLevelChanged.emit(self._zoom_level)
            self.update()

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

    cursorPosChanged = pyqtSignal(float, float, arguments=['x', 'y'])

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
            # Use unified handler
            self._handle_input(pos, pressure, rotation, is_press=True)
            event.accept()
            
        elif t == QTabletEvent.Type.TabletMove:
            self._handle_input(pos, pressure, rotation, is_press=False)
            event.accept()
            
        elif t == QTabletEvent.Type.TabletRelease:
            self._drawing = False
            self._last_point = None
            self.emit_layers_update()
            
            # Timelapse Trigger
            self._timelapse_stroke_count += 1
            if self._timelapse_stroke_count % 1 == 0: # Capture EVERY stroke for smooth video
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
        # print(f"MousePress: src={event.source()} dev={event.device().type()}", flush=True) # DEBUG
        
        self._drawing = True
        self._last_point = event.position()
        
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
        if not self._drawing: return # Only track drag
        
        current_point = event.position()
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
        self._drawing = False
        self._last_point = None
        
        # LASSO FILL TRIGGER
        if self._current_tool == "fill" and self._fill_mode == "lasso":
            self.apply_lasso_fill()
            self._lasso_points = []
            self.update()

        self.emit_layers_update() 

        
        # Timelapse Trigger
        self._timelapse_stroke_count += 1
        if self._timelapse_stroke_count % 1 == 0:
            self._capture_timelapse_frame()
            
        event.accept()



    def _handle_input(self, current_point, pressure, rotation, is_press=False):
        """Unified Input Handler for Tablet and Mouse."""
        if self._current_tool == "hand":
             if is_press: 
                 self._last_point = current_point # Important to reset anchor
                 return 
             if self._last_point:
                 delta = current_point - self._last_point
                 self.viewOffset = self._view_offset + delta
                 self._last_point = current_point
             return

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
            self._prev_point = current_point # Store specific previous point for Bezier
            self._mid_point = current_point # Store calculated mid point
            
        else:
            # --- STEP 2: STROKE INTERPOLATION (Quadratic Bezier) ---
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
    
    def loadBrushTip(self, name):
        """Carga la textura de la punta del pincel en el motor."""
        if name in self._custom_brushes:
            brush = self._custom_brushes[name]
            
            # Check if we already have a cached QImage
            if "cached_stamp" in brush:
                self._current_brush_name = name
                self.brushSize = brush.get("size", 50)
                self.brushSpacing = brush.get("spacing", 0.1)
                self.brushOpacity = brush.get("opacity", 1.0)
                self.brushHardness = brush.get("hardness", 0.5)
                self.brushColorChanged.emit(self._brush_color.name())
                return

            # Fallback for old brushes with PIL tip_data
            tip_img = brush.get("tip_data")
            if tip_img:
                try:
                    from PIL import Image, ImageOps
                    if tip_img.mode != "RGBA":
                        if tip_img.mode == "L":
                             rgb = Image.new("RGB", tip_img.size, (255,255,255))
                             tip_img = Image.merge("RGBA", (*rgb.split(), tip_img))
                        else:
                             tip_img = tip_img.convert("RGBA")
                        
                    ptr = tip_img.tobytes("raw", "RGBA")
                    qimg = QImage(ptr, tip_img.width, tip_img.height, QImage.Format.Format_RGBA8888).copy()
                    
                    brush["cached_stamp"] = qimg 
                    self._current_brush_name = name
                    self.brushSize = brush.get("size", 20)
                    self.brushSpacing = brush.get("spacing", 0.1)
                    self.brushOpacity = brush.get("opacity", 1.0)
                    self.brushHardness = brush.get("hardness", 0.5)
                    self.brushColorChanged.emit(self._brush_color.name()) 
                except Exception as e:
                    print(f"Error loading brush tip {name}: {e}")

    @pyqtProperty(str, notify=brushTipImageChanged)
    def brushTip(self):
        """Returns base64 encoded png of current brush tip for Ghost Cursor."""
        # Use a moderate size for preview (64px)
        # Fix: Use current brush color instead of black, so user sees what they paint!
        stamp = self._get_brush_stamp(64, self._brush_color)
        if stamp and not stamp.isNull():
             ba = QByteArray()
             buffer = QBuffer(ba)
             buffer.open(QIODevice.OpenModeFlag.WriteOnly)
             stamp.save(buffer, "PNG")
             return "data:image/png;base64," + base64.b64encode(ba.data()).decode()
        return ""
                
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

    @pyqtSlot(str, result=int)
    def importABR(self, file_url):
        """
        Lee un archivo .abr, extrae los pinceles y genera máscaras blancas con transparencia.
        """
        path = QUrl(file_url).toLocalFile() if "://" in file_url else file_url
        if not os.path.exists(path):
            print(f"Error: Archivo no encontrado en {path}")
            return 0

        try:
            print(f"--- INICIANDO IMPORTACIÓN ABR: {os.path.basename(path)} ---")
            
            if not globals().get('HAS_PY_ABR', False):
                 print("Error: PyABRParser no disponible.")
                 return 0
                 
            parser_results = PyABRParser.parse(path)
            if not hasattr(parser_results, 'brushes'): return 0
                
            brushes_extracted = 0
            
            for i, brush_data in enumerate(parser_results.brushes):
                try:
                    # 1. Decodificación de nombre
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
                        print(f"  [OK] '{final_name}'")
                    
                except Exception as inner_e:
                    print(f"  [ERROR] Pincel {i} falló: {inner_e}")

            self._update_available_brushes()
            return brushes_extracted

        except Exception as e:
            print(f"Fallo crítico ABR: {e}")
            return 0

    def geometryChange(self, new_geometry, old_geometry):
        super().geometryChange(new_geometry, old_geometry)
        # If resized, we might need to recreate layers or just accept clipping
        if not self.layers:
            self.reset_canvas()

    @pyqtSlot(float, float, QColor)
    def apply_color_drop(self, x, y, new_color):
        if not self.layers or self._active_layer_index < 0:
            return

        layer = self.layers[self._active_layer_index]
        if layer.locked or not layer.visible: return
        
        # GUARDAR ESTADO PARA DESHACER (CRUCIAL)
        self.save_undo_state()
        
        # 1. TRADUCCIÓN DE COORDENADAS
        if self._zoom_level == 0: self._zoom_level = 1.0
        ix = int((x - self._view_offset.x()) / self._zoom_level)
        iy = int((y - self._view_offset.y()) / self._zoom_level)

        if not (0 <= ix < layer.image.width() and 0 <= iy < layer.image.height()):
            return

        # 2. PREPARACIÓN DE BUFFER
        if layer.image.format() != QImage.Format.Format_ARGB32:
            layer.image = layer.image.convertToFormat(QImage.Format.Format_ARGB32)

        w, h = layer.image.width(), layer.image.height()
        bpl = layer.image.bytesPerLine()
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())
        
        try:
            # Vista strided segura
            arr_view = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=ptr, strides=(bpl, 4, 1))
            
            # --- LÓGICA ROBUSTA (SIMPLIFICADA) ---
            # Volvemos a lo que funcionaba: Relleno de 3 canales sin máscaras complejas
            
            # 1. Copia de trabajo
            work_img = arr_view.copy()

            # 2. PREPARAR CANALES (Split & Merge)
            b, g, r, a = cv2.split(work_img)
            bgr = cv2.merge([b, g, r])
            
            # 3. MÁSCARA LIMPIA (H+2, W+2)
            # Quitamos el dilated_edges que estaba bloqueando el relleno
            mask = np.zeros((h + 2, w + 2), np.uint8)

            # 4. EJECUTAR FLOODFILL
            target_bgr = (new_color.blue(), new_color.green(), new_color.red())
            
            # Use Dynamic Tolerance from Settings
            t = self._fill_tolerance
            tolerance = (t, t, t)
            
            # Flags: Connectivity 4 | FIXED_RANGE
            num_filled, _, mask, _ = cv2.floodFill(
                bgr, mask, (ix, iy), target_bgr,
                loDiff=tolerance, upDiff=tolerance,
                flags=4 | cv2.FLOODFILL_FIXED_RANGE
            )

            
            print(f"Relleno Básico: {num_filled} px")


            
            # 6. ACTUALIZAR ALPHA
            # Recortamos la máscara resultante para ver dónde pintó
            # Nota: dilated_edges (255) ya estaba en la máscara. floodFill pone 1s en lo nuevo.
            fill_mask = mask[1:-1, 1:-1]
            
            # Detectar dónde pintó floodFill (valor 1)
            # Ojo: Si la máscara original tenía 255, floodFill evita esas zonas.
            newly_filled = (fill_mask == 1)
            
            # Hacer opaco lo recién pintado
            a[newly_filled] = 255
            
            # 7. RECONSTRUIR
            final_bgra = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], a])
            arr_view[:] = final_bgra
            
            self.update()
            self.layersChanged.emit(self.getLayersList())
            print(f"Relleno inteligente (Gap Closing) en ({ix},{iy})")
            
        except Exception as e:
            print(f"CRITICAL ERROR en ColorDrop: {e}")
            import traceback
            traceback.print_exc()

    def apply_lasso_fill(self):
        """Fills the polygon defined by self._lasso_points."""
        if not self.layers or self._active_layer_index < 0: return
        if not self._lasso_points or len(self._lasso_points) < 3: return
        
        layer = self.layers[self._active_layer_index]
        if layer.locked or not layer.visible: return
        self.save_undo_state()

        # 1. Convert Screen Points -> Canvas Pixels
        # Logic: P_img = (P_screen - Offset) / Zoom
        poly_pts = []
        xo = self._view_offset.x()
        yo = self._view_offset.y()
        z = self._zoom_level if self._zoom_level > 0 else 1.0

        for p in self._lasso_points:
             ix = int((p.x() - xo) / z)
             iy = int((p.y() - yo) / z)
             poly_pts.append([ix, iy])

        # Convert to numpy format for fillPoly (shape: (1, N, 2) or (N, 2)?)
        # cv2.fillPoly expects list of arrays. Each array is point set.
        pts = np.array(poly_pts, np.int32)
        pts = pts.reshape((-1, 1, 2))

        # 2. Prepare Image
        if layer.image.format() != QImage.Format.Format_ARGB32:
             layer.image = layer.image.convertToFormat(QImage.Format.Format_ARGB32)
        
        w, h = layer.image.width(), layer.image.height()
        bpl = layer.image.bytesPerLine()
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())

        try:
             # 3. Secure Memory Access
             arr_view = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=ptr, strides=(bpl, 4, 1))
             work_img = arr_view.copy()

             # 4. Split Channels
             b, g, r, a = cv2.split(work_img)
             bgr = cv2.merge([b, g, r])

             # 5. Fill Poly
             # Color
             c = self._brush_color # Use primary color
             target_bgr = (c.blue(), c.green(), c.red())
             
             # Fill color channel
             cv2.fillPoly(bgr, [pts], target_bgr)
             
             # Fill Alpha channel (Make Opaque)
             cv2.fillPoly(a, [pts], 255)

             # 6. Reconstruct
             final_bgra = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], a])
             arr_view[:] = final_bgra
             
             self.update()
             # We should emit layersChanged but let's avoid it for perf unless needed for thumbnails
             # self.layersChanged.emit(self.getLayersList()) 
             print(f"Lasso Fill Applied ({len(poly_pts)} pts)")

        except Exception as e:
             print(f"Lasso Fill Error: {e}")


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
