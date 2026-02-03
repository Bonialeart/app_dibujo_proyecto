"""
ArtFlow Studio - Modern New Canvas Dialog
Visually rich, dashboard-style interface for creating projects
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QGridLayout, QGraphicsDropShadowEffect,
    QButtonGroup, QScrollArea, QWidget, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QPen

# --- Data Configuration ---
TEMPLATES = {
    "Illustration": [
        ("Full HD", 1920, 1080, "#4facfe", "#00f2fe", "🖥️", 72),
        ("4K UHD", 3840, 2160, "#43e97b", "#38f9d7", "📺", 72),
        ("Concept Art", 5000, 2800, "#667eea", "#764ba2", "🎨", 300),
        ("Square", 2000, 2000, "#fdfbfb", "#ebedee", "⬜", 300, True),  # Inverted text for light bg
    ],
    "Social Media": [
        ("Insta Square", 1080, 1080, "#e1306c", "#fd1d1d", "📸", 72),
        ("Insta Portrait", 1080, 1350, "#833ab4", "#c13584", "🖼️", 72),
        ("Insta Story", 1080, 1920, "#fd1d1d", "#f56040", "📱", 72),
        ("TikTok/Reel", 1080, 1920, "#000000", "#25F4EE", "🎵", 72),
        ("YouTube", 1280, 720, "#ff0000", "#990000", "▶️", 72),
    ],
    "Print": [
        ("A4 Paper", 2480, 3508, "#11998e", "#38ef7d", "📄", 300),
        ("A3 Paper", 3508, 4961, "#108dc7", "#ef8e38", "📜", 300),
        ("Letter", 2550, 3300, "#FC466B", "#3F5EFB", "📝", 300),
        ("Poster", 5400, 7200, "#00b09b", "#96c93d", "🎇", 300),
    ],
    "Comic": [
        ("Manga B4", 3035, 4299, "#232526", "#414345", "🗯️", 600),
        ("Doujinshi A5", 1748, 2480, "#3a6186", "#89253e", "📘", 600),
        ("Webtoon", 800, 6000, "#485563", "#29323c", "🖱️", 300),
    ]
}

class CategoryButton(QPushButton):
    """Sidebar button to select categories."""
    def __init__(self, text, icon, parent=None):
        super().__init__(parent)
        self.setText(f" {text}") # Spacer
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 11))
        # Store icon as property if needed, but we use text+emoji for now or just text
        
        # We will use CSS for styling state
        
class TemplateCard(QPushButton):
    """Large, visual card for a canvas template. Premium feel."""
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(150, 190)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.title = data[0]
        self.c_width = data[1]
        self.c_height = data[2]
        self.color_start = data[3]
        self.color_end = data[4]
        self.icon_text = data[5]
        self.target_dpi = data[6]
        self.dark_text = data[7] if len(data) > 7 else False
        
        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0,0,0, 60))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # State handling
        is_checked = self.isChecked()
        is_hover = self.underMouse()
        
        # 1. Background Base
        bg_color = QColor("#2a2a2a") if not is_hover else QColor("#333333")
        if is_checked:
            bg_color = QColor("#2d2d2d")
        
        painter.setBrush(bg_color)
        
        # Selection Border
        if is_checked:
            pen = QPen(QColor("#0078d4"), 2)
            painter.setPen(pen)
            draw_rect = rect.adjusted(1, 1, -1, -1)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            draw_rect = rect
            
        painter.drawRoundedRect(draw_rect, 12, 12)
        
        # 2. Gradient Header (Top half)
        header_height = 90
        grad = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top() + header_height)
        grad.setColorAt(0, QColor(self.color_start))
        grad.setColorAt(1, QColor(self.color_end))
        
        path = QPainter.Path()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), header_height, 12, 12)
        
        painter.save()
        painter.setClipPath(path)
        painter.fillRect(rect.x(), rect.y(), rect.width(), header_height, grad)
        painter.restore()
        
        # 3. Icon
        painter.setPen(QColor("#ffffff") if not self.dark_text else QColor("#222222"))
        font = QFont("Segoe UI Emoji", 28)
        painter.setFont(font)
        painter.drawText(rect.x(), rect.y(), rect.width(), header_height, Qt.AlignmentFlag.AlignCenter, self.icon_text)
        
        # 4. Text Content
        text_y_start = header_height + 25
        
        # Title
        painter.setPen(QColor("#ffffff"))
        if is_checked:
             painter.setPen(QColor("#5aa9fb"))
             
        font_title = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.drawText(rect.x() + 10, text_y_start, rect.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, self.title)
        
        # Dimensions
        painter.setPen(QColor("#999999"))
        font_sub = QFont("Segoe UI", 9)
        painter.setFont(font_sub)
        dim_str = f"{self.c_width} x {self.c_height}"
        painter.drawText(rect.x() + 10, text_y_start + 22, rect.width() - 20, 16, Qt.AlignmentFlag.AlignLeft, dim_str)
        
        # DPI Badge
        badge_rect = QRectF(rect.x() + 10, text_y_start + 45, 30, 16)
        # Using a simple text for DPI instead of badge to keep it clean
        painter.drawText(rect.x() + 10, text_y_start + 42, rect.width() - 20, 16, Qt.AlignmentFlag.AlignLeft, f"{self.target_dpi} DPI")

from PyQt6.QtCore import QRectF

class ModernNewCanvasDialog(QDialog):
    canvas_created = pyqtSignal(int, int, int) # w, h, dpi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Proyecto")
        self.resize(1000, 650)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.selected_w = 1920
        self.selected_h = 1080
        self.selected_dpi = 72
        
        self.category_btns = []
        self.template_cards = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Translucent background handling
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        background = QFrame()
        background.setObjectName("popupBg")
        background.setStyleSheet("""
            QFrame#popupBg {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 16px;
            }
        """)
        
        # Deep Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 200))
        background.setGraphicsEffect(shadow)
        
        layout_container = QHBoxLayout(background)
        layout_container.setContentsMargins(0, 0, 0, 0)
        layout_container.setSpacing(0)
        
        # ===========================
        # 1. Sidebar (Categories)
        # ===========================
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QWidget { background-color: #222222; border-top-left-radius: 16px; border-bottom-left-radius: 16px; }
            QPushButton {
                text-align: left;
                padding-left: 20px;
                border: none;
                color: #888;
                background: transparent;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                color: #ddd;
                background: #2a2a2a;
            }
            QPushButton:checked {
                color: white;
                background: #2d2d2d;
                border-left: 3px solid #0078d4;
                font-weight: bold;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 30, 0, 30)
        sidebar_layout.setSpacing(5)
        
        lbl_brand = QLabel("ArtFlow")
        lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_brand.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        sidebar_layout.addWidget(lbl_brand)
        
        self.cat_group = QButtonGroup()
        self.cat_group.setExclusive(True)
        self.cat_group.buttonClicked.connect(self._on_category_changed)
        
        cats = ["Illustration", "Print", "Comic", "Social Media"]
        for cat in cats:
            btn = CategoryButton(cat, "")
            self.cat_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            self.category_btns.append(btn)
            
        sidebar_layout.addStretch()
        
        # Settings/About link could go here
        
        layout_container.addWidget(sidebar)
        
        # ===========================
        # 2. Main Content (Grid)
        # ===========================
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        self.lbl_cat_title = QLabel("Illustration Docs")
        self.lbl_cat_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        content_layout.addWidget(self.lbl_cat_title)
        
        content_layout.addSpacing(20)
        
        # Scroll Area for Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #222;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.grid_widget)
        content_layout.addWidget(self.scroll)
        
        layout_container.addWidget(content_area)
        
        # ===========================
        # 3. Right Panel (Details)
        # ===========================
        right_panel = QFrame()
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("""
            QFrame { background-color: #1e1e1e; border-top-right-radius: 16px; border-bottom-right-radius: 16px; border-left: 1px solid #333; }
            QLabel { color: #bcbcbc; }
            QSpinBox {
                background: #252525;
                border: 1px solid #3e3e3e;
                color: white;
                border-radius: 4px;
                padding: 5px;
            }
            QSpinBox:focus { border: 1px solid #0078d4; }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(25, 40, 25, 40)
        right_layout.setSpacing(20)
        
        lbl_details = QLabel("Detalles del Lienzo")
        lbl_details.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        right_layout.addWidget(lbl_details)
        
        # Width
        self.spin_w = self._create_spinbox(1920)
        right_layout.addWidget(self._create_label_input("Ancho (px)", self.spin_w))
        
        # Height
        self.spin_h = self._create_spinbox(1080)
        right_layout.addWidget(self._create_label_input("Alto (px)", self.spin_h))
        
        # DPI
        self.spin_dpi = self._create_spinbox(72, 600)
        right_layout.addWidget(self._create_label_input("Resolución (DPI)", self.spin_dpi))
        
        # Units (Visual wrapper only for now, assume px)
        # Could add QComboBox for cm/inch conversion later
        
        right_layout.addStretch()
        
        # Color Mode
        lbl_mode = QLabel("Modo de Color")
        lbl_mode.setStyleSheet("font-size: 12px; font-weight: bold;")
        right_layout.addWidget(lbl_mode)
        
        mode_layout = QHBoxLayout()
        self.rb_rgb = QRadioButton("RGB")
        self.rb_rgb.setChecked(True)
        self.rb_rgb.setStyleSheet("color: white;")
        self.rb_cmyk = QRadioButton("CMYK")
        self.rb_cmyk.setStyleSheet("color: white;")
        mode_layout.addWidget(self.rb_rgb)
        mode_layout.addWidget(self.rb_cmyk)
        right_layout.addLayout(mode_layout)

        right_layout.addSpacing(20)

        # Actions
        btn_create = QPushButton("Crear")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setFixedHeight(50)
        btn_create.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d9; }
            QPushButton:pressed { background-color: #0060aa; }
        """)
        btn_create.clicked.connect(self.accept_creation)
        right_layout.addWidget(btn_create)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent; 
                color: #888; 
                border: 1px solid #444; 
                border-radius: 8px;
                height: 35px;
            }
            QPushButton:hover { color: white; border: 1px solid #666; }
        """)
        btn_cancel.clicked.connect(self.reject)
        right_layout.addWidget(btn_cancel)
        
        layout_container.addWidget(right_panel)
        main_layout.addWidget(background)
        
        # Init
        self.current_template_group = QButtonGroup()
        self.current_template_group.setExclusive(True)
        self.category_btns[0].setChecked(True) # Select first cat
        self._load_category("Illustration")

    def _create_spinbox(self, val, max_val=10000):
        spin = QSpinBox()
        spin.setRange(1, max_val)
        spin.setValue(val)
        spin.setFixedHeight(40)
        spin.valueChanged.connect(self.manual_change)
        return spin
        
    def _create_label_input(self, text, widget):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(6)
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return container

    def _on_category_changed(self, btn):
        cat_name = btn.text().strip()
        self._load_category(cat_name)

    def _load_category(self, category_name):
        self.lbl_cat_title.setText(category_name)
        
        # Clear grid
        # Note: In PySide/Qt, simply removing from layout doesn't delete widgets. 
        # But for this simple dialog, we can just delete them.
        for i in reversed(range(self.grid_layout.count())): 
            w = self.grid_layout.itemAt(i).widget()
            if w: w.setParent(None)
            
        # Rebuild grid
        templates = TEMPLATES.get(category_name, [])
        self.current_template_group = QButtonGroup() # New group
        self.current_template_group.setExclusive(True)
        
        row, col = 0, 0
        MAX_COLS = 3
        
        for data in templates:
            card = TemplateCard(data)
            card.clicked.connect(lambda ch, d=data: self.apply_template(d))
            self.current_template_group.addButton(card)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= MAX_COLS:
                col = 0
                row += 1
                
        # Fill selected matches logic
        # Default select nothing or keep manual?
        pass

    def apply_template(self, data):
        # data = (Name, W, H, C1, C2, Icon, DPI)
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        self.spin_dpi.blockSignals(True)
        
        self.spin_w.setValue(data[1])
        self.spin_h.setValue(data[2])
        self.spin_dpi.setValue(data[6])
        
        self.selected_w = data[1]
        self.selected_h = data[2]
        self.selected_dpi = data[6]
        
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)
        self.spin_dpi.blockSignals(False)

    def manual_change(self):
        # Deselect presets if manual change
        if self.current_template_group.checkedButton():
             # We rely on ButtonGroup exclusivity, but we need to uncheck manually
             self.current_template_group.setExclusive(False)
             self.current_template_group.checkedButton().setChecked(False)
             self.current_template_group.setExclusive(True)
             
        self.selected_w = self.spin_w.value()
        self.selected_h = self.spin_h.value()
        self.selected_dpi = self.spin_dpi.value()

    def accept_creation(self):
        self.canvas_created.emit(self.selected_w, self.selected_h, self.selected_dpi)
        self.accept()
