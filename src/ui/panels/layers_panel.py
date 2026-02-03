"""
ArtFlow Studio - Layers Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QSlider, QComboBox,
    QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter


class LayerItem(QFrame):
    """Custom widget for layer list items."""
    
    visibility_changed = pyqtSignal(bool)
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.layer_name = name
        self.is_visible = True
        self.is_locked = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Visibility toggle
        self.vis_btn = QPushButton("👁")
        self.vis_btn.setFixedSize(24, 24)
        self.vis_btn.setCheckable(True)
        self.vis_btn.setChecked(True)
        self.vis_btn.clicked.connect(self._toggle_visibility)
        self.vis_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:checked {
                opacity: 1.0;
            }
            QPushButton:!checked {
                opacity: 0.3;
            }
        """)
        layout.addWidget(self.vis_btn)
        
        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(40, 40)
        self.thumbnail.setStyleSheet("background: #3a3a5a; border-radius: 4px;")
        layout.addWidget(self.thumbnail)
        
        # Name
        self.name_label = QLabel(self.layer_name)
        self.name_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.name_label, 1)
        
        # Lock toggle
        self.lock_btn = QPushButton("🔓")
        self.lock_btn.setFixedSize(24, 24)
        self.lock_btn.setCheckable(True)
        self.lock_btn.clicked.connect(self._toggle_lock)
        self.lock_btn.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.lock_btn)
    
    def _toggle_visibility(self):
        self.is_visible = self.vis_btn.isChecked()
        self.visibility_changed.emit(self.is_visible)
    
    def _toggle_lock(self):
        self.is_locked = self.lock_btn.isChecked()
        self.lock_btn.setText("🔒" if self.is_locked else "🔓")


class LayersPanel(QWidget):
    """Panel for layer management."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._add_default_layers()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Capas")
        title.setStyleSheet("color: #a0a0b0; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # Blend mode and opacity
        controls = QHBoxLayout()
        
        self.blend_combo = QComboBox()
        self.blend_combo.addItems([
            "Normal", "Multiplicar", "Pantalla", "Superponer",
            "Luz suave", "Luz fuerte", "Sobreexponer", "Subexponer"
        ])
        self.blend_combo.setStyleSheet("""
            QComboBox {
                background: #252540;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        controls.addWidget(self.blend_combo)
        
        layout.addLayout(controls)
        
        # Opacity slider
        opacity_layout = QHBoxLayout()
        
        opacity_label = QLabel("Opacidad")
        opacity_label.setStyleSheet("color: #a0a0b0;")
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #252540;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00d4aa;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #00d4aa;
                border-radius: 3px;
            }
        """)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value = QLabel("100%")
        self.opacity_value.setStyleSheet("color: #ffffff; min-width: 40px;")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.opacity_value)
        
        layout.addLayout(opacity_layout)
        
        # Layer list
        self.layer_list = QListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.layer_list.setStyleSheet("""
            QListWidget {
                background: #1a1a2e;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
            }
            QListWidget::item {
                background: #252540;
                border-radius: 4px;
                margin: 2px 4px;
                padding: 4px;
            }
            QListWidget::item:selected {
                background: #00d4aa;
            }
            QListWidget::item:hover {
                background: #3a3a5a;
            }
        """)
        layout.addWidget(self.layer_list, 1)
        
        # Layer actions
        actions = QHBoxLayout()
        actions.setSpacing(4)
        
        btn_style = """
            QPushButton {
                background: #252540;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #3a3a5a;
            }
        """
        
        add_btn = QPushButton("+")
        add_btn.setStyleSheet(btn_style)
        add_btn.clicked.connect(self._add_layer)
        actions.addWidget(add_btn)
        
        folder_btn = QPushButton("📁")
        folder_btn.setStyleSheet(btn_style)
        actions.addWidget(folder_btn)
        
        delete_btn = QPushButton("🗑")
        delete_btn.setStyleSheet(btn_style)
        delete_btn.clicked.connect(self._delete_layer)
        actions.addWidget(delete_btn)
        
        actions.addStretch()
        
        merge_btn = QPushButton("⬇ Combinar")
        merge_btn.setStyleSheet(btn_style)
        actions.addWidget(merge_btn)
        
        layout.addLayout(actions)
        
        self.setStyleSheet("background: #1a1a2e;")
    
    def _add_default_layers(self):
        """Add default layers."""
        self._add_layer_item("Layer 1")
        self._add_layer_item("Background")
    
    def _add_layer(self):
        """Add a new layer."""
        count = self.layer_list.count()
        self._add_layer_item(f"Layer {count + 1}")
    
    def _add_layer_item(self, name: str):
        """Add a layer item to the list."""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 50))
        
        widget = LayerItem(name)
        
        self.layer_list.insertItem(0, item)
        self.layer_list.setItemWidget(item, widget)
    
    def _delete_layer(self):
        """Delete selected layer."""
        current = self.layer_list.currentRow()
        if current >= 0 and self.layer_list.count() > 1:
            self.layer_list.takeItem(current)
