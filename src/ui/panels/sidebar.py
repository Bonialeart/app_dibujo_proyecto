"""
ArtFlow Studio - Sidebar Navigation Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont


class SidebarButton(QPushButton):
    """Custom styled sidebar button."""
    
    def __init__(self, text: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a0a0b0;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #252540;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #00d4aa;
                color: #0f0f1a;
            }
        """)


class Sidebar(QWidget):
    """Left sidebar with navigation."""
    
    section_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("sidebar")
        
        self._current_section = "home"
        self._buttons = {}
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Setup sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)
        
        # Logo/Brand
        brand_layout = QHBoxLayout()
        
        logo_label = QLabel("🎨")
        logo_label.setFont(QFont("Segoe UI", 24))
        brand_layout.addWidget(logo_label)
        
        brand_text = QLabel("ArtFlow")
        brand_text.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        brand_text.setStyleSheet("color: #00d4aa;")
        brand_layout.addWidget(brand_text)
        
        brand_layout.addStretch()
        layout.addLayout(brand_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3a3a5a; max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(16)
        
        # Navigation buttons
        nav_sections = [
            ("home", "🏠", "Inicio"),
            ("learn", "📚", "Aprender"),
            ("brushes", "🖌️", "Pinceles"),
            ("resources", "🔗", "Recursos"),
        ]
        
        for section_id, icon, label in nav_sections:
            btn = SidebarButton(f"  {icon}  {label}")
            btn.clicked.connect(lambda checked, s=section_id: self._on_button_clicked(s))
            self._buttons[section_id] = btn
            layout.addWidget(btn)
        
        # Set home as active
        self._buttons["home"].setChecked(True)
        
        layout.addStretch()
        
        # Bottom section - Profile
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #3a3a5a; max-height: 1px;")
        layout.addWidget(separator2)
        layout.addSpacing(8)
        
        settings_btn = SidebarButton("  ⚙️  Configuración")
        layout.addWidget(settings_btn)
        
        # Premium badge
        premium_frame = QFrame()
        premium_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fbbf24, stop:1 #d97706);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        premium_layout = QHBoxLayout(premium_frame)
        premium_layout.setContentsMargins(12, 8, 12, 8)
        
        premium_label = QLabel("👑 Premium")
        premium_label.setStyleSheet("color: #0f0f1a; font-weight: bold;")
        premium_layout.addWidget(premium_label)
        
        layout.addWidget(premium_frame)
    
    def _apply_styles(self):
        """Apply sidebar styling."""
        self.setStyleSheet("""
            #sidebar {
                background-color: #0f0f1a;
                border-right: 1px solid #252540;
            }
        """)
    
    def _on_button_clicked(self, section: str):
        """Handle navigation button click."""
        if section == self._current_section:
            return
        
        # Update button states
        for btn_id, btn in self._buttons.items():
            btn.setChecked(btn_id == section)
        
        self._current_section = section
        self.section_changed.emit(section)
