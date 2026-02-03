"""
ArtFlow Studio - Application Constants
"""

# Application Info
APP_NAME = "ArtFlow Studio"
APP_VERSION = "1.0.0"
APP_AUTHOR = "ArtFlow Team"

# Window Settings
WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 720
WINDOW_DEFAULT_WIDTH = 1600
WINDOW_DEFAULT_HEIGHT = 900

# Canvas Settings
CANVAS_MAX_SIZE = 16384
CANVAS_DEFAULT_SIZE = 2048
CANVAS_BACKGROUND_COLOR = "#1a1a2e"

# Brush Settings
BRUSH_MIN_SIZE = 1
BRUSH_MAX_SIZE = 500
BRUSH_DEFAULT_SIZE = 20
BRUSH_MIN_OPACITY = 0.01
BRUSH_MAX_OPACITY = 1.0
BRUSH_DEFAULT_OPACITY = 1.0

# Layer Settings
LAYER_MAX_COUNT = 100
LAYER_DEFAULT_NAME = "Layer"

# Tool Types
class ToolType:
    BRUSH = "brush"
    ERASER = "eraser"
    PENCIL = "pencil"
    AIRBRUSH = "airbrush"
    MARKER = "marker"
    FILL = "fill"
    EYEDROPPER = "eyedropper"
    MOVE = "move"
    TRANSFORM = "transform"
    SELECTION = "selection"
    LASSO = "lasso"
    TEXT = "text"
    SHAPE = "shape"
    SMUDGE = "smudge"
    BLUR = "blur"

# Blend Modes
class BlendMode:
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"

# Resource Categories
class ResourceCategory:
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    TEMPLATE = "template"
    PALETTE = "palette"
    TYPOGRAPHY = "typography"
    MODEL_3D = "3d_model"

# Brush Categories
class BrushCategory:
    PAINT = "paint"
    SKETCH = "sketch"
    TEXTURE = "texture"
    WATERCOLOR = "watercolor"
    INK = "ink"
    CHARCOAL = "charcoal"
    MARKER = "marker"
    SPECIAL = "special"

# Video Playlist Categories
class PlaylistCategory:
    ILLUSTRATION = "illustration"
    CONCEPT_ART = "concept_art"
    ANIMATION = "animation"
    CHARACTER_DESIGN = "character_design"
    ENVIRONMENT = "environment"
    FUNDAMENTALS = "fundamentals"

# Theme Colors (Premium Dark Theme)
class ThemeColors:
    # Primary
    PRIMARY = "#00d4aa"
    PRIMARY_LIGHT = "#33ddbb"
    PRIMARY_DARK = "#00a88a"
    
    # Accent
    ACCENT = "#7c3aed"
    ACCENT_LIGHT = "#a78bfa"
    ACCENT_DARK = "#5b21b6"
    
    # Background
    BG_DARK = "#0f0f1a"
    BG_MAIN = "#1a1a2e"
    BG_LIGHT = "#252540"
    BG_CARD = "#2a2a45"
    
    # Surface
    SURFACE_1 = "#16213e"
    SURFACE_2 = "#1f2b50"
    SURFACE_3 = "#2a3a60"
    
    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0b0"
    TEXT_MUTED = "#606070"
    
    # Status
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#3b82f6"
    
    # Gold (Premium)
    GOLD = "#fbbf24"
    GOLD_LIGHT = "#fcd34d"
    GOLD_DARK = "#d97706"

# File Extensions
SUPPORTED_IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".webp", ".psd", ".tiff", ".bmp"]
SUPPORTED_BRUSH_FORMATS = [".abr", ".brush", ".afbrushes"]
SUPPORTED_PROJECT_FORMAT = ".artflow"

# API Endpoints
BRUSH_API_BASE = "https://api.artflow.studio/v1/brushes"
RESOURCE_API_BASE = "https://api.artflow.studio/v1/resources"

# Cache Settings
CACHE_MAX_SIZE_MB = 500
CACHE_EXPIRY_DAYS = 30
