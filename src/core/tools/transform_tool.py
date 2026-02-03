from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal, QPointF, QRectF, Qt
from PyQt6.QtGui import QImage, QColor, QPainter, QTransform, QBrush
import numpy as np

class TransformToolMixin:
    """
    Mixin for QCanvasItem to handle Transformation logic (Scale, Rotate, Translate).
    """
    
    transformChanged = pyqtSignal()
    
    def _init_transform_tool(self):
        self._transform_active = False
        self._transform_buffer = None # QImage of the content being transformed
        self._transform_matrix = QTransform()
        self._transform_orig_pos = QPointF(0,0)
        self._transform_preview = None # Cached resultant image
        
    @pyqtSlot()
    def startTransform(self):
        """Captures the current selection (or layer content) into a buffer for transforming."""
        if self._active_layer_index < 0: return
        
        layer = self.layers[self._active_layer_index]
        self._transform_active = True
        
        # 1. Capture Content
        # If selection active, capture only selected pixels? For now, capture whole layer.
        # Ideally: Crop to bounding box of non-transparent pixels
        self._transform_buffer = layer.image.copy()
        
        # 2. Reset Matrix
        self._transform_matrix.reset()
        
        # 3. Clear original content from layer (it's now "floating")
        # In a real app we might hide it or use a "floating layer".
        # For simplicity: Clear layer, store in buffer.
        # If canceled, restore buffer.
        
        # Optimization: Don't clear immediately, only clear when rendering?
        # Let's keep it simple: We are entering "Transform Mode". 
        # The layer image stays as is until "Apply" is clicked?
        # Better UX: Layer stays, we render overlay. When Apply, we burn it.
        # But we need to hide the original content so it looks like it's moving.
        
        painter = QPainter(layer.image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(layer.image.rect(), Qt.GlobalColor.transparent)
        painter.end()
        
        self.isTransformingChanged.emit(True)
        self.update()

    @pyqtSlot(float, float, float, float, float, float)
    def updateTransformProperties(self, x, y, scale, rotation, w, h):
        """Updates the matrix from QML Item properties (x, y, scale, rotation, width, height)."""
        # Reconstruct the transform matrix to match QML Item behavior
        # QML Item Rotation/Scale is around Center (w/2, h/2) by default
        
        m = QTransform()
        
        # 1. Translate to Center of the Item (which is at x + w/2, y + h/2)
        cx = w / 2.0
        cy = h / 2.0
        
        m.translate(x + cx, y + cy)
        m.rotate(rotation)
        m.scale(scale, scale)
        m.translate(-cx, -cy)
        
        self._transform_matrix = m
        self.update()

    @pyqtSlot(float, float, float, float, float, float)
    def updateTransformMatrix(self, m11, m12, m13, m21, m22, m23):
        """Updates the matrix from QML."""
        self._transform_matrix.setMatrix(m11, m12, m13, m21, m22, m23, 0.0, 0.0, 1.0)
        self.update()

    @pyqtSlot()
    def applyTransform(self):
        """Burns the transformed buffer back into the layer."""
        if not self._transform_active or self._transform_buffer is None: return
        
        layer = self.layers[self._active_layer_index]
        
        # Render transformed buffer
        painter = QPainter(layer.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.setTransform(self._transform_matrix)
        painter.drawImage(0, 0, self._transform_buffer)
        painter.end()
        
        self._transform_active = False
        self._transform_buffer = None
        self.isTransformingChanged.emit(False)
        self.update()
        
    @pyqtSlot()
    def cancelTransform(self):
        """Restores the original content."""
        if not self._transform_active or self._transform_buffer is None: return
        
        layer = self.layers[self._active_layer_index]
        layer.image = self._transform_buffer.copy() # Restore
        
        self._transform_active = False
        self._transform_buffer = None
        self.isTransformingChanged.emit(False)
        self.update()

    def _draw_transform_preview(self, painter):
        """Draws the transformed content during the operation."""
        if not self._transform_active or self._transform_buffer is None: return
        
        painter.save()
        # View Transform
        painter.translate(self._view_offset)
        painter.scale(self._zoom_level, self._zoom_level)
        
        # User Transform
        painter.setTransform(self._transform_matrix, True)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(0, 0, self._transform_buffer)
        
        # Draw Border/Bounding Box?
        # QML Overlay handles handles, but we might want a border here too
        # painter.setPen(QPen(Qt.GlobalColor.blue, 2))
        # painter.drawRect(self._transform_buffer.rect())
        
        painter.restore()
