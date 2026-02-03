from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtCore import Qt, QBuffer, QByteArray, QIODevice
import base64

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

    def is_group(self):
        return self.type == "group"
