"""
ArtFlow Studio - Brushes Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QScrollArea, QGridLayout, QLineEdit,
    QTabWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QColor, QPainter


class BrushPreview(QFrame):
    """Brush preview thumbnail widget."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, brush_data: dict, parent=None):
        super().__init__(parent)
        self.brush_data = brush_data
        self.setFixedSize(80, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Preview image
        preview = QLabel()
        preview.setFixedSize(72, 60)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet("background: #252540; border-radius: 4px;")
        
        # Draw brush stroke preview
        pixmap = QPixmap(72, 60)
        pixmap.fill(QColor("#252540"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        
        # Draw a sample stroke
        for i in range(5):
            size = 4 + i * 2
            x = 10 + i * 12
            y = 30 - i * 3 + (i % 2) * 6
            painter.drawEllipse(x, y, size, size)
        
        painter.end()
        preview.setPixmap(pixmap)
        layout.addWidget(preview)
        
        # Name
        name = QLabel(self.brush_data.get("name", "Brush"))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        name.setWordWrap(True)
        layout.addWidget(name)
        
        self.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border: 2px solid transparent;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #00d4aa;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.brush_data)


class BrushesPanel(QWidget):
    """Panel for brush selection and configuration."""
    
    brush_changed = pyqtSignal(dict)
    brush_size_changed = pyqtSignal(int)
    brush_opacity_changed = pyqtSignal(float)
    
    def __init__(self, library_mode: bool = False, parent=None):
        super().__init__(parent)
        self.library_mode = library_mode
        self._current_brush = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        if self.library_mode:
            self._setup_library_ui(layout)
        else:
            self._setup_panel_ui(layout)
        
        self.setStyleSheet("background: #1a1a2e;")
    
    def _setup_panel_ui(self, layout):
        """Setup compact panel UI for dock widget."""
        # Size slider
        size_layout = QHBoxLayout()
        size_label = QLabel("Tamaño")
        size_label.setStyleSheet("color: #a0a0b0;")
        size_layout.addWidget(size_label)
        
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 500)
        self.size_slider.setValue(20)
        self.size_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #252540; height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00d4aa; width: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #00d4aa; border-radius: 3px; }
        """)
        size_layout.addWidget(self.size_slider)
        
        self.size_value = QLabel("20 px")
        self.size_value.setStyleSheet("color: #fff; min-width: 50px;")
        self.size_slider.valueChanged.connect(lambda v: self.size_value.setText(f"{v} px"))
        self.size_slider.valueChanged.connect(self.brush_size_changed.emit)
        size_layout.addWidget(self.size_value)
        layout.addLayout(size_layout)
        
        # Opacity slider
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacidad")
        opacity_label.setStyleSheet("color: #a0a0b0;")
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setStyleSheet(self.size_slider.styleSheet())
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value = QLabel("100%")
        self.opacity_value.setStyleSheet("color: #fff; min-width: 50px;")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_value.setText(f"{v}%"))
        self.opacity_slider.valueChanged.connect(lambda v: self.brush_opacity_changed.emit(v / 100.0))
        opacity_layout.addWidget(self.opacity_value)
        layout.addLayout(opacity_layout)
        
        # Brush grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        brushes_widget = QWidget()
        self.brushes_grid = QGridLayout(brushes_widget)
        self.brushes_grid.setSpacing(4)
        
        # Add default brushes
        default_brushes = [
            {"name": "Redondo", "type": "round"},
            {"name": "Suave", "type": "soft"},
            {"name": "Duro", "type": "hard"},
            {"name": "Textura", "type": "texture"},
            {"name": "Acuarela", "type": "watercolor"},
            {"name": "Lápiz", "type": "pencil"},
            {"name": "Carboncillo", "type": "charcoal"},
            {"name": "Tinta", "type": "ink"},
        ]
        
        for i, brush in enumerate(default_brushes):
            preview = BrushPreview(brush)
            preview.clicked.connect(self._on_brush_selected)
            self.brushes_grid.addWidget(preview, i // 2, i % 2)
        
        scroll.setWidget(brushes_widget)
        layout.addWidget(scroll, 1)
        
        # Import button
        import_btn = QPushButton("📥 Importar .ABR")
        import_btn.setStyleSheet("""
            QPushButton {
                background: #252540;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00d4aa;
                color: #0f0f1a;
            }
        """)
        import_btn.clicked.connect(self._import_abr)
        layout.addWidget(import_btn)
    
    def _setup_library_ui(self, layout):
        """Setup full library UI for main content area."""
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Biblioteca de Pinceles")
        title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Search
        search = QLineEdit()
        search.setPlaceholderText("🔍 Buscar pinceles...")
        search.setFixedWidth(300)
        search.setStyleSheet("""
            QLineEdit {
                background: #252540;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                padding: 10px 16px;
            }
        """)
        header.addWidget(search)
        
        layout.addLayout(header)
        
        # Category tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                color: #a0a0b0;
                padding: 12px 24px;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: #00d4aa;
                border-bottom-color: #00d4aa;
            }
        """)
        
        categories = ["Todos", "Pintura", "Boceto", "Textura", "Acuarela", "Tinta", "Especiales"]
        
        for cat in categories:
            tab_content = self._create_brush_grid()
            tabs.addTab(tab_content, cat)
        
        layout.addWidget(tabs, 1)
    
    def _create_brush_grid(self) -> QWidget:
        """Create a scrollable brush grid."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)
        
        # Sample brushes for the library
        brushes = [
            {"name": "Charcoal Shaders", "size": "25MB", "downloads": "15K", "price": "free"},
            {"name": "Watercolor Washes", "size": "25MB", "downloads": "12K", "price": "free"},
            {"name": "Vexticre Pack", "size": "18MB", "downloads": "8K", "price": "$5"},
            {"name": "Paint Mashes", "size": "25MB", "downloads": "20K", "price": "free"},
            {"name": "Fteuharm Pott", "size": "15MB", "downloads": "6K", "price": "free"},
            {"name": "Martup Stroke", "size": "18MB", "downloads": "10K", "price": "free"},
        ]
        
        for i, brush in enumerate(brushes):
            card = self._create_brush_card(brush)
            grid.addWidget(card, i // 4, i % 4)
        
        scroll.setWidget(content)
        return scroll
    
    def _create_brush_card(self, brush: dict) -> QFrame:
        """Create a brush download card."""
        card = QFrame()
        card.setFixedSize(200, 240)
        card.setStyleSheet("""
            QFrame {
                background: #252540;
                border-radius: 12px;
            }
            QFrame:hover {
                background: #2a2a50;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Preview
        preview = QLabel()
        preview.setFixedHeight(120)
        preview.setStyleSheet("background: #1a1a2e; border-radius: 8px;")
        layout.addWidget(preview)
        
        # Name
        name = QLabel(brush["name"])
        name.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(name)
        
        # Info
        info = QLabel(f"⬇ {brush['downloads']} · {brush['size']}")
        info.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        layout.addWidget(info)
        
        # Download button
        btn_text = "Descargar" if brush["price"] == "free" else brush["price"]
        btn = QPushButton(f"⬇ {btn_text}")
        btn.setStyleSheet("""
            QPushButton {
                background: #00d4aa;
                color: #0f0f1a;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #33ddbb;
            }
        """)
        layout.addWidget(btn)
        
        return card
    
    def _on_brush_selected(self, brush_data: dict):
        self._current_brush = brush_data
        self.brush_changed.emit(brush_data)
    
    def _import_abr(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Pinceles ABR", "",
            "Archivos ABR (*.abr);;Todos los archivos (*)"
        )
        
        if file_path:
            # TODO: Use C++ ABR parser
            QMessageBox.information(
                self, "Importar Pinceles",
                f"Archivo seleccionado: {file_path}\n\nPróximamente: Importación completa de pinceles ABR."
            )
