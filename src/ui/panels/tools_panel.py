"""
ArtFlow Studio - Tools Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon


import os

class ToolButton(QPushButton):
    """Custom tool button with SVG icon support."""
    
    def __init__(self, icon_path: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Load icon
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
        else:
            # Fallback if icon missing
            print(f"[ToolButton] Warning: Icon not found at {icon_path}")
            self.setText("?")
            
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background: #252540;
            }
            QPushButton:checked {
                background: #00d4aa;
            }
        """)


class ToolsPanel(QWidget):
    """Left toolbar with drawing tools."""
    
    tool_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(54) # Increased slightly for better padding
        
        # Base directory for icons
        self.icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icons"
        )
        
        self._current_tool = "brush"
        self._buttons = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 10, 7, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Tool groups
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        tools = [
            ("move", "move.svg", "Mover (V)"),
            ("selection", "selection.svg", "Selección (M)"),
            ("brush", "brush.svg", "Pincel (B)"),
            ("pencil", "pencil.svg", "Lápiz (P)"),
            ("eraser", "eraser.svg", "Borrador (E)"),
            ("fill", "fill.svg", "Rellenar (G)"),
            ("eyedropper", "picker.svg", "Cuentagotas (I)"),
            ("text", "text.svg", "Texto (T)"),
            ("shape", "shape.svg", "Formas (U)"),
            ("smudge", "hand.svg", "Difuminar"),
        ]
        
        for tool_id, icon_name, tooltip in tools:
            icon_path = os.path.join(self.icons_dir, icon_name)
            btn = ToolButton(icon_path, tooltip)
            btn.clicked.connect(lambda checked, t=tool_id: self._on_tool_clicked(t))
            
            self._buttons[tool_id] = btn
            self.button_group.addButton(btn)
            layout.addWidget(btn)
            
            # Add separator after selection tools
            if tool_id == "selection":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: #3a3a5a; margin: 4px 0;")
                layout.addWidget(sep)
        
        # Set brush as default
        self._buttons["brush"].setChecked(True)
        
        layout.addStretch()
        
        # Bottom tools
        bottom_tools = [
            ("zoom", "zoom.svg", "Zoom (Z)"),
            ("rotate", "rotate.svg", "Rotar Vista (R)"),
        ]
        
        for tool_id, icon_name, tooltip in bottom_tools:
            icon_path = os.path.join(self.icons_dir, icon_name)
            btn = ToolButton(icon_path, tooltip)
            btn.clicked.connect(lambda checked, t=tool_id: self._on_tool_clicked(t))
            self._buttons[tool_id] = btn
            self.button_group.addButton(btn)
            layout.addWidget(btn)
        
        self.setStyleSheet("""
            QWidget {
                background: #0f0f1a;
                border-right: 1px solid #252540;
            }
        """)
    
    def _on_tool_clicked(self, tool: str):
        if tool != self._current_tool:
            self._current_tool = tool
            self.tool_changed.emit(tool)
    
    def set_tool(self, tool: str):
        if tool in self._buttons:
            self._buttons[tool].setChecked(True)
            self._current_tool = tool
    
    def get_current_tool(self) -> str:
        return self._current_tool
