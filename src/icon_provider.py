import os
from PyQt6.QtQuick import QQuickImageProvider
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize, Qt

class IconProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        # Base directory for icons: src/assets/icons
        # Assuming this file is in src/
        self.base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
        print(f"[IconProvider] Icon path initialized: {self.base_path}")

    def requestPixmap(self, id, size, requestedSize=None):
        # PyQt6 signature can vary. If requestedSize is None, then 'size' is likely the requestedSize.
        if requestedSize is None:
            actual_requested_size = size
            # We don't have a 'size' output parameter to fill, which is fine for simple pixels.
        else:
            actual_requested_size = requestedSize

        # 'id' will be the filename, e.g., "pen.svg"
        file_path = os.path.join(self.base_path, id)
        
        # Determine size (default to 48x48 if not specified)
        width = actual_requested_size.width() if actual_requested_size and actual_requested_size.width() > 0 else 48
        height = actual_requested_size.height() if actual_requested_size and actual_requested_size.height() > 0 else 48
        
        if os.path.exists(file_path):
            # Load SVG as QIcon and generate Pixmap
            icon = QIcon(file_path)
            pixmap = icon.pixmap(QSize(width, height))
            return pixmap, pixmap.size()
        else:
            print(f"[IconProvider] ERROR: File not found: {file_path}")
            # Return empty transparent pixmap to avoid garbage noise (static)
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.transparent)
            return pixmap, pixmap.size()
