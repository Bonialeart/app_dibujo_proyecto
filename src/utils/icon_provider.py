import os
from PyQt6.QtQuick import QQuickImageProvider
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize

class IconProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        # Base directory for icons
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
        print(f"[IconProvider] Icon path initialized: {self.base_path}")

    def requestPixmap(self, id, size, requestedSize):
        # 'id' will be the filename, e.g., "pen.svg"
        file_path = os.path.join(self.base_path, id)
        
        # Determine size (default to 48x48 if not specified)
        width = requestedSize.width() if requestedSize.width() > 0 else 48
        height = requestedSize.height() if requestedSize.height() > 0 else 48
        
        if os.path.exists(file_path):
            # Load SVG as QIcon and generate Pixmap
            icon = QIcon(file_path)
            pixmap = icon.pixmap(QSize(width, height))
            # print(f"[IconProvider] Loaded: {id}") 
            return pixmap
        else:
            print(f"[IconProvider] ERROR: File not found: {file_path}")
            # Return empty pixmap (or customized error placeholder)
            return QPixmap(width, height)
