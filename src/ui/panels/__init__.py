"""
ArtFlow Studio - Panels Module
"""

from .home_panel import HomePanel
from .canvas_panel import CanvasPanel
from .layers_panel import LayersPanel
from .colors_panel import ColorsPanel
from .brushes_panel import BrushesPanel
from .tools_panel import ToolsPanel
from .learn_panel import LearnPanel
from .resources_panel import ResourcesPanel
from .sidebar import Sidebar

__all__ = [
    'HomePanel',
    'CanvasPanel',
    'LayersPanel', 
    'ColorsPanel',
    'BrushesPanel',
    'ToolsPanel',
    'LearnPanel',
    'ResourcesPanel',
    'Sidebar'
]

