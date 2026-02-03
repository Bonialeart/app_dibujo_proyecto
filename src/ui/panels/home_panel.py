"""
ArtFlow Studio - Home Panel (Welcome Screen)
Premium landing page with recent projects and templates
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QLinearGradient, QBrush


class ProjectCard(QFrame):
    """Card for recent project or template."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, project_data: dict, is_template: bool = False, parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.is_template = is_template
        self.setFixedSize(240, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
        self._apply_shadow()
    
    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Thumbnail area
        thumb = QFrame()
        thumb.setFixedHeight(130)
        
        # Preview gradient based on type
        if self.is_template:
            colors = self.project_data.get("colors", ["#7c3aed", "#00d4aa"])
            thumb.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors[0]}, stop:1 {colors[1]});
                border-radius: 12px 12px 0 0;
            """)
        else:
            thumb.setStyleSheet("""
                background: #252540;
                border-radius: 12px 12px 0 0;
            """)
        
        # Size label for templates
        if self.is_template:
            size_label = QLabel(self.project_data.get("size", "1920×1080"))
            size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            size_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.9);
                font-size: 18px;
                font-weight: bold;
            """)
            thumb_layout = QVBoxLayout(thumb)
            thumb_layout.addWidget(size_label)
        else:
            # For recent projects, show last edited
            info_layout = QVBoxLayout(thumb)
            info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
            info_layout.setContentsMargins(12, 12, 12, 12)
            
            date_label = QLabel(self.project_data.get("last_edited", "Hoy"))
            date_label.setStyleSheet("""
                background: rgba(0, 0, 0, 0.5);
                color: #a0a0b0;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            """)
            info_layout.addWidget(date_label)
        
        layout.addWidget(thumb)
        
        # Info section
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #1a1a2e; border-radius: 0 0 12px 12px;")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)
        
        title = QLabel(self.project_data.get("name", "Sin título"))
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(title)
        
        subtitle = QLabel(self.project_data.get("category", "Proyecto"))
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        info_layout.addWidget(subtitle)
        
        layout.addWidget(info_frame)
        
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 12px;
                border: 1px solid #252540;
            }
            QFrame:hover {
                border-color: #00d4aa;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_data)


class NewCanvasButton(QFrame):
    """Large button for creating new canvas."""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(240, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
        self._apply_shadow()
    
    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 212, 170, 60))
        self.setGraphicsEffect(shadow)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        
        # Plus icon
        plus = QLabel("+")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setStyleSheet("""
            color: #00d4aa;
            font-size: 48px;
            font-weight: 300;
        """)
        layout.addWidget(plus)
        
        # Text
        text = QLabel("Nuevo Lienzo")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(text)
        
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #252540);
                border: 2px dashed #00d4aa;
                border-radius: 12px;
            }
            QFrame:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #252540, stop:1 #2a2a55);
                border-style: solid;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class HomePanel(QWidget):
    """Home/Welcome screen with projects and templates."""
    
    # Signals
    new_canvas_requested = pyqtSignal(int, int)  # width, height
    open_project_requested = pyqtSignal(str)  # project path
    navigate_to_draw = pyqtSignal()
    show_new_canvas_dialog = pyqtSignal()  # Show the modal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 40, 60, 40)
        content_layout.setSpacing(40)
        
        # Header with branding
        header = self._create_header()
        content_layout.addLayout(header)
        
        # Quick actions
        quick_actions = self._create_quick_actions()
        content_layout.addLayout(quick_actions)
        
        # Templates section
        templates_section = self._create_templates_section()
        content_layout.addLayout(templates_section)
        
        # Recent projects section
        recent_section = self._create_recent_section()
        content_layout.addLayout(recent_section)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0a15, stop:1 #0f0f1a);
            }
        """)
    
    def _create_header(self) -> QVBoxLayout:
        """Create welcome header."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Welcome text
        welcome = QLabel("Bienvenido a")
        welcome.setStyleSheet("color: #a0a0b0; font-size: 16px;")
        layout.addWidget(welcome)
        
        # App name with gradient effect
        app_name = QLabel("ArtFlow Studio")
        app_name.setStyleSheet("""
            color: #ffffff;
            font-size: 42px;
            font-weight: bold;
        """)
        layout.addWidget(app_name)
        
        # Tagline
        tagline = QLabel("Tu estudio de arte digital profesional")
        tagline.setStyleSheet("color: #00d4aa; font-size: 16px; font-weight: 500;")
        layout.addWidget(tagline)
        
        return layout
    
    def _create_quick_actions(self) -> QHBoxLayout:
        """Create quick action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        # New canvas button
        new_btn = NewCanvasButton()
        new_btn.clicked.connect(self._on_new_canvas)
        layout.addWidget(new_btn)
        
        # Quick start templates
        quick_templates = [
            {"name": "Ilustración", "size": "2048×2048", "width": 2048, "height": 2048, 
             "colors": ["#7c3aed", "#a855f7"], "category": "Cuadrado"},
            {"name": "Arte Conceptual", "size": "3840×2160", "width": 3840, "height": 2160,
             "colors": ["#0ea5e9", "#06b6d4"], "category": "4K Landscape"},
            {"name": "Retrato", "size": "1080×1920", "width": 1080, "height": 1920,
             "colors": ["#f43f5e", "#ec4899"], "category": "Vertical"},
        ]
        
        for template in quick_templates:
            card = ProjectCard(template, is_template=True)
            card.clicked.connect(self._on_template_selected)
            layout.addWidget(card)
        
        layout.addStretch()
        
        return layout
    
    def _create_templates_section(self) -> QVBoxLayout:
        """Create templates gallery section."""
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Section header
        header = QHBoxLayout()
        
        title = QLabel("📐 Plantillas de Lienzo")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        see_all = QPushButton("Ver todas →")
        see_all.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #00d4aa;
                border: none;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #33ddbb;
            }
        """)
        header.addWidget(see_all)
        
        layout.addLayout(header)
        
        # Templates grid
        grid = QHBoxLayout()
        grid.setSpacing(16)
        
        templates = [
            {"name": "A4 Print", "size": "2480×3508", "width": 2480, "height": 3508,
             "colors": ["#10b981", "#059669"], "category": "Impresión"},
            {"name": "Instagram Post", "size": "1080×1080", "width": 1080, "height": 1080,
             "colors": ["#f97316", "#fb923c"], "category": "Redes Sociales"},
            {"name": "YouTube Thumbnail", "size": "1280×720", "width": 1280, "height": 720,
             "colors": ["#ef4444", "#f87171"], "category": "Video"},
            {"name": "Manga Page", "size": "1654×2339", "width": 1654, "height": 2339,
             "colors": ["#8b5cf6", "#a78bfa"], "category": "Cómic"},
        ]
        
        for template in templates:
            card = ProjectCard(template, is_template=True)
            card.clicked.connect(self._on_template_selected)
            grid.addWidget(card)
        
        grid.addStretch()
        layout.addLayout(grid)
        
        return layout
    
    def _create_recent_section(self) -> QVBoxLayout:
        """Create recent projects section."""
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Section header
        header = QHBoxLayout()
        
        title = QLabel("🕐 Proyectos Recientes")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        layout.addLayout(header)
        
        # Empty state or projects
        # For now, show empty state
        empty_state = QFrame()
        empty_state.setFixedHeight(150)
        empty_state.setStyleSheet("""
            background: #1a1a2e;
            border: 1px dashed #3a3a5a;
            border-radius: 12px;
        """)
        
        empty_layout = QVBoxLayout(empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("🎨")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("font-size: 32px;")
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("Aún no tienes proyectos guardados")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet("color: #a0a0b0; font-size: 14px;")
        empty_layout.addWidget(empty_text)
        
        empty_hint = QLabel("¡Crea tu primer lienzo y empieza a dibujar!")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint.setStyleSheet("color: #606070; font-size: 12px;")
        empty_layout.addWidget(empty_hint)
        
        layout.addWidget(empty_state)
        
        return layout
    
    def _on_new_canvas(self):
        """Handle new canvas button click - show dialog."""
        self.show_new_canvas_dialog.emit()
    
    def _on_template_selected(self, template_data: dict):
        """Handle template selection."""
        width = template_data.get("width", 2048)
        height = template_data.get("height", 2048)
        self.new_canvas_requested.emit(width, height)
        self.navigate_to_draw.emit()
