"""
ArtFlow Studio - Main Window (Refined)
Clean UI inspired by Clip Studio Paint and Procreate
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QDockWidget, QStackedWidget,
    QLabel, QFrame, QPushButton, QToolBar, QSlider,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QColor

from .panels.home_panel import HomePanel
from .panels.canvas_panel import CanvasPanel
from .panels.layers_panel import LayersPanel
from .panels.colors_panel import ColorsPanel
from .panels.brushes_panel import BrushesPanel
from .panels.tools_panel import ToolsPanel
from .panels.learn_panel import LearnPanel
from .panels.resources_panel import ResourcesPanel
from .panels.sidebar import Sidebar
from .panels.resources_panel import ResourcesPanel
from .panels.sidebar import Sidebar
from .dialogs.modern_new_canvas import ModernNewCanvasDialog


class MainWindow(QMainWindow):
    """Main application window with clean, professional UI."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ArtFlow Studio Pro")
        self.setMinimumSize(1366, 768)
        
        # Track current mode
        self.current_mode = "home"
        
        # Create UI components
        self._setup_ui()
        self._setup_menus()
        self._setup_drawing_toolbar()
        self._setup_statusbar()
        self._setup_docks()
        self._connect_signals()
        
        # Apply styling
        self._apply_styles()
        
        # Start with home panel
        self._show_home_mode()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar (minimal)
        self.sidebar = Sidebar()
        self.sidebar.section_changed.connect(self._on_section_changed)
        main_layout.addWidget(self.sidebar)
        
        # Content area
        self.content_stack = QStackedWidget()
        
        # Create panels
        self.home_panel = HomePanel()
        self.canvas_panel = CanvasPanel()
        self.learn_panel = LearnPanel()
        self.resources_panel = ResourcesPanel()
        self.brushes_library_panel = BrushesPanel(library_mode=True)
        
        # Add to stack
        self.content_stack.addWidget(self.home_panel)            # 0
        self.content_stack.addWidget(self.canvas_panel)          # 1
        self.content_stack.addWidget(self.learn_panel)           # 2
        self.content_stack.addWidget(self.brushes_library_panel) # 3
        self.content_stack.addWidget(self.resources_panel)       # 4
        
        main_layout.addWidget(self.content_stack, 1)
    
    def _setup_menus(self):
        """Setup minimal menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&Archivo")
        
        new_action = QAction("&Nuevo Lienzo", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._show_new_canvas_dialog)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Abrir...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Guardar", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        file_menu.addAction(save_action)
        
        export_action = QAction("&Exportar...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        home_action = QAction("🏠 &Inicio", self)
        home_action.setShortcut(QKeySequence("Ctrl+H"))
        home_action.triggered.connect(self._show_home_mode)
        file_menu.addAction(home_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Editar")
        
        undo_action = QAction("↩ &Deshacer", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("↪ &Rehacer", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction("🗑 &Limpiar Lienzo", self)
        clear_action.triggered.connect(self._clear_canvas)
        edit_menu.addAction(clear_action)
        
        # View menu
        view_menu = menubar.addMenu("&Ver")
        
        zoom_in = QAction("🔍+ Acercar", self)
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        view_menu.addAction(zoom_in)
        
        zoom_out = QAction("🔍- Alejar", self)
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        view_menu.addAction(zoom_out)
    
    def _setup_drawing_toolbar(self):
        """Setup bottom toolbar with brush size and opacity (like Clip Studio)."""
        self.drawing_toolbar = QToolBar("Controles de Dibujo")
        self.drawing_toolbar.setMovable(False)
        self.drawing_toolbar.setIconSize(QSize(20, 20))
        self.drawing_toolbar.setStyleSheet("""
            QToolBar {
                background: #0a0a12;
                border: none;
                border-top: 1px solid #1a1a2e;
                padding: 8px 16px;
                spacing: 16px;
            }
        """)
        
        # Brush size section
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(8)
        
        size_icon = QLabel("🖌️")
        size_icon.setStyleSheet("font-size: 16px;")
        size_layout.addWidget(size_icon)
        
        self.toolbar_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.toolbar_size_slider.setRange(1, 500)
        self.toolbar_size_slider.setValue(20)
        self.toolbar_size_slider.setFixedWidth(200)
        self.toolbar_size_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #252540;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00d4aa;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #00d4aa;
                border-radius: 3px;
            }
        """)
        self.toolbar_size_slider.valueChanged.connect(self._on_toolbar_size_changed)
        size_layout.addWidget(self.toolbar_size_slider)
        
        self.toolbar_size_label = QLabel("20")
        self.toolbar_size_label.setFixedWidth(40)
        self.toolbar_size_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        size_layout.addWidget(self.toolbar_size_label)
        
        self.drawing_toolbar.addWidget(size_widget)
        
        # Separator
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background: #3a3a5a;")
        self.drawing_toolbar.addWidget(separator)
        
        # Opacity section
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(8)
        
        opacity_icon = QLabel("💧")
        opacity_icon.setStyleSheet("font-size: 16px;")
        opacity_layout.addWidget(opacity_icon)
        
        self.toolbar_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.toolbar_opacity_slider.setRange(1, 100)
        self.toolbar_opacity_slider.setValue(100)
        self.toolbar_opacity_slider.setFixedWidth(150)
        self.toolbar_opacity_slider.setStyleSheet(self.toolbar_size_slider.styleSheet())
        self.toolbar_opacity_slider.valueChanged.connect(self._on_toolbar_opacity_changed)
        opacity_layout.addWidget(self.toolbar_opacity_slider)
        
        self.toolbar_opacity_label = QLabel("100%")
        self.toolbar_opacity_label.setFixedWidth(45)
        self.toolbar_opacity_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        opacity_layout.addWidget(self.toolbar_opacity_label)
        
        self.drawing_toolbar.addWidget(opacity_widget)
        
        # Add spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.drawing_toolbar.addWidget(spacer)
        
        # Color preview (quick access)
        self.toolbar_color_btn = QPushButton()
        self.toolbar_color_btn.setFixedSize(40, 40)
        self.toolbar_color_btn.setStyleSheet("""
            QPushButton {
                background: #000000;
                border: 3px solid #3a3a5a;
                border-radius: 20px;
            }
            QPushButton:hover {
                border-color: #00d4aa;
            }
        """)
        self.drawing_toolbar.addWidget(self.toolbar_color_btn)
        
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.drawing_toolbar)
        self.drawing_toolbar.hide()  # Hidden by default
    
    def _setup_statusbar(self):
        """Setup minimal status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Canvas info
        self.canvas_size_label = QLabel("")
        self.canvas_size_label.setStyleSheet("color: #606070; padding: 0 12px;")
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #00d4aa; font-weight: bold; padding: 0 12px;")
        
        self.status_bar.addPermanentWidget(self.canvas_size_label)
        self.status_bar.addPermanentWidget(self.zoom_label)
        
        self.status_bar.showMessage("Bienvenido a ArtFlow Studio ✨")
    
    def _setup_docks(self):
        """Setup floating panels (Procreate style - minimal and elegant)."""
        # Colors dock
        self.colors_panel = ColorsPanel()
        self.colors_dock = QDockWidget("Colores", self)
        self.colors_dock.setWidget(self.colors_panel)
        self.colors_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | 
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.colors_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.colors_dock)
        
        # Layers dock
        self.layers_panel = LayersPanel()
        self.layers_dock = QDockWidget("Capas", self)
        self.layers_dock.setWidget(self.layers_panel)
        self.layers_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | 
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.layers_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)
        
        # Brushes dock
        self.brushes_panel = BrushesPanel()
        self.brushes_dock = QDockWidget("Pinceles", self)
        self.brushes_dock.setWidget(self.brushes_panel)
        self.brushes_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | 
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.brushes_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.brushes_dock)
        
        # Tab the docks together
        self.tabifyDockWidget(self.layers_dock, self.brushes_dock)
        self.layers_dock.raise_()
    
    def _connect_signals(self):
        """Connect all signals between components."""
        # Home panel
        self.home_panel.new_canvas_requested.connect(self._create_canvas)
        self.home_panel.navigate_to_draw.connect(self._show_draw_mode)
        self.home_panel.show_new_canvas_dialog.connect(self._show_new_canvas_dialog)
        
        # Color panel → Canvas & Toolbar
        self.colors_panel.color_changed.connect(self._on_color_changed)
        
        # Brush panel → Canvas
        self.brushes_panel.brush_size_changed.connect(self._on_brush_size_changed)
        self.brushes_panel.brush_opacity_changed.connect(self._on_brush_opacity_changed)
        self.brushes_panel.brush_changed.connect(self._on_brush_changed)
    
    def _apply_styles(self):
        """Apply clean, modern styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f1a;
            }
            QMenuBar {
                background-color: #0a0a12;
                color: #ffffff;
                padding: 4px 8px;
                border-bottom: 1px solid #1a1a2e;
            }
            QMenuBar::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #00d4aa;
                color: #0f0f1a;
            }
            QMenu {
                background-color: #1a1a2e;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                padding: 8px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #00d4aa;
                color: #0f0f1a;
            }
            QMenu::separator {
                height: 1px;
                background: #3a3a5a;
                margin: 4px 8px;
            }
            QStatusBar {
                background-color: #0a0a12;
                color: #606070;
                border-top: 1px solid #1a1a2e;
            }
            QDockWidget {
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
            }
            QDockWidget::title {
                background: #1a1a2e;
                padding: 10px 12px;
                border-bottom: 1px solid #252540;
            }
            QDockWidget::close-button,
            QDockWidget::float-button {
                background: transparent;
                border: none;
                padding: 4px;
            }
        """)
    
    # === Mode Navigation ===
    
    def _on_section_changed(self, section: str):
        """Handle sidebar navigation."""
        if section == "home":
            self._show_home_mode()
        elif section == "learn":
            self._show_learn_mode()
        elif section == "brushes":
            self._show_brushes_library()
        elif section == "resources":
            self._show_resources_mode()
    
    def _show_home_mode(self):
        """Show home/welcome screen."""
        self.current_mode = "home"
        self.content_stack.setCurrentWidget(self.home_panel)
        
        # Hide drawing UI
        self.colors_dock.hide()
        self.layers_dock.hide()
        self.brushes_dock.hide()
        self.drawing_toolbar.hide()
        
        self.status_bar.showMessage("Inicio ✨")
    
    def _show_draw_mode(self):
        """Show drawing canvas."""
        self.current_mode = "draw"
        self.content_stack.setCurrentWidget(self.canvas_panel)
        
        # Show drawing UI
        self.colors_dock.show()
        self.layers_dock.show()
        self.brushes_dock.show()
        self.drawing_toolbar.show()
        
        self.status_bar.showMessage("Modo Dibujo 🎨")
    
    def _show_learn_mode(self):
        """Show learning content."""
        self.current_mode = "learn"
        self.content_stack.setCurrentWidget(self.learn_panel)
        
        self.colors_dock.hide()
        self.layers_dock.hide()
        self.brushes_dock.hide()
        self.drawing_toolbar.hide()
        
        self.status_bar.showMessage("Aprende 📚")
    
    def _show_brushes_library(self):
        """Show brush library."""
        self.current_mode = "brushes"
        self.content_stack.setCurrentWidget(self.brushes_library_panel)
        
        self.colors_dock.hide()
        self.layers_dock.hide()
        self.brushes_dock.hide()
        self.drawing_toolbar.hide()
        
        self.status_bar.showMessage("Biblioteca de Pinceles 🖌️")
    
    def _show_resources_mode(self):
        """Show resources."""
        self.current_mode = "resources"
        self.content_stack.setCurrentWidget(self.resources_panel)
        
        self.colors_dock.hide()
        self.layers_dock.hide()
        self.brushes_dock.hide()
        self.drawing_toolbar.hide()
        
        self.status_bar.showMessage("Recursos 🔗")
    
    # === Canvas Actions ===
    
    def _show_new_canvas_dialog(self):
        """Show elegant new canvas dialog."""
        dialog = ModernNewCanvasDialog(self)
        # Connect to a wrapper to handle creation and navigation
        dialog.canvas_created.connect(self._on_canvas_created_from_dialog)
        dialog.exec()

    def _on_canvas_created_from_dialog(self, width, height, dpi):
        self._create_canvas(width, height, dpi)
        self._show_draw_mode()
    
    def _create_canvas(self, width: int, height: int, dpi: int = 72):
        """Create a new canvas."""
        self.canvas_panel.create_new_canvas(width, height, dpi)
        self.canvas_size_label.setText(f"{width} × {height} px ({dpi} DPI)")
        self.status_bar.showMessage(f"Nuevo lienzo: {width}×{height} px @ {dpi} DPI ✨")
    
    def _clear_canvas(self):
        """Clear current canvas."""
        if hasattr(self.canvas_panel, 'canvas'):
            self.canvas_panel.canvas.clear()
            self.status_bar.showMessage("Lienzo limpiado 🗑️")
    
    # === Tool Updates ===
    
    def _on_color_changed(self, color: QColor):
        """Update brush color everywhere."""
        self.canvas_panel.canvas.brush_color = color
        
        # Update toolbar color button
        self.toolbar_color_btn.setStyleSheet(f"""
            QPushButton {{
                background: {color.name()};
                border: 3px solid #3a3a5a;
                border-radius: 20px;
            }}
            QPushButton:hover {{
                border-color: #00d4aa;
            }}
        """)
    
    def _on_brush_size_changed(self, size: int):
        """Update brush size."""
        self.canvas_panel.canvas.brush_size = size
        self.toolbar_size_slider.blockSignals(True)
        self.toolbar_size_slider.setValue(size)
        self.toolbar_size_slider.blockSignals(False)
        self.toolbar_size_label.setText(str(size))
    
    def _on_brush_opacity_changed(self, opacity: float):
        """Update brush opacity."""
        self.canvas_panel.canvas.brush_opacity = opacity
        percent = int(opacity * 100)
        self.toolbar_opacity_slider.blockSignals(True)
        self.toolbar_opacity_slider.setValue(percent)
        self.toolbar_opacity_slider.blockSignals(False)
        self.toolbar_opacity_label.setText(f"{percent}%")
    
    def _on_toolbar_size_changed(self, value: int):
        """Handle toolbar size slider change."""
        self.canvas_panel.canvas.brush_size = value
        self.toolbar_size_label.setText(str(value))
        # Sync with brushes panel
        self.brushes_panel.size_slider.blockSignals(True)
        self.brushes_panel.size_slider.setValue(value)
        self.brushes_panel.size_slider.blockSignals(False)
        self.brushes_panel.size_value.setText(f"{value} px")
    
    def _on_toolbar_opacity_changed(self, value: int):
        """Handle toolbar opacity slider change."""
        opacity = value / 100.0
        self.canvas_panel.canvas.brush_opacity = opacity
        self.toolbar_opacity_label.setText(f"{value}%")
        # Sync with brushes panel
        self.brushes_panel.opacity_slider.blockSignals(True)
        self.brushes_panel.opacity_slider.setValue(value)
        self.brushes_panel.opacity_slider.blockSignals(False)
        self.brushes_panel.opacity_value.setText(f"{value}%")

    def _on_brush_changed(self, brush_data: dict):
        """Handle brush selection change."""
        brush_type = brush_data.get("type", "default")
        self.canvas_panel.canvas.brush_type = brush_type
        self.status_bar.showMessage(f"Pincel seleccionado: {brush_data.get('name', 'Pincel')}")
