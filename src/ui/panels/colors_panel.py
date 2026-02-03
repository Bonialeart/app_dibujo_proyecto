"""
ArtFlow Studio - Colors Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QConicalGradient, QRadialGradient, QMouseEvent
import math


class ColorWheel(QWidget):
    """HSV Color wheel widget."""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        
        self._hue = 0
        self._saturation = 1.0
        self._value = 1.0
        
        self.setMouseTracking(True)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 10
        
        # Draw hue ring
        for i in range(360):
            color = QColor.fromHsvF(i / 360.0, 1.0, 1.0)
            painter.setPen(color)
            angle = math.radians(i)
            x1 = center.x() + int((radius - 15) * math.cos(angle))
            y1 = center.y() - int((radius - 15) * math.sin(angle))
            x2 = center.x() + int(radius * math.cos(angle))
            y2 = center.y() - int(radius * math.sin(angle))
            painter.drawLine(x1, y1, x2, y2)
        
        # Draw SV square
        inner_radius = radius - 20
        square_size = int(inner_radius * 1.4)
        square_x = center.x() - square_size // 2
        square_y = center.y() - square_size // 2
        
        # Saturation gradient (left to right)
        for x in range(square_size):
            for y in range(square_size):
                s = x / square_size
                v = 1.0 - (y / square_size)
                color = QColor.fromHsvF(self._hue / 360.0, s, v)
                painter.setPen(color)
                painter.drawPoint(square_x + x, square_y + y)
        
        # Draw current position marker
        sx = int(self._saturation * square_size)
        sy = int((1.0 - self._value) * square_size)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawEllipse(QPoint(square_x + sx, square_y + sy), 5, 5)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawEllipse(QPoint(square_x + sx, square_y + sy), 6, 6)
    
    def mousePressEvent(self, event: QMouseEvent):
        self._update_color(event.position())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_color(event.position())
    
    def _update_color(self, pos):
        center = self.rect().center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        distance = math.sqrt(dx * dx + dy * dy)
        radius = min(self.width(), self.height()) // 2 - 10
        inner_radius = radius - 20
        
        if distance > inner_radius * 0.7:
            # On hue ring
            angle = math.atan2(-dy, dx)
            self._hue = (math.degrees(angle) + 360) % 360
        else:
            # In SV square
            square_size = int(inner_radius * 1.4)
            square_x = center.x() - square_size // 2
            square_y = center.y() - square_size // 2
            
            sx = max(0, min(square_size, pos.x() - square_x))
            sy = max(0, min(square_size, pos.y() - square_y))
            
            self._saturation = sx / square_size
            self._value = 1.0 - (sy / square_size)
        
        self.update()
        self.color_changed.emit(self.get_color())
    
    def get_color(self) -> QColor:
        return QColor.fromHsvF(self._hue / 360.0, self._saturation, self._value)
    
    def set_color(self, color: QColor):
        self._hue = color.hueF() * 360
        self._saturation = color.saturationF()
        self._value = color.valueF()
        self.update()


class ColorsPanel(QWidget):
    """Panel for color selection."""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_color = QColor(0, 0, 0)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Color wheel
        wheel_container = QHBoxLayout()
        wheel_container.addStretch()
        
        self.color_wheel = ColorWheel()
        self.color_wheel.color_changed.connect(self._on_wheel_changed)
        wheel_container.addWidget(self.color_wheel)
        
        wheel_container.addStretch()
        layout.addLayout(wheel_container)
        
        # Color preview
        preview_layout = QHBoxLayout()
        
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(60, 40)
        self.color_preview.setStyleSheet(f"""
            background: {self._current_color.name()};
            border: 2px solid #3a3a5a;
            border-radius: 4px;
        """)
        preview_layout.addWidget(self.color_preview)
        
        # Hex input
        self.hex_input = QLineEdit("#000000")
        self.hex_input.setMaxLength(7)
        self.hex_input.setStyleSheet("""
            QLineEdit {
                background: #252540;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
            }
        """)
        self.hex_input.returnPressed.connect(self._on_hex_changed)
        preview_layout.addWidget(self.hex_input)
        
        layout.addLayout(preview_layout)
        
        # RGB sliders
        self._create_slider_row(layout, "R", 0, 255, 0)
        self._create_slider_row(layout, "G", 0, 255, 0)
        self._create_slider_row(layout, "B", 0, 255, 0)
        
        layout.addSpacing(8)
        
        # Recent colors
        recent_label = QLabel("Colores recientes")
        recent_label.setStyleSheet("color: #a0a0b0;")
        layout.addWidget(recent_label)
        
        self.recent_colors = QGridLayout()
        self.recent_colors.setSpacing(4)
        
        # Add some default recent colors
        default_colors = [
            "#000000", "#ffffff", "#ff0000", "#00ff00",
            "#0000ff", "#ffff00", "#ff00ff", "#00ffff",
            "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4"
        ]
        
        for i, color in enumerate(default_colors):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"""
                background: {color};
                border: 1px solid #3a3a5a;
                border-radius: 4px;
            """)
            btn.clicked.connect(lambda c, col=color: self.set_color(QColor(col)))
            self.recent_colors.addWidget(btn, i // 6, i % 6)
        
        layout.addLayout(self.recent_colors)
        layout.addStretch()
        
        self.setStyleSheet("background: #1a1a2e;")
    
    def _create_slider_row(self, parent_layout, label: str, min_val: int, max_val: int, default: int):
        row = QHBoxLayout()
        
        lbl = QLabel(label)
        lbl.setFixedWidth(20)
        lbl.setStyleSheet("color: #a0a0b0;")
        row.addWidget(lbl)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.setStyleSheet("""
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
        """)
        slider.valueChanged.connect(self._on_slider_changed)
        row.addWidget(slider)
        
        setattr(self, f"slider_{label.lower()}", slider)
        
        value = QLabel(str(default))
        value.setFixedWidth(30)
        value.setStyleSheet("color: #ffffff;")
        slider.valueChanged.connect(lambda v: value.setText(str(v)))
        row.addWidget(value)
        
        parent_layout.addLayout(row)
    
    def _on_wheel_changed(self, color: QColor):
        self._current_color = color
        self._update_ui()
        self.color_changed.emit(color)
    
    def _on_hex_changed(self):
        hex_str = self.hex_input.text()
        if QColor.isValidColorName(hex_str):
            self.set_color(QColor(hex_str))
    
    def _on_slider_changed(self):
        r = self.slider_r.value()
        g = self.slider_g.value()
        b = self.slider_b.value()
        self._current_color = QColor(r, g, b)
        self._update_ui(update_sliders=False)
        self.color_changed.emit(self._current_color)
    
    def _update_ui(self, update_sliders=True):
        self.color_preview.setStyleSheet(f"""
            background: {self._current_color.name()};
            border: 2px solid #3a3a5a;
            border-radius: 4px;
        """)
        self.hex_input.setText(self._current_color.name())
        
        if update_sliders:
            self.slider_r.blockSignals(True)
            self.slider_g.blockSignals(True)
            self.slider_b.blockSignals(True)
            
            self.slider_r.setValue(self._current_color.red())
            self.slider_g.setValue(self._current_color.green())
            self.slider_b.setValue(self._current_color.blue())
            
            self.slider_r.blockSignals(False)
            self.slider_g.blockSignals(False)
            self.slider_b.blockSignals(False)
    
    def set_color(self, color: QColor):
        self._current_color = color
        self.color_wheel.set_color(color)
        self._update_ui()
        self.color_changed.emit(color)
    
    def get_color(self) -> QColor:
        return self._current_color
