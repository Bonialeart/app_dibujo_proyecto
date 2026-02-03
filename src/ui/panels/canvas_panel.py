"""
ArtFlow Studio - Canvas Panel (Refined with Brush Logic)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QMouseEvent, QWheelEvent
import numpy as np

from utils.simple_brush_logic import SimpleBrushEngine

class CanvasWidget(QWidget):
    """The actual drawing canvas widget with brush logic."""
    
    def __init__(self, width: int = 1920, height: int = 1080, parent=None):
        super().__init__(parent)
        
        self.canvas_width = width
        self.canvas_height = height
        self.zoom = 1.0
        
        # Create canvas image
        self.canvas_image = QImage(width, height, QImage.Format.Format_ARGB32)
        self.canvas_image.fill(QColor(255, 255, 255))
        
        # Drawing state
        self.is_drawing = False
        self.last_point = None
        self.brush_size = 20
        self.brush_color = QColor(0, 0, 0)
        self.brush_opacity = 1.0
        self.brush_type = "default" # default, pencil, ink, airbrush, marker
        
        # Enable tablet events
        self.setAttribute(Qt.WidgetAttribute.WA_TabletTracking)
        self.setMouseTracking(True)
        
        # Background pattern (static for performance)
        self.bg_pattern = self._create_checkerboard_pattern()
        
        self._update_size()
    
    def _create_checkerboard_pattern(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(240, 240, 240))
        painter = QPainter(pixmap)
        color = QColor(200, 200, 200)
        painter.fillRect(0, 0, 16, 16, color)
        painter.fillRect(16, 16, 16, 16, color)
        painter.end()
        return pixmap
    
    def _update_size(self):
        """Update widget size based on zoom."""
        w = int(self.canvas_width * self.zoom)
        h = int(self.canvas_height * self.zoom)
        self.setFixedSize(w, h)
    
    def set_zoom(self, zoom: float):
        """Set canvas zoom level."""
        self.zoom = max(0.05, min(5.0, zoom))
        self._update_size()
        self.update()
    
    def paintEvent(self, event):
        """Render the canvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Draw checkerboard background tiled
        painter.drawTiledPixmap(self.rect(), self.bg_pattern)
        
        # Draw the canvas image centered/scaled
        target_rect = self.rect()
        painter.drawImage(target_rect, self.canvas_image)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            pos = self._canvas_point(event.position())
            self.last_point = pos
            
            # Draw initial dab
            painter = QPainter(self.canvas_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            SimpleBrushEngine.draw_dab(
                painter, pos, self.brush_type, 
                self.brush_color, self.brush_size, self.brush_opacity
            )
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_drawing and self.last_point:
            current = self._canvas_point(event.position())
            
            painter = QPainter(self.canvas_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Use engine logic for pen configuration
            SimpleBrushEngine.configure_painter(
                painter, self.brush_type,
                self.brush_color, self.brush_size, self.brush_opacity
            )
            
            painter.drawLine(self.last_point, current)
            self.last_point = current
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            self.last_point = None
    
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self.set_zoom(self.zoom * factor)
    
    def _canvas_point(self, pos) -> QPoint:
        return QPoint(
            int(pos.x() / self.zoom),
            int(pos.y() / self.zoom)
        )
    
    def clear(self):
        self.canvas_image.fill(QColor(255, 255, 255))
        self.update()


class CanvasPanel(QWidget):
    """Refined panel containing the canvas and viewport controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Viewport container (Gray background like Photoshop/Procreate workspace)
        self.viewport = QScrollArea()
        self.viewport.setWidgetResizable(True) 
        self.viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport.setStyleSheet("""
            QScrollArea {
                background-color: #282828;
                border: none;
            }
            QScrollBar {
                background: #333;
            }
        """)
        
        # Wrapper widget to center canvas if smaller than viewport
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.canvas = CanvasWidget(2048, 2048)
        # Apply shadow to canvas to make it "pop"
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,100))
        self.canvas.setGraphicsEffect(shadow)
        
        scroll_layout.addWidget(self.canvas)
        self.viewport.setWidget(self.scroll_content)
        
        layout.addWidget(self.viewport)
    
    def create_new_canvas(self, width: int, height: int, dpi: int = 72):
        # Remove old canvas from layout
        layout = self.scroll_content.layout()
        if layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create new one
        self.canvas = CanvasWidget(width, height)
        
        # Set DPI metadata
        dpm = int(dpi / 0.0254)
        self.canvas.canvas_image.setDotsPerMeterX(dpm)
        self.canvas.canvas_image.setDotsPerMeterY(dpm)
        
        # Apply shadow
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0,0,0,150))
        self.canvas.setGraphicsEffect(shadow)
        
        layout.addWidget(self.canvas)
