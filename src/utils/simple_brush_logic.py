"""
ArtFlow Studio - Brush Engine Fix
Logic to actually switch brush characteristics
"""

from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QRadialGradient, QConicalGradient
from PyQt6.QtCore import Qt, QPoint

class SimpleBrushEngine:
    """Helper class to configure QPainter for different brush types."""
    
    @staticmethod
    def configure_painter(painter: QPainter, brush_type: str, color: QColor, size: float, opacity: float):
        """Configure the painter based on brush type."""
        
        effective_color = QColor(color)
        effective_color.setAlphaF(opacity)
        
        # Reset
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        if brush_type == "pencil":
            # Hard, pixelated-like stroke
            pen = QPen(effective_color, size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
        elif brush_type == "marker":
            # Semi-transparent, multiply-like effect (simulated)
            # In QPainter basic, we just set opacity lower
            if opacity > 0.5: opacity = 0.5
            effective_color.setAlphaF(opacity)
            pen = QPen(effective_color, size)
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            painter.setPen(pen)
            
        elif brush_type == "airbrush":
            # Soft edges (Requires gradient drawing which implies custom point drawing, 
            # but for line drawing, we simulate with very low opacity and overlapping)
            # A true airbrush needs point-by-point rendering with radial gradients
            # For this simple implementation, we use a very soft, low opacity line
            effective_color.setAlphaF(min(opacity, 0.1)) # Very transparent to build up
            pen = QPen(effective_color, size * 1.5) # Bigger spill
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
        elif brush_type == "ink":
            # Sharp, high contrast
            effective_color.setAlphaF(1.0) # Always fully opaque at center
            pen = QPen(effective_color, size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
        else: # Default/Round
            pen = QPen(effective_color, size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
    @staticmethod
    def draw_dab(painter: QPainter, point: QPoint, brush_type: str, color: QColor, size: float, opacity: float):
        """Draw a single 'dab' or dot for dot-based brushes."""
        # This is used for 'click' or slow movement stamps
        effective_color = QColor(color)
        effective_color.setAlphaF(opacity)
        
        if brush_type == "airbrush":
            grad = QRadialGradient(point, size / 2)
            grad.setColorAt(0, effective_color)
            color_transparent = QColor(effective_color)
            color_transparent.setAlphaF(0)
            grad.setColorAt(1, color_transparent)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(point, int(size/2), int(size/2))
            
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(effective_color)
            painter.drawEllipse(point, int(size/2), int(size/2))
