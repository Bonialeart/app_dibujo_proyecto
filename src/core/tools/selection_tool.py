from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal, QPointF, QRect, Qt
from PyQt6.QtGui import QImage, QColor, QPainter, QPolygonF, QBrush, QPen
import cv2
import numpy as np

class SelectionToolMixin:
    """
    Mixin for QCanvasItem to handle Selection logic (Rect, Lasso, Magic Wand).
    Manages _selection_mask (QImage, Format_Grayscale8). 0=Unselected, 255=Selected.
    """
    
    selectionChanged = pyqtSignal()
    
    def _init_selection_tool(self):
        # Selection State
        self._selection_mask = None # QImage(Grayscale8) or None if no selection
        self._selection_active = False
        self._marching_ants_offset = 0
        
        # Tools state
        self._selection_mode = "replace" # replace, add, subtract
    
    def get_selection_active(self):
        return self._selection_active
        
    def _ensure_selection_buffer(self):
        w, h = self._canvas_width, self._canvas_height
        # Use canvas dimensions instead of boundingRect to avoid AttributeError/ambiguity in Mixin
        if self._selection_mask is None or self._selection_mask.width() != w or self._selection_mask.height() != h:
            self._selection_mask = QImage(w, h, QImage.Format.Format_Grayscale8)
            self._selection_mask.fill(0)
            
    @pyqtSlot()
    def clearSelection(self):
        self._selection_mask = None
        self._selection_active = False
        self.selectionChanged.emit()
        self.update()

    @pyqtSlot()
    def selectAll(self):
        self._ensure_selection_buffer()
        self._selection_mask.fill(255)
        self._selection_active = True
        self.selectionChanged.emit()
        self.update()

    @pyqtSlot(int, int, int, int, str)
    def selectRect(self, x, y, w, h, mode="replace"):
        self._ensure_selection_buffer()
        painter = QPainter(self._selection_mask)
        
        if mode == "replace":
            self._selection_mask.fill(0)
            painter.setBrush(QBrush(Qt.GlobalColor.white))
        elif mode == "add":
            painter.setBrush(QBrush(Qt.GlobalColor.white))
        elif mode == "subtract":
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Coordinates are already in canvas space (provided by caller)
        rect = QRect(x, y, w, h).intersected(QRect(0, 0, self._canvas_width, self._canvas_height))
        painter.drawRect(rect)
        painter.end()
        
        self._selection_active = True
        self.selectionChanged.emit()
        self.update()

    def _draw_selection_overlay(self, painter):
        """Draws the marching ants effect."""
        if not self._selection_active or self._selection_mask is None: return
        
        # Create a visual overlay (blue tint + dashed line)
        # This is expensive to generate every frame for marching ants from a mask
        # Optimization: Generate outline path only when selection changes?
        # For now, simplistic approach: overlay tint
        
        # Transform painter to view
        painter.save()
        painter.translate(self._view_offset)
        painter.scale(self._zoom_level, self._zoom_level)
        
        # 1. Tinte Azulado (Visual aid) - Only where selected
        # Generating a colored mask from grayscale on CPU is slow every frame.
        # Ideally, this should be done with a shader or pre-cached image.
        # Fallback: Just borders if possible? or simple rect if it is a rect.
        # For prototype: We won't draw the full mask tint in software mode efficiently 
        # without lagging on 4k canvas. skipping fill tint for speed.
        
        # 2. Border/Outline (Marching Ants)
        # We can use GPU/Native for this later. 
        # For now, let's just draw a simple indicator or if usage is low.
        # 1. Tinte Azulado (Visual aid)
        # Draw the mask with a blue tint
        # CompositionMode_SourceOver with a colored brush masked by the image?
        # Efficient way:
        # Create a colored QImage or draw image with opacity?
        # Simplest: Draw the mask using a customized painter.
        # But mask is Grayscale. 
        # We want to draw Blue where Mask > 0.
        
        # Fast Hack: Draw mask as alpha channel of a Blue Rect?
        # painter.setClipRegion? No.
        
        # Let's just draw the rectangles if we are in Rect Select mode (for speed)
        # But we need to support Lasso.
        
        # For prototype: Draw the mask image with Opacity 0.2
        # But mask is grayscale (white=selected). 
        # If we draw it, it appears white locally.
        # We can set CompositionMode to multiply? No.
        
        painter.setOpacity(0.3)
        # Draw the mask (White)
        # painter.drawImage(0, 0, self._selection_mask)
        
        # To make it BLUE:
        # We can use a CompositionMode.
        # Draw a Blue Rect covering the screen, Masked by the Selection Mask.
        
        # 1. Save state
        # 2. Set Clip to Mask? Qt doesn't support QImage clip easily without path.
        
        # 3. Draw Mask to a temporary buffer, tint it, draw buffer?
        # Too slow.
        
        # 4. Just draw the mask as White Overlay for now.
        # Better than nothing.
        # FIX: Disabling this as it causes a full-screen GREY overlay (0=Black, 255=White)
        # painter.drawImage(0, 0, self._selection_mask)
        
        # Draw Border (Marching Ants equivalent - simple rect for now if available)
        if hasattr(self, "_selection_rect"):
             painter.setOpacity(1.0)
             pen = QPen(Qt.GlobalColor.white, 1, Qt.PenStyle.DashLine)
             painter.setPen(pen)
             painter.drawRect(self._selection_rect) 
        painter.restore()

    @pyqtSlot(list, str)
    def selectLasso(self, points, mode="replace"):
        """
        points: list of QPointF
        mode: 'replace', 'add', 'subtract'
        """
        if not points or len(points) < 3: return
        
        self._ensure_selection_buffer()
        painter = QPainter(self._selection_mask)
        
        if mode == "replace":
            self._selection_mask.fill(0)
            painter.setBrush(QBrush(Qt.GlobalColor.white))
        elif mode == "add":
            painter.setBrush(QBrush(Qt.GlobalColor.white))
        elif mode == "subtract":
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw Polygon
        poly = QPolygonF(points)
        painter.drawPolygon(poly)
        painter.end()
        
        self._selection_active = True
        self.selectionChanged.emit()
        self.update()
