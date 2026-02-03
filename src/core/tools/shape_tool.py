from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal, QPointF, QRectF, Qt
from PyQt6.QtGui import QImage, QColor, QPainter, QBrush, QPen
import numpy as np

class ShapeToolMixin:
    """
    Mixin for QCanvasItem to handle Geometric Shape drawing.
    """
    
    def _init_shape_tool(self):
        self._shape_start_pos = None
        self._shape_current_pos = None
        self._shape_preview_active = False
        
    def _draw_shape_preview(self, painter):
        """Draws the shape being dragged."""
        if not self._shape_preview_active or not self._shape_start_pos or not self._shape_current_pos: return
        
        tool = getattr(self, "_current_tool", "brush")
        if tool not in ["line", "rect", "ellipse"]: return

        p1 = (self._shape_start_pos - self._view_offset) / self._zoom_level
        p2 = (self._shape_current_pos - self._view_offset) / self._zoom_level
        
        painter.save()
        painter.translate(self._view_offset)
        painter.scale(self._zoom_level, self._zoom_level)
        
        pen = QPen(QColor(self._brush_color), self._brush_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush) # Outlined shapes for now? Or fill? 
        # Typically shapes in paint apps are outlined unless "Fill" is checked.
        
        if tool == "line":
            painter.drawLine(p1, p2)
        elif tool == "rect":
            rect = QRectF(p1, p2).normalized()
            painter.drawRect(rect)
        elif tool == "ellipse":
            rect = QRectF(p1, p2).normalized()
            painter.drawEllipse(rect)
            
        painter.restore()

    def commit_shape_to_layer(self):
        """Finalizes the shape onto the pixel layer."""
        if self._active_layer_index < 0: return
        layer = self.layers[self._active_layer_index]
        if layer.locked: return
        
        tool = getattr(self, "_current_tool", "brush")
        p1 = (self._shape_start_pos - self._view_offset) / self._zoom_level
        p2 = (self._shape_current_pos - self._view_offset) / self._zoom_level
        
        painter = QPainter(layer.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(self._brush_color)
        color.setAlphaF(self._brush_opacity)
        
        pen = QPen(color, self._brush_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush) # Todo: fill option
        
        if tool == "line":
            painter.drawLine(p1, p2)
        elif tool == "rect":
            rect = QRectF(p1, p2).normalized()
            painter.drawRect(rect)
        elif tool == "ellipse":
            rect = QRectF(p1, p2).normalized()
            painter.drawEllipse(rect)
            
        painter.end()
        self.update()
