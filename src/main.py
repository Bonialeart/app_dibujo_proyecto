"""
ArtFlow Studio - Main Entry Point
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase

from ui.main_window import MainWindow
from utils.config import config


def setup_high_dpi():
    """Configure high DPI scaling."""
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"


def setup_fonts():
    """Load custom fonts."""
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))


def main():
    """Main application entry point."""
    setup_high_dpi()
    
    app = QApplication(sys.argv)
    app.setApplicationName("ArtFlow Studio")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ArtFlow")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    setup_fonts()
    
    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "ui", "styles", "modern_theme.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    
    # Create and show main window
    window = MainWindow()
    
    # Restore window geometry
    if config.get("window.maximized"):
        window.showMaximized()
    else:
        width = config.get("window.width", 1600)
        height = config.get("window.height", 900)
        window.resize(width, height)
        window.show()
    
    # Run application
    exit_code = app.exec()
    
    # Save window state
    config.set("window.width", window.width())
    config.set("window.height", window.height())
    config.set("window.maximized", window.isMaximized())
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
