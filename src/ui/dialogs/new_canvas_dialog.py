"""
ArtFlow Studio - New Canvas Dialog
Elegant modal for creating a new canvas with presets
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QGridLayout, QGraphicsDropShadowEffect,
    QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class PresetButton(QPushButton):
    """Preset size button with icon and description."""
    
    def __init__(self, name: str, width: int, height: int, icon: str, parent=None):
        super().__init__(parent)
        self.preset_width = width
        self.preset_height = height
        
        self.setFixedSize(140, 100)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setText(f"{icon}\n{name}\n{width}×{height}")
        
        self.setStyleSheet("""
            QPushButton {
                background: #252540;
                color: #a0a0b0;
                border: 2px solid #3a3a5a;
                border-radius: 12px;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton:hover {
                background: #2a2a55;
                border-color: #00d4aa;
                color: #ffffff;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00d4aa, stop:1 #00a88a);
                color: #0f0f1a;
                border-color: #00d4aa;
                font-weight: bold;
            }
        """)


class NewCanvasDialog(QDialog):
    """Elegant dialog for creating a new canvas."""
    
    canvas_created = pyqtSignal(int, int)  # width, height
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Nuevo Lienzo")
        self.setFixedSize(520, 480)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._selected_width = 2048
        self._selected_height = 2048
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Main container with shadow
        container = QFrame(self)
        container.setGeometry(10, 10, 500, 460)
        container.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border-radius: 20px;
                border: 1px solid #3a3a5a;
            }
        """)
        
        # Apply shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 150))
        container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("✨ Nuevo Lienzo")
        title.setStyleSheet("""
            color: #ffffff;
            font-size: 24px;
            font-weight: bold;
        """)
        header.addWidget(title)
        
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #a0a0b0;
                border: none;
                font-size: 18px;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Presets section
        presets_label = QLabel("Plantillas Rápidas")
        presets_label.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        layout.addWidget(presets_label)
        
        presets_grid = QGridLayout()
        presets_grid.setSpacing(12)
        
        self.preset_group = QButtonGroup(self)
        
        presets = [
            ("Cuadrado", 2048, 2048, "⬜"),
            ("Ilustración", 2480, 3508, "🖼️"),
            ("Paisaje", 3840, 2160, "🌄"),
            ("Retrato", 1080, 1920, "📱"),
            ("Instagram", 1080, 1080, "📷"),
            ("YouTube", 1920, 1080, "▶️"),
        ]
        
        for i, (name, w, h, icon) in enumerate(presets):
            btn = PresetButton(name, w, h, icon)
            btn.clicked.connect(lambda checked, pw=w, ph=h: self._on_preset_selected(pw, ph))
            self.preset_group.addButton(btn)
            presets_grid.addWidget(btn, i // 3, i % 3)
        
        # Select first by default
        first_btn = self.preset_group.buttons()[0]
        first_btn.setChecked(True)
        
        layout.addLayout(presets_grid)
        
        # Custom size section
        custom_label = QLabel("Tamaño Personalizado")
        custom_label.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        layout.addWidget(custom_label)
        
        size_layout = QHBoxLayout()
        size_layout.setSpacing(16)
        
        # Width
        width_layout = QVBoxLayout()
        width_lbl = QLabel("Ancho (px)")
        width_lbl.setStyleSheet("color: #606070; font-size: 11px;")
        width_layout.addWidget(width_lbl)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 8192)
        self.width_spin.setValue(2048)
        self.width_spin.setStyleSheet("""
            QSpinBox {
                background: #252540;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border-color: #00d4aa;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background: #3a3a5a;
                border-radius: 4px;
            }
        """)
        self.width_spin.valueChanged.connect(self._on_size_changed)
        width_layout.addWidget(self.width_spin)
        size_layout.addLayout(width_layout)
        
        # Link icon
        link_label = QLabel("🔗")
        link_label.setStyleSheet("font-size: 20px;")
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_layout.addWidget(link_label)
        
        # Height
        height_layout = QVBoxLayout()
        height_lbl = QLabel("Alto (px)")
        height_lbl.setStyleSheet("color: #606070; font-size: 11px;")
        height_layout.addWidget(height_lbl)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 8192)
        self.height_spin.setValue(2048)
        self.height_spin.setStyleSheet(self.width_spin.styleSheet())
        self.height_spin.valueChanged.connect(self._on_size_changed)
        height_layout.addWidget(self.height_spin)
        size_layout.addLayout(height_layout)
        
        layout.addLayout(size_layout)
        
        layout.addStretch()
        
        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(12)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFixedHeight(48)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #252540;
                color: #a0a0b0;
                border: none;
                border-radius: 12px;
                padding: 0 32px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a3a5a;
                color: #ffffff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)
        
        create_btn = QPushButton("✨ Crear Lienzo")
        create_btn.setFixedHeight(48)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4aa, stop:1 #00a88a);
                color: #0f0f1a;
                border: none;
                border-radius: 12px;
                padding: 0 48px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #33ddbb, stop:1 #00d4aa);
            }
        """)
        create_btn.clicked.connect(self._on_create)
        actions.addWidget(create_btn, 1)
        
        layout.addLayout(actions)
    
    def _on_preset_selected(self, width: int, height: int):
        self._selected_width = width
        self._selected_height = height
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
    
    def _on_size_changed(self):
        self._selected_width = self.width_spin.value()
        self._selected_height = self.height_spin.value()
        # Uncheck presets when manually changing
        for btn in self.preset_group.buttons():
            btn.setChecked(False)
    
    def _on_create(self):
        self.canvas_created.emit(self._selected_width, self._selected_height)
        self.accept()
    
    def get_size(self) -> tuple:
        return (self._selected_width, self._selected_height)
